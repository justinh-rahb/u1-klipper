# Motor phase current calibration and runtime control for Snapmaker U1
#
# Copyright (C) 2024  Snapmaker U1 Klipper Fork Contributors
#
# This file may be distributed under the terms of the GNU GPLv3 license.
#
# Direct Phase Current Control ("motor ANC")
# ==========================================
# Stepper motors emit vibration/noise when the commanded stator field, rotor
# flux, and mechanical load produce periodic force/torque error.  This module
# measures acceleration-error harmonics with the printer's accelerometer and
# fits a small periodic tangential field-angle correction
#
#     delta(theta) = sum_n( mag_n * sin(n*theta + phase_n) )
#
# and applies it in realtime by driving the TMC2240 DIRECT_MODE register
# from an MCU-side lookup table synchronized to the stepper position
# (see src/motor_phase_calibrate.c).
#
# Requirements/limits (v1):
#   - X/Y axes with SPI-connected TMC2240 drivers only.  UART-connected
#     TMC2240s can load this module but cannot calibrate or run.
#   - Runtime application is gated on MOTOR_PHASE_BENCH confirming the
#     MCU has SPI timing headroom at the configured update rate.
#   - While GCONF.direct_mode is enabled the TMC's internal sequencer
#     (MSCNT) does not follow step pulses; after disabling, the physical
#     rotor phase may differ from the sequencer phase by up to two full
#     steps.  Calibration therefore ends with a "re-home" advisory.
#
# Persisted results (SAVE_CONFIG):
#   {axis}_forward_correction / {axis}_reverse_correction:
#       comma-separated "harmonic:magnitude:phase" terms (radians)
#   {axis}_phase_invert: 0/1, sign of the step-position -> electrical
#       phase relationship measured during calibration

import math, logging

######################################################################
# Pure DSP / LUT helpers (unit-testable, no Klipper dependencies)
######################################################################

def _solve_linear_system(a, b):
    """Solve Ax=b with partial-pivot Gauss-Jordan elimination."""
    n = len(b)
    if not n:
        return []
    a = [row[:] for row in a]
    b = b[:]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[pivot][col]) < 1e-18:
            return [0.] * n
        if pivot != col:
            a[col], a[pivot] = a[pivot], a[col]
            b[col], b[pivot] = b[pivot], b[col]
        inv = 1. / a[col][col]
        for j in range(col, n):
            a[col][j] *= inv
        b[col] *= inv
        for r in range(n):
            if r == col:
                continue
            f = a[r][col]
            if not f:
                continue
            for j in range(col, n):
                a[r][j] -= f * a[col][j]
            b[r] -= f * b[col]
    return b

def extract_harmonics(thetas, values, harmonics):
    """Fit real harmonic coefficients at electrical angles.

    Returns {n: (magnitude, phase)} such that
        values[i] ~= sum_n( magnitude_n * cos(n*thetas[i] + phase_n) )
    plus DC and broadband noise.

    This is a real least-squares fit over the basis
        1, cos(n*theta), sin(n*theta)
    rather than a raw DFT bin.  It produces the same result as a DFT for
    uniform integer-period samples, but remains well-defined when the
    accelerometer samples are slightly non-uniform or the cruise window does
    not land exactly on an integer electrical-period boundary.
    """
    m = len(values)
    if not m:
        return {n: (0., 0.) for n in harmonics}
    harmonics = list(harmonics)
    cols = 1 + 2 * len(harmonics)
    ata = [[0.] * cols for _ in range(cols)]
    aty = [0.] * cols
    for theta, v in zip(thetas, values):
        row = [1.]
        for n in harmonics:
            a = n * theta
            row.append(math.cos(a))
            row.append(math.sin(a))
        for i, ri in enumerate(row):
            aty[i] += ri * v
            for j, rj in enumerate(row):
                ata[i][j] += ri * rj
    # Tiny ridge protects against degenerate windows without affecting the
    # normal calibration case (many samples, two harmonics).
    for i in range(cols):
        ata[i][i] += max(1., ata[i][i]) * 1e-12
    coeff = _solve_linear_system(ata, aty)
    result = {}
    for n in harmonics:
        idx = 1 + 2 * harmonics.index(n)
        c = coeff[idx]
        s = coeff[idx + 1]
        # c*cos(n*t) + s*sin(n*t) == mag*cos(n*t + phase)
        result[n] = (math.hypot(c, s), math.atan2(-s, c))
    return result

