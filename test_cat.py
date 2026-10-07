import unittest
from cat import CAT, bcd_encode, bcd_decode, level_encode, level_decode


class FakeSerial:
    def __init__(self, response):
        self.response = response
        self.pending = b''
        self.sent = []

    def reset_input_buffer(self):
        self.pending = b''

    def write(self, frame):
        self.sent.append(frame)
        self.pending = frame + self.response

    def read(self, n):
        data, self.pending = self.pending[:n], self.pending[n:]
        return data


class ProtocolTests(unittest.TestCase):
    def test_frequency_wire_example(self):
        self.assertEqual(bcd_encode(14200000, 5), bytes.fromhex('00 00 20 14 00'))
        self.assertEqual(bcd_decode(bytes.fromhex('00 00 20 14 00')), 14200000)

    def test_level_byte_order(self):
        self.assertEqual(level_encode(255), bytes.fromhex('02 55'))
        self.assertEqual(level_decode(bytes.fromhex('02 55')), 255)
        for value in range(256):
            self.assertEqual(level_decode(level_encode(value)), value)

    def test_invalid_bcd_rejected(self):
        with self.assertRaises(ValueError):
            level_decode(bytes.fromhex('00 FA'))

    def test_echo_and_other_radio_ignored(self):
        response = bytes.fromhex('FE FE E0 70 03 00 00 10 07 00 FD FE FE E0 88 03 00 00 20 14 00 FD')
        serial = FakeSerial(response)
        self.assertEqual(CAT(serial).read_frequency(), 14200000)
        self.assertEqual(serial.sent[0], bytes.fromhex('FE FE 88 E0 03 FD'))

    def test_rejection_reported(self):
        with self.assertRaisesRegex(RuntimeError, 'rejected'):
            CAT(FakeSerial(bytes.fromhex('FE FE E0 88 FA FD'))).transaction([5], b'12345', True)

    def test_ack_is_not_a_read_response(self):
        serial = FakeSerial(bytes.fromhex('FE FE E0 88 FB FD FE FE E0 88 04 01 01 FD'))
        self.assertEqual(CAT(serial).transaction([4]), b'\x01\x01')

    def test_bad_frequency_never_sent(self):
        serial = FakeSerial(b'')
        with self.assertRaises(ValueError):
            CAT(serial).set_frequency(40000000)
        self.assertEqual(serial.sent, [])


if __name__ == '__main__':
    unittest.main()
