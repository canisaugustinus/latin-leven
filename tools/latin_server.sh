#!/bin/bash
ptyxis -- /bin/sh -c 'distrobox enter mintbox -- python3 /var/home/$USER/Documents/code/latin-leven/wiktionary_latin_py/wiktionary_latin.py distrobox-host-exec flatpak run org.mozilla.firefox http://localhost:5000/'
