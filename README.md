# HamTec G90 touchscreen controller — version 0.1

Local Raspberry Pi 4 controller for a ROADOM 1024×600 HDMI touchscreen.
This is working application source with a demo mode and a physical CAT/IQ
path. It has not been tested on a physical G90, Pi, or ROADOM display.

## Connections

1. Pi micro-HDMI → monitor HDMI. Connect its USB touch cable and supply
   monitor power according to the monitor instructions.
2. Keep the stock G90 head connected to the body. Boot the G90 before
   inserting the supplied blue USB serial cable in the head's communication
   socket. Connect USB to the Pi. The rear COMM socket is not the CAT socket.
3. Rear I/Q → true stereo line input on your USB audio interface → Pi USB.
   Both capture channels are required. A mono microphone input is unsuitable.
   A stereo-capable adapter is assumed, not verified. Confirm input levels,
   channel assignment, and electrical compatibility before connection. Turn
   off microphone enhancement/AGC; start with low input gain. Use ferrites
   and suitable isolation where needed. Do not connect serial signals to
   the audio adapter or use RS-232 voltage levels at the radio jack.

## Install on Raspberry Pi OS

The following commands install the application in a virtual environment.
Run from the extracted `g90-controller` directory. They require internet
access on the Pi. No installation or changes have been made to your Pi.

```bash
sudo apt update
sudo apt install python3-venv libportaudio2
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:8080` on the Pi. Default mode is DEMO. It sends no radio
commands. The spectrum stays blank without real input; no synthetic signal
or SWR results are presented as measurements.

Use Chromium's kiosk option to fill the touch display, if Chromium is
installed (the executable name varies by Raspberry Pi OS version):

```bash
chromium --kiosk http://127.0.0.1:8080
```

## Find the serial port and stereo capture device

```bash
ls -l /dev/serial/by-id/
source .venv/bin/activate
python -m sounddevice
```

Choose the audio INPUT device that exposes at least two input channels.
Use a stable `/dev/serial/by-id/` path for CAT. If serial access is denied,
check membership of the Pi OS serial access group, commonly `dialout`.
Do not run the web application as root.

Start a physical session (replace the illustrative port and device index):

```bash
python app.py --live --port /dev/serial/by-id/YOUR_G90_CABLE --iq-device 2
```

Boot the G90, insert its head CAT cable, then press CONNECT CAT on screen.
There are no automatic serial commands before you press that button.
Frequency polling starts after successful connection. Stop the application
and disconnect the head CAT cable before cycling G90 power. Do not leave
software polling while the radio boots into its firmware update interface.

The default address is 88 hex. If reads fail, stop the app and try:

```bash
python app.py --live --port /dev/serial/by-id/YOUR_G90_CABLE --address 70 --iq-device 2
```

Use `--swap-iq` for reversed spectral orientation. Default capture is 48 kHz;
`--sample-rate 96000` is optional only if both radio output and adapter make
it useful. Sample rate is not a claim about useful G90 RF bandwidth.

## Implemented controls

- Frequency, mode, band frequency jumps, tuning step, touch drag tuning dial,
  frequency keypad, VFO A/B and swap, split.
- AF level, squelch, RF power level, CW pitch/speed level, PRE, AGC, NB, COMP,
  dial lock, ATT toggle.
- ATU bypass/enable/start and status query, PTT release (RECEIVE).
- S, power and SWR raw meter queries; serial command diagnostics.
- Stereo complex FFT, spectrum/waterfall, I/Q swap option, input clipping
  warning, and stale-capture suppression.
- Browser-local frequency/mode presets (not radio memory writes).

Start tuning is disabled in live mode unless launched with `--allow-tune`.
Enable this only after normal read/write controls have been checked and with
a suitable antenna or dummy load and a permitted transmit frequency:

```bash
python app.py --live --port /dev/serial/by-id/YOUR_G90_CABLE --iq-device 2 --allow-tune
```

START TUNE requires a separate on-screen confirmation. It produces RF.
RECEIVE sends CAT PTT release; it is NOT a verified abort for the radio's
autonomous tuner. It may not terminate an ATU cycle. Keep physical radio
controls accessible. If the cable disconnects, software cannot guarantee
receipt of a release command. No general PTT-on control is provided.

## Material limitations

- SWR sweep is intentionally unavailable. No verified CAT command launches
  the built-in scanner or downloads its graph. A future Pi sweep needs
  validated low-power carrier generation, SWR conversion, transmit-frequency
  limits, timing, stop behaviour and restoration of radio settings.
- Meter displays show **raw** numbers, not calibrated watts/S-units/SWR ratio.
  No SWR graph or ratio is invented from unverified conversion.
- Level sliders use 0–255 CAT units. Watts/WPM/Hz calibration is pending.
  Strict BCD decoding will report unsupported/non-BCD firmware responses,
  rather than silently guessing their meaning.
- Filter/RIT controls are disabled; firmware-specific extensions, DATA modes,
  RF gain, microphone settings, radio memories, VOX, menu controls, audio
  playback and recording are not implemented. CAT does not expose everything.
- AGC is shown as numeric 0–3 because documented names and library mappings
  differ; check each state on the physical radio for your firmware.
- Frequency/mode and tuner state are polled. Switch/level values are updated
  after controller actions; initial slider values are defaults, not polled
  radio state. Switch read-back is verified. VFO/split labels represent
  acknowledged requests, not separately verified current radio state.
- Firmware-dependent ATT may toggle rather than accept an absolute state.
  Read its diagnostic response and verify physically.
- Use one serial client at a time. Close flrig/WSJT-X CAT polling while this
  app owns the port. Bind remains loopback-only; do not expose it publicly.

## Checks before RF use

1. Confirm two-channel capture and tune past a known signal to verify I/Q
   orientation. Adjust gain if clipping appears.
2. Check frequency/mode read-back and all switches against the physical G90.
3. Verify level scaling with your exact head/base firmware. Do not infer
   RF watts from slider position until calibrated.
4. Only then test ATU start at a permitted frequency with a suitable load.
5. Keep SWR sweep disabled until a validated implementation exists.

## Protocol sources

- Radioddity, *G90 CAT control and digital modes v1.0*, command tables:
  https://device.report/m/3fa57e83d810eafc0a99998edb5d8759e366c7eef4a3dd3329cf585d51aecf0d
- G90 operation manual:
  https://device.report/m/93ee18ec37ce5a7a753ac46eed8ebc196b4bc99cffe88e30c34e32807f3cc4ec
- Hamlib G90 source, used to cross-check framing/settings and known limits:
  https://github.com/Hamlib/Hamlib/blob/master/rigs/icom/xiegu.c

See COMMANDS.md for the baseline command map. Tests run with:

```bash
python -m unittest discover -s tests -v
```
