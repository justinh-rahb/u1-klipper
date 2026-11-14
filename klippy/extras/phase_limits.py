# Phase calibration limits for the stock U1 motion planner
# Adapted from Hannott/kalico, resonance_tester.py
# Copyright (C) 2020-2024 Dmitry Butyugin
# This file may be distributed under the terms of the GNU GPLv3 license.
from contextlib import contextmanager

@contextmanager
def suspend_limits(printer, max_accel, max_velocity, input_shaping, gcmd):
    # Override maximum acceleration and cruise ratio
    # based on the maximum test frequency
    gcode = printer.lookup_object("gcode")
    input_shaper = printer.lookup_object("input_shaper", None)
    if input_shaper is not None and not input_shaping:
        input_shaper.disable_shaping()
        gcode.respond_info("Disabled [input_shaper] for resonance testing")
    else:
        input_shaper = None
    toolhead = printer.lookup_object("toolhead")
    systime = printer.get_reactor().monotonic()
    toolhead_info = toolhead.get_status(systime)
    old_max_accel = toolhead_info["max_accel"]
    old_minimum_cruise_ratio = toolhead_info["minimum_cruise_ratio"]
    old_max_velocity = toolhead_info["max_velocity"]
    gcode.run_script_from_command(
        "SET_VELOCITY_LIMIT ACCEL=%.3f MINIMUM_CRUISE_RATIO=0 VELOCITY=%.3f"
        % (max_accel, max_velocity)
    )
    kin = toolhead.get_kinematics()
    old_max_velocities = getattr(kin, "max_velocities", None)
    if old_max_velocities is not None:
        kin.max_velocities = [
            max_velocity,
            max_velocity,
            old_max_velocities[-1],
        ]
    old_max_accels = getattr(kin, "max_accels", None)
    if old_max_accels is not None:
        kin.max_accels = [max_accel, max_accel, old_max_accels[-1]]
    # FIXME: could be cleaner if limited_corexy were using the same format than
    # limited_cartesian
    old_max_x_accel = getattr(kin, "max_x_accel", None)
    if old_max_x_accel is not None:
        kin.max_x_accel = max_accel
    old_max_y_accel = getattr(kin, "max_y_accel", None)
    if old_max_y_accel is not None:
        kin.max_y_accel = max_accel
    old_scale_per_axis = getattr(kin, "scale_per_axis", None)
    if old_scale_per_axis is not None:
        kin.scale_per_axis = False
    try:
        yield
    finally:
        # Restore input shaper if it was disabled for resonance testing
        if input_shaper is not None:
            input_shaper.enable_shaping()
            gcode.respond_info("Re-enabled [input_shaper]")
        # Restore the original acceleration values
        gcode.run_script_from_command(
            "SET_VELOCITY_LIMIT ACCEL=%.3f MINIMUM_CRUISE_RATIO=%.3f VELOCITY=%.3f"
            % (old_max_accel, old_minimum_cruise_ratio, old_max_velocity)
        )
        if old_max_velocities is not None:
            kin.max_velocities = old_max_velocities
        if old_max_accels is not None:
            kin.max_accels = old_max_accels
        if old_max_x_accel is not None:
            kin.max_x_accel = old_max_x_accel
        if old_max_y_accel is not None:
            kin.max_y_accel = old_max_y_accel
        if old_scale_per_axis is not None:
            kin.scale_per_axis = old_scale_per_axis
