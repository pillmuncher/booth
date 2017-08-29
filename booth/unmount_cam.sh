#!/usr/bin/env bash

set -o nounset
sleep 9
gmount=$( gvfs-mount -l  |  sed -n '/gphoto2:/ {s/.* //p; q}' )
if [ $gmount ]
then
    echo "Kamera $gmount wird ausgehängt."
    gvfs-mount -u  "$gmount"
    sleep 0.5
else
    echo "Kamera ist nicht eingehängt."
fi
