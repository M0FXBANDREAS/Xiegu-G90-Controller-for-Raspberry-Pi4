"""Small, serialized G90 CI-V transport. No automatic transmit commands."""
import threading
import time


def bcd_encode(value, size):
    if not isinstance(value, int) or not 0 <= value < 10 ** (size * 2):
        raise ValueError('Value outside BCD range')
    s = f'{value:0{size * 2}d}'
    return bytes(int(s[i:i + 2], 16) for i in range(len(s) - 2, -1, -2))


def bcd_decode(data):
    value = 0
    for i, byte in enumerate(data):
        if byte >> 4 > 9 or byte & 15 > 9:
            raise ValueError('Invalid BCD response')
        value += ((byte >> 4) * 10 + (byte & 15)) * 100 ** i
    return value


def level_encode(value):
    # CI-V levels use most significant BCD pair first, unlike frequencies.
    if not 0 <= value <= 255:
        raise ValueError('Level outside 0..255')
    return bcd_encode(value, 2)[::-1]


def level_decode(data):
    if len(data) != 2:
        raise ValueError('Expected two-byte level')
    return bcd_decode(data[::-1])


class CAT:
    def __init__(self, serial_port, address=0x88):
        self.serial = serial_port
        self.address = address
        self.lock = threading.Lock()
        self.log = []

    def transaction(self, command, data=b'', write=False):
        command = bytes(command)
        frame = b'\xfe\xfe' + bytes([self.address, 0xe0]) + command + data + b'\xfd'
        with self.lock:
            self.serial.reset_input_buffer()
            self.serial.write(frame)
            self.log.append(frame.hex(' ').upper())
            self.log = self.log[-20:]
            deadline = time.monotonic() + 1.2
            buffer = bytearray()
            while time.monotonic() < deadline:
                byte = self.serial.read(1)
                if not byte:
                    continue
                buffer.extend(byte)
                if len(buffer) > 512:
                    buffer.clear()
                if byte != b'\xfd':
                    continue
                start = buffer.find(b'\xfe\xfe')
                packet = bytes(buffer[start:]) if start >= 0 else b''
                buffer.clear()
                if len(packet) < 6 or packet[2:4] != bytes([0xe0, self.address]):
                    continue  # cable echo, broadcasts, and other addresses
                payload = packet[4:-1]
                if payload == b'\xfa':
                    raise RuntimeError('Radio rejected command')
                if write and payload == b'\xfb':
                    return b''
                if payload.startswith(command):
                    return payload[len(command):]
            raise TimeoutError('No matching CAT response; check power, cable and address')

    def read_frequency(self):
        data = self.transaction([3])
        if len(data) != 5:
            raise ValueError('Unexpected frequency response')
        return bcd_decode(data)

    def set_frequency(self, hz):
        if not 500_000 <= hz <= 30_000_000:
            raise ValueError('Receive frequency must be 0.5–30 MHz')
        self.transaction([5], bcd_encode(hz, 5), True)
        return self.read_frequency()
