"""Stock-U1 integration: flush ordering and future motor-disable events."""
from types import SimpleNamespace
import pytest
import toolhead
from extras import phase_stepping


def test_phase_generation_runs_before_stock_trapq_cleanup():
    events = []
    mcu = SimpleNamespace(flush_moves=lambda *a: events.append('mcu_flush'))
    th = SimpleNamespace(
        last_flush_time=0., print_time=1., kin_flush_delay=0.,
        step_generators=[lambda t: events.append(('steps', t))],
        flush_callbacks=[lambda f, s: events.append(('phase', f, s))],
        min_restart_time=0., clear_history_time=0., can_pause=True,
        trapq=object(),
        trapq_finalize_moves=lambda *a: events.append('free_moves'),
        extruder=SimpleNamespace(update_move_time=lambda *a: None),
        all_mcus=[mcu])
    toolhead.ToolHead._advance_flush_time(th, 0.5)
    assert events[0][0] == 'steps'
    assert events[1] == ('phase', 0.5, events[0][1])
    assert events[2:] == ['free_moves', 'mcu_flush']


@pytest.mark.parametrize('print_time,wait', [(None, False), (12.5, True)])
def test_stock_motor_off_waits_for_pending_motion(print_time, wait):
    calls = []
    ps = phase_stepping.PhaseStepping.__new__(phase_stepping.PhaseStepping)
    ps.resume_after_homing = True
    ps._disable = lambda **kw: calls.append(kw)
    ps._handle_motor_off(print_time)
    assert not ps.resume_after_homing
    assert calls == [{'wait': wait}]


@pytest.mark.parametrize('fails', [False, True])
def test_calibration_restores_stock_limits_without_gcmd_run_script(fails):
    from extras import phase_limits
    commands, shaping = [], []
    kin = SimpleNamespace(max_velocities=[300., 300., 10.],
                          max_accels=[5000., 5000., 500.],
                          scale_per_axis=True)
    old_v, old_a = kin.max_velocities, kin.max_accels
    th = SimpleNamespace(
        get_status=lambda t: {'max_velocity': 300., 'max_accel': 5000.,
                              'minimum_cruise_ratio': 0.5},
        get_kinematics=lambda: kin)
    objs = {'gcode': SimpleNamespace(run_script_from_command=commands.append,
                                    respond_info=lambda m: None),
            'toolhead': th,
            'input_shaper': SimpleNamespace(
                disable_shaping=lambda: shaping.append('off'),
                enable_shaping=lambda: shaping.append('on'))}
    printer = SimpleNamespace(lookup_object=lambda n, d=None: objs.get(n, d),
                              get_reactor=lambda: SimpleNamespace(monotonic=lambda: 0.))
    try:
        with phase_limits.suspend_limits(printer, 2000., 100., False, object()):
            assert kin.max_velocities[:2] == [100., 100.]
            if fails:
                raise RuntimeError('interrupted')
    except RuntimeError:
        assert fails
    assert kin.max_velocities is old_v and kin.max_accels is old_a
    assert kin.scale_per_axis
    assert shaping == ['off', 'on']
    assert commands == [
        'SET_VELOCITY_LIMIT ACCEL=2000.000 MINIMUM_CRUISE_RATIO=0 VELOCITY=100.000',
        'SET_VELOCITY_LIMIT ACCEL=5000.000 MINIMUM_CRUISE_RATIO=0.500 VELOCITY=300.000']
