#!/usr/bin/env python3
"""vibration_probe.py の時系列を取り込み、実効サンプリングレートとスペクトルを出す。

    python3 tools/spectrum.py [--out ディレクトリ]

Step 0 の検証用。既知の周波数(室内照明のフリッカ = 商用電源の2倍)が
スペクトルに立てば、センサから周波数抽出までの経路が通っていることになる。
"""
import argparse
import pathlib
import sys

import numpy as np

import repl

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROBE = ROOT / "openmv" / "vibration_probe.py"


def parse(out: str):
    t, a = [], []
    inside = False
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("BEGIN"):
            inside = True
        elif line.startswith("END"):
            inside = False
        elif inside and "," in line:
            us, val = line.split(",")
            t.append(int(us))
            a.append(int(val))
    return np.array(t, dtype=np.float64) * 1e-6, np.array(a, dtype=np.float64)


def spectrum(t: np.ndarray, a: np.ndarray):
    """等間隔とみなして FFT。実効サンプリングレートは実測時刻から求める。"""
    fs = (len(t) - 1) / (t[-1] - t[0])
    a = a - a.mean()
    a *= np.hanning(len(a))  # 窓関数。周波数の裾漏れを抑える
    spec = np.abs(np.fft.rfft(a))
    freq = np.fft.rfftfreq(len(a), 1.0 / fs)
    return fs, freq, spec


def build_source(samples: int, roi: str) -> str:
    """基板へ送るスクリプトの SAMPLES / ROI を差し替える。"""
    lines = []
    for line in PROBE.read_text().splitlines():
        if line.startswith("SAMPLES ="):
            line = f"SAMPLES = {samples}"
        elif line.startswith("ROI ="):
            line = f"ROI = {roi}"
        lines.append(line)
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=1500)
    ap.add_argument("--roi", default="(96, 96, 128, 128)",
                    help="'None' で全画面。狭いほど高レートになる")
    ap.add_argument("--out", default=str(ROOT / "captures" / "spectrum"))
    args = ap.parse_args()
    outdir = pathlib.Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    port = repl.find_port()
    print(f"接続先: {port}  ROI: {args.roi}")
    out, err = repl.run(build_source(args.samples, args.roi), port, timeout=180.0)
    if err:
        print(err, file=sys.stderr)

    t, a = parse(out)
    if len(t) < 64:
        print("時系列を取得できなかった:", out[:400], file=sys.stderr)
        return 1

    fs, freq, spec = spectrum(t, a)
    dt = np.diff(t) * 1000
    print(f"サンプル数       : {len(t)}")
    print(f"実効サンプリング : {fs:.1f} Hz(ナイキスト {fs / 2:.1f} Hz)")
    print(f"サンプル間隔     : 平均 {dt.mean():.2f} ms / 標準偏差 {dt.std():.3f} ms / 最大 {dt.max():.2f} ms")

    np.savetxt(outdir / "timeseries.csv", np.c_[t, a], delimiter=",",
               header="time_s,activity", comments="")
    np.savetxt(outdir / "spectrum.csv", np.c_[freq, spec], delimiter=",",
               header="freq_hz,magnitude", comments="")

    # DC 近傍は除いてピークを探す
    lo = freq > 5
    order = np.argsort(spec[lo])[::-1][:8]
    print("\n主要ピーク:")
    for i in order:
        print(f"  {freq[lo][i]:7.2f} Hz  強度 {spec[lo][i]:.0f}")
    print(f"\nCSV: {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
