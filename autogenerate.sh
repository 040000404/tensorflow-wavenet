#!/bin/bash

tempArr=(0.8 0.9)       # temperature array
silenceArr=(1.0 5.0)    # silence_threshold array

genItemLength=$(( ${#tempArr[@]} * ${#silenceArr[@]} ))
genStep=0

# generate 정보 출력
echo -e "Start Generating for ${genItemLength} items\n"
echo -e "TempArr : ${tempArr[@]}"
echo -e "silenceArr : ${silenceArr[@]}\n"

# for loop 두 번 돌리는 부분.
# 아래와 같이 각 라인에 \를 넣어주면 여러 줄의 명령을 한 번에 실행할 수 있습니다.
# generate_w_silence.py를 사용한 것은 silence_threshold를 args로 받기 위함입니다.

for t in ${tempArr[@]};
do
    for s in ${silenceArr[@]};
    do
        echo "Generating ${genStep} : t=${t} s=${s}"
        trainStep=$((genStep + 1))

        python3 generate.py \
        --wav_out_path=generated/0730/2008trim-160000samples_wav_seed_19-16-L-end-t_${t}-s_${s}.wav \
        --wav_seed=seed/16-19-L-end.wav \
         --temperature=${t} \
         --samples 160000 \
         logdir/train/2020-07-24T03-29-23/model.ckpt-99999 > ./generated/0730/log_${t}_${s}_L.txt

         python3 generate.py \
        --wav_out_path=generated/0730/2008trim-160000samples_wav_seed_19-16-R-end-t_${t}-s_${s}.wav \
        --wav_seed=seed/16-19-R-end.wav \
         --temperature=${t} \
         --samples 160000 \
         logdir/train/2020-07-24T03-29-23/model.ckpt-99999 > ./generated/0730/log_${t}_${s}_R.txt

    done;
done;
