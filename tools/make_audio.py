"""Music and sound effects for Severance: Lumon Office, synthesized with numpy + scipy (nothing downloaded).
python tools/make_audio.py [--only office,jazz]  ->  assets/audio/*.wav

Music loops carry a RIFF 'smpl' chunk so Godot imports them looping.
  office   72 BPM, D minor: soft piano arpeggios, a cold pad and a sparse descending motif (the severed floor)
  testing  dark drone, wind and metallic pings (the sub-level)
  tension  104 BPM staccato ostinato with ticking hats (patrols)
  jazz     132 BPM swing, 24 bars of F blues: walking bass, ride, brushes, Rhodes comping, muted trumpet
"""
import os
import sys
import wave
import struct
import numpy as np
from scipy import signal

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "assets", "audio")
os.makedirs(OUT, exist_ok=True)
SR = 32000
rng = np.random.default_rng(3)
ONLY = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else None


# ----------------------------------------------------------------------------- io
def save(name, x, gain=0.85, loop=False, sr=SR):
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    m = np.max(np.abs(x)) or 1.0
    x = x / m * gain
    data = (np.clip(x, -1, 1) * 32767).astype("<i2")
    path = os.path.join(OUT, name + ".wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.tobytes())
    if loop:
        n = len(x)
        smpl = struct.pack("<9I", 0, 0, int(1e9 / sr), 60, 0, 0, 0, 1, 0)
        smpl += struct.pack("<6I", 0, 0, 0, n - 1, 0, 0)
        with open(path, "r+b") as f:
            f.seek(0, 2)
            f.write(b"smpl" + struct.pack("<I", len(smpl)) + smpl)
            size = f.tell() - 8
            f.seek(4)
            f.write(struct.pack("<I", size))
    print("wav", name, round(len(x) / sr, 2), "s")


def mono_save(name, x, gain=0.8):
    save(name, x, gain, False, 22050) if False else save(name, x, gain)


# ----------------------------------------------------------------------------- dsp
def T(d):
    return np.arange(int(SR * d)) / SR


def mf(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def note_num(s):
    names = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
    n = names[s[0]]
    i = 1
    if len(s) > 2 or (len(s) == 2 and s[1] in "#b"):
        if s[1] == "#":
            n += 1
            i = 2
        elif s[1] == "b":
            n -= 1
            i = 2
    return n + 12 * (int(s[i:]) + 1)


def adsr(n, a=0.01, d=0.1, s=0.7, r=0.2):
    e = np.ones(n) * s
    na, nd, nr = int(a * SR), int(d * SR), int(r * SR)
    na = max(1, min(na, n))
    e[:na] = np.linspace(0, 1, na)
    if na + nd < n:
        e[na:na + nd] = np.linspace(1, s, nd)
    if nr > 0:
        nr = min(nr, n)
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def lowpass(x, fc, order=2):
    b, a = signal.butter(order, min(fc / (SR / 2), 0.99), "low")
    return signal.lfilter(b, a, x)


def highpass(x, fc, order=2):
    b, a = signal.butter(order, min(fc / (SR / 2), 0.99), "high")
    return signal.lfilter(b, a, x)


def bandpass(x, lo, hi, order=2):
    b, a = signal.butter(order, [lo / (SR / 2), min(hi / (SR / 2), 0.99)], "band")
    return signal.lfilter(b, a, x)


def reverb(x, secs=2.2, wet=0.3, seed=1, stereo=True):
    r = np.random.default_rng(seed)
    n = int(secs * SR)
    tt = np.arange(n) / SR
    outs = []
    for ch in range(2 if stereo else 1):
        ir = r.standard_normal(n) * np.exp(-tt * 6.9 / secs)
        ir = lowpass(ir, 5000)
        ir[: int(0.012 * SR)] = 0
        ir /= np.sqrt(np.sum(ir ** 2))
        y = signal.fftconvolve(x, ir)[: len(x)]
        outs.append(x * (1 - wet) + y * wet * 1.4)
    return np.stack(outs, 1) if stereo else outs[0]


def place(buf, x, at):
    i = int(at * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(x))
    buf[i:j] += x[: j - i]


def place_wrap(buf, x, at):
    """add with wrap-around so loops tail into their own start"""
    i = int(at * SR) % len(buf)
    n = len(x)
    j = i + n
    if j <= len(buf):
        buf[i:j] += x
    else:
        k = len(buf) - i
        buf[i:] += x[:k]
        rest = x[k:]
        buf[: len(rest)] += rest[: len(buf)]


# ----------------------------------------------------------------------------- instruments
def piano(f, dur=2.5, vel=1.0, bright=1.0):
    tt = T(dur)
    y = np.zeros_like(tt)
    for k in range(1, 9):
        fk = f * k * np.sqrt(1 + 0.0004 * k * k)
        amp = (1.0 / k ** 1.25) * (bright if k > 2 else 1.0)
        dec = 0.9 / (1 + 0.45 * k) * (1.6 if f < 300 else 1.0)
        y += amp * np.sin(2 * np.pi * fk * tt + rng.uniform(0, 6)) * np.exp(-tt / (dec * 2.2))
    ham = rng.standard_normal(int(0.012 * SR)) * np.linspace(1, 0, int(0.012 * SR)) * 0.25
    y[: len(ham)] += ham
    y *= adsr(len(tt), 0.003, 0.05, 1.0, 0.12)
    return y * vel


def rhodes(f, dur=1.0, vel=1.0):
    tt = T(dur)
    idx = 1.8 * np.exp(-tt * 6)
    y = np.sin(2 * np.pi * f * tt + idx * np.sin(2 * np.pi * f * tt))
    y += 0.25 * np.sin(2 * np.pi * f * 2 * tt) * np.exp(-tt * 3)
    y *= np.exp(-tt * 1.6) * adsr(len(tt), 0.004, 0.1, 1.0, 0.08)
    return y * vel


def pad(freqs, dur, cutoff=900, att=1.2, rel=1.5):
    tt = T(dur)
    y = np.zeros_like(tt)
    for f in freqs:
        for det in (-0.12, 0.0, 0.13):
            ff = f * 2 ** (det / 12)
            ph = rng.uniform(0, 1)
            y += (2 * ((ff * tt + ph) % 1.0) - 1) * 0.33
    y = lowpass(y, cutoff, 2)
    y *= adsr(len(tt), att, 0.2, 1.0, rel)
    return y / max(1, len(freqs))


def bass_pluck(f, dur=0.5, vel=1.0):
    tt = T(dur)
    y = np.sin(2 * np.pi * f * tt) + 0.45 * np.sin(2 * np.pi * 2 * f * tt) * np.exp(-tt * 8) + 0.15 * np.sin(2 * np.pi * 3 * f * tt) * np.exp(-tt * 12)
    y *= np.exp(-tt * 3.2) * adsr(len(tt), 0.004, 0.05, 1.0, 0.05)
    th = np.sin(2 * np.pi * 60 * tt) * np.exp(-tt * 40) * 0.4
    return (y + th) * vel


def brass(f, dur, vel=1.0, mute=True):
    tt = T(dur)
    vib = 0.006 * np.sin(2 * np.pi * 5.5 * tt) * np.clip(tt / 0.25, 0, 1)
    ph = np.cumsum(f * (1 + vib)) / SR
    y = 2 * (ph % 1.0) - 1
    y = bandpass(y, 500, 2600 if mute else 4500)
    y *= adsr(len(tt), 0.04, 0.08, 0.8, 0.07)
    return y * vel


def kick(vel=1.0):
    tt = T(0.35)
    f = 110 * np.exp(-tt * 18) + 45
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 9) * vel


def brush(vel=1.0, dur=0.22):
    x = rng.standard_normal(int(dur * SR))
    x = bandpass(x, 1500, 7000)
    return x * np.exp(-np.arange(len(x)) / SR * 14) * vel * 0.6


def ride(vel=1.0):
    tt = T(0.9)
    x = highpass(rng.standard_normal(len(tt)), 5000) * 0.5
    for fq in (3150, 4620, 5810, 7260):
        x += 0.2 * np.sin(2 * np.pi * fq * tt + rng.uniform(0, 6))
    return x * np.exp(-tt * 4.5) * vel * 0.5


def hat(vel=1.0):
    tt = T(0.06)
    return highpass(rng.standard_normal(len(tt)), 7000) * np.exp(-tt * 70) * vel


def bell(f, dur=2.5, vel=1.0):
    tt = T(dur)
    y = np.zeros_like(tt)
    for r, a, d in ((1, 1, 1.4), (2.76, 0.5, 0.8), (5.4, 0.25, 0.4), (8.9, 0.12, 0.2)):
        y += a * np.sin(2 * np.pi * f * r * tt) * np.exp(-tt / d)
    return y * vel * adsr(len(tt), 0.002, 0.05, 1, 0.1)


# ----------------------------------------------------------------------------- music
def music_office():
    bpm = 72.0
    beat = 60 / bpm
    bars = 16
    L = bars * 4 * beat
    buf = np.zeros(int(L * SR))
    chords = [["D3", "A3", "D4", "F4", "E4"], ["Bb2", "F3", "D4", "F4", "A4"], ["G2", "D3", "Bb3", "D4", "E4"],
              ["A2", "E3", "A3", "C#4", "E4"]]
    arp = [0, 2, 3, 4, 3, 2, 1, 2]
    for b in range(bars):
        ch = chords[b % 4]
        ns = [note_num(n) for n in ch]
        t0 = b * 4 * beat
        place_wrap(buf, piano(mf(ns[0] - 12), 4.0, 0.55, 0.6), t0)
        for k, ai in enumerate(arp):
            vel = 0.32 if k % 2 == 0 else 0.22
            place_wrap(buf, piano(mf(ns[ai] + 12), 2.2, vel, 0.8), t0 + k * beat * 0.5)
        pd = pad([mf(n) for n in ns[1:4]], 4 * beat + 1.0, cutoff=700, att=1.4, rel=1.6)
        place_wrap(buf, pd * 0.35, t0 - 0.3)
    # the motif (bars 5-8, 13-16): sparse descending line with a question at the end
    motif = [("A5", 0, 1.5), ("G5", 1.5, 0.5), ("F5", 2, 2), ("E5", 4, 1.5), ("D5", 5.5, 0.5), ("E5", 6, 2),
             ("D5", 8, 1.5), ("C5", 9.5, 0.5), ("Bb4", 10, 2), ("A4", 12, 1), ("C#5", 13, 1), ("E5", 14, 2)]
    for start_bar in (4, 12):
        for n, at, dur in motif:
            place_wrap(buf, piano(mf(note_num(n)), 3.0, 0.42, 1.2), start_bar * 4 * beat + at * beat)
            place_wrap(buf, bell(mf(note_num(n)) * 2, 2.0, 0.05), start_bar * 4 * beat + at * beat)
    # tape wobble
    tt = np.arange(len(buf)) / SR
    wob = 1 + 0.002 * np.sin(2 * np.pi * 0.35 * tt)
    idx = np.clip(np.cumsum(wob) - 1, 0, len(buf) - 1)
    buf = np.interp(idx, np.arange(len(buf)), buf)
    buf += lowpass(rng.standard_normal(len(buf)), 900) * 0.006   # air
    st = reverb(buf, 3.0, 0.38, seed=4)
    save("office", st, 0.8, loop=True)


def music_testing():
    L = 48.0
    tt = np.arange(int(L * SR)) / SR
    y = np.zeros_like(tt)
    for f, a in ((41.2, 0.5), (61.7, 0.35), (82.4, 0.2), (87.3, 0.12)):
        y += a * np.sin(2 * np.pi * f * tt + 0.4 * np.sin(2 * np.pi * 0.05 * tt))
    lfo = 0.6 + 0.4 * np.sin(2 * np.pi * tt / L * 3)
    y *= lfo
    wind = bandpass(rng.standard_normal(len(tt)), 200, 900) * (0.25 + 0.2 * np.sin(2 * np.pi * tt / L * 2 + 1)) * 0.5
    y += wind
    for k in range(10):
        at = (k * 4.7 + rng.uniform(0, 1.5)) % L
        place_wrap(y, bell(mf(rng.choice([74, 77, 81, 86, 89])), 3.0, 0.12), at)
    for k in range(int(L / 2.0)):
        place_wrap(y, kick(0.25), k * 2.0)
        place_wrap(y, kick(0.15), k * 2.0 + 0.32)
    st = reverb(y, 4.0, 0.45, seed=7)
    save("testing", st, 0.7, loop=True)


def music_tension():
    bpm = 104.0
    s16 = 60 / bpm / 4
    bars = 8
    L = bars * 16 * s16
    buf = np.zeros(int(L * SR))
    seq = [62, 62, 65, 62, 67, 62, 65, 64, 62, 62, 65, 62, 69, 67, 65, 64]
    for b in range(bars):
        tr = 0 if b < 4 else (-2 if b < 6 else 3)
        for k, n in enumerate(seq):
            at = (b * 16 + k) * s16
            x = brass(mf(n + tr - 12), s16 * 0.9, 0.5 if k % 4 == 0 else 0.3, mute=True)
            place_wrap(buf, lowpass(x, 1800), at)
            place_wrap(buf, hat(0.25 if k % 2 else 0.12), at)
        place_wrap(buf, kick(0.8), b * 16 * s16)
        place_wrap(buf, kick(0.6), (b * 16 + 8) * s16)
        place_wrap(buf, pad([mf(50 + tr), mf(57 + tr), mf(62 + tr)], 16 * s16 + 0.5, 500, 0.8, 0.8) * 0.4, b * 16 * s16)
    st = reverb(buf, 1.8, 0.25, seed=9)
    save("tension", st, 0.75, loop=True)


def music_jazz():
    bpm = 132.0
    beat = 60 / bpm
    bars = 24
    L = bars * 4 * beat
    buf = np.zeros(int(L * SR))
    sw = beat * 2 / 3            # swung second eighth
    blues = ["F", "Bb", "F", "F", "Bb", "Bb", "F", "D", "G", "C", "F", "C"]
    roots = {"F": 53, "Bb": 46, "D": 50, "G": 43, "C": 48}
    shells = {"F": [57, 63, 68], "Bb": [56, 62, 67], "D": [54, 60, 66], "G": [53, 59, 65], "C": [52, 58, 64]}
    for b in range(bars):
        c = blues[b % 12]
        r = roots[c]
        t0 = b * 4 * beat
        # walking bass: root, 3rd/5th, 6th, chromatic approach to the next root
        nxt = roots[blues[(b + 1) % 12]]
        walk = [r, r + 4 if c != "D" else r + 3, r + 7, nxt + (1 if (b % 2) else -1)]
        for k, n in enumerate(walk):
            place_wrap(buf, bass_pluck(mf(n - 12), beat * 1.1, 0.85), t0 + k * beat)
        # ride: ding, ding-a ding
        for k in range(4):
            place_wrap(buf, ride(0.5 if k % 2 == 0 else 0.35), t0 + k * beat)
            if k % 2 == 1:
                place_wrap(buf, ride(0.25), t0 + k * beat + sw)
        # brushes on 2 and 4, a kick feathered on 1
        place_wrap(buf, brush(0.55), t0 + beat)
        place_wrap(buf, brush(0.6), t0 + 3 * beat)
        place_wrap(buf, kick(0.35), t0)
        # rhodes comping (Charleston rhythm: 1 and the 'and' of 2)
        for at in (0.0, beat + sw):
            for n in shells[c]:
                place_wrap(buf, rhodes(mf(n), beat * 1.2, 0.22), t0 + at)
    # muted trumpet: a defiant riff answered by itself, twice through the 12 bars
    riff = [("C5", 0, 0.66), ("Eb5", 0.66, 0.34), ("F5", 1, 1), ("Ab5", 2.66, 0.34), ("F5", 3, 1),
            ("Eb5", 4.66, 0.34), ("C5", 5, 1.5), ("Bb4", 6.66, 0.34), ("C5", 7, 1)]
    answer = [("F5", 0, 0.66), ("Ab5", 0.66, 0.34), ("Bb5", 1, 1), ("C6", 2.66, 0.34), ("Bb5", 3, 0.66),
              ("Ab5", 3.66, 0.34), ("F5", 4, 2)]
    for chorus in range(2):
        base = chorus * 12 * 4 * beat
        for start_bar, phrase in ((0, riff), (4, [(n, a, d) for n, a, d in riff]), (8, answer)):
            for n, at, dur in phrase:
                sh = 2 if chorus == 1 and start_bar == 4 else 0
                place_wrap(buf, brass(mf(note_num(n) + sh), dur * beat * 0.95, 0.42), base + start_bar * 4 * beat + at * beat)
    st = reverb(buf, 1.6, 0.22, seed=11)
    save("jazz", st, 0.82, loop=True)


# ----------------------------------------------------------------------------- ambience
def amb_hum():
    L = 12.0
    tt = np.arange(int(L * SR)) / SR
    y = 0.4 * np.sin(2 * np.pi * 60 * tt) + 0.2 * np.sin(2 * np.pi * 120 * tt) + 0.08 * np.sin(2 * np.pi * 180 * tt)
    y += lowpass(rng.standard_normal(len(tt)), 400) * 0.6       # HVAC
    y += highpass(rng.standard_normal(len(tt)), 6000) * 0.02 * (1 + np.sin(2 * np.pi * 120 * tt))   # fluorescent buzz
    fade = int(0.5 * SR)
    y[:fade] = y[:fade] * np.linspace(0, 1, fade) + y[-fade:] * np.linspace(1, 0, fade)
    y = y[: len(y) - fade]
    save("hum", reverb(y, 0.8, 0.2), 0.5, loop=True)


def amb_drone():
    L = 14.0
    tt = np.arange(int(L * SR)) / SR
    y = 0.5 * np.sin(2 * np.pi * 48 * tt) + 0.3 * np.sin(2 * np.pi * 72.3 * tt)
    y += bandpass(rng.standard_normal(len(tt)), 80, 300) * 0.7
    fade = int(0.7 * SR)
    y[:fade] = y[:fade] * np.linspace(0, 1, fade) + y[-fade:] * np.linspace(1, 0, fade)
    y = y[: len(y) - fade]
    save("drone", reverb(y, 1.5, 0.3), 0.5, loop=True)


# ----------------------------------------------------------------------------- sfx
def env_exp(n, k):
    return np.exp(-np.arange(n) / SR * k)


def sfx():
    def s(name, x, g=0.8, verb=0.0):
        if verb > 0:
            x = reverb(np.concatenate([x, np.zeros(int(0.6 * SR))]), 1.0, verb, stereo=True)
        save(name, x, g)

    # UI
    s("click", np.sin(2 * np.pi * 1300 * T(0.05)) * env_exp(int(0.05 * SR), 90), 0.5)
    s("beep", np.sign(np.sin(2 * np.pi * 1760 * T(0.09))) * 0.3 * env_exp(int(0.09 * SR), 25), 0.4)
    s("tick", np.sin(2 * np.pi * 2400 * T(0.025)) * env_exp(int(0.025 * SR), 160), 0.35)
    s("select", np.concatenate([np.sin(2 * np.pi * 880 * T(0.05)), np.sin(2 * np.pi * 1320 * T(0.07))]) * 0.6
      * env_exp(int(0.12 * SR), 18), 0.45)
    s("close", np.sin(2 * np.pi * np.cumsum(np.linspace(900, 300, int(0.12 * SR))) / SR) * env_exp(int(0.12 * SR), 20), 0.4)
    s("switch", np.concatenate([bell(mf(76), 0.12, 1), bell(mf(83), 0.5, 1)]), 0.45, 0.25)
    s("blip_lo", np.sin(2 * np.pi * 330 * T(0.05)) * env_exp(int(0.05 * SR), 50), 0.3)
    s("blip_hi", np.sin(2 * np.pi * 620 * T(0.05)) * env_exp(int(0.05 * SR), 50), 0.3)
    # CRT / refinement
    tt = T(0.5)
    crt = highpass(rng.standard_normal(len(tt)), 3000) * 0.3 * env_exp(len(tt), 8) + np.sin(2 * np.pi * 15700 * tt) * 0.05
    crt += np.sin(2 * np.pi * np.cumsum(np.linspace(80, 40, len(tt))) / SR) * env_exp(len(tt), 6) * 0.6
    s("crt_on", crt, 0.6)
    tt = T(0.45)
    sweep = np.sin(2 * np.pi * np.cumsum(np.linspace(500, 1400, len(tt))) / SR) * env_exp(len(tt), 7)
    s("refine", sweep * 0.6 + bandpass(rng.standard_normal(len(tt)), 2000, 6000) * env_exp(len(tt), 10) * 0.3, 0.6, 0.2)
    tt = T(0.32)
    s("wrong", np.sign(np.sin(2 * np.pi * 140 * tt)) * 0.4 * env_exp(len(tt), 7) + np.sin(2 * np.pi * 148 * tt) * 0.3, 0.45)
    s("good", np.concatenate([bell(mf(79), 0.1, 1), bell(mf(84), 0.6, 1)]), 0.5, 0.25)
    s("hit", bell(mf(72), 0.3, 1) + brush(0.3, 0.3)[: int(0.3 * SR)], 0.45)
    # jingles
    j = np.zeros(int(2.4 * SR))
    for k, n in enumerate([62, 66, 69, 74]):
        place(j, piano(mf(n), 1.8, 0.6), k * 0.11)
        place(j, bell(mf(n + 12), 1.6, 0.15), k * 0.11)
    s("directive", j, 0.7, 0.35)
    j = np.zeros(int(1.6 * SR))
    for k, n in enumerate([67, 74]):
        place(j, bell(mf(n), 1.3, 0.8), k * 0.12)
    s("chime", j, 0.5, 0.35)
    s("step_done", bell(mf(81), 0.8, 0.8), 0.4, 0.3)
    j = np.zeros(int(1.6 * SR))
    for k, n in enumerate([72, 76, 79, 84]):
        place(j, bell(mf(n), 1.2, 0.7), k * 0.07)
    s("win", j, 0.55, 0.3)
    j = np.zeros(int(1.0 * SR))
    for k, n in enumerate([79, 86]):
        place(j, bell(mf(n), 0.8, 0.7), k * 0.06)
    s("pickup", j, 0.5, 0.2)
    # world
    tt = T(0.09)
    step = lowpass(rng.standard_normal(len(tt)), 900) * env_exp(len(tt), 45) + np.sin(2 * np.pi * 90 * tt) * env_exp(len(tt), 60) * 0.5
    s("step", step, 0.6)
    tt = T(1.0)
    door = lowpass(rng.standard_normal(len(tt)), 600) * np.sin(np.pi * np.clip(tt / 0.8, 0, 1)) * 0.5
    door += np.sin(2 * np.pi * 70 * tt) * np.exp(-((tt - 0.85) * 25) ** 2) * 0.8
    s("door", door, 0.6)
    s("ding", bell(mf(81), 2.0, 1) + bell(mf(77), 2.0, 0.6), 0.6, 0.3)
    tt = T(0.5)
    lever = np.sin(2 * np.pi * np.cumsum(np.linspace(300, 120, len(tt))) / SR) * env_exp(len(tt), 6) * 0.5
    lever += np.sin(2 * np.pi * 55 * tt) * np.exp(-((tt - 0.4) * 30) ** 2) * 1.2
    s("lever", lever, 0.7)
    tt = T(2.4)
    alarm = np.sign(np.sin(2 * np.pi * (700 + 250 * np.sign(np.sin(2 * np.pi * 2.5 * tt))) * tt)) * 0.4
    s("alarm", lowpass(alarm, 3000) * adsr(len(tt), 0.02, 0.1, 1, 0.3), 0.6, 0.3)
    tt = T(0.9)
    caught = np.sin(2 * np.pi * np.cumsum(np.linspace(600, 180, len(tt))) / SR) * env_exp(len(tt), 3)
    caught += np.sin(2 * np.pi * np.cumsum(np.linspace(630, 190, len(tt))) / SR) * env_exp(len(tt), 3)
    s("caught", caught, 0.6, 0.3)
    tt = T(0.5)
    snort = lowpass(rng.standard_normal(len(tt)), 400) * np.sin(np.pi * tt / 0.5) * (1 + np.sin(2 * np.pi * 30 * tt))
    s("snort", snort, 0.5)
    tt = T(0.25)
    s("print", np.sign(np.sin(2 * np.pi * 220 * tt)) * 0.2 * np.sin(np.pi * tt / 0.25) + lowpass(rng.standard_normal(len(tt)), 1500) * 0.2, 0.35)
    tt = T(0.4)
    slurp = bandpass(rng.standard_normal(len(tt)), 300, 1500) * np.abs(np.sin(2 * np.pi * 9 * tt)) * np.sin(np.pi * tt / 0.4)
    s("slurp", slurp, 0.5)
    # goat bleat: buzzy vowel with vibrato
    tt = T(0.7)
    f0 = 520 * (1 + 0.06 * np.sin(2 * np.pi * 9 * tt)) * np.linspace(1.05, 0.92, len(tt))
    src = 2 * ((np.cumsum(f0) / SR) % 1) - 1
    bleat = bandpass(src, 700, 1300) + 0.6 * bandpass(src, 2200, 2800)
    bleat *= adsr(len(tt), 0.03, 0.1, 0.8, 0.2) * (0.7 + 0.3 * np.sin(2 * np.pi * 17 * tt))
    s("bleat", bleat, 0.6, 0.15)


def main():
    jobs = {"sfx": sfx, "office": music_office, "testing": music_testing, "tension": music_tension,
            "jazz": music_jazz, "hum": amb_hum, "drone": amb_drone}
    for k, fn in jobs.items():
        if ONLY and k not in ONLY:
            continue
        fn()
    print("DONE")


if __name__ == "__main__":
    main()
