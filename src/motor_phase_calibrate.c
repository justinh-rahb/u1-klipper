// Motor phase runtime engine — direct phase current control
//
// Copyright (C) 2024  Snapmaker U1 Klipper Fork Contributors
//
// This file may be distributed under the terms of the GNU GPLv3 license.
//
// Direct Phase Current Control (TMC2240 DIRECT_MODE)
// ==================================================
// The TMC2240 drivers for the U1 X/Y steppers sit on mainboard hardware
// SPI buses.  With GCONF.direct_mode set (host-controlled), the DIRECT_MODE
// register (0x2D) supplies the per-phase current vector (cur_a, cur_b)
// instead of the internal microstep table:
//   bits  8:0  — cur_a  (9-bit signed, –256 .. +255)
//   bits 24:16 — cur_b  (9-bit signed, –256 .. +255)
//
// This module holds per-axis current lookup tables (one per motion
// direction) computed by the host from accelerometer-measured harmonic
// corrections.  A timer running at the configured update rate marks work
// pending and wakes a task; the task samples the stepper position, derives
// the electrical phase index, and writes the corresponding LUT entry to
// DIRECT_MODE over SPI.
//
// Timing/concurrency model:
//   • The timer callback (IRQ context) does no SPI I/O — it only tracks
//     missed updates and wakes the task.  Step generation timing is never
//     stretched by SPI transfers.
//   • SPI writes happen in task context.  Klipper tasks are serialized
//     with host-issued spi_transfer/spi_send commands (also task context),
//     so engine writes cannot interleave with host TMC register traffic
//     on the same bus.
//   • The cost of task scheduling is jitter: if the task is not serviced
//     before the next timer fire, that update is counted as missed.  Too
//     many consecutive misses auto-disables the engine and notifies the
//     host.  The host must run motor_phase_bench and check the stats
//     before allowing runtime use.
//
// Phase indexing:
//   Stepper position advances one microstep per step pulse.  One
//   electrical period is 4 full steps = 4*microsteps pulses.  The host
//   aligns our index to the TMC's internal sequencer (MSCNT) via the
//   phase_offset/invert arguments of motor_phase_enable.
//
//   phase  = (offset ± position) mod (4*microsteps)
//   index  = phase scaled to lut_size entries
//
// The host owns GCONF.direct_mode.  On shutdown this module writes a zero
// current vector so no stale LUT current persists into the next session.

#include <string.h> // memcpy
#include "basecmd.h" // oid_alloc
#include "board/irq.h" // irq_disable
#include "board/misc.h" // timer_read_time
#include "command.h" // DECL_COMMAND
#include "sched.h" // DECL_TASK
#include "spicmds.h" // spidev_transfer
#include "stepper.h" // stepper_get_position_by_oid

#define TMC_DIRECT_MODE_REG 0x2D
#define MP_WRITE_FLAG 0x80

// Auto-disable after this many consecutive missed updates
#define MP_MAX_CONSEC_MISS 8

enum {
    MPF_RUNNING     = 1 << 0,  // realtime updates active
    MPF_BENCH       = 1 << 1,  // bench mode (forced writes, fixed count)
    MPF_INVERT      = 1 << 2,  // step position decreases electrical phase
    MPF_FAULT       = 1 << 3,  // auto-disabled after missed update budget
    MPF_NOTIFY      = 1 << 4,  // fault/bench-end message pending
    MPF_LUT_FWD     = 1 << 5,  // forward LUT fully loaded (host-tracked too)
    MPF_LUT_REV     = 1 << 6,  // reverse LUT fully loaded
};

struct motor_phase {
    struct timer timer;
    struct spidev_s *spi;       // resolved lazily (config order independent)
    uint32_t update_ticks;      // ticks between runtime updates
    uint32_t budget_ticks;      // write-duration budget (60% of update)
    uint32_t last_pos;          // stepper position at previous update
    // Statistics (task context)
    uint32_t update_count;      // position samples taken
    uint32_t write_count;       // SPI writes performed
    uint32_t miss_count;        // timer fired while previous update pending
    uint32_t over_count;        // writes exceeding budget_ticks
    uint32_t max_write_ticks;   // slowest write observed
    uint32_t sum_write_ticks;   // for average (bench reporting)
    uint32_t min_write_ticks;
    // Bench mode
    uint32_t bench_remaining;
    // Configuration
    uint16_t lut_size;
    uint16_t phase_offset;      // in microstep pulses, 0..electrical-1
    uint16_t phase_mask;        // 4*microsteps - 1
    uint16_t scale;             // current scale, 256 = 1.0
    uint16_t last_index;        // last LUT index written
    uint8_t idx_shift;          // |log2(lut_size) - log2(4*microsteps)|
    uint8_t idx_shift_up;       // 1: index = phase << shift, 0: phase >> shift
    uint8_t stepper_oid;
    uint8_t spi_oid;
    uint8_t direction;          // 0=forward, 1=reverse (last seen)
    uint8_t last_dir_written;
    uint8_t consec_miss;
    uint8_t flags;
    volatile uint8_t pending;   // set by timer, cleared by task
    int16_t lut[];              // [2][lut_size][2] — dir, index, (ia, ib)
};

