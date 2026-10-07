import argparse
import secrets
import threading
import time
from flask import Flask, jsonify, render_template, request
from cat import CAT, level_encode, level_decode

MODES = {'LSB': 0, 'USB': 1, 'AM': 2, 'CW': 3, 'NFM': 5, 'CWR': 7}
SWITCHES = {'pre': 2, 'agc': 0x12, 'nb': 0x22, 'comp': 0x44, 'lock': 0x50}
LEVELS = {'volume': 1, 'squelch': 3, 'pitch': 9, 'power': 10, 'speed': 12}


class Controller:
    def __init__(self, args):
        self.args = args
        self.cat = None
        self.guard = threading.Lock()
        self.frequency = 14200000
        self.mode = 'USB'
        self.values = dict(volume=90, squelch=0, pitch=128, power=25, speed=90)
        self.switches = dict(pre=0, agc=1, nb=0, comp=0, lock=0)
        self.tuner = 0
        self.split = 0
        self.vfo = 'A'
        self.spectrum = None
        self.iq_time = 0
        self.iq_error = 'I/Q capture not selected'
        self.iq_clipped = False
        if args.iq_device is not None:
            threading.Thread(target=self.capture, daemon=True).start()

    def connect(self):
        if self.args.demo:
            return 'Demonstration only'
        if self.cat:
            return 'Already connected'
        import serial
        # Opening with control lines disabled; the supplied cable must be
        # inserted in the head AFTER radio startup, per the vendor manual.
        port = serial.Serial()
        port.port = self.args.port
        port.baudrate = 19200
        port.timeout = 0.05
        port.dtr = False
        port.rts = False
        port.open()
        candidate = CAT(port, self.args.address)
        try:
            self.frequency = candidate.read_frequency()
        except Exception:
            port.close()
            raise
        self.cat = candidate
        return 'CAT connected'

    def capture(self):
        try:
            import numpy as np
            import sounddevice as sd
            from iq import spectrum
            device = self.args.iq_device
            device = int(device) if device.isdigit() else device
            sd.check_input_settings(device=device, channels=2,
                                    samplerate=self.args.sample_rate, dtype='float32')
            def callback(samples, frames, timestamp, status):
                self.iq_error = str(status) if status else ''
                self.iq_clipped = bool(np.max(np.abs(samples)) >= 0.99)
                self.spectrum = spectrum(samples, self.args.swap_iq)
                self.iq_time = time.monotonic()
            with sd.InputStream(device=device, channels=2, samplerate=self.args.sample_rate,
                                dtype='float32', blocksize=2048, callback=callback):
                while True:
                    time.sleep(1)
        except Exception as exc:
            self.iq_error = str(exc)

    def status(self):
        error = ''
        meters = {}
        if self.cat:
            try:
                self.frequency = self.cat.read_frequency()
                mode = self.cat.transaction([4])
                if not mode:
                    raise ValueError('Empty mode response')
                self.mode = next((k for k, v in MODES.items() if v == mode[0]), 'Unknown')
            except Exception as exc:
                error = str(exc)
            # Optional meters must not make the whole controller unavailable.
            for name, code in [('signal', 2), ('rf_power', 0x11), ('swr', 0x12)]:
                try:
                    meters[name] = level_decode(self.cat.transaction([0x15, code]))
                except Exception:
                    meters[name] = None
            try:
                data = self.cat.transaction([0x1c, 1])
                self.tuner = data[0] if data else None
            except Exception:
                self.tuner = None
        return dict(demo=self.args.demo, connected=bool(self.cat), frequency=self.frequency,
                    mode=self.mode, tuner=self.tuner, meters=meters, error=error,
                    values=self.values, switches=self.switches, vfo=self.vfo, split=self.split,
                    spectrum=self.spectrum if time.monotonic() - self.iq_time < 2 else None,
                    iq_error=self.iq_error, iq_clipped=self.iq_clipped,
                    sample_rate=self.args.sample_rate, allow_tune=self.args.allow_tune,
                    log=self.cat.log if self.cat else [])

    def action(self, name, value):
        if name == 'connect':
            return self.connect()
        if not self.args.demo and not self.cat:
            raise ValueError('Connect CAT first')
        cat = self.cat
        if name == 'frequency':
            hz = int(value)
            if not 500000 <= hz <= 30000000:
                raise ValueError('Frequency must be 0.5–30 MHz')
            self.frequency = cat.set_frequency(hz) if cat else hz
        elif name == 'mode':
            if value not in MODES:
                raise ValueError('Unknown mode')
            if cat:
                cat.transaction([6], bytes([MODES[value], 1]), True)
                data = cat.transaction([4])
                if not data or data[0] != MODES[value]:
                    raise ValueError('Mode did not read back correctly')
            self.mode = value
        elif name in LEVELS:
            level = int(value)
            if not 0 <= level <= 255:
                raise ValueError('Level must be 0–255')
            if cat:
                command = [0x14, LEVELS[name]]
                cat.transaction(command, level_encode(level), True)
                actual = level_decode(cat.transaction(command))
                self.values[name] = actual
                if actual != level:
                    raise ValueError(f'Radio returned level {actual}; requested {level}')
            else:
                self.values[name] = level
        elif name in SWITCHES:
            value = int(value)
            if value not in (range(4) if name == 'agc' else range(2)):
                raise ValueError('Invalid switch state')
            if cat:
                command = [0x16, SWITCHES[name]]
                cat.transaction(command, bytes([value]), True)
                actual = cat.transaction(command)
                if not actual or actual[0] != value:
                    raise ValueError('Switch did not read back correctly')
            self.switches[name] = value
        elif name == 'att':
            if cat:
                cat.transaction([0x11], b'\x00', True)
                actual = cat.transaction([0x11])
                return 'ATT returned: ' + actual.hex(' ')
            return 'Demo ATT toggled'
        elif name == 'vfo':
            if value not in ('A', 'B', 'SWAP'):
                raise ValueError('Unknown VFO operation')
            if cat:
                cat.transaction([7, {'A': 0, 'B': 1, 'SWAP': 0xb0}[value]], write=True)
            self.vfo = value if value != 'SWAP' else self.vfo
        elif name == 'split':
            value = int(value)
            if value not in (0, 1):
                raise ValueError('Invalid split state')
            if cat:
                cat.transaction([0xf], bytes([value]), True)
            self.split = value
        elif name == 'tuner':
            value = int(value)
            if value not in (0, 1, 2):
                raise ValueError('Invalid tuner state')
            if value == 2 and not self.args.demo and not self.args.allow_tune:
                raise ValueError('RF tuning disabled. Restart with --allow-tune after bench checks.')
            if cat:
                # Never retry an RF-producing command automatically.
                cat.transaction([0x1c, 1], bytes([value]), True)
            else:
                self.tuner = 1 if value == 2 else value
        elif name == 'receive':
            if cat:
                cat.transaction([0x1c, 0], b'\x00', True)
            return 'Receive command sent; verify radio state'
        else:
            raise ValueError('Unsupported operation')
        return 'Demo updated' if self.args.demo else 'Command completed'


