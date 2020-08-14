#!/bin/sh
APP_LIST = "git nano curl python3 python3-pip"

apt-get update  # To get the latest package lists
apt-get install -y $APP_LIST #install packages listed in APP_LIST
pip3 install -U pip #upgrade pip
alias python=python3 #make python command to use python3

pip install -r requirements_gpu.txt