def accel_to_phase_coeffs(accel_harmonics, elec_freq, elec_wavelength):
    """Convert measured acceleration harmonics to phase correction terms.

    accel_harmonics: {n: (accel_magnitude_mm_s2, phase)} measured against
        electrical angle theta, cosine convention (see extract_harmonics).
    elec_freq: electrical rotations per second during the measurement.
    elec_wavelength: mm of axis travel per electrical period (4 full steps).

    The real-domain model is:
      Lorentz force / torque is proportional to the interaction of the
      commanded stator current vector with rotor flux.  For small errors,
      a tangential electrical-angle perturbation changes torque roughly
      linearly, so the first-order correction can be represented as a small
      phase shift delta(theta).

    An acceleration harmonic a(theta) = A*cos(n*theta + p) integrates to a
    position ripple x(theta) = -A/(n*w_e)^2 * cos(n*theta + p) with
    w_e = 2*pi*elec_freq.  The compensating electrical-angle correction is
    the ripple converted to electrical radians and negated:
        delta(theta) = A/(n*w_e)^2 * (2*pi/elec_wavelength)
                       * cos(n*theta + p)
    Returned in sine convention: {n: (mag, phase)} for mag*sin(n*t+phase).
    """
    coeffs = {}
    w_e = 2. * math.pi * elec_freq
    for n, (mag, phase) in accel_harmonics.items():
        pos_amp = mag / ((n * w_e) ** 2)
        theta_amp = pos_amp * 2. * math.pi / elec_wavelength
        # cos(x + p) == sin(x + p + pi/2)
        coeffs[n] = (theta_amp, _wrap_angle(phase + .5 * math.pi))
    return coeffs

def combine_coeffs(coeff_list):
    """Average correction coefficient sets by phase-aware vector mean."""
    if not coeff_list:
        return {}
    harmonics = set()
    for c in coeff_list:
        harmonics.update(c.keys())
    out = {}
    for n in sorted(harmonics):
        re = im = 0.
        for c in coeff_list:
            mag, phase = c.get(n, (0., 0.))
            re += mag * math.cos(phase)
            im += mag * math.sin(phase)
        re /= len(coeff_list)
        im /= len(coeff_list)
        out[n] = (math.hypot(re, im), math.atan2(im, re))
    return out

def build_correction_lut(coeffs, lut_size, amplitude):
    """Build a corrected current-vector LUT.

    coeffs: {n: (mag, phase)} in sine convention (radians of electrical
        angle correction).  amplitude: peak DAC value (<= 255).
    Returns a list of lut_size (ia, ib) integer tuples in [-256, 255].
    """
    lut = []
    for i in range(lut_size):
        theta = 2. * math.pi * i / lut_size
        delta = 0.
        for n, (mag, phase) in coeffs.items():
            delta += mag * math.sin(n * theta + phase)
        ia = int(round(amplitude * math.cos(theta + delta)))
        ib = int(round(amplitude * math.sin(theta + delta)))
        lut.append((max(-256, min(255, ia)), max(-256, min(255, ib))))
    return lut

def pack_lut_entries(lut, start, count):
    """Pack LUT entries as little-endian int16 (ia, ib) pairs."""
    out = bytearray()
    for ia, ib in lut[start:start+count]:
        out += (ia & 0xffff).to_bytes(2, 'little')
        out += (ib & 0xffff).to_bytes(2, 'little')
    return bytes(out)

def format_correction(coeffs):
    return ",".join("%d:%.9f:%.6f" % (n, mag, phase)
                    for n, (mag, phase) in sorted(coeffs.items()))

def parse_correction(value):
    """Parse "n:mag:phase,..." into {n: (mag, phase)}; None/"" -> None."""
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    coeffs = {}
    for term in value.split(','):
        parts = term.strip().split(':')
        if len(parts) != 3:
            raise ValueError("Invalid correction term '%s'" % (term,))
        coeffs[int(parts[0])] = (float(parts[1]), float(parts[2]))
    return coeffs

def _wrap_angle(a):
    while a > math.pi:
        a -= 2. * math.pi
    while a < -math.pi:
        a += 2. * math.pi
    return a


######################################################################
# Per-axis state
######################################################################

# Peak DAC amplitude of the base sine waveform (matches the TMC internal
# microstep table's typical 248 peak, leaving headroom for correction)
BASE_AMPLITUDE = 248
# LUT entries per motor_phase_load_lut message (4 bytes per entry)
LUT_CHUNK_ENTRIES = 8
# Sequencer counts per full step (MSCNT is 0..1023 over 4 full steps)
MSCNT_PER_FULLSTEP = 256
# Fraction of the constant-speed window trimmed from each end
CRUISE_TRIM = 0.15

class MotorPhaseAxis:
    def __init__(self, axis, oid):
        self.axis = axis                # 'x' or 'y'
        self.stepper_name = 'stepper_' + axis
        self.oid = oid
        self.stepper = None             # MCU_stepper
        self.tmc = None                 # TMC2240 printer object
        self.runtime_ok = False         # SPI-connected, MCU engine configured
        self.runtime_reason = "not configured"
        self.microsteps = None
        self.electrical_pulses = None   # step pulses per electrical period
        self.step_dist = None
        self.full_step_dist = None
        self.forward_coeffs = None
        self.reverse_coeffs = None
        self.phase_invert = False
        self.enabled = False
        self.bench_ok = False
        self.last_bench = None
        self.last_improvement = None
        self.fault = None
        # MCU command wrappers
        self.load_lut_cmd = None
        self.enable_cmd = None
        self.set_current_cmd = None
        self.bench_cmd = None
        self.query_status_cmd = None
        self.pos_query_cmd = None