def create_app(args):
    app = Flask(__name__)
    controller = Controller(args)
    token = secrets.token_hex(24)
    app.config['controller'] = controller

    @app.get('/')
    def index():
        return render_template('index.html', token=token)

    @app.get('/api/state')
    def state():
        with controller.guard:
            return jsonify(controller.status())

    @app.post('/api/action')
    def action():
        if request.headers.get('X-G90-Token') != token or not request.is_json:
            return jsonify(error='Invalid local session'), 403
        try:
            body = request.get_json()
            with controller.guard:
                message = controller.action(body['name'], body.get('value'))
            return jsonify(message=message)
        except Exception as exc:
            return jsonify(error=str(exc)), 400
    return app


def arguments():
    parser = argparse.ArgumentParser(description='Local G90 touchscreen controller')
    parser.add_argument('--live', action='store_true', help='Enable physical CAT connection')
    parser.add_argument('--port', help='/dev/serial/by-id/... (use --live)')
    parser.add_argument('--address', type=lambda x: int(x, 16), default=0x88)
    parser.add_argument('--iq-device', help='Stereo PortAudio input index or name')
    parser.add_argument('--sample-rate', type=int, choices=[48000, 96000], default=48000)
    parser.add_argument('--swap-iq', action='store_true')
    parser.add_argument('--allow-tune', action='store_true', help='Allow RF-producing ATU start')
    args = parser.parse_args()
    if args.live and not args.port:
        parser.error('--live requires --port')
    if not 0 <= args.address <= 255:
        parser.error('Address must be one byte')
    args.demo = not args.live
    return args


if __name__ == '__main__':
    create_app(arguments()).run(host='127.0.0.1', port=8080, threaded=True, debug=False)
