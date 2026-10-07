import unittest
import numpy as np
from iq import spectrum


class IQTests(unittest.TestCase):
    def test_known_positive_frequency_and_reversal(self):
        phase = 2 * np.pi * 256 * np.arange(2048) / 2048
        samples = np.column_stack([.5 * np.cos(phase), .5 * np.sin(phase)])
        normal = spectrum(samples)
        reversed_iq = spectrum(samples, swap=True)
        self.assertEqual(int(np.argmax(normal)), 320)
        self.assertEqual(int(np.argmax(reversed_iq)), 192)
        self.assertAlmostEqual(max(normal), -6, delta=.2)

    def test_silence_is_finite(self):
        self.assertTrue(np.isfinite(spectrum(np.zeros((2048, 2)))).all())

    def test_mono_rejected(self):
        with self.assertRaises(ValueError):
            spectrum(np.zeros((2048, 1)))
