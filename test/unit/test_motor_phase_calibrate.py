#!/usr/bin/env python3
# Unit tests for the pure DSP/LUT helpers in motor_phase_calibrate.py
#
# Run directly:  python3 test/unit/test_motor_phase_calibrate.py
#
# The module is loaded by file path so no Klipper runtime is required —
# the functions under test are dependency-free by design.

import math, os, random, sys, unittest
import importlib.util

MODULE_PATH = os.path.join(os.path.dirname(__file__), '..', '..',
                           'klippy', 'extras', 'motor_phase_calibrate.py')

spec = importlib.util.spec_from_file_location(
    "motor_phase_calibrate", MODULE_PATH)
mpc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mpc)


def synth_thetas(cycles=8., count=4096):
    return [2. * math.pi * cycles * i / count for i in range(count)]


class TestExtractHarmonics(unittest.TestCase):
    def test_clean_two_harmonics(self):
        thetas = synth_thetas()
        values = [3.0 * math.cos(2 * t + 0.7)
                  + 1.5 * math.cos(4 * t - 1.2) + 10.0  # DC offset
                  for t in thetas]
        result = mpc.extract_harmonics(thetas, values, [2, 4])
        mag2, ph2 = result[2]
        mag4, ph4 = result[4]
        self.assertAlmostEqual(mag2, 3.0, delta=0.01)
        self.assertAlmostEqual(ph2, 0.7, delta=0.01)
        self.assertAlmostEqual(mag4, 1.5, delta=0.01)
        self.assertAlmostEqual(ph4, -1.2, delta=0.01)

    def test_with_noise(self):
        rng = random.Random(42)
        thetas = synth_thetas(cycles=16., count=8192)
        values = [2.0 * math.cos(2 * t - 2.5)
                  + 0.8 * math.cos(4 * t + 1.9)
                  + rng.gauss(0., 1.) for t in thetas]
        result = mpc.extract_harmonics(thetas, values, [2, 4])
        mag2, ph2 = result[2]
        mag4, ph4 = result[4]
        self.assertAlmostEqual(mag2, 2.0, delta=0.1)
        self.assertAlmostEqual(ph2, -2.5, delta=0.1)
        self.assertAlmostEqual(mag4, 0.8, delta=0.1)
        self.assertAlmostEqual(ph4, 1.9, delta=0.15)

    def test_nonuniform_non_integer_window(self):
        # Calibration samples come from the accelerometer during a trimmed
        # cruise window, not from a perfect one-period DFT grid.  The helper
        # should therefore fit the real basis functions directly.
        rng = random.Random(7)
        thetas = []
        values = []
        for i in range(1500):
            base = 2. * math.pi * 5.37 * i / 1500
            theta = base + rng.uniform(-0.0007, 0.0007)
            thetas.append(theta)
            values.append(1.7 * math.cos(2 * theta + 0.42)
                          + 0.55 * math.cos(4 * theta - 2.1)
                          + 0.02 * math.cos(theta)
                          + 3.0)
        result = mpc.extract_harmonics(thetas, values, [2, 4])
        self.assertAlmostEqual(result[2][0], 1.7, delta=0.02)
        self.assertAlmostEqual(result[2][1], 0.42, delta=0.02)
        self.assertAlmostEqual(result[4][0], 0.55, delta=0.02)
        self.assertAlmostEqual(result[4][1], -2.1, delta=0.02)

    def test_absent_harmonic_is_small(self):
        thetas = synth_thetas()
        values = [5.0 * math.cos(2 * t) for t in thetas]
        result = mpc.extract_harmonics(thetas, values, [2, 4])
        self.assertAlmostEqual(result[2][0], 5.0, delta=0.01)
        self.assertLess(result[4][0], 0.05)

    def test_empty_input(self):
        result = mpc.extract_harmonics([], [], [2, 4])
        self.assertEqual(result[2], (0., 0.))
        self.assertEqual(result[4], (0., 0.))


