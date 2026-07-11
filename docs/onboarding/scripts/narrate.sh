#!/usr/bin/env bash
#
# Regenerate the AI voiceover for the onboarding videos and mux it onto the
# silent screen recordings. See ../README.md for the full "house style".
#
# Requirements: ffmpeg, ffprobe, piper-tts (pip install piper-tts) and a Piper
# voice model. Defaults to en_US-lessac-medium.
#
# Usage:
#   MODEL=/path/to/en_US-lessac-medium.onnx ./narrate.sh
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"          # .../docs/onboarding/scripts
ROOT="$(cd "$HERE/.." && pwd)"                                # .../docs/onboarding
VIDEOS="$ROOT/videos"
MODEL="${MODEL:-$HOME/piper_voices/en_US-lessac-medium.onnx}" # override via env

# key -> narration script (in this folder). Video is videos/<key>.mp4.
KEYS=(
  "01-global-search"
  "02-complete-an-interview"
  "03-answersets-bulk-regenerate"
  "04-templates-interview-editor"
)

for key in "${KEYS[@]}"; do
  txt="$HERE/${key}.txt"
  vid="$VIDEOS/${key}.mp4"
  wav="$(mktemp --suffix=.wav)"
  out="$VIDEOS/${key}.mp4"        # overwrite in place with narrated version
  tmp_out="$(mktemp --suffix=.mp4)"
  echo "=== $key ==="
  python3 -m piper -m "$MODEL" -f "$wav" < "$txt" 2>/dev/null
  vdur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$vid")
  adur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$wav")
  # Hold the last video frame so nothing is cut off if narration runs long,
  # and add a 0.4s lead-in + 0.5s tail so the voice never feels clipped.
  target=$(python3 -c "print(max($vdur,$adur)+0.5)")
  ffmpeg -y -loglevel error -i "$vid" -i "$wav" \
    -filter_complex "[0:v]tpad=stop_mode=clone:stop_duration=${target}[v];[1:a]adelay=400|400,apad[a]" \
    -map "[v]" -map "[a]" -t "$target" \
    -c:v libx264 -pix_fmt yuv420p -c:a aac -b:a 128k "$tmp_out"
  mv "$tmp_out" "$out"
  rm -f "$wav"
  echo "wrote $out"
done
