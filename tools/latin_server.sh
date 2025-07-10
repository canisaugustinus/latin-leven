#!/bin/bash
ptyxis -- /bin/sh -c 'python /<path_to_repo>/latin-leven/wiktionary_latin_py/wiktionary_latin.py |
  tee /dev/tty | {
    grep -q "Done" && flatpak run org.mozilla.firefox http://localhost:5000/
    cat >/dev/null
  }'

# ptyxis is our terminal
# -- after ptyxis means "execute the following stuff"
# /bin/sh is there so that all the single-quoted commands run together in the new ptyxis window

# tee /dev/tty duplicates npm's output and sends it to both the terminal and the command that follows in the pipeline.

# grep -q silently exits at the first "Done" match with 0 as its status; this triggers the next command in the "&&" list (flatpak run org.mozilla.firefox http://localhost:5000/).

# cat /dev/null is there just to keep the pipe open: grep -q exiting would cause tee to receive a SIGPIPE signal when trying to write further data to the pipe and exit in turn. This cat prevents that by reading from the pipe until npm and tee exit.
