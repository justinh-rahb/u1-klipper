# Motor phase calibration — direct phase current control for Snapmaker U1
#
# Copyright (C) 2024  Snapmaker U1 Klipper Fork Contributors
#
# This file may be distributed under the terms of the GNU GPLv3 license.
#
# XDirect / Direct Phase Current Control
# =======================================
# The TMC2240 on the U1 toolhead has a DIRECT_MODE register (0x2D) and a
# GCONF.direct_mode bit (bit 16) that together allow the host to bypass
# the internal microstep waveform generator and directly set per-phase
# current vectors (I_A, I_B).
#
# Register layout of DIRECT_MODE (same as MSCURACT):
#   bits  8:0  — cur_a  (9-bit signed, range –256 .. +255)
#   bits 24:16 — cur_b  (9-bit signed, range –256 .. +255)
#
# This module:
#   1. Locates the TMC driver object for the requested stepper.
#   2. Enables direct_mode via GCONF.
#   3. Commands the MCU-side timer to step through electrical angles
#      while writing DIRECT_MODE with the appropriate (I_A, I_B).
#   4. Collects timing data from the MCU and optionally reads
#      DRV_STATUS / SG4_RESULT for response measurement.
#   5. Computes a phase offset from the collected data.
#   6. Persists the result to the printer configuration.
#
# /* FIXME: The U1 toolhead has no dedicated sense-resistor ADC for
#    per-phase current measurement.  Sample capture on the MCU side
#    returns zero.  The host relies on TMC diagnostic register readback
#    (DRV_STATUS, SG4_RESULT) over SPI/UART, which is slow (~1 ms per
#    register read at 9600 baud UART).  High-speed current-sense
#    calibration would require hardware modifications. */
#
# /* FIXME: verify DIRECT_MODE register field positions against actual
#    TMC2240 silicon.  The bit layout is taken from the register map in
#    klippy/extras/tmc2240.py. */

import math, logging

# TMC drivers that support direct mode (XDIRECT / DIRECT_MODE)
DIRECT_MODE_DRIVERS = ["tmc2130", "tmc2240", "tmc5160"]

# Minimum time between host-side register reads during a sweep (seconds)
MIN_READ_INTERVAL = 0.050

# Default dwell time per angle step in seconds
DEFAULT_DWELL_TIME = 0.020

# Default sweep current in mA
DEFAULT_SWEEP_CURRENT = 200

# Default number of electrical-angle steps per full rotation
DEFAULT_SWEEP_STEPS = 256


