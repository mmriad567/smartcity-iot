import unittest
from unittest.mock import MagicMock

import scripts.simulator as sim


class SimulatorStateTest(unittest.TestCase):

    def setUp(self):
        sim.state.update({'tank_pct': 80.0, 'soil_pct': 50.0, 'ldr': 2000, 'bin_pct': 20.0})
        sim.cmd_state.update({'pump': 'auto', 'light': 'auto'})
        sim.tick_count = 0

    def test_tank_decreases_on_tick(self):
        before = sim.state['tank_pct']
        sim.update_state()
        self.assertLess(sim.state['tank_pct'], before)

    def test_bin_increases_on_tick(self):
        before = sim.state['bin_pct']
        sim.update_state()
        self.assertGreater(sim.state['bin_pct'], before)

    def test_tank_never_below_zero(self):
        sim.state['tank_pct'] = 0.0
        for _ in range(5):
            sim.update_state()
        self.assertGreaterEqual(sim.state['tank_pct'], 0.0)

    def test_bin_never_above_hundred(self):
        sim.state['bin_pct'] = 100.0
        for _ in range(5):
            sim.update_state()
        self.assertLessEqual(sim.state['bin_pct'], 100.0)

    def test_soil_increases_when_pump_manual_on(self):
        sim.state['soil_pct'] = 40.0
        sim.cmd_state['pump'] = 'on'
        sim.update_state()
        self.assertGreater(sim.state['soil_pct'], 40.0)

    def test_soil_decreases_when_pump_off(self):
        sim.state['soil_pct'] = 40.0
        sim.cmd_state['pump'] = 'off'
        sim.update_state()
        self.assertLess(sim.state['soil_pct'], 40.0)

    def test_soil_increases_when_auto_and_dry(self):
        sim.state['soil_pct'] = 20.0
        sim.cmd_state['pump'] = 'auto'
        sim.update_state()
        self.assertGreater(sim.state['soil_pct'], 20.0)

    def test_soil_decreases_when_auto_and_wet(self):
        sim.state['soil_pct'] = 60.0
        sim.cmd_state['pump'] = 'auto'
        sim.update_state()
        self.assertLess(sim.state['soil_pct'], 60.0)

    def test_pump_locked_when_tank_critical(self):
        sim.state['tank_pct'] = 5.0
        sim.state['soil_pct'] = 20.0
        sim.cmd_state['pump'] = 'on'
        # Pump requested ON but tank is critical -> soil should not increase from pump
        before = sim.state['soil_pct']
        sim.update_state()
        # Soil can only decrease (no pump); it must not jump up by +5
        self.assertLess(sim.state['soil_pct'], before + 1.0)

    def test_build_telemetry_shape(self):
        payload = sim.build_telemetry()
        for key in ('node_id', 'tank_pct', 'soil_pct', 'ldr', 'bin_pct', 'ts'):
            self.assertIn(key, payload)
        self.assertEqual(payload['node_id'], 'esp32-01')
        self.assertIsInstance(payload['ldr'], int)

    def test_on_message_applies_pump_command(self):
        msg = MagicMock()
        msg.topic = sim.TOPIC_COMMAND
        msg.payload = b'{"pump":"on"}'
        sim.on_message(None, None, msg)
        self.assertEqual(sim.cmd_state['pump'], 'on')

    def test_on_message_ignores_invalid_payload(self):
        msg = MagicMock()
        msg.topic = sim.TOPIC_COMMAND
        msg.payload = b'{not json'
        try:
            sim.on_message(None, None, msg)
        except Exception as e:
            self.fail(f'on_message raised on bad JSON: {e}')

    def test_on_message_ignores_unknown_command(self):
        sim.cmd_state['pump'] = 'auto'
        msg = MagicMock()
        msg.topic = sim.TOPIC_COMMAND
        msg.payload = b'{"pump":"garbage"}'
        sim.on_message(None, None, msg)
        self.assertEqual(sim.cmd_state['pump'], 'auto')


if __name__ == '__main__':
    unittest.main()