class TestAccelToPhaseCoeffs(unittest.TestCase):
    def test_known_conversion(self):
        # A = 100 mm/s^2 at harmonic 2, 10 electrical rev/s, 0.2 mm
        # electrical wavelength (U1 X/Y: 4 * 0.05 mm full steps)
        elec_freq = 10.
        w_e = 2. * math.pi * elec_freq
        coeffs = mpc.accel_to_phase_coeffs({2: (100., 0.3)}, elec_freq, 0.2)
        mag, phase = coeffs[2]
        expected_pos = 100. / (2 * w_e) ** 2  # mm
        expected_mag = expected_pos * 2. * math.pi / 0.2  # rad
        self.assertAlmostEqual(mag, expected_mag, places=9)
        self.assertAlmostEqual(phase, 0.3 + math.pi / 2., places=9)

    def test_phase_wraps(self):
        coeffs = mpc.accel_to_phase_coeffs({4: (10., 3.0)}, 5., 0.2)
        _, phase = coeffs[4]
        self.assertLessEqual(phase, math.pi)
        self.assertGreaterEqual(phase, -math.pi)
        self.assertAlmostEqual(phase, 3.0 + math.pi / 2. - 2. * math.pi,
                               places=9)

    def test_higher_harmonic_smaller_ripple(self):
        # Same accel magnitude at a higher harmonic means smaller position
        # ripple (double differentiation) — coefficient must shrink by n^2
        coeffs = mpc.accel_to_phase_coeffs(
            {2: (50., 0.), 4: (50., 0.)}, 8., 0.2)
        self.assertAlmostEqual(coeffs[2][0] / coeffs[4][0], 4., places=6)


class TestCombineCoeffs(unittest.TestCase):
    def test_identical_sets(self):
        c = {2: (1.0, 0.5), 4: (0.3, -1.0)}
        out = mpc.combine_coeffs([c, c, c])
        self.assertAlmostEqual(out[2][0], 1.0, places=9)
        self.assertAlmostEqual(out[2][1], 0.5, places=9)
        self.assertAlmostEqual(out[4][0], 0.3, places=9)

    def test_opposite_phases_cancel(self):
        out = mpc.combine_coeffs([{2: (1.0, 0.)}, {2: (1.0, math.pi)}])
        self.assertLess(out[2][0], 1e-9)

    def test_empty(self):
        self.assertEqual(mpc.combine_coeffs([]), {})


class TestBuildCorrectionLut(unittest.TestCase):
    def test_zero_coeffs_pure_sine(self):
        lut = mpc.build_correction_lut({}, 512, 248)
        self.assertEqual(len(lut), 512)
        self.assertEqual(lut[0], (248, 0))
        self.assertEqual(lut[128], (0, 248))
        self.assertEqual(lut[256], (-248, 0))
        self.assertEqual(lut[384], (0, -248))

    def test_all_entries_in_range(self):
        # Even absurdly large corrections must stay in the 9-bit range
        lut = mpc.build_correction_lut({2: (2.0, 0.3), 4: (1.5, -2.0)},
                                       512, 255)
        for ia, ib in lut:
            self.assertGreaterEqual(ia, -256)
            self.assertLessEqual(ia, 255)
            self.assertGreaterEqual(ib, -256)
            self.assertLessEqual(ib, 255)
            self.assertIsInstance(ia, int)
            self.assertIsInstance(ib, int)

    def test_constant_amplitude(self):
        # Phase-only correction must preserve the current vector magnitude
        lut = mpc.build_correction_lut({2: (0.1, 1.0)}, 256, 200)
        for ia, ib in lut:
            self.assertAlmostEqual(math.hypot(ia, ib), 200., delta=1.)

    def test_correction_shifts_phase(self):
        # delta(theta) = 0.1*sin(2*theta): at theta=pi/4 the shift is
        # maximal (+0.1 rad); verify against direct computation
        lut = mpc.build_correction_lut({2: (0.1, 0.)}, 512, 248)
        i = 64  # theta = pi/4
        theta = 2. * math.pi * i / 512
        expect_ia = round(248 * math.cos(theta + 0.1))
        expect_ib = round(248 * math.sin(theta + 0.1))
        self.assertEqual(lut[i], (expect_ia, expect_ib))


