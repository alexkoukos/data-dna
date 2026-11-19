"""Synthesises every sound in the film from sine/noise (no samples, no licences): run from film/.
python3 tools/make_audio.py  ->  assets/sfx/*.wav, assets/bgm/tense.wav, assets/bgm/upbeat.wav"""
import wave, numpy as np, pathlib

SR = 44100
rng = np.random.default_rng(7)
out_sfx = pathlib.Path("assets/sfx"); out_sfx.mkdir(parents=True, exist_ok=True)
out_bgm = pathlib.Path("assets/bgm"); out_bgm.mkdir(parents=True, exist_ok=True)

def t(d): return np.arange(int(SR * d)) / SR
def env(n, a=0.005, r=0.2):
    e = np.ones(n); na, nr = int(a * SR), int(r * SR)
    e[:na] = np.linspace(0, 1, na); e[-nr:] = np.linspace(1, 0, nr); return e
def save(path, x, peak=0.9):
    x = x / max(1e-9, np.abs(x).max()) * peak
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
def lp(x, k):  # one-pole low-pass, k in 0..1 (bigger = brighter)
    y = np.zeros_like(x); a = 0.0; k = np.broadcast_to(k, x.shape)
    for i, v in enumerate(x): a += k[i] * (v - a); y[i] = a
    return y

# bass hit: sine drop 90 -> 38 Hz + a little thump noise
d = 1.4; x = t(d); f = 38 + 52 * np.exp(-x * 9)
hit = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 2.6) + 0.25 * lp(rng.standard_normal(len(x)), 0.05) * np.exp(-x * 14)
save(out_sfx / "bass-hit.wav", hit)

# typewriter tick: short click + body, jittered when placed by the timeline
x = t(0.07); tick = (rng.standard_normal(len(x)) * np.exp(-x * 140) * 0.6 + np.sin(2 * np.pi * 1700 * x) * np.exp(-x * 90))
save(out_sfx / "tick.wav", tick)

# mouse click
x = t(0.09); click = np.sin(2 * np.pi * 2300 * x) * np.exp(-x * 120) + rng.standard_normal(len(x)) * np.exp(-x * 220) * 0.5
save(out_sfx / "click.wav", click)

# VHS rewind: noise swept through a rising band + a wobbling whine
d = 2.6; x = t(d); n = rng.standard_normal(len(x))
sweep = 300 + 2600 * (x / d) ** 1.4
whine = np.sin(2 * np.pi * np.cumsum(sweep) / SR) * (0.5 + 0.5 * np.sin(2 * np.pi * 17 * x))
rw = (lp(n, 0.35) * 0.9 + whine * 0.35) * env(len(x), 0.05, 0.35)
save(out_sfx / "rewind.wav", rw)

# whoosh (bee slide-in / diagram steps)
d = 0.7; x = t(d); w = lp(rng.standard_normal(len(x)), 0.06 + 0.5 * (x / d)) * np.sin(np.pi * x / d) ** 1.5
save(out_sfx / "whoosh.wav", w)

# soft chime for "caught"
d = 1.2; x = t(d)
ch = sum(np.sin(2 * np.pi * f * x) * a for f, a in [(880, 1), (1320, .5), (1760, .25)]) * np.exp(-x * 4)
save(out_sfx / "chime.wav", ch)

# alert buzz for "blocked"
d = 0.5; x = t(d); bz = np.sign(np.sin(2 * np.pi * 110 * x)) * 0.5 + np.sin(2 * np.pi * 220 * x) * 0.5
save(out_sfx / "buzz.wav", bz * env(len(x), 0.005, 0.15), 0.6)

# ---- music ----
def kick(n):
    x = t(0.3); f = 45 + 80 * np.exp(-x * 30); k = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 11)
    y = np.zeros(n); y[:len(k)] = k; return y
def hat(open_=False):
    x = t(0.12 if open_ else 0.04); h = rng.standard_normal(len(x)); h = h - lp(h, 0.3)
    return h * np.exp(-x * (28 if open_ else 90))
def place(buf, snd, at, gain=1.0):
    i = int(at * SR); j = min(len(buf), i + len(snd))
    if i < len(buf): buf[i:j] += snd[:j - i] * gain

# tense: 100 bpm, low pulse on 8ths + a ticking hat + a slowly rising drone. 17 s
d = 17.0; N = int(SR * d); tense = np.zeros(N); bpm = 100; beat = 60 / bpm
for k in range(int(d / (beat / 2))):
    at = k * beat / 2; g = 0.55 + 0.4 * (at / d)
    x = t(0.22); note = np.sin(2 * np.pi * 55 * x) * np.exp(-x * 9) + 0.3 * np.sin(2 * np.pi * 110 * x) * np.exp(-x * 14)
    place(tense, note, at, g)
    if k % 2 == 1: place(tense, hat(), at, 0.25 + 0.3 * (at / d))
x = t(d); tense += (np.sin(2 * np.pi * 48 * x) + 0.6 * np.sin(2 * np.pi * 72.4 * x)) * 0.10 * (0.3 + x / d)
save(out_bgm / "tense.wav", tense * env(N, 0.2, 0.05), 0.75)

# upbeat: 118 bpm, four on the floor, offbeat bass, pentatonic arpeggio. 60 s
d = 64.0; N = int(SR * d); up = np.zeros(N); bpm = 118; beat = 60 / bpm
roots = [110.0, 87.31, 130.81, 98.0]                     # A, F, C, G (one per bar)
scale = [1, 9 / 8, 5 / 4, 3 / 2, 5 / 3, 2]               # major pentatonic ratios
for b in range(int(d / beat)):
    at = b * beat; bar = (b // 4) % 4; root = roots[bar]
    place(up, kick(N), at, 0.9)
    place(up, hat(True), at + beat / 2, 0.35)
    place(up, hat(), at + beat / 4, 0.18); place(up, hat(), at + 3 * beat / 4, 0.18)
    x = t(beat * 0.45); bass = np.sin(2 * np.pi * root * x) * np.exp(-x * 5) + 0.2 * np.sin(2 * np.pi * root * 2 * x) * np.exp(-x * 8)
    place(up, bass, at + beat / 2, 0.55)
    for q in range(2):                                    # two arp notes per beat
        f = root * 4 * scale[(b * 2 + q * 3 + bar) % len(scale)]
        x = t(beat / 2 * 0.9); pl = (np.sin(2 * np.pi * f * x) + 0.3 * np.sin(2 * np.pi * 2 * f * x)) * np.exp(-x * 9)
        place(up, pl, at + q * beat / 2, 0.16)
up *= np.concatenate([np.linspace(0, 1, int(SR * 0.4)), np.ones(N - int(SR * 0.4) - int(SR * 2.5)), np.linspace(1, 0, int(SR * 2.5))])
save(out_bgm / "upbeat.wav", up, 0.8)
print("ok")

# typewriter lines: one tick per visible character, 45 ms apart (matches the film's typewriter)
LINES = ["Leaked.", "A GDPR fine.", "Konstantinos was fired.", "This is Shadow AI."]
x = t(0.07); tk = (rng.standard_normal(len(x)) * np.exp(-x * 140) * 0.6 + np.sin(2 * np.pi * 1700 * x) * np.exp(-x * 90))
for n, s in enumerate(LINES, 1):
    buf = np.zeros(int(SR * (len(s) * 0.045 + 0.2)))
    for i, ch in enumerate(s):
        if ch != " ": place(buf, tk, i * 0.045, 0.8 + 0.2 * rng.random())
    save(out_sfx / f"type{n}.wav", buf)
