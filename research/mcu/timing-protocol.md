# Clock Frequency and Timing Protocol Analysis

Analysis of how AT32F403A (240 MHz) and AT32F415 (144 MHz) clock frequencies
interact with Klipper's tick-based timing architecture, USB clock stability,
and the MCU command protocol.

## Clock Frequency Architecture

Klipper's timing model is MCU-agnostic. Each MCU declares its clock speed via
a firmware constant, and the host adapts all time ↔ tick conversions
accordingly.

### Firmware Declaration

Both AT32 variants declare `CLOCK_FREQ` in `src/Kconfig` using the same
mechanism as every other Klipper MCU:

| MCU | CLOCK_FREQ | Tick Period | Kconfig Line |
|------------|-------------|-----------|--------------|
| AT32F403A | 240 000 000 | 4.17 ns | 224 |
| AT32F415 | 144 000 000 | 6.94 ns | 223 |
| STM32F103 | 72 000 000 | 13.89 ns | (reference) |
| STM32F105 | 72 000 000 | 13.89 ns | (reference) |

The constant is emitted by `DECL_CONSTANT("CLOCK_FREQ", ...)` in the compiled
firmware and reported to the host at connection time.

### Host-Side Retrieval

`klippy/mcu.py` reads the constant on connect:

```python
self._mcu_freq = self.get_constant_float('CLOCK_FREQ')
```

All subsequent time conversions use this value. No STM32-specific clock
frequencies are hardcoded anywhere in the Python code — the design is fully
MCU-agnostic: report your clock speed, Klipper handles the rest.

### System Clock Source

Both AT32 chips derive their system clock from an external crystal (HEXT)
through PLL multiplication, not from internal RC oscillators:

- **AT32F403A**: HEXT → PLL → 240 MHz system clock
- **AT32F415**: HEXT → PLL → 144 MHz system clock

This means the system clock stability is determined by the crystal, which is
orders of magnitude better than an internal RC oscillator.

## Step Timing

### Tick-Based Architecture

Klipper's step timing is fundamentally clock-tick based. The step compression
algorithm (`klippy/chelper/stepcompress.c`) works entirely in MCU clock ticks.
The `CLOCK_FREQ` constant ensures the host correctly converts between real time
and MCU ticks, so no tick-based constants need manual adjustment for different
MCU frequencies.

### Precision Gains

Higher clock frequencies provide finer step timing granularity:

| MCU | Min Step Interval | Relative Precision |
|------------|-------------------|--------------------------|
| STM32F103 | 13.89 ns | 1× (baseline) |
| AT32F415 | 6.94 ns | 2× finer |
| AT32F403A | 4.17 ns | 3.33× finer |

In practice this additional precision is rarely the limiting factor — IRQ
latency and MCU processing overhead dominate the minimum achievable step
interval — but it does give the step compression algorithm slightly more
headroom to represent acceleration curves.

### Stepper Code Changes

`src/stepper.c` has modifications that add `type`, `index`, `print_act`, and
`move_line` fields to the stepper structure. These are for power-loss position
tracking (recording where each stepper was when power was lost) and do **not**
alter the core step timing logic. The timer-driven step execution path is
unchanged.

## USB Clock Stability

### AT32F403A: ACC + SOF Locking

The AT32F403A uses its internal high-speed RC oscillator (HICK) to generate
the 48 MHz USB clock. To meet USB ±0.25% tolerance, the Auto Clock Calibration
(ACC) peripheral locks HICK to the USB Start-of-Frame (SOF) signal:

- SOF arrives every 1 ms (1 kHz) when USB is connected.
- ACC continuously adjusts HICK trim to match.
- Calibration begins when the USB clock is enabled in
  `at32f403a_clock_setup()` — there is no explicit convergence wait.

**Key point**: HICK is used **only** for the USB 48 MHz clock. The system
clock (240 MHz) comes from HEXT → PLL and is completely independent. Therefore:

- USB disconnect does **not** affect step timing or MCU clock stability.
- USB disconnect **does** cause HICK to drift (typical internal RC accuracy
  ~1%), which may degrade USB communication quality on reconnect.
- After cold start, the first USB packets may have slightly off timing until
  ACC converges (typically a few SOF frames).

### AT32F415: Crystal-Derived USB Clock

The AT32F415 derives its 48 MHz USB clock directly from HEXT via the PLL
(144 ÷ 3 = 48 MHz). There is:

