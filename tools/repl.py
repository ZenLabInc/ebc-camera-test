#!/usr/bin/env python3
"""OpenMV/MicroPython の raw REPL にスクリプトを流し込んで結果を受け取る最小ツール。

使い方:
    python3 tools/repl.py <スクリプト.py> [ポート] [タイムアウト秒]
    echo 'print(1+1)' | python3 tools/repl.py -

OpenMV IDE を使わずに CLI だけで疎通確認・撮影を回すために用意している。
"""
import sys
import time

import serial

DEFAULT_PORT = "/dev/cu.usbmodem11101"


def find_port() -> str:
    from serial.tools import list_ports

    for p in list_ports.comports():
        if "usbmodem" in p.device:
            return p.device
    return DEFAULT_PORT


def run(code: str, port: str, timeout: float = 30.0) -> tuple[str, str]:
    """raw REPL で code を実行し (stdout, stderr) を返す。"""
    ser = serial.Serial(port, 115200, timeout=0.1, dsrdtr=True)
    try:
        ser.write(b"\r\x03\x03")  # Ctrl-C 2回で実行中のスクリプトを停止
        time.sleep(0.2)
        ser.reset_input_buffer()

        ser.write(b"\x01")  # Ctrl-A: raw REPL へ
        rest = _read_until(ser, b"raw REPL; CTRL-B to exit\r\n>", 5, b"")[1]

        ser.write(code.encode() + b"\x04")  # Ctrl-D で実行開始
        _, rest = _read_until(ser, b"OK", 5, rest)

        out, rest = _read_until(ser, b"\x04", timeout, rest)  # 正常出力
        err, rest = _read_until(ser, b"\x04", 5, rest)        # 例外トレースバック

        ser.write(b"\x02")  # Ctrl-B: 通常 REPL へ戻す
        return out.decode(errors="replace"), err.decode(errors="replace")
    finally:
        ser.close()


def _read_until(
    ser: serial.Serial, ending: bytes, timeout: float, buf: bytes = b""
) -> tuple[bytes, bytes]:
    """ending が現れるまで読む。(ending より前の部分, ending より後の残り) を返す。

    1回の read で複数の区切りをまたいで届くことがあるため、残りバイトは
    呼び出し側に返して次の待ち受けに引き継ぐ。
    """
    deadline = time.time() + timeout
    while True:
        idx = buf.find(ending)
        if idx >= 0:
            return buf[:idx], buf[idx + len(ending) :]
        if time.time() >= deadline:
            raise TimeoutError(f"{ending!r} を待っている間にタイムアウト。受信済み: {buf!r}")
        chunk = ser.read(256)
        if chunk:
            buf += chunk
        else:
            time.sleep(0.01)


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    src = sys.stdin.read() if sys.argv[1] == "-" else open(sys.argv[1]).read()
    port = sys.argv[2] if len(sys.argv) > 2 else find_port()
    timeout = float(sys.argv[3]) if len(sys.argv) > 3 else 30.0

    out, err = run(src, port, timeout)
    if out:
        print(out, end="")
    if err:
        print(err, end="", file=sys.stderr)
    return 1 if err else 0


if __name__ == "__main__":
    raise SystemExit(main())
