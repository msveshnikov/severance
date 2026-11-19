"""Procedural sound effects and music for «Горячая сумка» (system Python + numpy). No downloads.
usage: python blender/scripts/make_audio.py  -> assets/audio/*.wav (16-bit mono)
"""
import os
import wave
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "assets", "audio")
os.makedirs(OUT, exist_ok=True)
SR = 22050
rng = np.random.default_rng(1)


def t(d):
    return np.arange(int(SR * d)) / SR


def env(n, a=0.005, r=0.2, sustain=1.0):
    e = np.ones(n) * sustain
    na = max(1, int(a * SR))
    e[:na] = np.linspace(0, 1, na)
    nr = int(r * SR)
    if nr > 0 and nr < n:
        e[-nr:] *= np.linspace(1, 0, nr) ** 2
    return e


def save(name, x, gain=0.8):
    x = np.asarray(x, dtype=np.float64)
    m = np.max(np.abs(x)) or 1
    x = x / m * gain
    data = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    print("wav", name, round(len(x) / SR, 2))


def lp(x, k=0.1):
    y = np.zeros_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += k * (x[i] - acc)
        y[i] = acc
    return y


def lp_fast(x, n=8):
    k = np.ones(n) / n
    return np.convolve(x, k, mode="same")


def tone(f, d, kind="sine", decay=None, vib=0.0):
    tt = t(d)
    ph = 2 * np.pi * f * tt + vib * np.sin(2 * np.pi * 6 * tt)
    if kind == "sine":
        s = np.sin(ph)
    elif kind == "square":
        s = np.sign(np.sin(ph)) * 0.5
    elif kind == "tri":
        s = 2 / np.pi * np.arcsin(np.sin(ph))
    else:
        s = np.sin(ph)
    if decay:
        s *= np.exp(-tt / decay)
    return s


def noise(d):
    return rng.uniform(-1, 1, int(SR * d))


def sfx():
    save("ui", tone(880, 0.06, "sine", 0.02) + 0.3 * tone(1760, 0.06, "sine", 0.01), 0.5)
    b = np.zeros(int(SR * 1.2))
    for st in (0.0, 0.18):
        s = tone(2600, 1.0, "sine", 0.35) + 0.6 * tone(3390, 1.0, "sine", 0.25) + 0.3 * tone(5200, 1.0, "sine", 0.1)
        i = int(st * SR)
        b[i:i + len(s)] += s[:len(b) - i]
    save("bell", b, 0.6)
    c = np.concatenate([tone(988, 0.08, "square", 0.05), tone(1319, 0.25, "square", 0.12)])
    save("coin", c, 0.45)
    save("notify", np.concatenate([tone(1568, 0.09, "sine", 0.06), tone(2349, 0.22, "sine", 0.1)]), 0.55)
    save("accept", np.concatenate([tone(f, 0.07, "tri", 0.06) for f in (523, 659, 784, 1046)]), 0.55)
    save("fail", np.concatenate([tone(f, 0.12, "square", 0.1) for f in (392, 311, 233)]), 0.4)
    k = np.zeros(int(SR * 0.7))
    for st in (0.0, 0.2, 0.4):
        s = lp_fast(noise(0.08), 30) * np.exp(-t(0.08) / 0.02) + 0.6 * tone(110, 0.08, "sine", 0.03)
        i = int(st * SR)
        k[i:i + len(s)] += s
    save("knock", k, 0.8)
    save("intercom", tone(440, 0.5, "square") * env(int(SR * 0.5), r=0.05) + 0.3 * tone(880, 0.5, "square"), 0.35)
    save("crash", lp_fast(noise(0.6), 6) * np.exp(-t(0.6) / 0.15) + 0.5 * tone(70, 0.6, "sine", 0.2), 0.9)
    save("whistle", tone(2900, 0.7, "sine", None, vib=30) * env(int(SR * 0.7), 0.02, 0.15), 0.5)
    save("splash", lp_fast(noise(0.35), 3) * np.exp(-t(0.35) / 0.08), 0.6)
    save("step", lp_fast(noise(0.07), 12) * np.exp(-t(0.07) / 0.015), 0.6)
    save("pickup", np.concatenate([tone(660, 0.06, "tri", 0.05), tone(990, 0.12, "tri", 0.08)]), 0.5)
    save("deliver", np.concatenate([tone(f, 0.09, "square", 0.08) for f in (784, 988, 1175, 1568)]), 0.4)
    save("phone_open", np.concatenate([tone(1200, 0.04, "sine", 0.02), tone(1600, 0.06, "sine", 0.03)]), 0.4)
    save("ring", np.tile(np.concatenate([tone(440, 0.4, "sine") * 0.5 + tone(480, 0.4, "sine") * 0.5,
                                         np.zeros(int(SR * 0.4))]), 2), 0.4)
    save("fall", np.concatenate([tone(f, 0.08, "tri", 0.07) for f in (700, 520, 380, 260)]) +
         0, 0.5)
    save("lock", np.concatenate([lp_fast(noise(0.03), 4) * 0.6, np.zeros(400), tone(1800, 0.05, "square", 0.02)]), 0.5)
    save("brake", lp_fast(noise(0.4), 2) * env(int(SR * 0.4), 0.02, 0.2) * 0.5 + 0.3 * tone(3200, 0.4, "sine", 0.2), 0.4)
    save("level_up", np.concatenate([tone(f, 0.1, "square", 0.09) for f in (523, 659, 784, 1046, 784, 1046)]), 0.4)
    save("tram_bell", np.concatenate([tone(1400, 0.25, "sine", 0.15), tone(1400, 0.35, "sine", 0.2)]) +
         0, 0.5)
    save("horn", (tone(392, 0.35, "square") + tone(494, 0.35, "square")) * env(int(SR * 0.35), 0.01, 0.05), 0.35)


