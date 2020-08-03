from __future__ import division
from __future__ import print_function

import argparse
from datetime import datetime
import json
import os
import warnings

import librosa
import numpy as np
import tensorflow as tf

from wavenet import WaveNetModel, mu_law_decode, mu_law_encode, audio_reader

import dynamic_changer as dynamic

SAMPLES = 16000
TEMPERATURE = 1.0
TEMP_CHANGE = None
LOGDIR = './logdir'
WAVENET_PARAMS = 'wavenet_params_new.json'
SAVE_EVERY = None
SILENCE_THRESHOLD = 0.1

def get_arguments():
    def _str_to_bool(s):
        """Convert string to bool (in argparse context)."""
        if s.lower() not in ['true', 'false']:
            raise ValueError('Argument needs to be a '
                             'boolean, got {}'.format(s))
        return {'true': True, 'false': False}[s.lower()]

    def _ensure_positive_float(f):
        """Ensure argument is a positive float."""
        if float(f) < 0:
            raise argparse.ArgumentTypeError(
                    'Argument must be greater than zero')
        return float(f)

    parser = argparse.ArgumentParser(description='WaveNet generation script')
    parser.add_argument(
        'checkpoint', type=str, help='Which model checkpoint to generate from')
    parser.add_argument(
        '--samples',
        type=int,
        default=SAMPLES,
        help='How many waveform samples to generate')
    parser.add_argument(
        '--temperature',
        type=_ensure_positive_float,
        default=TEMPERATURE,
        help='Sampling temperature')
    parser.add_argument(
        '--logdir',
        type=str,
        default=LOGDIR,
        help='Directory in which to store the logging '
        'information for TensorBoard.')
    parser.add_argument(
        '--wavenet_params',
        type=str,
        default=WAVENET_PARAMS,
        help='JSON file with the network parameters')
    parser.add_argument(
        '--wav_out_path',
        type=str,
        default=None,
        help='Path to output wav file')
    parser.add_argument(
        '--save_every',
        type=int,
        default=SAVE_EVERY,
        help='How many samples before saving in-progress wav')
    parser.add_argument(
        '--fast_generation',
        type=_str_to_bool,
        default=True,
        help='Use fast generation')
    parser.add_argument(
        '--wav_seed',
        type=str,
        default=None,
        help='The wav file to start generation from')
    parser.add_argument(
        '--temperature_change',
        type=str,
        default=TEMP_CHANGE,
        help='Change the temperature dynamically during generation.')
    parser.add_argument(
        '--silence_threshold',
        type=str,
        default=SILENCE_THRESHOLD,
        help='The threshold of silence.')
    parser.add_argument(
        '--silence_change',
        type=str,
        default=TEMP_CHANGE,
        help='Change the silence dynamically during generation.')

    #additional arguments for dynamic_changer
    parser.add_argument('--tform', type=str, default=None)
    parser.add_argument('--tmin', type=float, default=0)
    parser.add_argument('--tmax', type=float, default=1)
    parser.add_argument('--tperiod', type=float, default=1)

    arguments = parser.parse_args()
    return arguments

def write_wav(waveform, sample_rate, filename):
    y = np.array(waveform)
    librosa.output.write_wav(filename, y, sample_rate)
    print('Updated wav file at {}'.format(filename))

def create_seed(filename,
                sample_rate,
                quantization_channels,
                window_size,
                silence_threshold):
    audio, _ = librosa.load(filename, sr=sample_rate, mono=True)
    audio = audio_reader.trim_silence(audio, silence_threshold)

    quantized = mu_law_encode(audio, quantization_channels)
    cut_index = tf.cond(tf.size(quantized) < tf.constant(window_size),
                        lambda: tf.size(quantized),
                        lambda: tf.constant(window_size))

    return quantized[:cut_index]

