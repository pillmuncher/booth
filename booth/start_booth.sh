#!/usr/bin/env bash

set -o nounset

gmount=$( gvfs-mount -l  |  sed -n '/gphoto2:/ {s/.* //p; q}' )
if [[ "$gmount" = "" ]]
then
    echo "Kamera ist nicht eingehängt."
else
    echo "Der Mountname ist $gname"
    gvfs-mount -u  "$gmount"
    sleep 0.1
fi

python booth.py

if [ $? -eq 64 ]
then
    sudo shutdown now -h
elif [ $? -eq 65 ]
then
    sudo reboot
fi