- No HICK dependency for USB.
- No ACC / SOF locking required.
- USB clock stability identical to system clock stability.

### Summary Table

| Property | AT32F403A | AT32F415 |
|-----------------------------|---------------------|---------------------|
| USB 48 MHz source | HICK (ACC-trimmed) | HEXT / PLL (144/3) |
| SOF locking | Yes (ACC) | No |
| USB affected by disconnect? | Yes (HICK drifts) | No |
| System clock affected? | No | No |
| Step timing affected? | No | No |

## Protocol Compatibility

### Unchanged Wire Protocol

The Klipper MCU command protocol (message encoding, framing, CRC) is
**unchanged** for AT32 chips. All AT32 changes are purely at the HAL level,
beneath the protocol layer. Existing host-side code communicates with AT32
MCUs using exactly the same binary protocol as STM32 MCUs.

### New MCU Commands

The U1 firmware adds new commands for hardware-specific features. These use
standard Klipper command registration (`DECL_COMMAND` macros) and follow the
normal protocol conventions:

**Inductance sensing:**
- `inductance_coil_config`
- `query_inductance_coil`
- `virtual_gpio_trigger`

**Power loss detection:**
- `config_power_loss_check`
- `enable_power_loss`
- `query_power_loss_*`

No changes to message encoding, framing, or CRC were introduced.

## Python Integration

### Time Conversion

`mcu.py` provides `seconds_to_clock()` which scales correctly for any
frequency:

```python
def seconds_to_clock(self, time):
    return int(time * self._mcu_freq)
```

At 240 MHz, 1 ms → 240 000 ticks. At 144 MHz, 1 ms → 144 000 ticks.

### Clock Synchronization

`klippy/clocksync.py` adapts to the reported `CLOCK_FREQ` automatically. The
synchronization algorithm is frequency-independent — it operates on measured
round-trip times and tick deltas.

### U1 Python Extras

The Python-side extras for U1-specific features use standard MCU command
interfaces with no AT32-specific workarounds:

- `inductance_coil.py`: default `freq_cal_cycle = 0.001 s`, converted to
  ticks via `seconds_to_clock()`.
- `power_loss_check.py`: default trigger time `0.0109 s`, similarly converted.

No Python-side workarounds for AT32 clock frequencies were found anywhere in
the codebase.

## Potential Concerns

### 1. 32-Bit Tick Counter Overflow

Higher clock frequencies cause the 32-bit tick counter to wrap faster:

| MCU | Overflow Period |
|------------|-----------------|
| STM32F103 | ~59.7 s |
| AT32F415 | ~29.8 s |
| AT32F403A | ~17.9 s |

Klipper handles counter wraparound in `clocksync.py` using modular
arithmetic, so this is not a correctness bug. However, the tighter window at
240 MHz means:

- Clock synchronization must run frequently enough to track wraparounds
  (Klipper's default sync interval is well within bounds).
- Any code that compares raw tick values across long time spans must use the
  wraparound-aware comparison helpers.

### 2. Step Rate Limits

Higher tick resolution allows higher *theoretical* step rates, but the
practical limit is bounded by:

- MCU instruction throughput per step IRQ.
- IRQ entry/exit latency.
- Competing IRQ sources (USB, ADC, other timers).

The AT32F403A's 240 MHz core does provide more headroom here compared to a
72 MHz STM32F103, but the relationship is not linear because memory wait
states and peripheral bus dividers also come into play.

### 3. Timer Peripheral Clock Rates

APB bus clocks differ significantly:

| MCU | APB1 | APB2 |
|------------|---------|---------|
| STM32F103 | 36 MHz | 72 MHz |
| AT32F403A | 120 MHz | 120 MHz |

Timer prescaler configurations in the AT32 HAL account for this via the
`system_core_clock` variable, so timer period registers are set correctly.
No manual prescaler adjustment is needed when porting.

### 4. ACC Convergence at Cold Start (AT32F403A Only)

There is no explicit wait for ACC convergence after enabling the USB clock.
The ACC runs continuously in the background and typically converges within a
few SOF frames (~ms). The risk is minimal: the first few USB packets after a
cold start may have marginally degraded timing, but Klipper's protocol-level
retransmission handles occasional corruption gracefully.

This concern does not apply to the AT32F415, which uses a crystal-derived USB
clock.
