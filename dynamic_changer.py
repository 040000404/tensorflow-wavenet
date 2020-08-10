
import numpy as np
import matplotlib.pyplot as plt
import terminalplot as tplt
import argparse

FORM = "sine"
PERIOD = 1

def get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--form', type=str, default=FORM)
    parser.add_argument('--min', type=float, default=0)
    parser.add_argument('--max', type=float, default=1)
    parser.add_argument('--period', type=float)
    parser.add_argument('--frequency', type=float, default=None)
    parser.add_argument('--graph', type=str, default="graphic")
    
    return parser.parse_args()

def frequency_to_period(frequency):
    return 1/frequency

def wave(form, min, max, period, step, samplerate, samplesize):
    axis = (min+max)/2
    input = (np.pi*2/period) / samplerate * step #x value mapped into 2*pi
    if form == "sine":
        return sine(min, max, axis, input)
    elif form == "square":
        if sine(min, max, axis, input) >= axis:
            return max
        elif sine(min, max, axis, input) < axis:
            return min
    elif form == "triangle":
        return triangle(min, max, axis, input)
    else: 
        raise Exception("wrong value on --form")

def sine(min, max, axis, input):
    range = max-min
    if range <= 0:
        raise Exception("wrong range of min-max")
    return (np.sin(input)*0.5*range+axis)

def triangle(min, max, axis, input):
    temp_period = (np.pi*2)*np.floor(input/(np.pi*2))
    if input%(np.pi*2) < np.pi*0.5:
        return((max-axis)/(0.5*np.pi)*(input-temp_period))+axis
    elif input%(np.pi*2) < np.pi*1.5:
        return((min-max)/(np.pi)*(input-(0.5*np.pi)-temp_period))+max
    elif input%(np.pi*2) < np.pi*2:
        return((axis-min)/(0.5*np.pi)*(input-(1.5*np.pi)-temp_period))+min

def generate_value(step, samplerate, form, _min, _max, period, samplesize):
    #array for graph plot
    x_array = []
    y_array = []
    arrays = [x_array, y_array]

    # outputs y_value as each x_value (step)
    for x in range(samplesize):
        x_array.append(step)
        y_array.append(wave(form, _min, _max, period, step, samplerate, samplesize))         
        step += 1
    return arrays

def generate_graph(arrays, graph):   
    #get x, y values to draw a graph
    x_array = arrays[0]
    y_array = arrays[1]

    #determine if show graph or not
    if graph == "graphic": #generates new graphic window with matplotlib
        plt.scatter(x_array, y_array, color="green", marker="1", s=30)
        plt.xlabel('x_axis')
        plt.ylabel('y_axis')
        plt.title('plot')
        plt.show()
    elif graph == "terminal": #draw graph in terminal
        tplt.plot(x_array, y_array)
    elif graph == None:
        warning.warn("Graph type is assigned. No graph will be shown.")

def main():
    args = get_arguments()

    #set some arbitary values for step and samplerate
    # these values will be replaced with real values in generate.py
    step = 0
    samplerate = 16000
    samplesize = 17000
    if args.frequency is not None:
        if args.period is not None:
            raise ValueError("Frequency and Period both assigned. Assign only one of them.")
        else: #change frequency into period
            PERIOD = frequency_to_period(args.frequency)
    else: #get period input value
        try:
            PERIOD = args.period
            if PERIOD is None:
                raise TypeError
        except TypeError:
            PERIOD = 1

    generate_graph(generate_value(step, samplerate, args.form, args.min, args.max, PERIOD, samplesize), args.graph)

if __name__ == '__main__':
    main()
