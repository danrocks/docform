# DocForm onboarding videos

Short, dense, narrated walkthroughs that introduce new users to key DocForm
features. This folder holds the finished videos, the narration scripts, and the
tooling to regenerate them — plus the **house style** below so future videos
match the look, pacing, and voice ("timbre") of the existing set.

## The videos

| # | File | Feature | ~Length |
|---|------|---------|---------|
| 1 | [`videos/01-global-search.mp4`](videos/01-global-search.mp4) | Global search across templates/submissions/answersets | ~16s |
| 2 | [`videos/02-complete-an-interview.mp4`](videos/02-complete-an-interview.mp4) | Complete an interview → generate a document | ~22s |
| 3 | [`videos/03-answersets-bulk-regenerate.mp4`](videos/03-answersets-bulk-regenerate.mp4) | Manage answersets + bulk regenerate | ~15s |
| 4 | [`videos/04-templates-interview-editor.mp4`](videos/04-templates-interview-editor.mp4) | Templates & the interview editor | ~14s |

Each video is a silent screen recording with on-screen caption overlays, plus an
AI voiceover muxed on top. The narration text for each lives in
[`scripts/`](scripts).

> Note: the environment used to record these has **no LibreOffice**, so the
> interview video shows `.docx` download only — PDF is disabled with an
> on-screen note. On a server with LibreOffice, PDF export works too.

---

## House style — how to match the timbre of these videos

Follow these conventions so any new clip feels like part of the same series.

### 1. Framing & capture
- **Resolution:** record at **1024×768**, browser **maximized** (no half-open
  or partially covered windows).
- **App state:** run locally, logged in as `admin` on the `demo` tenant, with the
  standard seeded data (Acme Service Agreement + Monthly Invoice templates and a
  few generated answersets). See `.agents/skills/testing-docform/SKILL.md` for
  startup + seeding.
- **Start clean:** begin each recording from a neutral page (usually the
  Dashboard or the feature's list page), not mid-flow.

### 2. Scope — one feature per clip
- Keep each clip **~15–25 seconds** and focused on a **single workflow**.
- Show the *golden path* a new user would take; skip edge cases and admin-only
  config. This is onboarding, not regression testing.

### 3. On-screen captions (annotations)
- Add **~5 caption beats** per clip, one per meaningful step (open the page →
  do the action → see the result).
- Voice: **second person, imperative, benefit-led** — e.g.
  *"Click any result to jump straight to it."* Keep each caption **under ~80
  characters**.
- The captions and the voiceover should say the *same thing* in the same order.

### 4. Voiceover ("timbre")
- **Engine:** [Piper](https://github.com/rhasspy/piper) neural TTS.
- **Voice model:** `en_US-lessac-medium` (calm, neutral US English). Keep this
  exact voice for consistency across the series.
- **Tone:** friendly, confident, concise. No filler ("basically", "just want
  to"), no marketing hype.
- **Pacing:** target the clip length. Piper `lessac-medium` speaks ~**3
  words/second**, so budget roughly:
  - 15s clip → ~38 words · 20s clip → ~50 words.
- **Tips:** spell tricky terms phonetically in the script (e.g. write `I D` so
  "ID" is read as letters). End on the payoff ("…in one click, every document is
  refreshed.").

### 5. Assembly
- Narration is muxed with a **0.4s lead-in** and a **0.5s tail** so the voice
  never feels clipped.
- If narration is longer than the video, the **last frame is held** (ffmpeg
  `tpad`) rather than speeding up the footage.
- Output: H.264 (`yuv420p`) video + AAC 128k audio `.mp4`.

---

## Regenerating the voiceover

Silent source recordings are produced with the screen recorder while following
the house style above. To (re)generate the narration and mux it on:

```bash
# 1. Install tooling
pip install piper-tts            # ffmpeg/ffprobe must already be installed

# 2. Get the voice model (once)
mkdir -p ~/piper_voices && cd ~/piper_voices
BASE=https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium
curl -sL -O $BASE/en_US-lessac-medium.onnx
curl -sL -O $BASE/en_US-lessac-medium.onnx.json

# 3. Edit the scripts in docs/onboarding/scripts/*.txt, then:
cd docs/onboarding/scripts
./narrate.sh                     # or: MODEL=/path/to/model.onnx ./narrate.sh
```

`narrate.sh` reads each `scripts/<key>.txt`, synthesizes audio with Piper, and
overwrites `videos/<key>.mp4` with the narrated version.

To change the wording, edit the matching `scripts/*.txt` and re-run. To swap the
voice, download a different Piper model and point `MODEL` at it (but prefer
keeping `lessac-medium` for a consistent series).