class TestRoundTrip(unittest.TestCase):
    def test_measure_correct_measure(self):
        """Synthesize accel from a known position ripple, extract harmonics,
        convert to correction coefficients, and verify the correction
        cancels the ripple model."""
        elec_freq = 12.5
        elec_wavelength = 0.2
        w_e = 2. * math.pi * elec_freq
        # True position ripple: x(theta) = P2*cos(2 th + p2) + P4*cos(...)
        ripple = {2: (0.002, 1.1), 4: (0.0008, -0.4)}  # mm
        thetas = synth_thetas(cycles=24., count=8192)
        accel = []
        for t in thetas:
            a = 0.
            for n, (P, p) in ripple.items():
                # x = P cos(n th + p), th = w_e * time =>
                # a = -(n w_e)^2 P cos(n th + p)
                a += -(n * w_e) ** 2 * P * math.cos(n * t + p)
            accel.append(a)
        measured = mpc.extract_harmonics(thetas, accel, [2, 4])
        coeffs = mpc.accel_to_phase_coeffs(measured, elec_freq,
                                           elec_wavelength)
        for n, (P, p) in ripple.items():
            mag, phase = coeffs[n]
            # Expected correction magnitude: ripple in electrical radians
            expect_mag = P * 2. * math.pi / elec_wavelength
            self.assertAlmostEqual(mag, expect_mag, delta=expect_mag * .02)
            # a has phase p + pi (negated cos); correction sine convention
            # adds pi/2: total expected phase = p + pi + pi/2 (wrapped).
            # The correction delta(theta) evaluated as a shift must OPPOSE
            # the ripple: check delta at the ripple's positive peak.
            theta_peak = -p / n  # ripple max where cos(n th + p) = 1
            delta = mag * math.sin(n * theta_peak + phase)
            ripple_rad = P * 2. * math.pi / elec_wavelength
            self.assertAlmostEqual(delta, -ripple_rad,
                                   delta=ripple_rad * .02)


class TestPackLutEntries(unittest.TestCase):
    def test_signed_little_endian(self):
        data = mpc.pack_lut_entries([(-1, -256), (255, 0)], 0, 2)
        self.assertEqual(data, b'\xff\xff\x00\xff\xff\x00\x00\x00')

    def test_chunk_bounds(self):
        lut = [(i, -i) for i in range(10)]
        data = mpc.pack_lut_entries(lut, 8, 8)  # only 2 entries remain
        self.assertEqual(len(data), 8)
        self.assertEqual(data[:2], (8).to_bytes(2, 'little'))

    def test_full_lut_size(self):
        lut = mpc.build_correction_lut({}, 512, 248)
        total = b''.join(mpc.pack_lut_entries(lut, s, 8)
                         for s in range(0, 512, 8))
        self.assertEqual(len(total), 512 * 4)


class TestCorrectionStrings(unittest.TestCase):
    def test_round_trip(self):
        coeffs = {2: (0.012345678, -1.5), 4: (0.0004, 3.0)}
        s = mpc.format_correction(coeffs)
        parsed = mpc.parse_correction(s)
        for n in coeffs:
            self.assertAlmostEqual(parsed[n][0], coeffs[n][0], places=8)
            self.assertAlmostEqual(parsed[n][1], coeffs[n][1], places=5)

    def test_empty_and_none(self):
        self.assertIsNone(mpc.parse_correction(None))
        self.assertIsNone(mpc.parse_correction(''))
        self.assertIsNone(mpc.parse_correction('   '))

    def test_invalid_raises(self):
        with self.assertRaises(ValueError):
            mpc.parse_correction('2:0.1')
        with self.assertRaises(ValueError):
            mpc.parse_correction('nonsense')


if __name__ == '__main__':
    unittest.main(verbosity=2)
