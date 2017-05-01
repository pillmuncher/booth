#!/usr/bin/env bash

set -o nounset

set gmount=$( gvfs-mount -l  |  sed -n '/gphoto2:/ {s/.* //p; q}' )
echo "Die Kamera ist unter $gmount eingehängt."
if [ "$gmount" = "" ]
then
    echo "Kamera ist nicht eingehängt."
else
    echo "Kamera $gmount wird ausgehängt."
    # gvfs-mount -u  "$gmount"
    # sleep 0.5
fi

# python booth.py

# if [ $? -eq 64 ]
# then
    # sudo shutdown now -h
# elif [ $? -eq 65 ]
# then
    # sudo reboot
# fi
