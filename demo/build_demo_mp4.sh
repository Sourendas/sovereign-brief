#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${OUT:-$ROOT/demo/sovereign-brief-demo.mp4}"
FONT="${FONT:-/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf}"
FONTB="${FONTB:-/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf}"
if ! command -v ffmpeg >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  sudo -E apt-get update
  sudo -E apt-get install -y ffmpeg
fi
mkdir -p "$(dirname "$OUT")"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

tf() {
  local id="$1" y="$2" size="$3" color="$4" font="$5" text="$6"
  printf '%s' "$text" > "$WORK/$id.txt"
  printf "drawtext=textfile=%s:fontfile=%s:fontsize=%s:fontcolor=%s:x=64:y=%s" \
    "$WORK/$id.txt" "$font" "$size" "$color" "$y"
}

render() {
  local dur="$1" name="$2"
  shift 2
  local vf="drawbox=x=0:y=0:w=1280:h=8:color=0x3d9cf0:t=fill"
  local i=0
  while [[ $# -gt 0 ]]; do
    i=$((i+1))
    vf="${vf},$(tf "$name$i" "$1" "$2" "$3" "$4" "$5")"
    shift 5
  done
  ffmpeg -y -hide_banner -loglevel error -f lavfi -i "color=c=0x0f1419:s=1280x720:d=${dur}:r=24" \
    -vf "$vf" -frames:v $((dur*24)) \
    -c:v libx264 -profile:v high -pix_fmt yuv420p -crf 28 -preset veryfast \
    "$WORK/$name.mp4" >/dev/null
}

render 6 s1 \
  40 22 0x3d9cf0 "$FONTB" "HACK APERTUS 2026  ·  TRACK 2B OWN PROJECT" \
  90 40 0xe7ecf3 "$FONTB" "SovereignBrief" \
  200 30 0xe7ecf3 "$FONT" "Paste a policy or ops memo." \
  260 30 0xe7ecf3 "$FONT" "Apertus returns a summary and five next actions." \
  340 26 0x9aa8bc "$FONT" "This cut shows the saved sample brief, not a new model call." \
  400 26 0x9aa8bc "$FONT" "Static demo: sourendas.github.io/sovereign-brief" \
  460 26 0x9aa8bc "$FONT" "Local UI: uvicorn main:app  ·  static/index.html" \
  650 22 0x9aa8bc "$FONT" "Owner: Souren Das  ·  GitHub Sourendas  ·  Not a Devpost submission"

render 8 s2 \
  40 22 0x3d9cf0 "$FONTB" "SAMPLE DOCUMENT" \
  90 40 0xe7ecf3 "$FONTB" "Contoso Municipal Ops memo" \
  145 22 0x9aa8bc "$FONT" "From samples/sample_policy.txt · comments due Friday" \
  220 26 0xe7ecf3 "$FONT" "Subject: Draft update to remote vendor access & document" \
  265 26 0xe7ecf3 "$FONT" "retention (comments due Fri)." \
  330 26 0xe7ecf3 "$FONT" "HelpdeskPro stores tickets in a US region by default." \
  375 26 0xe7ecf3 "$FONT" "FormFlow can pin EU storage but it is not enabled." \
  420 26 0xe7ecf3 "$FONT" "CloudOCR is used ad-hoc with personal emails." \
  480 26 0xe7ecf3 "$FONT" "Proposed effective date: 1 Nov 2026. Backlog: about 18,000 PDFs." \
  540 26 0xe7ecf3 "$FONT" "Asks: approve the date, accept a HelpdeskPro attachment pause," \
  585 26 0xe7ecf3 "$FONT" "and nominate owners for retention jobs and Hindi privacy-notice QA."

render 7 s3 \
  40 22 0x3d9cf0 "$FONTB" "SAVED APERTUS BRIEF" \
  90 36 0xe7ecf3 "$FONTB" "Summary from the 2 Oct 2026 run" \
  150 22 0x9aa8bc "$FONT" "Model: swiss-ai/Apertus-8B-Instruct-2509 via the Hugging Face router (Public AI)." \
  190 22 0x9aa8bc "$FONT" "swiss-ai/Apertus-v1.5-8B was not on the router. No new inference call in this video." \
  280 22 0x3d9cf0 "$FONTB" "Summary" \
  340 32 0xe7ecf3 "$FONTB" "Draft update to remote vendor access & document" \
  390 32 0xe7ecf3 "$FONTB" "retention (comments due Fri)." \
  520 22 0x9aa8bc "$FONT" "Risks, decisions, and open questions were not stored, so they are not shown."

render 9 s4 \
  40 22 0x3d9cf0 "$FONTB" "SAVED BRIEF OUTCOME" \
  95 40 0xe7ecf3 "$FONTB" "Five next actions" \
  190 26 0xe7ecf3 "$FONT" "1  Confirm approval of Nov 1 effective date by Friday" \
  270 26 0xe7ecf3 "$FONT" "2  Accept HelpdeskPro pause as interim risk control" \
  350 26 0xe7ecf3 "$FONT" "3  Nominate owners for retention jobs and Hindi privacy-notice QA" \
  430 26 0xe7ecf3 "$FONT" "4  Schedule training for front-desk staff" \
  510 26 0xe7ecf3 "$FONT" "5  Provide quote for HelpdeskPro migration budget"

render 7 s5 \
  40 22 0x3d9cf0 "$FONTB" "TRY IT" \
  95 40 0xe7ecf3 "$FONTB" "Open demo and source" \
  190 20 0x3d9cf0 "$FONTB" "Static demo" \
  230 28 0xe7ecf3 "$FONT" "https://sourendas.github.io/sovereign-brief/" \
  300 20 0x3d9cf0 "$FONTB" "Repository" \
  340 28 0xe7ecf3 "$FONT" "https://github.com/Sourendas/sovereign-brief" \
  410 20 0x3d9cf0 "$FONTB" "Track" \
  450 28 0xe7ecf3 "$FONT" "2B Own Project · not Track 1 red-team" \
  520 20 0x3d9cf0 "$FONTB" "Built with" \
  560 28 0xe7ecf3 "$FONT" "Python, FastAPI, Apertus 8B Instruct 2509, GitHub Pages" \
  650 22 0x9aa8bc "$FONT" "Deadline 16 Oct 2026 15:30 IST · Draft asset only · not submitted"

ffmpeg -y -hide_banner -loglevel error \
  -i "$WORK/s1.mp4" -i "$WORK/s2.mp4" -i "$WORK/s3.mp4" -i "$WORK/s4.mp4" -i "$WORK/s5.mp4" \
  -filter_complex "[0:v][1:v][2:v][3:v][4:v]concat=n=5:v=1:a=0,fps=24,format=yuv420p" \
  -c:v libx264 -profile:v high -pix_fmt yuv420p -crf 28 -preset veryfast -movflags +faststart \
  "$OUT"
ffprobe -v error -show_entries format=duration,size -show_entries stream=codec_name,width,height,pix_fmt -of default=nw=1 "$OUT"