static struct task_wake mp_wake;

// ---------- timer callback (IRQ context — no SPI I/O here) ----------

static uint_fast8_t
mp_timer_event(struct timer *t)
{
    struct motor_phase *mp = container_of(t, struct motor_phase, timer);
    if (mp->pending) {
        mp->miss_count++;
        if (++mp->consec_miss >= MP_MAX_CONSEC_MISS
            && !(mp->flags & MPF_BENCH)) {
            // Task is not keeping up — stop and report rather than run
            // an uncontrolled current waveform
            mp->flags = (mp->flags & ~MPF_RUNNING) | MPF_FAULT | MPF_NOTIFY;
            sched_wake_task(&mp_wake);
            return SF_DONE;
        }
    } else {
        mp->consec_miss = 0;
    }
    mp->pending = 1;
    sched_wake_task(&mp_wake);
    if (mp->flags & MPF_BENCH && !--mp->bench_remaining) {
        mp->flags = (mp->flags & ~MPF_BENCH) | MPF_NOTIFY;
        return SF_DONE;
    }
    mp->timer.waketime += mp->update_ticks;
    return SF_RESCHEDULE;
}

// ---------- helpers (task context) ----------

static void
mp_write_vector(struct motor_phase *mp, int_fast16_t ia, int_fast16_t ib)
{
    uint32_t val = ((uint32_t)((uint16_t)ib & 0x1ff) << 16)
        | ((uint16_t)ia & 0x1ff);
    uint8_t msg[5] = { TMC_DIRECT_MODE_REG | MP_WRITE_FLAG,
                       val >> 24, val >> 16, val >> 8, val };
    spidev_transfer(mp->spi, 0, sizeof(msg), msg);
}

static void
mp_resolve_spi(struct motor_phase *mp)
{
    if (!mp->spi)
        mp->spi = spidev_oid_lookup(mp->spi_oid);
}

static void
mp_reset_stats(struct motor_phase *mp)
{
    mp->update_count = mp->write_count = 0;
    mp->miss_count = mp->over_count = 0;
    mp->max_write_ticks = mp->sum_write_ticks = 0;
    mp->min_write_ticks = (uint32_t)-1;
    mp->consec_miss = 0;
}

// Perform one position sample → LUT index → SPI write cycle
static void
mp_update(struct motor_phase *mp, uint8_t force_write)
{
    uint32_t t0 = timer_read_time();
    uint32_t pos = stepper_get_position_by_oid(mp->stepper_oid);
    int32_t delta = pos - mp->last_pos;
    mp->last_pos = pos;
    if (delta > 0)
        mp->direction = 0;
    else if (delta < 0)
        mp->direction = 1;
    uint32_t phase = mp->flags & MPF_INVERT
        ? (uint32_t)(mp->phase_offset - pos) & mp->phase_mask
        : (mp->phase_offset + pos) & mp->phase_mask;
    uint16_t index = mp->idx_shift_up
        ? phase << mp->idx_shift : phase >> mp->idx_shift;
    mp->update_count++;
    if (!force_write && index == mp->last_index
        && mp->direction == mp->last_dir_written)
        return;
    int16_t *e = &mp->lut[((uint32_t)mp->direction * mp->lut_size + index)
                          * 2];
    int_fast16_t ia = (int32_t)e[0] * mp->scale >> 8;
    int_fast16_t ib = (int32_t)e[1] * mp->scale >> 8;
    mp_write_vector(mp, ia, ib);
    mp->last_index = index;
    mp->last_dir_written = mp->direction;
    uint32_t dt = timer_read_time() - t0;
    mp->write_count++;
    mp->sum_write_ticks += dt;
    if (dt > mp->max_write_ticks)
        mp->max_write_ticks = dt;
    if (dt < mp->min_write_ticks)
        mp->min_write_ticks = dt;
    if (dt > mp->budget_ticks)
        mp->over_count++;
}

