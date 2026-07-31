# 基板上の LED を点滅させ、イベントカメラがその光変化に反応するかを見る。
#
# 母艦から手を振ってもらう必要がない「自己完結した光学的応答テスト」。
# レンズ前に何か(机・壁・手)があれば LED 光が反射して戻り、
# 点灯/消灯の瞬間に大量のイベントが立つ。
# ノイズフロアと点滅タイミングの相関が取れれば、センサは確かに光に応答している。

import sensor
import time
from machine import LED

FRAMES = 300
PERIOD = 25  # 25フレーム(約0.5秒)ごとに LED を反転
NEUTRAL = 128


def event_count(img):
    hist = img.get_histogram(bins=256).bins()
    total = img.width() * img.height()
    on = sum(hist[NEUTRAL + 1 :])
    off = sum(hist[:NEUTRAL])
    return int(on * total), int(off * total)


def main():
    sensor.reset()
    sensor.set_pixformat(sensor.GRAYSCALE)
    sensor.set_framesize(sensor.B320X320)
    sensor.skip_frames(time=1000)
    print("SETUP %dx%d" % (sensor.width(), sensor.height()))

    led = LED("LED_RED")
    led.off()
    state = 0
    clock = time.clock()
    for i in range(FRAMES):
        if i % PERIOD == 0:
            state ^= 1
            led.on() if state else led.off()
        clock.tick()
        img = sensor.snapshot()
        on, off = event_count(img)
        print("FRAME %d fps=%.1f on=%d off=%d led=%d" % (i, clock.fps(), on, off, state))
    led.off()
    print("DONE")


main()
