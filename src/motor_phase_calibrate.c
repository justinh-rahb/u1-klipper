// Motor phase calibration support — direct phase current control
//
// Copyright (C) 2024  Snapmaker U1 Klipper Fork Contributors
//
// This file may be distributed under the terms of the GNU GPLv3 license.
//
// XDirect / Direct Phase Current Control
// =======================================
// The TMC2240 driver on the U1 toolhead supports a "direct mode" where the
// host can bypass the internal microstep waveform generator and command
// explicit per-phase current vectors (I_A, I_B).  This is activated by
// setting GCONF.direct_mode (bit 16) and then writing the DIRECT_MODE
// register (address 0x2D) with the desired cur_a/cur_b values.
//
// On the TMC2240 the DIRECT_MODE register uses the same field layout as
// MSCURACT:
//   bits  8:0  — cur_a  (9-bit signed, –256 .. +255)
//   bits 24:16 — cur_b  (9-bit signed, –256 .. +255)
//
// Because the TMC2240 register writes happen over SPI or UART from the
// host Python layer (via the existing tmc_uart / tmc2130 helpers), this
// MCU-side module does NOT bit-bang TMC registers directly.  Instead it
// provides:
//   • A timer-driven state machine that sequences through electrical
//     angles during a sweep and sends results back to the host.
//   • Protocol commands so the host can configure, start, query, and
//     receive sweep data.
//
// Actual TMC register I/O (GCONF, DIRECT_MODE, MSCURACT reads) is
// performed on the host side in motor_phase_calibrate.py using the
// existing MCU_TMC_SPI / MCU_TMC_uart infrastructure.
//
// Hardware notes (AT32F415RC toolhead):
//   • ARM Cortex-M4, 144 MHz, 256 KB flash, 32 KB RAM
//   • Timer resolution: 32-bit system tick at 144 MHz
//   • No dedicated sense-resistor ADC channel is exposed for per-phase
//     current measurement on the U1 toolhead PCB, so sample capture
//     returns zero.  The host must rely on TMC diagnostic registers
//     (DRV_STATUS, SG4_RESULT) read over SPI/UART instead.
//
// /* FIXME: verify DIRECT_MODE register field layout against hardware —
//    the bit positions are inferred from the TMC2240 Python register map
//    in klippy/extras/tmc2240.py.  If the actual silicon differs, the
//    host-side register writes will need adjustment. */

#include <string.h> // memset
#include "basecmd.h" // oid_alloc
#include "board/irq.h" // irq_disable
#include "board/misc.h" // timer_read_time
#include "command.h" // DECL_COMMAND
#include "sched.h" // DECL_TASK

// ---------- data structures ----------

enum {
    MPC_IDLE = 0,
    MPC_SWEEPING = 1,
    MPC_HOLDING = 2,
};

struct motor_phase_cal {
    struct timer timer;
    uint32_t dwell_ticks;       // ticks between angle steps
    uint16_t current_limit;     // max current in mA (informational)
    uint16_t sweep_steps;       // total electrical-angle steps in sweep
    uint16_t sweep_pos;         // current position in sweep
    int16_t hold_ia;            // explicit hold current phase A
    int16_t hold_ib;            // explicit hold current phase B
    uint8_t state;              // MPC_IDLE / MPC_SWEEPING / MPC_HOLDING
    uint8_t flags;
};

enum {
    MPCF_REPORT = 1 << 0,
    MPCF_DONE   = 1 << 1,
};

static struct task_wake mpc_wake;

// ---------- timer callback ----------

static uint_fast8_t
mpc_event(struct timer *t)
{
    struct motor_phase_cal *m = container_of(t, struct motor_phase_cal, timer);
    if (m->state == MPC_SWEEPING) {
        m->sweep_pos++;
        if (m->sweep_pos >= m->sweep_steps) {
            m->state = MPC_IDLE;
            m->flags |= MPCF_DONE;
            sched_wake_task(&mpc_wake);
            return SF_DONE;
        }
        m->flags |= MPCF_REPORT;
        sched_wake_task(&mpc_wake);
        m->timer.waketime += m->dwell_ticks;
        return SF_RESCHEDULE;
    }
    // MPC_HOLDING — stay scheduled so host can query, but do nothing
    if (m->state == MPC_HOLDING) {
        m->timer.waketime += m->dwell_ticks;
        return SF_RESCHEDULE;
    }
    return SF_DONE;
}

// ---------- host→MCU commands ----------