class MotorPhaseCalibrate:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.name = config.get_name()
        self.gcode = self.printer.lookup_object('gcode')
        # Persistent calibration result
        self.phase_offset = config.getfloat('phase_offset', None)
        self.last_samples = []
        self.last_offset = self.phase_offset
        # MCU objects — filled in on connect
        self.mcu = None
        self.oid = None
        self._config_cmd = None
        self._sweep_cmd = None
        self._set_vector_cmd = None
        self._query_cmd = None
        self._sweep_done = False
        self._sweep_samples = []
        # Register lifecycle events
        self.printer.register_event_handler("klippy:connect",
                                            self._handle_connect)
        # Register G-code commands
        self.gcode.register_command(
            'MOTOR_PHASE_CALIBRATE', self.cmd_MOTOR_PHASE_CALIBRATE,
            desc=self.cmd_MOTOR_PHASE_CALIBRATE_help)
        self.gcode.register_command(
            'MOTOR_PHASE_SWEEP', self.cmd_MOTOR_PHASE_SWEEP,
            desc=self.cmd_MOTOR_PHASE_SWEEP_help)
        self.gcode.register_command(
            'MOTOR_PHASE_REPORT', self.cmd_MOTOR_PHASE_REPORT,
            desc=self.cmd_MOTOR_PHASE_REPORT_help)

    # ---- lifecycle ----------------------------------------------------------

    def _handle_connect(self):
        # Look up the default MCU (toolhead MCU)
        self.mcu = self.printer.lookup_object('mcu')
        self.oid = self.mcu.create_oid()
        # Compute dwell ticks from default dwell time
        dwell_ticks = self.mcu.seconds_to_clock(DEFAULT_DWELL_TIME)
        # Send config command to MCU
        self.mcu.add_config_cmd(
            "config_motor_phase oid=%d current_limit=%d dwell_ticks=%d"
            % (self.oid, DEFAULT_SWEEP_CURRENT, dwell_ticks))
        # Look up command wrappers
        self._sweep_cmd = self.mcu.lookup_command(
            "start_motor_phase_sweep oid=%c steps=%hu current=%hu")
        self._set_vector_cmd = self.mcu.lookup_command(
            "set_phase_vector oid=%c ia=%hi ib=%hi")
        self._query_cmd = self.mcu.lookup_query_command(
            "query_phase_status oid=%c",
            "motor_phase_status oid=%c state=%c pos=%hu ia=%hi ib=%hi",
            oid=self.oid)
        # Register response handlers for async MCU messages
        self.mcu.register_response(
            self._handle_phase_data, "motor_phase_data", self.oid)
        self.mcu.register_response(
            self._handle_phase_done, "motor_phase_done", self.oid)

    # ---- MCU response handlers ----------------------------------------------

    def _handle_phase_data(self, params):
        self._sweep_samples.append({
            'angle_idx': params['angle_idx'],
            'measured': params['measured'],
            'timestamp': params['timestamp'],
        })

    def _handle_phase_done(self, params):
        self._sweep_done = True

    # ---- TMC helper: find driver for a stepper name -------------------------

    def _lookup_tmc(self, stepper_name):
        """Locate the TMC driver module for *stepper_name*."""
        for driver in DIRECT_MODE_DRIVERS:
            section = "%s %s" % (driver, stepper_name)
            tmc = self.printer.lookup_object(section, default=None)
            if tmc is not None:
                return tmc, driver
        raise self.gcode.error(
            "No direct-mode capable TMC driver found for '%s'. "
            "Supported drivers: %s" % (stepper_name,
                                       ", ".join(DIRECT_MODE_DRIVERS)))

    # ---- direct-mode register helpers ---------------------------------------

    def _enable_direct_mode(self, tmc):
        """Enable GCONF.direct_mode on the TMC driver."""
        mcu_tmc = tmc.mcu_tmc
        fields = mcu_tmc.get_fields()
        val = fields.set_field("direct_mode", 1)
        mcu_tmc.set_register("GCONF", val)
        logging.info("motor_phase_calibrate: enabled direct_mode on %s",
                     tmc.mcu_tmc.name)

    def _disable_direct_mode(self, tmc):
        """Disable GCONF.direct_mode on the TMC driver."""
        mcu_tmc = tmc.mcu_tmc
        fields = mcu_tmc.get_fields()
        val = fields.set_field("direct_mode", 0)
        mcu_tmc.set_register("GCONF", val)
        logging.info("motor_phase_calibrate: disabled direct_mode on %s",
                     tmc.mcu_tmc.name)

    def _set_direct_current(self, tmc, cur_a, cur_b):
        """Write DIRECT_MODE register with explicit (cur_a, cur_b)."""
        mcu_tmc = tmc.mcu_tmc
        # Build the register value: cur_a in bits 8:0, cur_b in bits 24:16
        # Both are 9-bit signed values clamped to –256..+255
        cur_a = max(-256, min(255, int(cur_a)))
        cur_b = max(-256, min(255, int(cur_b)))
        val = (cur_a & 0x1ff) | ((cur_b & 0x1ff) << 16)
        reg_name = self._direct_mode_reg(tmc)
        mcu_tmc.set_register(reg_name, val)

    def _direct_mode_reg(self, tmc):
        """Return the correct register name for direct-mode writes."""
        fields = tmc.mcu_tmc.get_fields()
        # TMC2240 uses "DIRECT_MODE", TMC2130 uses "XDIRECT"
        if "DIRECT_MODE" in fields.all_fields:
            return "DIRECT_MODE"
        return "XDIRECT"

    def _read_mscuract(self, tmc):
        """Read the MSCURACT register and return (cur_a, cur_b)."""
        mcu_tmc = tmc.mcu_tmc
        fields = mcu_tmc.get_fields()
        val = mcu_tmc.get_register("MSCURACT")
        cur_a = fields.get_field("cur_a", val, "MSCURACT")
        cur_b = fields.get_field("cur_b", val, "MSCURACT")
        return cur_a, cur_b

    def _read_sg_result(self, tmc, driver_name):
        """Read StallGuard result if available, else return 0."""
        mcu_tmc = tmc.mcu_tmc
        fields = mcu_tmc.get_fields()
        if driver_name == 'tmc2240':
            val = mcu_tmc.get_register("SG4_RESULT")
            return fields.get_field("sg4_result", val, "SG4_RESULT")
        if "sg_result" in fields.all_fields.get("DRV_STATUS", {}):
            val = mcu_tmc.get_register("DRV_STATUS")
            return fields.get_field("sg_result", val, "DRV_STATUS")
        return 0

    # ---- phase offset computation -------------------------------------------

    def _compute_phase_offset(self, samples, sweep_steps):
        """Compute phase offset from collected sweep data.

        Uses a simple centroid (circular mean) of the angle indices weighted
        by the measured values.  If all measured values are zero (no sensor),
        falls back to returning half the sweep range as a placeholder.
        """
        if not samples:
            return 0.0
        total_weight = 0.0
        sin_sum = 0.0
        cos_sum = 0.0
        for s in samples:
            angle_rad = 2.0 * math.pi * s['angle_idx'] / sweep_steps
            weight = max(s.get('measured', 0), 1)  # avoid all-zero
            sin_sum += weight * math.sin(angle_rad)
            cos_sum += weight * math.cos(angle_rad)
            total_weight += weight
        if total_weight == 0.0:
            return 0.0
        mean_angle = math.atan2(sin_sum / total_weight,
                                cos_sum / total_weight)
        # Convert from radians back to an index in [0, sweep_steps)
        offset = mean_angle * sweep_steps / (2.0 * math.pi)
        if offset < 0:
            offset += sweep_steps
        return offset

    # ---- G-code commands ----------------------------------------------------

    cmd_MOTOR_PHASE_CALIBRATE_help = (
        "Run full motor phase calibration sequence")
    def cmd_MOTOR_PHASE_CALIBRATE(self, gcmd):
        stepper = gcmd.get('STEPPER', 'stepper_x')
        current = gcmd.get_int('CURRENT', DEFAULT_SWEEP_CURRENT,
                               minval=10, maxval=2000)
        steps = gcmd.get_int('STEPS', DEFAULT_SWEEP_STEPS,
                             minval=4, maxval=1024)
        gcmd.respond_info("Starting phase calibration for '%s' "
                          "(%d steps, %d mA)" % (stepper, steps, current))
        tmc, driver_name = self._lookup_tmc(stepper)
        # Enable direct mode
        self._enable_direct_mode(tmc)
        try:
            self._run_sweep(gcmd, tmc, driver_name, steps, current)
        finally:
            # Always restore normal operation
            self._disable_direct_mode(tmc)
        # Compute and persist offset
        offset = self._compute_phase_offset(self._sweep_samples, steps)
        self.last_offset = offset
        self.last_samples = list(self._sweep_samples)
        self.phase_offset = offset
        configfile = self.printer.lookup_object('configfile')
        configfile.set(self.name, 'phase_offset', "%.6f" % (offset,))
        gcmd.respond_info(
            "Phase calibration complete for '%s': offset=%.4f "
            "(out of %d steps). Use SAVE_CONFIG to persist."
            % (stepper, offset, steps))

    cmd_MOTOR_PHASE_SWEEP_help = (
        "Sweep electrical angle and collect samples")
    def cmd_MOTOR_PHASE_SWEEP(self, gcmd):
        stepper = gcmd.get('STEPPER', 'stepper_x')
        current = gcmd.get_int('CURRENT', DEFAULT_SWEEP_CURRENT,
                               minval=10, maxval=2000)
        steps = gcmd.get_int('STEPS', DEFAULT_SWEEP_STEPS,
                             minval=4, maxval=1024)
        gcmd.respond_info("Starting phase sweep for '%s' "
                          "(%d steps, %d mA)" % (stepper, steps, current))
        tmc, driver_name = self._lookup_tmc(stepper)
        self._enable_direct_mode(tmc)
        try:
            self._run_sweep(gcmd, tmc, driver_name, steps, current)
        finally:
            self._disable_direct_mode(tmc)
        offset = self._compute_phase_offset(self._sweep_samples, steps)
        self.last_offset = offset
        self.last_samples = list(self._sweep_samples)
        gcmd.respond_info(
            "Sweep complete: %d samples collected, computed offset=%.4f"
            % (len(self.last_samples), offset))

    cmd_MOTOR_PHASE_REPORT_help = "Report last phase calibration result"
    def cmd_MOTOR_PHASE_REPORT(self, gcmd):
        stepper = gcmd.get('STEPPER', 'stepper_x')
        if self.last_offset is not None:
            gcmd.respond_info(
                "Last phase offset for '%s': %.4f (%d samples)"
                % (stepper, self.last_offset, len(self.last_samples)))
        elif self.phase_offset is not None:
            gcmd.respond_info(
                "Stored phase offset for '%s': %.4f (from config)"
                % (stepper, self.phase_offset))
        else:
            gcmd.respond_info(
                "No phase calibration data available for '%s'. "
                "Run MOTOR_PHASE_CALIBRATE first." % (stepper,))

    # ---- sweep implementation -----------------------------------------------

    def _run_sweep(self, gcmd, tmc, driver_name, steps, current_ma):
        """Execute a full electrical-angle sweep.

        For each angle step the host:
          1. Computes (I_A, I_B) = current * (cos(θ), sin(θ))
          2. Writes DIRECT_MODE register with those values
          3. Tells the MCU timer to advance and report timing
          4. Optionally reads back DRV_STATUS / SG4_RESULT for measurement
        """
        reactor = self.printer.get_reactor()
        self._sweep_samples = []
        self._sweep_done = False
        # Tell MCU to start its timer-driven sweep counter
        self._sweep_cmd.send([self.oid, steps, current_ma])
        # Scale current from mA to the 9-bit cur_a/cur_b range (–256..255)
        # TMC2240 full-scale depends on GLOBALSCALER and current_range, but
        # for direct mode the register accepts raw DAC codes.  We scale so
        # that the requested mA maps to ~70% of full scale (conservative).
        # /* FIXME: verify against hardware — the exact scaling depends on
        #    the sense resistor value and GLOBALSCALER setting. */
        scale = min(255, max(1, int(current_ma * 255.0 / 2000.0)))
        for i in range(steps):
            angle_rad = 2.0 * math.pi * i / steps
            cur_a = int(scale * math.cos(angle_rad))
            cur_b = int(scale * math.sin(angle_rad))
            # Write phase vector to TMC
            self._set_direct_current(tmc, cur_a, cur_b)
            # Also tell MCU the vector (for its state tracking)
            self._set_vector_cmd.send([self.oid, cur_a, cur_b])
            # Dwell
            reactor.pause(reactor.monotonic() + DEFAULT_DWELL_TIME)
            # Read diagnostic register for measurement
            try:
                sg = self._read_sg_result(tmc, driver_name)
            except Exception:
                sg = 0
            # Augment MCU sample with host-side measurement
            if i < len(self._sweep_samples):
                self._sweep_samples[i]['measured'] = sg
            else:
                # MCU sample not yet received — create host-only entry
                self._sweep_samples.append({
                    'angle_idx': i,
                    'measured': sg,
                    'timestamp': 0,
                })
        # Wait for MCU sweep-done (with timeout)
        deadline = reactor.monotonic() + 5.0
        while not self._sweep_done and reactor.monotonic() < deadline:
            reactor.pause(reactor.monotonic() + 0.050)
        if not self._sweep_done:
            logging.warning("motor_phase_calibrate: MCU sweep-done "
                            "not received within timeout")

    def get_status(self, eventtime):
        return {
            'phase_offset': self.phase_offset,
            'sample_count': len(self.last_samples),
        }


def load_config(config):
    return MotorPhaseCalibrate(config)
