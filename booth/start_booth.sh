#!/usr/bin/env bash

sleep 4

python booth.py

if [ $? -eq 64 ]
then
    sudo shutdown now -h
elif [ $? -eq 65 ]
then
    sudo reboot
fi
