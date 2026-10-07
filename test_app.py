import re
import unittest
from types import SimpleNamespace
from app import create_app, Controller


def args(demo=True):
    return SimpleNamespace(demo=demo, iq_device=None, allow_tune=False,
                           sample_rate=48000, port='unused', address=0x88)


class AppTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(args())
        self.client = self.app.test_client()
        page = self.client.get('/').get_data(as_text=True)
        self.token = re.search(r'const TOKEN="([a-f0-9]+)"', page)[1]

    def post(self, name, value=None):
        return self.client.post('/api/action', json=dict(name=name, value=value),
                                headers={'X-G90-Token': self.token})

    def test_demo_startup_no_radio(self):
        state = self.client.get('/api/state').get_json()
        self.assertTrue(state['demo'])
        self.assertFalse(state['connected'])
        self.assertIsNone(state['spectrum'])
        self.assertEqual(state['log'], [])

    def test_local_session_required(self):
        self.assertEqual(self.client.post('/api/action', json={'name': 'connect'}).status_code, 403)

    def test_demo_frequency_readback(self):
        self.assertEqual(self.post('frequency', 7100000).status_code, 200)
        self.assertEqual(self.client.get('/api/state').get_json()['frequency'], 7100000)

    def test_invalid_operations_rejected(self):
        for name, value in [('frequency', 40_000_000), ('mode', 'INVALID'),
                            ('power', 300), ('ptt', 1), ('sweep', 1)]:
            self.assertEqual(self.post(name, value).status_code, 400)

    def test_demo_tuner_does_not_send_commands(self):
        self.assertEqual(self.post('tuner', 2).status_code, 200)
        self.assertIsNone(self.app.config['controller'].cat)

    def test_live_tune_gate_no_frame_sent(self):
        class FakeCAT:
            def transaction(self, *a, **kw):
                raise AssertionError('RF command must not be sent')
        controller = Controller(args(demo=False))
        controller.cat = FakeCAT()
        with self.assertRaisesRegex(ValueError, 'RF tuning disabled'):
            controller.action('tuner', 2)


if __name__ == '__main__':
    unittest.main()
