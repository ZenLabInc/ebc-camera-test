# GenX320 イベントカメラの疎通確認スクリプト(OpenMV RT1060 上で実行)。
#
# フレームを撮って統計を出し、要求されたフレームだけ base64 で母艦へ送る。
# tools/capture.py から raw REPL 経由で流し込まれる想定。
#
# イベントカメラの GRAYSCALE 出力は「イベント無し = 128」を基準に、
# 明るくなった画素が 128 超、暗くなった画素が 128 未満になる。
# したがって 128 からのズレの個数がそのフレームのイベント数になる。

import binascii
import sensor
import time

FRAMES = 60  # 統計を取るフレーム数
SEND = (0, 20, 40)  # 実データを母艦へ送るフレーム番号
NEUTRAL = 128  # イベント無しの画素値
# ここは capture.py が --frames / --send で上書きする(CONFIG マーカー)


def setup():
    sensor.reset()
    sensor.set_pixformat(sensor.GRAYSCALE)
    sensor.set_framesize(sensor.B320X320)
    sensor.ioctl(sensor.IOCTL_GENX320_SET_BIASES, sensor.GENX320_BIASES_DEFAULT)
    sensor.skip_frames(time=1000)
    print("SETUP %dx%d" % (sensor.width(), sensor.height()))


def event_count(img):
    """128 から外れた画素数を (増加, 減少) で返す。"""
    # get_histogram() は 0-255 を bins 個に量子化して返す。256 bins で画素値そのまま。
    hist = img.get_histogram(bins=256).bins()
    total = img.width() * img.height()
    on = off = 0
    for v in range(NEUTRAL + 1, 256):
        on += hist[v]
    for v in range(0, NEUTRAL):
        off += hist[v]
    return int(on * total), int(off * total)


def main():
    setup()
    clock = time.clock()
    for i in range(FRAMES):
        clock.tick()
        img = sensor.snapshot()
        on, off = event_count(img)
        print("FRAME %d fps=%.1f on=%d off=%d" % (i, clock.fps(), on, off))
        if i in SEND:
            print("BEGIN %d %d %d" % (i, img.width(), img.height()))
            buf = img.bytearray()
            step = 3072  # 4KB 弱ずつ base64 化して吐く(メモリ節約)
            for o in range(0, len(buf), step):
                print(binascii.b2a_base64(buf[o : o + step]).decode().strip())
            print("END %d" % i)
    print("DONE")


main()
