#!/usr/bin/env bash
# Cuts the raw footage (docs/demo) into the 1920x1080 pieces the film uses (film/assets/clips).
# Run from the repo root: bash film/tools/prep_clips.sh
set -euo pipefail
BEF=docs/demo/before-no-gate-claude-upload.mp4
BR=docs/demo/broll
O=film/assets/clips
mkdir -p "$O"
ENC=(-an -c:v libx264 -preset medium -crf 17 -pix_fmt yuv420p -r 30 -g 15)
SCR="crop=3420:1924:0:200,scale=1920:1080:flags=lanczos"
b() { ls $BR/broll-$1-*.mp4 | head -1; }

ffmpeg -loglevel error -y -ss 0.3 -t 4.0 -i "$(b 4)" -vf "scale=1920:1080:flags=lanczos" "${ENC[@]}" $O/A1.mp4 &
ffmpeg -loglevel error -y -ss 0.3 -t 2.6 -i "$(b 4)" -vf "scale=1920:1080:flags=lanczos" "${ENC[@]}" $O/A1s.mp4 &   # short cut, only for the rewind/replay
ffmpeg -loglevel error -y -ss 10 -t 10.3 -i $BEF -vf "$SCR,setpts=PTS/3.5" "${ENC[@]}" $O/B.mp4 &
ffmpeg -loglevel error -y -ss 0 -t 2.8 -i "$(b 1)" -vf "scale=1920:1080:flags=lanczos" "${ENC[@]}" $O/A2.mp4 &
ffmpeg -loglevel error -y -ss 20.5 -t 2.5 -i $BEF -vf "$SCR" "${ENC[@]}" $O/C.mp4 &
ffmpeg -loglevel error -y -i "$(b 2)" -vf "scale=1920:1080:flags=lanczos" "${ENC[@]}" $O/D.mp4 &
ffmpeg -loglevel error -y -ss 24 -t 2.9 -i $BEF -vf "$SCR" "${ENC[@]}" $O/E.mp4 &
wait
for f in $O/*.mp4; do echo "$f $(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f")"; done

# --- the rewind and the 2x replay of part 1 (built from the short opening shot) ---
LIST=$(mktemp); for n in A1s B A2 C D E; do echo "file '$PWD/$O/$n.mp4'"; done > "$LIST"
P1=$(mktemp -t p1).mp4
ffmpeg -loglevel error -y -f concat -safe 0 -i "$LIST" -an -c:v libx264 -crf 14 -pix_fmt yuv420p -r 30 "$P1"
ffmpeg -loglevel error -y -i "$P1" -vf "setpts=PTS/2" "${ENC[@]}" $O/replay.mp4
ffmpeg -loglevel error -y -i "$P1" -vf "scale=960:540,reverse,setpts=PTS/6,noise=alls=28:allf=t,eq=saturation=1.6:contrast=1.15,scale=1920:1080:flags=neighbor,drawgrid=w=0:h=6:t=2:c=black@0.35" "${ENC[@]}" $O/rewind.mp4
ffmpeg -loglevel error -y -sseof -0.04 -i $O/E.mp4 -frames:v 1 $O/E_last.png

# --- screen recordings of the app (film/assets/recordings, made with Playwright from the running stack) ---
for f in film/assets/recordings/*.webm; do n=$(basename "$f" .webm); ffmpeg -loglevel error -y -i "$f" "${ENC[@]}" "$O/$n.mp4"; done
echo "clips ready"
