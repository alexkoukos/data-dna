# The Hive demo film

The finished film is [`docs/demo/hive-film.mp4`](../docs/demo/hive-film.mp4) (1:44, 1920x1080). This folder is the source: a [HyperFrames](https://hyperframes.heygen.com) project, with HTML scenes animated by GSAP and rendered to MP4.

## What the film shows

| Time | Part | Source |
|---|---|---|
| 0:00–0:24 | The problem: the restricted Akryon PDF goes into a personal Claude account, Enter, freeze. "This is Shadow AI." | `docs/demo/before-no-gate-claude-upload.mp4`, `docs/demo/broll/` |
| 0:24–0:33 | Why it matters: 77% paste company data (LayerX 2025), +$670K per breach (IBM 2025) | Text |
| 0:33–0:45 | Rewind, then the same steps again at 2x | The same footage |
| 0:45–1:12 | Hive: the landing page demo (masked, blocked), prompt injection blocked, reworded memo caught, the security view | `assets/recordings/` (the real app) |
| 1:12–1:21 | How it works: extension, local detection, block/redact/log | Text |
| 1:21–1:35 | The business: price against ChatGPT Business, market, plan | Numbers from `business/model.py` |
| 1:35–1:44 | Team, logo, "Your data is the honey. We guard the gate." | `assets/brand/` |

Everything on screen is real footage, a real recording of the app, or the brand files. The music and sounds are made from sine waves and noise in `tools/make_audio.py`. Fonts are the website's own: Plus Jakarta Sans, Playfair Display and Poppins.

## Placeholders to replace

- **Voice.** `assets/vo/v1.wav` to `v14.wav` are a scratch track made with the macOS voice "Daniel" (`tools/make_vo.sh` has every line). Record the same lines and save them under the same names.
- **Team.** The team slide shows initials. Add a team clip as `assets/clips/H.mp4` (see the comment in `index.html`).
- **Extension on claude.ai.** The Hive part uses the landing page and the company chat. A screen recording of the extension blocking the PDF on claude.ai would be stronger.

## Build it

You need Node.js 18+, ffmpeg and Python 3 with `numpy`. Run from the repo root unless noted.

```bash
make up                                      # the app, for the recordings
cd film && npm i --no-save playwright && npx playwright install chromium
node tools/record_app.mjs                    # optional: re-record assets/recordings/*.webm
cd .. && bash film/tools/prep_clips.sh       # footage -> film/assets/clips/*.mp4
cd film && python3 tools/make_audio.py       # music and sounds -> assets/bgm, assets/sfx
ffmpeg -y -i assets/bgm/upbeat.wav -t 61 -af afade=t=out:st=58.5:d=2.5 assets/bgm/upbeat-cut.wav
ffmpeg -y -i assets/bgm/tense.wav -t 15.45 -af afade=t=out:st=15.1:d=0.35 assets/bgm/tense-cut.wav
npm run check                                # 0 errors
npm run render                               # renders/hive-film.mp4, about 30 minutes
```

Keep HyperFrames at exactly `0.9.34` so the film renders the same everywhere.

## What is where

| Path | What |
|---|---|
| `index.html` | The whole film: every shot, caption, zoom and sound, with its start time |
| `tools/prep_clips.sh` | Cuts the raw footage and recordings into 1920x1080 clips, builds the rewind and the replay |
| `tools/record_app.mjs` | Records the app clips from the running stack with Playwright |
| `tools/make_audio.py` | Makes the music, typewriter, bass hits, rewind and chimes |
| `tools/make_vo.sh` | The voiceover lines and the scratch voice |