def main():
    args = get_arguments()
    started_datestring = "{0:%Y-%m-%dT%H-%M-%S}".format(datetime.now())
    logdir = os.path.join(args.logdir, 'generate', started_datestring)
    
    # open wavenet_params file
    if args.wavenet_params.startswith('wavenet_params_'):
        with open(args.wavenet_params, 'r') as config_file:
            wavenet_params = json.load(config_file)
    else:
        with open('wavenet_params_'+args.wavenet_params, 'r') as config_file:
            wavenet_params = json.load(config_file)    

    sess = tf.Session()

    net = WaveNetModel(
        batch_size=1,
        dilations=wavenet_params['dilations'],
        filter_width=wavenet_params['filter_width'],
        residual_channels=wavenet_params['residual_channels'],
        dilation_channels=wavenet_params['dilation_channels'],
        quantization_channels=wavenet_params['quantization_channels'],
        skip_channels=wavenet_params['skip_channels'],
        use_biases=wavenet_params['use_biases'],
        scalar_input=wavenet_params['scalar_input'],
        initial_filter_width=wavenet_params['initial_filter_width'],
        global_condition_channels=None,
        global_condition_cardinality=None)

    samples = tf.placeholder(tf.int32)

    if args.fast_generation:
        next_sample = net.predict_proba_incremental(samples, None)
    else:
        next_sample = net.predict_proba(samples, None)

    if args.fast_generation:
        sess.run(tf.global_variables_initializer())
        sess.run(net.init_ops)

    variables_to_restore = {
        var.name[:-2]: var for var in tf.global_variables()
        if not ('state_buffer' in var.name or 'pointer' in var.name)}
    saver = tf.train.Saver(variables_to_restore)

    print('Restoring model from {}'.format(args.checkpoint))
    saver.restore(sess, args.checkpoint)

    decode = mu_law_decode(samples, wavenet_params['quantization_channels'])

    quantization_channels = wavenet_params['quantization_channels']
    if args.wav_seed:
        seed = create_seed(args.wav_seed,
                           wavenet_params['sample_rate'],
                           quantization_channels,
                           net.receptive_field,
                           args.silence_threshold)
        waveform = sess.run(seed).tolist()
    else:
        # Silence with a single random sample at the end.
        waveform = [quantization_channels / 2] * (net.receptive_field - 1)
        waveform.append(np.random.randint(quantization_channels))

    if args.fast_generation and args.wav_seed:
        # When using the incremental generation, we need to
        # feed in all priming samples one by one before starting the
        # actual generation.
        # TODO This could be done much more efficiently by passing the waveform
        # to the incremental generator as an optional argument, which would be
        # used to fill the queues initially.
        outputs = [next_sample]
        outputs.extend(net.push_ops)

        print('Priming generation...')
        for i, x in enumerate(waveform[-net.receptive_field: -1]):
            if i % 100 == 0:
                print('Priming sample {}'.format(i))
            sess.run(outputs, feed_dict={samples: x})
        print('Done.')

    last_sample_timestamp = datetime.now()
    for step in range(args.samples):
        if args.fast_generation:
            outputs = [next_sample]
            outputs.extend(net.push_ops)
            window = waveform[-1]
        else:
            if len(waveform) > net.receptive_field:
                window = waveform[-net.receptive_field:]
            else:
                window = waveform
            outputs = [next_sample]

        # Run the WaveNet to predict the next sample.
        prediction = sess.run(outputs, feed_dict={samples: window})[0]

        # Scale prediction distribution using temperature.
        np.seterr(divide='ignore')

        # temperature change by every 1/5 samples

        if args.temperature_change == None: #static
            _temp_temperature = args.temperature
        elif args.temperature_change == "dynamic":
            if args.tform == None: #random
                if step % int(args.samples/5) == 0:
                    _temp_temperature = args.temperature * np.random.rand()
            elif args.tform == "sine": #sine
                _temp_temperature = dynamic.sine(args.tmin, args.tmax, args.tperiod, step, args.samples)
            elif args.tform == "square": #square
                _temp_temperature = dynamic.square(args.tmin, args.tmax, args.tperiod, step, args.samples)                  
        else:
                raise Exception("wrong temperature_change value")

        scaled_prediction = np.log(prediction) / _temp_temperature
        scaled_prediction = (scaled_prediction -
                             np.logaddexp.reduce(scaled_prediction))
        scaled_prediction = np.exp(scaled_prediction)
        np.seterr(divide='warn')

        # Prediction distribution at temperature=1.0 should be unchanged after
        # scaling.
        if args.temperature == 1.0 and args.temperature_change == None:
            np.testing.assert_allclose(
                    prediction, scaled_prediction, atol=1e-5,
                    err_msg = 'Prediction scaling at temperature=1.0 is not working as intended.')

        sample = np.random.choice(
            np.arange(quantization_channels), p=scaled_prediction)
        waveform.append(sample)

        # Show progress only once per second.
        current_sample_timestamp = datetime.now()
        time_since_print = current_sample_timestamp - last_sample_timestamp
        if time_since_print.total_seconds() > 1.:
            print('Sample {:3<d}/{:3<d}, temperature {:3<f}'.format(step + 1, args.samples, _temp_temperature),
                  end='\r')
            last_sample_timestamp = current_sample_timestamp

        # If we have partial writing, save the result so far.
        if (args.wav_out_path and args.save_every and
                (step + 1) % args.save_every == 0):
            out = sess.run(decode, feed_dict={samples: waveform})
            write_wav(out, wavenet_params['sample_rate'], args.wav_out_path)

    # Introduce a newline to clear the carriage return from the progress.
    print()

    # Save the result as an audio summary.
    datestring = str(datetime.now()).replace(' ', 'T')
    writer = tf.summary.FileWriter(logdir)
    tf.summary.audio('generated', decode, wavenet_params['sample_rate'])
    summaries = tf.summary.merge_all()
    summary_out = sess.run(summaries,
                           feed_dict={samples: np.reshape(waveform, [-1, 1])})
    writer.add_summary(summary_out)

    # Save the result as a wav file.
    if args.wav_out_path:
        out = sess.run(decode, feed_dict={samples: waveform})
        write_wav(out, wavenet_params['sample_rate'], args.wav_out_path)

    print('Finished generating. The result can be viewed in TensorBoard.')


if __name__ == '__main__':
    main()