// config_motor_phase oid=%c current_limit=%hu dwell_ticks=%u
void
command_config_motor_phase(uint32_t *args)
{
    struct motor_phase_cal *m = oid_alloc(
        args[0], command_config_motor_phase, sizeof(*m));
    m->timer.func = mpc_event;
    m->current_limit = args[1];
    m->dwell_ticks = args[2];
    m->state = MPC_IDLE;
    m->sweep_steps = 0;
    m->sweep_pos = 0;
    m->hold_ia = 0;
    m->hold_ib = 0;
    m->flags = 0;
}
DECL_COMMAND(command_config_motor_phase,
             "config_motor_phase oid=%c current_limit=%hu dwell_ticks=%u");

// start_motor_phase_sweep oid=%c steps=%hu current=%hu
void
command_start_motor_phase_sweep(uint32_t *args)
{
    struct motor_phase_cal *m = oid_lookup(
        args[0], command_config_motor_phase);
    irq_disable();
    sched_del_timer(&m->timer);
    m->sweep_steps = args[1];
    m->current_limit = args[2];
    m->sweep_pos = 0;
    m->state = MPC_SWEEPING;
    m->flags = MPCF_REPORT;  // report initial position immediately
    m->timer.waketime = timer_read_time() + m->dwell_ticks;
    sched_add_timer(&m->timer);
    irq_enable();
    sched_wake_task(&mpc_wake);
}
DECL_COMMAND(command_start_motor_phase_sweep,
             "start_motor_phase_sweep oid=%c steps=%hu current=%hu");

// set_phase_vector oid=%c ia=%hi ib=%hi
void
command_set_phase_vector(uint32_t *args)
{
    struct motor_phase_cal *m = oid_lookup(
        args[0], command_config_motor_phase);
    irq_disable();
    sched_del_timer(&m->timer);
    m->hold_ia = args[1];
    m->hold_ib = args[2];
    m->state = MPC_HOLDING;
    m->timer.waketime = timer_read_time() + m->dwell_ticks;
    sched_add_timer(&m->timer);
    irq_enable();
}
DECL_COMMAND(command_set_phase_vector,
             "set_phase_vector oid=%c ia=%hi ib=%hi");

// query_phase_status oid=%c
void
command_query_phase_status(uint32_t *args)
{
    struct motor_phase_cal *m = oid_lookup(
        args[0], command_config_motor_phase);
    uint8_t state;
    uint16_t pos;
    int16_t ia, ib;
    irq_disable();
    state = m->state;
    pos = m->sweep_pos;
    ia = m->hold_ia;
    ib = m->hold_ib;
    irq_enable();
    sendf("motor_phase_status oid=%c state=%c pos=%hu ia=%hi ib=%hi"
          , args[0], state, pos, ia, ib);
}
DECL_COMMAND(command_query_phase_status,
             "query_phase_status oid=%c");

// ---------- task: send pending reports to host ----------

void
motor_phase_task(void)
{
    if (!sched_check_wake(&mpc_wake))
        return;
    uint8_t oid;
    struct motor_phase_cal *m;
    foreach_oid(oid, m, command_config_motor_phase) {
        uint8_t flags;
        irq_disable();
        flags = m->flags;
        m->flags = 0;
        irq_enable();
        if (flags & MPCF_REPORT) {
            // motor_phase_data: angle index, measured value (0 = no sensor),
            // timestamp
            // /* FIXME: measured_value is always 0 because the U1 toolhead
            //    has no dedicated sense-resistor ADC for per-phase current
            //    measurement.  The host reads TMC diagnostic registers
            //    (DRV_STATUS / SG4_RESULT) over SPI/UART instead. */
            sendf("motor_phase_data oid=%c angle_idx=%hu measured=%hu"
                  " timestamp=%u"
                  , oid, m->sweep_pos, (uint16_t)0, timer_read_time());
        }
        if (flags & MPCF_DONE) {
            sendf("motor_phase_done oid=%c total_steps=%hu"
                  , oid, m->sweep_steps);
        }
    }
}
DECL_TASK(motor_phase_task);

// ---------- shutdown ----------

static void
motor_phase_shutdown(void)
{
    uint8_t oid;
    struct motor_phase_cal *m;
    foreach_oid(oid, m, command_config_motor_phase) {
        m->state = MPC_IDLE;
        m->flags = 0;
    }
}
DECL_SHUTDOWN(motor_phase_shutdown);
