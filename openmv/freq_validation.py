# 既知周波数での検証(Step 0 の合否判定)。
#
# 基板の LED を「時計基準で」正確な周波数で点滅させ、その周波数が
# スペクトルに現れるかを見る。フレーム数ではなく time.ticks_us() で駆動するので、
# サンプリング周期とは独立した刺激になり、検証として意味を持つ。
#
# センサ → 高レートサンプリング → FFT → 周波数の同定、という経路全体が
# 通っていることの証明になる。周波数の読み取り誤差もここで分かる。

import array
import sensor
import time
from machine import LED

SAMPLES = 2000
FRAMERATE = 400
ROI = (96, 96, 128, 128)
STIM_HZ = 40.0  # LED の点滅周波数。この値がスペクトルに立つはず


def main():
    sensor.reset()
    sensor.set_pixformat(sensor.GRAYSCALE)
    sensor.set_framesize(sensor.B320X320)
    sensor.set_framerate(FRAMERATE)
    sensor.skip_frames(time=500)
    print("SETUP %dx%d stim=%.2fHz" % (sensor.width(), sensor.height(), STIM_HZ))

    led = LED("LED_RED")
    half_us = int(1000000.0 / STIM_HZ / 2)  # 半周期

    act = array.array("H", bytearray(2 * SAMPLES))
    ts = array.array("I", bytearray(4 * SAMPLES))

    state = 0
    next_toggle = time.ticks_add(time.ticks_us(), half_us)
    for i in range(SAMPLES):
        now = time.ticks_us()
        if time.ticks_diff(now, next_toggle) >= 0:
            state ^= 1
            led.on() if state else led.off()
            next_toggle = time.ticks_add(next_toggle, half_us)
        img = sensor.snapshot()
        # 128 未満の画素の割合 = OFF イベント。整数化して保存する。
        act[i] = int(img.get_histogram(bins=2, roi=ROI).bins()[0] * 60000)
        ts[i] = time.ticks_us()
    led.off()

    print("BEGIN %d" % SAMPLES)
    t0 = ts[0]
    for i in range(SAMPLES):
        print("%d,%d" % (time.ticks_diff(ts[i], t0), act[i]))
    print("END")


main()
