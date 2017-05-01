#!/usr/bin/env bash

set -o nounset

gname=$( gvfs-mount -l  |  sed -n '/gphoto2:/ {s/.* //p; q}' )
if [[ "$gname" = "" ]]
then
    echo "Kamera ist nicht eingehängt."
else
    echo "Der Mountname ist $gname."
    echo "Kamera wird ausgehängt."
    gvfs-mount -u  "$gname"
    sleep 0.5
fi

python booth.py

if [ $? -eq 64 ]
then
    sudo shutdown now -h
elif [ $? -eq 65 ]
then
    sudo reboot
fi