// ---------- host→MCU commands ----------

void
command_config_motor_phase(uint32_t *args)
{
    uint16_t lut_size = args[3], microsteps = args[4];
    if (!lut_size || lut_size > 1024 || (lut_size & (lut_size - 1)))
        shutdown("motor_phase: lut_size must be power of two <= 1024");
    if (!microsteps || microsteps > 256 || (microsteps & (microsteps - 1)))
        shutdown("motor_phase: microsteps must be power of two <= 256");
    struct motor_phase *mp = oid_alloc(
        args[0], command_config_motor_phase,
        sizeof(*mp) + 2 * lut_size * 2 * sizeof(int16_t));
    mp->timer.func = mp_timer_event;
    mp->stepper_oid = args[1];
    mp->spi_oid = args[2];
    mp->lut_size = lut_size;
    uint16_t electrical = 4 * microsteps;
    mp->phase_mask = electrical - 1;
    uint8_t l2lut = __builtin_ctz(lut_size), l2e = __builtin_ctz(electrical);
    if (l2lut >= l2e) {
        mp->idx_shift_up = 1;
        mp->idx_shift = l2lut - l2e;
    } else {
        mp->idx_shift_up = 0;
        mp->idx_shift = l2e - l2lut;
    }
    mp->update_ticks = args[5];
    mp->budget_ticks = args[5] * 6 / 10;
    mp->scale = 256;
    mp->min_write_ticks = (uint32_t)-1;
}
DECL_COMMAND(command_config_motor_phase,
             "config_motor_phase oid=%c stepper_oid=%c spi_oid=%c"
             " lut_size=%hu microsteps=%hu update_ticks=%u");

// Load a chunk of LUT entries.  data is little-endian int16 (ia, ib) pairs;
// offset is the index of the first entry in the chunk.
void
command_motor_phase_load_lut(uint32_t *args)
{
    struct motor_phase *mp = oid_lookup(args[0], command_config_motor_phase);
    uint8_t dir = args[1];
    uint16_t offset = args[2];
    uint8_t data_len = args[3];
    uint8_t *data = command_decode_ptr(args[4]);
    uint16_t count = data_len / 4;
    if (dir > 1 || offset + count > mp->lut_size)
        shutdown("motor_phase: invalid lut chunk");
    if (mp->flags & (MPF_RUNNING | MPF_BENCH))
        shutdown("motor_phase: can't load lut while running");
    int16_t *e = &mp->lut[((uint32_t)dir * mp->lut_size + offset) * 2];
    uint16_t i;
    for (i = 0; i < count; i++) {
        e[i*2] = (int16_t)(data[i*4] | (data[i*4+1] << 8));
        e[i*2+1] = (int16_t)(data[i*4+2] | (data[i*4+3] << 8));
    }
    if (offset + count == mp->lut_size)
        mp->flags |= dir ? MPF_LUT_REV : MPF_LUT_FWD;
}
DECL_COMMAND(command_motor_phase_load_lut,
             "motor_phase_load_lut oid=%c dir=%c offset=%hu data=%*s");

void
command_motor_phase_enable(uint32_t *args)
{
    struct motor_phase *mp = oid_lookup(args[0], command_config_motor_phase);
    uint8_t enable = args[1];
    irq_disable();
    sched_del_timer(&mp->timer);
    mp->flags &= ~(MPF_RUNNING | MPF_BENCH | MPF_FAULT);
    mp->pending = 0;
    irq_enable();
    if (!enable) {
        // Leave a zero vector so no stale LUT current persists while the
        // host still has GCONF.direct_mode set
        mp_resolve_spi(mp);
        mp_write_vector(mp, 0, 0);
        return;
    }
    if (!(mp->flags & MPF_LUT_FWD) || !(mp->flags & MPF_LUT_REV))
        shutdown("motor_phase: enable before lut loaded");
    mp_resolve_spi(mp);
    mp->flags = (mp->flags & ~MPF_INVERT) | (args[2] ? MPF_INVERT : 0);
    mp->phase_offset = args[3] & mp->phase_mask;
    mp_reset_stats(mp);
    mp->last_pos = stepper_get_position_by_oid(mp->stepper_oid);
    // Force an initial write so the vector matches the current position
    mp_update(mp, 1);
    irq_disable();
    mp->flags |= MPF_RUNNING;
    mp->timer.waketime = timer_read_time() + mp->update_ticks;
    sched_add_timer(&mp->timer);
    irq_enable();
}
DECL_COMMAND(command_motor_phase_enable,
             "motor_phase_enable oid=%c enable=%c invert=%c phase_offset=%hu");

