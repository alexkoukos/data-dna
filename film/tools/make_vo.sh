#!/usr/bin/env bash
# Scratch voiceover with the macOS voice "Daniel" (swap any assets/vo/vNN.wav for a real recording; keep the file name).
set -euo pipefail
cd "$(dirname "$0")/.."
V=Daniel; R=${RATE:-158}
say_line() { say -v "$V" -r "$R" -o "assets/vo/$1.aiff" "$2"; ffmpeg -loglevel error -y -i "assets/vo/$1.aiff" -ar 44100 -ac 1 -af "loudnorm=I=-16:TP=-1.5:LRA=7" "assets/vo/$1.wav"; rm "assets/vo/$1.aiff"; echo "$1 $(ffprobe -v error -show_entries format=duration -of csv=p=0 assets/vo/$1.wav)"; }
say_line v1 "Every company has a document that must never leave."
say_line v2 "One click is all it takes."
say_line v3 "Let's try that again."
say_line v4 "Same document. Same A I. Same click. But this time, Hive is watching."
say_line v5 "Meet Hive."
say_line v6 "It lives in your browser, and checks every prompt before it leaves."
say_line v7 "Sensitive data is masked. Attacks are blocked."
say_line v8 "Even a reworded secret is caught, by meaning."
say_line v9 "Your security team sees every decision, without ever seeing the data."
say_line v10 "Detection runs locally. Nothing leaves your machine. One docker compose, and you're live."
say_line v11 "Hive. Your data is the honey. We guard the gate."
RATE_FAST=170
R=$RATE_FAST say_line v12 "Seventy-seven percent of A I users paste company data. Shadow A I adds six hundred seventy thousand dollars to the average breach."
R=$RATE_FAST say_line v13 "Nine euros per user. A I included. Cheaper than ChatGPT Business, and every message is checked."
R=$RATE_FAST say_line v14 "A one point one billion euro market in Europe. Sixty-nine customers by twenty twenty-nine."
