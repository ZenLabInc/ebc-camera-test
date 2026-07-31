#!/usr/bin/env python3
"""openmv/event_probe.py を基板上で実行し、フレーム統計と画像を母艦に取り込む。

    python3 tools/capture.py [--frames N] [--send a,b,c] [--out ディレクトリ]

出力先に PNG(生 / 極性可視化 / 全フレーム積算)と、
フレームごとのイベント数 CSV を書き出す。
"""
import argparse
import base64
import pathlib
import sys

import numpy as np
from PIL import Image

import repl

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROBE = ROOT / "openmv" / "event_probe.py"
NEUTRAL = 128


def parse(out: str):
    """出力を (統計行のリスト, {フレーム番号: ndarray}) に分解する。"""
    stats, frames = [], {}
    cur = None
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("FRAME "):
            _, idx, fps, on, off = line.split()
            stats.append(
                {
                    "frame": int(idx),
                    "fps": float(fps.split("=")[1]),
                    "on": int(on.split("=")[1]),
                    "off": int(off.split("=")[1]),
                }
            )
        elif line.startswith("BEGIN "):
            _, idx, w, h = line.split()
            cur = {"idx": int(idx), "w": int(w), "h": int(h), "b64": []}
        elif line.startswith("END "):
            raw = base64.b64decode("".join(cur["b64"]))
            frames[cur["idx"]] = np.frombuffer(raw, dtype=np.uint8).reshape(
                cur["h"], cur["w"]
            )
            cur = None
        elif cur is not None and line:
            cur["b64"].append(line)
    return stats, frames


def colorize(arr: np.ndarray) -> Image.Image:
    """イベント極性を可視化する。増加=赤 / 減少=青 / 無イベント=黒。

    128 からのズレ幅は小さい(±16〜±64程度)ので、階調ではなく
    「イベントが出たか否か」を最大輝度で塗る。疎な点でも目視できる。
    """
    rgb = np.zeros((*arr.shape, 3), dtype=np.uint8)
    rgb[..., 0] = np.where(arr > NEUTRAL, 255, 0)
    rgb[..., 2] = np.where(arr < NEUTRAL, 255, 0)
    return Image.fromarray(rgb)


def accumulate(frames: dict[int, np.ndarray]) -> Image.Image:
    """全フレームのイベント発生回数を重ねた画像。静止シーンのノイズと
    実際の動きによるエッジを見分けるために使う。"""
    stack = np.stack(list(frames.values())).astype(np.int16)
    hits = (stack != NEUTRAL).sum(axis=0).astype(np.float32)
    if hits.max() > 0:
        hits = hits / hits.max() * 255
    return Image.fromarray(hits.astype(np.uint8))


def clustering(arr: np.ndarray) -> float:
    """イベント画素のうち、隣接4近傍にもイベントがある画素の割合。

    センサノイズは孤立した粒として出るのでこの値は低く、
    実際の被写体の動きはエッジ状に連続するので高くなる。
    ノイズフロアと本物の信号を見分けるための指標。
    """
    ev = arr != NEUTRAL
    if not ev.any():
        return 0.0
    nb = np.zeros_like(ev)
    nb[1:, :] |= ev[:-1, :]
    nb[:-1, :] |= ev[1:, :]
    nb[:, 1:] |= ev[:, :-1]
    nb[:, :-1] |= ev[:, 1:]
    return float((ev & nb).sum() / ev.sum())


def build_source(frames: int, send: list[int]) -> str:
    """基板へ送るスクリプトの FRAMES / SEND を差し替える。"""
    lines = []
    for line in PROBE.read_text().splitlines():
        if line.startswith("FRAMES ="):
            line = f"FRAMES = {frames}"
        elif line.startswith("SEND ="):
            line = f"SEND = ({', '.join(str(s) for s in send)},)"
        lines.append(line)
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=60)
    ap.add_argument("--send", default="0,20,40")
    ap.add_argument("--out", default=str(ROOT / "captures"))
    args = ap.parse_args()

    send = [int(s) for s in args.send.split(",") if s.strip()]
    outdir = pathlib.Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    port = repl.find_port()
    print(f"接続先: {port}")
    out, err = repl.run(build_source(args.frames, send), port, timeout=300.0)
    if err:
        print(err, file=sys.stderr)

    stats, frames = parse(out)
    if not stats:
        print("統計を取得できなかった。基板側の出力:", out[:500], file=sys.stderr)
        return 1

    csv = outdir / "events.csv"
    with csv.open("w") as f:
        f.write("frame,fps,on_events,off_events\n")
        for s in stats:
            f.write(f"{s['frame']},{s['fps']:.1f},{s['on']},{s['off']}\n")

    for idx, arr in sorted(frames.items()):
        Image.fromarray(arr).save(outdir / f"frame{idx:03d}_raw.png")
        colorize(arr).save(outdir / f"frame{idx:03d}_polarity.png")
        print(f"frame {idx:3d}: イベント画素の連結率 {clustering(arr):.1%}")
    if frames:
        accumulate(frames).save(outdir / "accumulated.png")

    total = [s["on"] + s["off"] for s in stats]
    fps = [s["fps"] for s in stats]
    print(f"フレーム数   : {len(stats)}")
    print(f"平均fps      : {sum(fps) / len(fps):.1f}")
    print(f"イベント/frame: 平均 {sum(total) / len(total):.0f} / 最大 {max(total)} / 最小 {min(total)}")
    print(f"画像         : {len(frames)} 枚 -> {outdir}")
    print(f"CSV          : {csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
