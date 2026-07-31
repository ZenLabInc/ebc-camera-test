# ebc-camera-test

OpenMV RT1060 + GenX320(Prophesee イベントベースカメラ)の疎通確認用リポジトリ。

初事業「イベントカメラ非接触振動監視端末」の最初のステップとして、
届いたハードから実際にイベントデータが取れることを CLI だけで検証する。
OpenMV IDE は使わない(将来 CI や無人計測に載せるため)。

## 構成

| パス | 役割 |
|---|---|
| `tools/repl.py` | MicroPython raw REPL にスクリプトを流し込む最小クライアント |
| `tools/capture.py` | 基板でプローブを実行し、統計 CSV と PNG を母艦に取り込む |
| `openmv/event_probe.py` | 基板上で動く撮影スクリプト |
| `captures/` | 取得結果(CSV / PNG) |

## 使い方

```bash
pip install pyserial pillow numpy
python3 tools/capture.py --frames 120 --send 0,30,60,90 --out captures/static
```

USB シリアルポートは `/dev/cu.usbmodem*` から自動検出する。

## 出力

- `events.csv` — フレームごとの fps と ON/OFF イベント数
- `frameNNN_raw.png` — センサ生出力(グレースケール)
- `frameNNN_polarity.png` — 極性可視化(明るくなった=赤 / 暗くなった=青)
- `accumulated.png` — 送信フレーム全体のイベント発生回数を積算したもの

## ハードウェア構成(2026-07-31 実測)

| 項目 | 値 |
|---|---|
| ボード | OpenMV RT1060(NXP MIMXRT1062DVJ6A) |
| ファームウェア | MicroPython 1.26.0 / `OPENMV_RT1060` |
| USB | VID `0x37C5` / MicroPython "Board in FS mode" |
| センサ | Prophesee GenX320(`sensor.GENX320` 定数あり) |
| 解像度 | 320 x 320(`sensor.B320X320`) |
| 画素形式 | `GRAYSCALE`(イベント無し = 128 を基準に ON が 128 超 / OFF が 128 未満) |
| フレームレート | 約 50〜57 fps(グレースケール積算モード) |

## 疎通確認の結果(2026-07-31)

静止シーンと、レンズ前で手を振ったときの比較。イベント数が約3.5倍に増え、
イベント画素の連結率(孤立ノイズか連続エッジかの指標)が明確に跳ね上がる。
`captures/hand/frame*_polarity.png` には被写体の輪郭がはっきり出ている。

| 計測 | フレーム数 | 平均イベント/frame | 最大 | 連結率 |
|---|---:|---:|---:|---:|
| 静止 (`captures/static`) | 120 | 5,391 | 6,738 | 25〜38% |
| 静止 (`captures/motion`) | 1,000 | 4,757 | 7,474 | 25〜33% |
| 手を振る (`captures/hand`) | 420 | **16,877** | **37,429** | **61〜73%** |

→ センサは光の変化に正しく応答しており、実データが取れている。

基板 LED(`openmv/led_stimulus.py`)による自己刺激テストは、LED がレンズの
真横にあり反射光が弱いため有意差が出なかった(点灯中 9,565 / 消灯中 9,230)。
光学的な応答確認には外部の動きを使うこと。

## 注意点

- ファームウェア 1.26 の `sensor` モジュールに `set_time_filter()` は無い。
  ノイズ抑制はバイアス設定(`IOCTL_GENX320_SET_BIASES`)か AFK
  (`IOCTL_GENX320_SET_AFK`)で行う。
- `sensor.get_id()` は `sensor.GENX320` / `GENX320ES` のどちらの定数とも一致しない
  (生のチップ ID レジスタ値を返している)。センサ同定は定数比較ではなく
  実際に `B320X320` で撮影できるかで確認する。
- このモードはイベントを一定時間ぶんフレームに積算した出力であり、
  イベントカメラ本来の μs 分解能タイムスタンプは取れていない。
  振動計測でその分解能が要る場合は EVT ストリームの直接読み出しを検討する。
