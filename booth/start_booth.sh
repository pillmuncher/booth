#!/usr/bin/env bash

python booth.py

if [ $? -eq 64 ]
then
  sudo shutdown now -h
elif [ $? -eq 65 ]
then
  sudo reboot
fi