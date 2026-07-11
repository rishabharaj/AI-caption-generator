#!/bin/bash
# Ensure apt-installed shared libraries are found by the dynamic linker
export LD_LIBRARY_PATH="/app/.apt/usr/lib/x86_64-linux-gnu:/app/.apt/usr/lib:/app/.apt/lib/x86_64-linux-gnu:/app/.apt/lib/pulseaudio${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export PATH="/app/.apt/usr/bin:$PATH"