def loops():
    # scooter motor: steady whine with harmonics (pitch is changed in the engine)
    d = 2.0
    tt = t(d)
    m = np.sin(2 * np.pi * 220 * tt) + 0.5 * np.sin(2 * np.pi * 440 * tt) + 0.25 * np.sin(2 * np.pi * 660 * tt)
    m += 0.15 * lp_fast(noise(d), 20)
    save("motor_loop", m, 0.35)
    # bicycle: chain ticks + soft tyre noise
    b = lp_fast(noise(d), 40) * 0.4
    for k in range(int(d * 8)):
        i = int(k * SR / 8)
        s = lp_fast(noise(0.012), 2) * np.exp(-t(0.012) / 0.004)
        b[i:i + len(s)] += s * 0.8
    save("pedal_loop", b, 0.4)
    # city ambience: brown noise + far traffic swells
    d = 8.0
    n = np.cumsum(noise(d)) * 0.02
    n -= lp_fast(n, 2000)
    tt = t(d)
    n *= 0.7 + 0.3 * np.sin(2 * np.pi * tt / d)
    save("city_loop", n, 0.35)
    r = lp_fast(noise(d), 3) * 0.8 + 0.2 * noise(d)
    save("rain_loop", r, 0.4)
    birds = np.zeros(int(SR * d))
    for k in range(10):
        st = rng.uniform(0, d - 0.5)
        f = rng.uniform(2500, 4200)
        s = tone(f, 0.12, "sine", 0.05, vib=8) * 0.5
        i = int(st * SR)
        birds[i:i + len(s)] += s
    save("birds_loop", birds + 0.05 * lp_fast(noise(d), 50), 0.3)


NOTES = {n: 440 * 2 ** ((i - 9) / 12) for i, n in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}


def note(n, octv):
    return NOTES[n] * 2 ** (octv - 4)


