# ebc-camera-test

[日本語](README.md)

A command-line validation project for the OpenMV RT1060 board and the Prophesee GenX320 event-based sensor. It verifies that the hardware produces event-activity frames and explores whether the available OpenMV firmware path is suitable for non-contact vibration measurement.

## What is included

- Minimal MicroPython raw-REPL client
- Capture scripts for event counts and polarity images
- High-rate scalar activity sampling
- Frequency-spectrum analysis
- Recorded CSV and PNG evidence from the documented experiments

The tested firmware exposes accumulated grayscale frames rather than the sensor's raw `(x, y, t)` event stream. The measured maximum scalar sampling rate was about 309 Hz with a 64×64 ROI, so the current path is useful for lower-frequency motion and vibration but does not satisfy the original 1 kHz target.

## Requirements and setup

- Python 3
- An OpenMV RT1060 with a GenX320 sensor
- A USB data cable

```sh
git clone https://github.com/ZenLabInc/ebc-camera-test.git
cd ebc-camera-test
python3 -m venv .venv
source .venv/bin/activate
pip install pyserial pillow numpy
python3 tools/capture.py --frames 120 --send 0,30,60,90 --out captures/static
```

The capture tool auto-detects `/dev/cu.usbmodem*` on macOS. Close other applications that use the serial port and connect only the intended board.

## Layout

- `tools/repl.py`: minimal raw-REPL transport
- `tools/capture.py`: run a board-side probe and retrieve CSV/PNG output
- `tools/spectrum.py`: calculate effective sample rate and spectra
- `openmv/`: MicroPython probes executed on the board
- `captures/`: checked-in experimental evidence

## Reproducing measurements

Record the firmware version, ROI, lighting, frame count, and sensor setup for each run. Compare a static scene with controlled motion, then verify a known-frequency source before interpreting an unknown vibration. Results in this repository describe one tested setup and are not a hardware performance guarantee.

## License

No open-source license has been declared. Copyright remains with its owner unless separate permission is granted.
