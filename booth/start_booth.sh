#!/usr/bin/env bash

set -o nounset

# hier bitte die Bezeichnung eintragen, nach der bei 'gvfs-mount --list'
# gesucht werden soll
KameraBezeichnung="Canon Digital Camera"

# Pruefung, ob die Kamera gemountet ist
# Input: Kameramodell gemaess "gvfs-mount --list"
# RC: 0 - online; <anderer RC> - nicht online
KameraOnline() {
    Kamera="${1}"
    echo "* pruefen, ob Kamera '${Kamera}' verbunden ist..."
    gvfs-mount --list | grep -q "${Kamera}.*gphoto2"
    RC=${?}
    if [[ ${RC} -eq 0 ]]
    then
        echo "  * verbunden"
    else
        echo "  * nicht verbunden"
    fi
    return ${RC}
}

### MAIN ###

# ermitteln, ob Kamera verbunden ist
KameraOnline "${KameraBezeichnung}"
if [[ ${?} -eq 0 ]]
then
    # Mountpunkt ermitteln
    echo "* Mountpunkt ermitteln..."
    MountPunkt=$(gvfs-mount --list | grep "${KameraBezeichnung}.*gphoto" | sed 's|^.*\(gphoto2://.*\)$|\1|g' | sort -u | head -n 1)
    echo "  * Mountpunkt: '${MountPunkt}'"

    # Kamera unmounten
    echo "* Kamera '${KameraBezeichnung}' unmounten..."
    gvfs-mount --unmount "${MountPunkt}"

    # kurz warten und noch einmal mount pruefen
    ping -c 2 localhost > /dev/null 2>&1
    KameraOnline "${KameraBezeichnung}"
fi

python booth.py

if [ $? -eq 64 ]
then
    sudo shutdown now -h
elif [ $? -eq 65 ]
then
    sudo reboot
fi