def music(name, bpm, prog, melody, lead="square", bass_kind="tri", swing=0.0, gain=0.45, drums=True):
    beat = 60 / bpm
    bars = len(prog)
    total = int(SR * beat * 4 * bars)
    out = np.zeros(total)

    def add(sig, start):
        i = int(start * SR)
        j = min(total, i + len(sig))
        out[i:j] += sig[:j - i]
    for b, chord in enumerate(prog):
        root, quality = chord
        third = 3 if quality == "m" else 4
        f0 = note(root, 2)
        for k in range(4):  # bass on every beat (root, fifth)
            f = f0 * (1.5 if k % 2 else 1.0)
            add(tone(f, beat * 0.9, bass_kind, beat * 0.5) * 0.5, (b * 4 + k) * beat)
        for k in range(8):  # off-beat chord stabs
            if k % 2 == 1:
                for semi in (0, third, 7):
                    f = note(root, 4) * 2 ** (semi / 12)
                    add(tone(f, beat * 0.3, "tri", beat * 0.15) * 0.12, (b * 4 + k * 0.5 + swing) * beat)
        if drums:
            for k in range(4):
                kick = tone(60, 0.15, "sine", 0.05) * 0.7
                add(kick, (b * 4 + k) * beat if k % 2 == 0 else (b * 4 + k) * beat + 10)
                if k % 2 == 1:
                    add(lp_fast(noise(0.1), 2) * np.exp(-t(0.1) / 0.03) * 0.25, (b * 4 + k) * beat)
                for h in range(2):
                    add(noise(0.03) * np.exp(-t(0.03) / 0.008) * 0.08, (b * 4 + k + h * 0.5) * beat)
    pos = 0.0
    for (n, octv, dur) in melody:
        if n != "-":
            add(tone(note(n, octv), dur * beat * 0.95, lead, dur * beat * 0.6) * 0.22, pos * beat)
        pos += dur
        if pos >= bars * 4:
            break
    save(name, out, gain)


def mel(s):
    out = []
    for tok in s.split():
        n, rest = tok.split(":")
        if n == "-":
            out.append(("-", 4, float(rest)))
        else:
            out.append((n[:-1], int(n[-1]), float(rest)))
    return out


if __name__ == "__main__":
    sfx()
    loops()
    prog = [("C", "M"), ("A", "m"), ("F", "M"), ("G", "M")] * 4
    m = mel("E5:1 G5:0.5 E5:0.5 C5:1 D5:1 E5:1 C5:1 A4:2 F4:1 A4:0.5 C5:0.5 F5:1 E5:1 D5:2 B4:1 G4:1 "
            "E5:0.5 E5:0.5 G5:1 A5:1 G5:1 E5:1 C5:1 A4:1 C5:1 F5:1 E5:0.5 D5:0.5 C5:1 A4:1 B4:1 D5:1 G5:2 "
            "C5:1 E5:1 G5:1 E5:1 A5:1 G5:1 E5:2 F5:1 E5:1 D5:1 C5:1 D5:2 G4:2 "
            "E5:1 D5:1 C5:1 D5:1 A4:2 C5:2 F4:1 A4:1 C5:1 F5:1 G5:2 B4:1 D5:1")
    music("music_day", 116, prog, m, lead="square", gain=0.45)
    progn = [("A", "m"), ("F", "M"), ("C", "M"), ("G", "M")] * 4
    mn = mel("A4:2 C5:1 E5:1 D5:2 C5:2 F4:2 A4:1 C5:1 B4:4 E4:2 G4:1 C5:1 B4:2 G4:2 D5:3 -:1 "
             "A4:2 C5:1 E5:1 G5:2 E5:2 F5:2 E5:1 D5:1 C5:4 E5:2 D5:1 C5:1 B4:2 D5:2 A4:4")
    music("music_night", 84, progn, mn, lead="tri", gain=0.4, drums=False)
    progm = [("F", "M"), ("G", "M"), ("E", "m"), ("A", "m"), ("D", "m"), ("G", "M"), ("C", "M"), ("C", "M")]
    mm = mel("C5:1 F5:1 A5:1 G5:1 F5:2 D5:2 E5:1 G5:1 B5:1 A5:1 G5:4 A5:1 G5:1 F5:1 E5:1 D5:2 F5:2 "
             "E5:1 D5:1 C5:1 D5:1 E5:4 C5:2")
    music("music_menu", 100, progm, mm, lead="tri", gain=0.42)
    print("DONE")