void
command_motor_phase_set_current(uint32_t *args)
{
    struct motor_phase *mp = oid_lookup(args[0], command_config_motor_phase);
    uint16_t scale = args[1];
    if (scale > 256)
        scale = 256;
    mp->scale = scale;
}
DECL_COMMAND(command_motor_phase_set_current,
             "motor_phase_set_current oid=%c scale=%hu");

// Run the full update pipeline count times at interval_ticks, with forced
// SPI writes, and report timing statistics.  Safe to run with
// GCONF.direct_mode off — the DIRECT_MODE register is inert then.
void
command_motor_phase_bench(uint32_t *args)
{
    struct motor_phase *mp = oid_lookup(args[0], command_config_motor_phase);
    uint32_t count = args[1];
    if (!count)
        shutdown("motor_phase: bench count must be nonzero");
    if (mp->flags & (MPF_RUNNING | MPF_BENCH))
        shutdown("motor_phase: already running");
    mp_resolve_spi(mp);
    mp_reset_stats(mp);
    mp->update_ticks = args[2];
    mp->budget_ticks = args[2] * 6 / 10;
    mp->bench_remaining = count;
    mp->last_pos = stepper_get_position_by_oid(mp->stepper_oid);
    irq_disable();
    mp->flags |= MPF_BENCH;
    mp->pending = 0;
    mp->timer.waketime = timer_read_time() + mp->update_ticks;
    sched_add_timer(&mp->timer);
    irq_enable();
}
DECL_COMMAND(command_motor_phase_bench,
             "motor_phase_bench oid=%c count=%u interval_ticks=%u");

void
command_query_motor_phase_status(uint32_t *args)
{
    struct motor_phase *mp = oid_lookup(args[0], command_config_motor_phase);
    sendf("motor_phase_status oid=%c flags=%c index=%hu updates=%u writes=%u"
          " misses=%u overruns=%u max_ticks=%u"
          , (uint8_t)args[0], mp->flags, mp->last_index, mp->update_count
          , mp->write_count, mp->miss_count, mp->over_count
          , mp->max_write_ticks);
}
DECL_COMMAND(command_query_motor_phase_status,
             "query_motor_phase_status oid=%c");

// ---------- task: runtime updates and async notifications ----------

void
motor_phase_task(void)
{
    if (!sched_check_wake(&mp_wake))
        return;
    uint8_t oid;
    struct motor_phase *mp;
    foreach_oid(oid, mp, command_config_motor_phase) {
        uint8_t flags = mp->flags;
        if (mp->pending && flags & (MPF_RUNNING | MPF_BENCH)) {
            mp_update(mp, flags & MPF_BENCH ? 1 : 0);
            mp->pending = 0;
        }
        if (flags & MPF_NOTIFY) {
            mp->flags &= ~MPF_NOTIFY;
            if (flags & MPF_FAULT) {
                // Auto-disabled: return to a safe zero vector and tell host
                mp->pending = 0;
                mp_write_vector(mp, 0, 0);
                sendf("motor_phase_fault oid=%c misses=%u", oid,
                      mp->miss_count);
            } else {
                uint32_t avg = mp->write_count
                    ? mp->sum_write_ticks / mp->write_count : 0;
                uint32_t min = mp->write_count ? mp->min_write_ticks : 0;
                sendf("motor_phase_bench_end oid=%c writes=%u misses=%u"
                      " overruns=%u min_ticks=%u max_ticks=%u avg_ticks=%u"
                      , oid, mp->write_count, mp->miss_count, mp->over_count
                      , min, mp->max_write_ticks, avg);
            }
        }
    }
}
DECL_TASK(motor_phase_task);

// ---------- shutdown ----------

void
motor_phase_shutdown(void)
{
    uint8_t oid;
    struct motor_phase *mp;
    foreach_oid(oid, mp, command_config_motor_phase) {
        uint8_t was_active = mp->flags & (MPF_RUNNING | MPF_BENCH);
        mp->flags &= ~(MPF_RUNNING | MPF_BENCH);
        mp->pending = 0;
        if (was_active & MPF_RUNNING && mp->spi)
            // Zero the current vector; the host re-inits GCONF on restart
            mp_write_vector(mp, 0, 0);
    }
}
DECL_SHUTDOWN(motor_phase_shutdown);
