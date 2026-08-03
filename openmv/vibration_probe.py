# 高レートで「イベント活動量のスカラー時系列」を取る(Step 0 の本命)。
#
# 振動計測に必要なのは画像ではなくスカラーの時系列なので、
# フレームごとに1つの数値まで落としてから母艦へ送る。
# こうすると 320x320 のフレームを毎回転送する必要がなく、
# センサのフレーム周期(約3ms)で律速される上限まで回せる。
#
# 活動量の指標は get_histogram(bins=2) の下位ビン、つまり画素値が 128 未満の割合。
# イベント無しの画素は 128 ちょうどなので、これは OFF イベントの発生率そのものになる。
#
# get_statistics().stdev() は一見それらしいが整数を返すため、
# イベントが疎な実環境では常に 0 になり分解能が無い(実測で確認済み)。
# ヒストグラムは float を返すので分解能が保たれる。

import array
import sensor
import time

# 実効サンプリングレートは ROI の広さで決まる(全画面147Hz / 128角267Hz / 64角304Hz)。
# 見たい周波数の2倍以上になるよう ROI を選ぶこと。ここは spectrum.py が上書きする。
SAMPLES = 1500
FRAMERATE = 400  # センサは 400 要求で約333fps に張り付く
ROI = (96, 96, 128, 128)  # None で全画面


def main():
    sensor.reset()
    sensor.set_pixformat(sensor.GRAYSCALE)
    sensor.set_framesize(sensor.B320X320)
    sensor.set_framerate(FRAMERATE)
    sensor.skip_frames(time=500)
    print("SETUP %dx%d" % (sensor.width(), sensor.height()))

    act = array.array("H", bytearray(2 * SAMPLES))  # 活動量(OFFイベント率)
    ts = array.array("I", bytearray(4 * SAMPLES))  # 取得時刻[us]

    # 計測ループ内では print も割り算もしない。純粋に撮る→測る→書くだけ。
    for i in range(SAMPLES):
        img = sensor.snapshot()
        h = img.get_histogram(bins=2) if ROI is None else img.get_histogram(bins=2, roi=ROI)
        act[i] = int(h.bins()[0] * 60000)
        ts[i] = time.ticks_us()

    print("BEGIN %d" % SAMPLES)
    t0 = ts[0]
    for i in range(SAMPLES):
        print("%d,%d" % (time.ticks_diff(ts[i], t0), act[i]))
    print("END")


main()