######################################################################
# Main module
######################################################################

class MotorPhaseCalibrate:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.name = config.get_name()
        self.gcode = self.printer.lookup_object('gcode')
        # Configuration
        axes = config.getlist('axes', ('x', 'y'))
        self.accel_chip_name = config.get('accel_chip', 'lis2dw')
        self.harmonics = config.getintlist('harmonics', (2, 4))
        for n in self.harmonics:
            if n < 1 or n > 16:
                raise config.error("motor_phase_calibrate: harmonic %d out"
                                   " of range" % (n,))
        self.lut_size = config.getint('lut_size', 512, minval=16, maxval=1024)
        if self.lut_size & (self.lut_size - 1):
            raise config.error(
                "motor_phase_calibrate: lut_size must be a power of two")
        self.calibration_speeds = config.getfloatlist(
            'calibration_speeds', (5., 10., 15.))
        self.calibration_distance = config.getfloat(
            'calibration_distance', 40., above=5.)
        self.calibration_accel = config.getfloat(
            'calibration_accel', 500., above=0.)
        self.runtime_update_rate = config.getint(
            'runtime_update_rate', 12000, minval=1000, maxval=24000)
        self.enable_runtime = config.getboolean('enable_runtime', False)
        self.minimum_improvement = config.getfloat(
            'minimum_improvement', 0.05, minval=0., maxval=1.)
        # Axis state and stored corrections
        self.axes = {}
        import mcu as mcu_mod
        self.mcu = mcu_mod.get_printer_mcu(self.printer,
                                           config.get('mcu', 'mcu'))
        for axis in axes:
            axis = axis.strip().lower()
            if axis not in ('x', 'y'):
                raise config.error(
                    "motor_phase_calibrate: only x/y axes supported")
            a = MotorPhaseAxis(axis, self.mcu.create_oid())
            try:
                a.forward_coeffs = parse_correction(
                    config.get('%s_forward_correction' % (axis,), None))
                a.reverse_coeffs = parse_correction(
                    config.get('%s_reverse_correction' % (axis,), None))
            except ValueError as e:
                raise config.error("motor_phase_calibrate: %s" % (e,))
            a.phase_invert = config.getboolean(
                '%s_phase_invert' % (axis,), False)
            self.axes[axis] = a
        # Deferred MCU/TMC wiring
        self.mcu.register_config_callback(self._build_config)
        self._bench_completion = None
        self.printer.load_object(config, 'force_move')
        self.printer.register_event_handler("klippy:ready",
                                            self._handle_ready)
        # G-code commands
        for cmd in ('MOTOR_PHASE_BENCH', 'MOTOR_PHASE_CALIBRATE',
                    'MOTOR_PHASE_APPLY', 'MOTOR_PHASE_REPORT',
                    'MOTOR_PHASE_CLEAR'):
            func = getattr(self, 'cmd_' + cmd)
            self.gcode.register_command(cmd, func,
                                        desc=getattr(self,
                                                     'cmd_%s_help' % (cmd,)))

    # ---- MCU configuration -----------------------------------------------

    def _build_config(self):
        toolhead = self.printer.lookup_object('toolhead')
        kin = toolhead.get_kinematics()
        steppers = {s.get_name(): s for s in kin.get_steppers()}
        for a in self.axes.values():
            stepper = steppers.get(a.stepper_name)
            if stepper is None:
                a.runtime_reason = "stepper '%s' not found" % (
                    a.stepper_name,)
                continue
            a.stepper = stepper
            a.step_dist = stepper.get_step_dist()
            tmc = self.printer.lookup_object(
                'tmc2240 ' + a.stepper_name, None)
            if tmc is None:
                a.runtime_reason = ("no TMC2240 for '%s' (only TMC2240 is"
                                    " supported)" % (a.stepper_name,))
                continue
            a.tmc = tmc
            fields = tmc.mcu_tmc.get_fields()
            mres = fields.get_field("mres")
            a.microsteps = 256 >> mres
            a.electrical_pulses = 4 * a.microsteps
            rot_dist, steps_per_rot = stepper.get_rotation_distance()
            full_steps = steps_per_rot // a.microsteps
            a.full_step_dist = rot_dist / full_steps
            tmc_spi = getattr(tmc.mcu_tmc, 'tmc_spi', None)
            if tmc_spi is None:
                a.runtime_reason = ("TMC2240 for '%s' is UART-connected;"
                                    " runtime control requires SPI"
                                    % (a.stepper_name,))
                continue
            spi = tmc_spi.spi
            if spi.get_mcu() is not self.mcu \
               or stepper.get_mcu() is not self.mcu:
                a.runtime_reason = ("stepper/TMC SPI not on mcu '%s'"
                                    % (self.mcu.get_name() or 'mcu',))
                continue
            update_ticks = self.mcu.seconds_to_clock(
                1. / self.runtime_update_rate)
            self.mcu.add_config_cmd(
                "config_motor_phase oid=%d stepper_oid=%d spi_oid=%d"
                " lut_size=%d microsteps=%d update_ticks=%d"
                % (a.oid, stepper.get_oid(), spi.get_oid(), self.lut_size,
                   a.microsteps, update_ticks))
            a.load_lut_cmd = self.mcu.lookup_command(
                "motor_phase_load_lut oid=%c dir=%c offset=%hu data=%*s")
            a.enable_cmd = self.mcu.lookup_command(
                "motor_phase_enable oid=%c enable=%c invert=%c"
                " phase_offset=%hu")
            a.set_current_cmd = self.mcu.lookup_command(
                "motor_phase_set_current oid=%c scale=%hu")
            a.bench_cmd = self.mcu.lookup_command(
                "motor_phase_bench oid=%c count=%u interval_ticks=%u")
            a.query_status_cmd = self.mcu.lookup_query_command(
                "query_motor_phase_status oid=%c",
                "motor_phase_status oid=%c flags=%c index=%hu updates=%u"
                " writes=%u misses=%u overruns=%u max_ticks=%u", oid=a.oid)
            a.pos_query_cmd = self.mcu.lookup_query_command(
                "stepper_get_position oid=%c",
                "stepper_position oid=%c pos=%i", oid=stepper.get_oid())
            self.mcu.register_response(self._handle_fault,
                                       "motor_phase_fault", a.oid)
            self.mcu.register_response(self._handle_bench_end,
                                       "motor_phase_bench_end", a.oid)
            a.runtime_ok = True
            a.runtime_reason = "ok"

    def _handle_ready(self):
        if not self.enable_runtime:
            return
        # Deferred auto-apply: bench first, then enable axes that have
        # stored corrections.  Runs without motion.
        reactor = self.printer.get_reactor()
        reactor.register_callback(self._auto_apply)

    def _auto_apply(self, eventtime):
        for a in self.axes.values():
            if not a.runtime_ok or a.forward_coeffs is None \
               or a.reverse_coeffs is None:
                continue
            try:
                result = self._run_bench(a, self.runtime_update_rate, 2.)
                if not self._bench_passed(a, result):
                    logging.warning(
                        "motor_phase_calibrate: %s bench failed, runtime"
                        " left disabled: %s", a.axis, result)
                    continue
                self._apply_axis(a)
                self.gcode.respond_info(
                    "motor_phase_calibrate: runtime phase correction"
                    " enabled on %s" % (a.axis,))
            except Exception as e:
                logging.exception("motor_phase_calibrate: auto-apply "
                                  "failed on %s", a.axis)
                self.gcode.respond_info(
                    "motor_phase_calibrate: auto-apply failed on %s: %s"
                    % (a.axis, e))

    # ---- async MCU responses ----------------------------------------------

    def _handle_fault(self, params):
        oid = params['oid']
        for a in self.axes.values():
            if a.oid == oid:
                a.fault = "auto-disabled after %d missed updates" % (
                    params['misses'],)
                a.enabled = False
                logging.error("motor_phase_calibrate: %s %s",
                              a.axis, a.fault)
        # GCONF.direct_mode is still set; clearing it needs the reactor
        reactor = self.printer.get_reactor()
        reactor.register_async_callback(
            (lambda et, oid=oid: self._fault_cleanup(oid)))

    def _fault_cleanup(self, oid):
        for a in self.axes.values():
            if a.oid == oid and a.tmc is not None:
                try:
                    self._set_direct_mode(a, 0)
                except Exception:
                    logging.exception("motor_phase_calibrate: fault cleanup")
                self.gcode.respond_info(
                    "!! motor_phase_calibrate: %s runtime correction"
                    " auto-disabled (%s); re-home before printing"
                    % (a.axis, a.fault))

    def _handle_bench_end(self, params):
        completion = self._bench_completion
        if completion is not None:
            reactor = self.printer.get_reactor()
            reactor.async_complete(completion, params)

    # ---- TMC helpers -------------------------------------------------------

    def _set_direct_mode(self, a, enable):
        fields = a.tmc.mcu_tmc.get_fields()
        val = fields.set_field("direct_mode", 1 if enable else 0)
        a.tmc.mcu_tmc.set_register("GCONF", val)

    def _read_mscnt(self, a):
        fields = a.tmc.mcu_tmc.get_fields()
        reg = a.tmc.mcu_tmc.get_register("MSCNT")
        return fields.get_field("mscnt", reg, "MSCNT")

    def _query_stepper_pos(self, a):
        params = a.pos_query_cmd.send([a.stepper.get_oid()])
        return params['pos']

    def _current_scale(self, a):
        # DIRECT_MODE values bypass IRUN scaling; mimic it so the corrected
        # waveform carries the same current as normal operation.
        # /* FIXME: verify on silicon that direct-mode DAC codes are scaled
        #    by GLOBALSCALER but not IRUN (TMC2240 datasheet 6.4). */
        fields = a.tmc.mcu_tmc.get_fields()
        irun = fields.get_field("irun")
        return min(256, (irun + 1) * 8)

    # ---- phase synchronization ----------------------------------------------

    def _sync_phase(self, a, probe=False):
        """Compute LUT phase offset (and optionally the invert flag).

        Aligns the MCU engine's position-derived phase with the TMC's
        internal sequencer (MSCNT).  With probe=True a one-full-step move
        is made to measure the sign of the position->MSCNT relationship.
        """
        toolhead = self.printer.lookup_object('toolhead')
        toolhead.wait_moves()
        mscnt_per_pulse = MSCNT_PER_FULLSTEP // a.microsteps
        pos0 = self._query_stepper_pos(a)
        mscnt0 = self._read_mscnt(a)
        if probe:
            force_move = self.printer.lookup_object('force_move')
            force_move.manual_move(a.stepper, a.full_step_dist, 5.,
                                   self.calibration_accel)
            toolhead.wait_moves()
            pos1 = self._query_stepper_pos(a)
            mscnt1 = self._read_mscnt(a)
            dpos = pos1 - pos0
            dmscnt = (mscnt1 - mscnt0) % 1024
            expect = (dpos * mscnt_per_pulse) % 1024
            expect_inv = (-dpos * mscnt_per_pulse) % 1024
            if dmscnt == expect:
                a.phase_invert = False
            elif dmscnt == expect_inv:
                a.phase_invert = True
            else:
                raise self.gcode.error(
                    "motor_phase_calibrate: MSCNT sync failed on %s"
                    " (moved %d pulses, mscnt delta %d, expected %d/%d)."
                    " Check that the motor is enabled and idle."
                    % (a.axis, dpos, dmscnt, expect, expect_inv))
            pos0, mscnt0 = pos1, mscnt1
        # phase = (offset +/- pos) mod electrical_pulses  must equal
        # mscnt0 / mscnt_per_pulse at pos0
        mscnt_pulses = int(round(mscnt0 / mscnt_per_pulse)) \
            % a.electrical_pulses
        sign = -1 if a.phase_invert else 1
        offset = (mscnt_pulses - sign * pos0) % a.electrical_pulses
        return offset

    # ---- LUT upload / engine control ----------------------------------------

    def _upload_lut(self, a, direction, coeffs):
        lut = build_correction_lut(coeffs, self.lut_size, BASE_AMPLITUDE)
        for start in range(0, self.lut_size, LUT_CHUNK_ENTRIES):
            data = pack_lut_entries(lut, start, LUT_CHUNK_ENTRIES)
            a.load_lut_cmd.send([a.oid, direction, start, data])

    def _engine_enable(self, a, offset):
        a.set_current_cmd.send([a.oid, self._current_scale(a)])
        a.enable_cmd.send([a.oid, 1, 1 if a.phase_invert else 0, offset])

    def _engine_disable(self, a):
        a.enable_cmd.send([a.oid, 0, 0, 0])

    def _apply_axis(self, a, sync_probe=False):
        """Upload stored LUTs, sync phase, and enable runtime correction."""
        toolhead = self.printer.lookup_object('toolhead')
        toolhead.wait_moves()
        self._upload_lut(a, 0, a.forward_coeffs)
        self._upload_lut(a, 1, a.reverse_coeffs)
        offset = self._sync_phase(a, probe=sync_probe)
        self._engine_enable(a, offset)
        self._set_direct_mode(a, 1)
        a.enabled = True
        a.fault = None

    def _unapply_axis(self, a):
        toolhead = self.printer.lookup_object('toolhead')
        toolhead.wait_moves()
        self._engine_disable(a)
        self._set_direct_mode(a, 0)
        a.enabled = False

    # ---- bench ---------------------------------------------------------------

    def _run_bench(self, a, rate, duration):
        if not a.runtime_ok:
            raise self.gcode.error(
                "motor_phase_calibrate: %s runtime unavailable: %s"
                % (a.axis, a.runtime_reason))
        if a.enabled:
            raise self.gcode.error(
                "motor_phase_calibrate: disable %s correction before"
                " benching (MOTOR_PHASE_APPLY AXIS=%s ENABLE=0)"
                % (a.axis, a.axis))
        reactor = self.printer.get_reactor()
        count = max(10, int(rate * duration))
        interval_ticks = self.mcu.seconds_to_clock(1. / rate)
        self._bench_completion = completion = reactor.completion()
        a.bench_cmd.send([a.oid, count, interval_ticks])
        result = completion.wait(reactor.monotonic() + duration + 5.)
        self._bench_completion = None
        if result is None:
            raise self.gcode.error(
                "motor_phase_calibrate: bench timeout on %s" % (a.axis,))
        clock_freq = self.mcu.seconds_to_clock(1.)
        stats = {
            'rate': rate,
            'writes': result['writes'],
            'misses': result['misses'],
            'overruns': result['overruns'],
            'min_us': result['min_ticks'] * 1e6 / clock_freq,
            'max_us': result['max_ticks'] * 1e6 / clock_freq,
            'avg_us': result['avg_ticks'] * 1e6 / clock_freq,
            'budget_us': .6e6 / rate,
        }
        a.last_bench = stats
        return stats

    def _bench_passed(self, a, stats):
        writes = max(1, stats['writes'])
        ok = (stats['overruns'] <= writes * .01
              and stats['misses'] <= writes * .01)
        if ok and stats['rate'] >= self.runtime_update_rate:
            a.bench_ok = True
        return ok

    # ---- measurement --------------------------------------------------------

    def _measure_direction(self, a, direction, offset, accel_client_factory):
        """Run calibration moves in one direction; return averaged harmonics.

        direction: 0 = forward (position increasing), 1 = reverse.
        Returns averaged {n: (mag, phase)} of acceleration vs electrical
        angle over all configured speeds.
        """
        toolhead = self.printer.lookup_object('toolhead')
        force_move = self.printer.lookup_object('force_move')
        from .force_move import calc_move_time
        sign = -1 if a.phase_invert else 1
        move_sign = -1. if direction else 1.
        per_speed = []
        for speed in self.calibration_speeds:
            dist = move_sign * self.calibration_distance
            axis_r, accel_t, cruise_t, cruise_v = calc_move_time(
                dist, speed, self.calibration_accel)
            if cruise_t <= 0.:
                raise self.gcode.error(
                    "motor_phase_calibrate: no constant-speed window at"
                    " %.1f mm/s; increase calibration_distance" % (speed,))
            toolhead.wait_moves()
            if direction:
                # Reverse measurement: unmeasured pre-move so the measured
                # move returns to the start.  Keeps the total excursion
                # bounded to [start, start + calibration_distance].
                force_move.manual_move(a.stepper, -dist, speed,
                                       self.calibration_accel)
                toolhead.wait_moves()
            pos_start = self._query_stepper_pos(a)
            client = accel_client_factory()
            t_start = toolhead.get_last_move_time()
            force_move.manual_move(a.stepper, dist, speed,
                                   self.calibration_accel)
            toolhead.wait_moves()
            client.finish_measurements()
            if not direction:
                # Forward measurement: unmeasured return move
                force_move.manual_move(a.stepper, -dist, speed,
                                       self.calibration_accel)
                toolhead.wait_moves()
            samples = client.get_samples()
            if not samples:
                raise self.gcode.error(
                    "motor_phase_calibrate: no accelerometer data from"
                    " '%s'" % (self.accel_chip_name,))
            # Constant-speed window (trimmed)
            trim = cruise_t * CRUISE_TRIM
            w0 = t_start + accel_t + trim
            w1 = t_start + accel_t + cruise_t - trim
            # Electrical angle as a function of time during cruise
            pulses_accel = .5 * speed * accel_t / a.step_dist
            pos_c0 = pos_start + move_sign * pulses_accel
            steps_per_sec = speed / a.step_dist
            elec_freq = steps_per_sec / a.electrical_pulses
            theta_c0 = 2. * math.pi * (
                (offset + sign * pos_c0) % a.electrical_pulses) \
                / a.electrical_pulses
            omega = 2. * math.pi * elec_freq * sign * move_sign
            thetas = []
            values = []
            accel_attr = 'accel_' + a.axis
            for s in samples:
                if s.time < w0 or s.time > w1:
                    continue
                thetas.append(theta_c0 + omega * (s.time - (t_start
                                                            + accel_t)))
                values.append(getattr(s, accel_attr))
            if len(values) < 32:
                raise self.gcode.error(
                    "motor_phase_calibrate: too few accelerometer samples"
                    " in constant-speed window (%d)" % (len(values),))
            harmonics = extract_harmonics(thetas, values, self.harmonics)
            per_speed.append((harmonics, elec_freq))
        # Convert each speed's accel harmonics to phase coefficients (which
        # are speed independent), then average
        coeff_sets = []
        mags = []
        for harmonics, elec_freq in per_speed:
            elec_wavelength = 4. * a.full_step_dist
            coeff_sets.append(accel_to_phase_coeffs(
                harmonics, elec_freq, elec_wavelength))
            mags.append(math.fsum(m for m, _ in harmonics.values()))
        return combine_coeffs(coeff_sets), math.fsum(mags) / len(mags)

    def _measure_both(self, a, offset, accel_client_factory):
        fwd = self._measure_direction(a, 0, offset, accel_client_factory)
        rev = self._measure_direction(a, 1, offset, accel_client_factory)
        return fwd, rev

    # ---- G-code commands ----------------------------------------------------

    cmd_MOTOR_PHASE_BENCH_help = (
        "Measure MCU DIRECT_MODE update timing headroom")
    def cmd_MOTOR_PHASE_BENCH(self, gcmd):
        stepper_name = gcmd.get('STEPPER', 'stepper_x')
        a = self._axis_by_stepper(stepper_name)
        rate = gcmd.get_int('RATE', self.runtime_update_rate,
                            minval=1000, maxval=24000)
        duration = gcmd.get_float('DURATION', 2., above=0., maxval=30.)
        stats = self._run_bench(a, rate, duration)
        passed = self._bench_passed(a, stats)
        gcmd.respond_info(
            "Motor phase bench on %s at %d Hz for %.1fs:\n"
            " writes=%d misses=%d overruns=%d\n"
            " write time min=%.1fus avg=%.1fus max=%.1fus"
            " (budget %.1fus)\n"
            " result: %s"
            % (stepper_name, rate, duration, stats['writes'],
               stats['misses'], stats['overruns'], stats['min_us'],
               stats['avg_us'], stats['max_us'], stats['budget_us'],
               "PASS" if passed else "FAIL (runtime enable refused)"))

    cmd_MOTOR_PHASE_CALIBRATE_help = (
        "Measure motor harmonics and calibrate phase current correction")
    def cmd_MOTOR_PHASE_CALIBRATE(self, gcmd):
        axis = gcmd.get('AXIS', 'X').lower()
        a = self.axes.get(axis)
        if a is None:
            raise gcmd.error("Unknown axis '%s'" % (axis,))
        if not a.runtime_ok:
            raise gcmd.error(
                "motor_phase_calibrate: %s unavailable: %s"
                % (axis, a.runtime_reason))
        force = gcmd.get_int('FORCE', 0)
        toolhead = self.printer.lookup_object('toolhead')
        kin_status = toolhead.get_kinematics().get_status(
            self.printer.get_reactor().monotonic())
        homed = axis in kin_status['homed_axes']
        if not homed and not force:
            raise gcmd.error(
                "Axis %s is not homed; home first or use FORCE=1 to"
                " calibrate in place" % (axis.upper(),))
        if homed:
            # Center the axis so calibration moves have room
            curpos = toolhead.get_position()
            axis_idx = 'xyz'.index(axis)
            rmin, rmax = kin_status['axis_minimum'], kin_status[
                'axis_maximum']
            center = (rmin[axis_idx] + rmax[axis_idx]) * .5
            curpos[axis_idx] = center - self.calibration_distance * .5
            toolhead.manual_move(curpos, 50.)
            toolhead.wait_moves()
        chip = self.printer.lookup_object(self.accel_chip_name)
        client_factory = chip.start_internal_client
        if a.enabled:
            self._unapply_axis(a)
        # Stepper-level moves bypass the toolhead; make sure the motor is
        # actually energized (mirrors FORCE_MOVE behavior)
        force_move = self.printer.lookup_object('force_move')
        force_move._force_enable(a.stepper)
        gcmd.respond_info("Measuring baseline vibration on %s..."
                          % (axis.upper(),))
        offset = self._sync_phase(a, probe=True)
        (fwd_coeffs, base_fwd_mag), (rev_coeffs, base_rev_mag) = \
            self._measure_both(a, offset, client_factory)
        gcmd.respond_info(
            "Baseline: fwd=%.1f mm/s^2 rev=%.1f mm/s^2\n"
            "Candidate correction fwd: %s\n"
            "Candidate correction rev: %s\n"
            "Testing correction..."
            % (base_fwd_mag, base_rev_mag, format_correction(fwd_coeffs),
               format_correction(rev_coeffs)))
        # Apply candidate and re-measure
        self._upload_lut(a, 0, fwd_coeffs)
        self._upload_lut(a, 1, rev_coeffs)
        try:
            offset = self._sync_phase(a)
            self._engine_enable(a, offset)
            self._set_direct_mode(a, 1)
            a.enabled = True
            (_, corr_fwd_mag), (_, corr_rev_mag) = self._measure_both(
                a, offset, client_factory)
        finally:
            self._unapply_axis(a)
        imp_fwd = (base_fwd_mag - corr_fwd_mag) / max(base_fwd_mag, 1e-9)
        imp_rev = (base_rev_mag - corr_rev_mag) / max(base_rev_mag, 1e-9)
        overall = (imp_fwd + imp_rev) * .5
        a.last_improvement = overall
        msg = ("Corrected: fwd=%.1f mm/s^2 (%+.1f%%)"
               " rev=%.1f mm/s^2 (%+.1f%%), overall %+.1f%%"
               % (corr_fwd_mag, imp_fwd * 100., corr_rev_mag,
                  imp_rev * 100., overall * 100.))
        if overall >= self.minimum_improvement and imp_fwd > 0. \
           and imp_rev > 0.:
            a.forward_coeffs = fwd_coeffs
            a.reverse_coeffs = rev_coeffs
            configfile = self.printer.lookup_object('configfile')
            configfile.set(self.name, '%s_forward_correction' % (axis,),
                           format_correction(fwd_coeffs))
            configfile.set(self.name, '%s_reverse_correction' % (axis,),
                           format_correction(rev_coeffs))
            configfile.set(self.name, '%s_phase_invert' % (axis,),
                           1 if a.phase_invert else 0)
            gcmd.respond_info(
                "%s\nImprovement >= %.0f%% — correction saved. Use"
                " SAVE_CONFIG to persist, then re-home before printing."
                % (msg, self.minimum_improvement * 100.))
        else:
            gcmd.respond_info(
                "%s\nBelow %.0f%% improvement — correction NOT saved."
                " Re-home before printing."
                % (msg, self.minimum_improvement * 100.))

    cmd_MOTOR_PHASE_APPLY_help = (
        "Enable or disable runtime phase current correction")
    def cmd_MOTOR_PHASE_APPLY(self, gcmd):
        axis = gcmd.get('AXIS', 'X').lower()
        a = self.axes.get(axis)
        if a is None:
            raise gcmd.error("Unknown axis '%s'" % (axis,))
        enable = gcmd.get_int('ENABLE', 1)
        if not enable:
            if a.enabled:
                self._unapply_axis(a)
                gcmd.respond_info(
                    "Motor phase correction disabled on %s; re-home"
                    " before printing" % (axis.upper(),))
            else:
                gcmd.respond_info("Motor phase correction already disabled"
                                  " on %s" % (axis.upper(),))
            return
        if not a.runtime_ok:
            raise gcmd.error("motor_phase_calibrate: %s unavailable: %s"
                             % (axis, a.runtime_reason))
        if a.forward_coeffs is None or a.reverse_coeffs is None:
            raise gcmd.error(
                "No stored correction for %s; run MOTOR_PHASE_CALIBRATE"
                " first" % (axis.upper(),))
        if not a.bench_ok:
            raise gcmd.error(
                "No passing MOTOR_PHASE_BENCH at >=%d Hz this session;"
                " run MOTOR_PHASE_BENCH STEPPER=%s first"
                % (self.runtime_update_rate, a.stepper_name))
        self._apply_axis(a)
        gcmd.respond_info("Motor phase correction enabled on %s"
                          % (axis.upper(),))

    cmd_MOTOR_PHASE_REPORT_help = "Report motor phase correction state"
    def cmd_MOTOR_PHASE_REPORT(self, gcmd):
        axis = gcmd.get('AXIS', None)
        axes = [axis.lower()] if axis else sorted(self.axes.keys())
        lines = []
        for name in axes:
            a = self.axes.get(name)
            if a is None:
                raise gcmd.error("Unknown axis '%s'" % (name,))
            lines.append("Axis %s: runtime=%s enabled=%s bench_ok=%s"
                         % (name.upper(), a.runtime_reason, a.enabled,
                            a.bench_ok))
            if a.forward_coeffs is not None:
                lines.append("  forward: %s"
                             % (format_correction(a.forward_coeffs),))
            if a.reverse_coeffs is not None:
                lines.append("  reverse: %s"
                             % (format_correction(a.reverse_coeffs),))
            lines.append("  phase_invert: %d" % (a.phase_invert,))
            if a.last_bench is not None:
                b = a.last_bench
                lines.append(
                    "  last bench: %dHz writes=%d misses=%d overruns=%d"
                    " max=%.1fus" % (b['rate'], b['writes'], b['misses'],
                                     b['overruns'], b['max_us']))
            if a.last_improvement is not None:
                lines.append("  last calibration improvement: %+.1f%%"
                             % (a.last_improvement * 100.,))
            if a.fault:
                lines.append("  FAULT: %s" % (a.fault,))
        gcmd.respond_info("\n".join(lines))

    cmd_MOTOR_PHASE_CLEAR_help = "Clear stored motor phase correction"
    def cmd_MOTOR_PHASE_CLEAR(self, gcmd):
        axis = gcmd.get('AXIS', 'X').lower()
        a = self.axes.get(axis)
        if a is None:
            raise gcmd.error("Unknown axis '%s'" % (axis,))
        if a.enabled:
            self._unapply_axis(a)
        a.forward_coeffs = a.reverse_coeffs = None
        a.last_improvement = None
        configfile = self.printer.lookup_object('configfile')
        configfile.set(self.name, '%s_forward_correction' % (axis,), '')
        configfile.set(self.name, '%s_reverse_correction' % (axis,), '')
        gcmd.respond_info("Cleared stored correction for %s. Use"
                          " SAVE_CONFIG to persist." % (axis.upper(),))

    # ---- helpers / status ---------------------------------------------------

    def _axis_by_stepper(self, stepper_name):
        for a in self.axes.values():
            if a.stepper_name == stepper_name:
                return a
        raise self.gcode.error(
            "No motor phase axis for stepper '%s'" % (stepper_name,))

    def get_status(self, eventtime):
        return {
            'axes': {
                name: {
                    'runtime_available': a.runtime_ok,
                    'enabled': a.enabled,
                    'bench_ok': a.bench_ok,
                    'has_correction': a.forward_coeffs is not None,
                    'last_improvement': a.last_improvement,
                    'fault': a.fault,
                } for name, a in self.axes.items()
            },
        }


def load_config(config):
    return MotorPhaseCalibrate(config)
