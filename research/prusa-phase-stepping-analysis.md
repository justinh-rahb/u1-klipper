# Prusa Phase Stepping — Research Analysis

Comparison of Prusa's `phase_stepping` implementation (MK4/XL/CORE One) with
our U1 `motor_phase_calibrate` module.  The goal is to identify clues and
techniques from Prusa's production system that can improve our calibration.

> **Source:** `research/prusa-firmware-buddy/lib/Marlin/Marlin/src/feature/phase_stepping/`

---

## 1. Architecture Overview — Prusa vs U1

| Aspect | Prusa (MK4/XL/CORE One) | U1 (current) |
|--------|------------------------|--------------|
| Driver IC | TMC2130 (SPI, direct mode via XDIRECT) | TMC2240 (SPI/UART, direct mode via DIRECT_MODE register 0x2D) |
| Sensor | On-board accelerometer (≤1500 Hz) | None — SG4_RESULT readback only (~1ms per read) |
| Harmonics | Up to 16 (typically 2nd + 4th) | Fundamental only (m=1) |
| Correction | Per-phase LUT with spectral decomposition | Single phase offset (scalar) |
| Directions | Forward + backward (separate corrections) | Single direction |
| Sweep type | Speed sweep + parameter sweeps at constant velocity | Static angle sweep with dwell |
| Computation | Sliding-window DFT with Hann weighting | Circular mean (= phase of DFT bin 1) |
| Runtime | Phase-corrected current waveform at 40–90 kHz ISR | Standard Klipper microstep table |

**Key takeaway:** Prusa's system is _fundamentally_ more capable because it has
an accelerometer and runs the corrected waveform in real time.  However, many
of their mathematical techniques can be adapted to our register-readback
approach.

---

## 2. What Prusa Does Mathematically (and How)

### 2.1 The Correction Model

Prusa models motor non-idealities as a **Fourier series of phase errors**.
For a rotor at electrical position θ, the _actual_ optimal stator phase is
not θ but θ + δ(θ), where:

$$
\delta(\theta) = \sum_{n=1}^{H} a_n \sin(n\theta + \phi_n)
$$

Each harmonic *n* has a **magnitude** *aₙ* and a **phase** *ϕₙ*. These are
stored in a `MotorPhaseCorrection` array of `SpectralItem{mag, pha}` — one
per harmonic up to H=16.

The corrected current waveform becomes:

$$
I_A(\theta) = I_0 \sin\bigl(\theta + \delta(\theta)\bigr), \qquad
I_B(\theta) = I_0 \cos\bigl(\theta + \delta(\theta)\bigr)
$$

This is pre-computed into a 1024-entry lookup table (`CorrectedCurrentLut`)
for fast ISR access.

**Contrast with U1:** We currently extract only a single scalar offset φ̂
(equivalent to Prusa's harmonic n=1 with fixed magnitude).  We do _not_
correct higher harmonics, and we do not apply corrections at runtime — we
just shift the microstep table origin.

### 2.2 Calibration Pipeline

Prusa's calibration has three stages per harmonic:

#### Stage 1: Speed Sweep — Find Resonant Speed

Move the axis through a speed ramp (e.g. 0.2–4 rev/s) while capturing
accelerometer data.  For each harmonic *n*, compute a sliding-window DFT at
the expected vibration frequency:

$$
f_{\text{analysis}}(v) = n \cdot v \cdot \frac{\text{motor\_steps}}{4}
$$

where *v* is the motor speed in rev/s and `motor_steps/4` converts to
electrical periods.  The DFT is computed as:

$$
\text{DFT}(t) = \left| \frac{2}{W} \sum_{k \in \text{window}} s(k) \cdot e^{-j \cdot \phi(k)} \right|
$$

where φ(k) is the instantaneous phase of the analysis frequency at sample k,
and W is the window size.  For accelerating movements, the phase is computed
by integrating the chirped frequency:

$$
\phi(k) = 2\pi \left( f_0 t + \frac{1}{2} \dot{f} t^2 \right)
$$

Peaks in the DFT magnitude vs. speed curve identify resonant speeds where the
harmonic is most visible.  Prusa uses **harmonic peak fitting** — if harmonics
2 and 4 are enabled, it looks for peaks at speeds where f₂ = 2·f₁ and
f₄ = 4·f₁, fitting:

$$
\hat{f}_1 = \frac{\sum_i p_i / h_i}{\sum_i 1/h_i^2}
$$

(This is the standard weighted least-squares solution for minimising
E = Σ(pᵢ − f̂₁/hᵢ)²: take dE/df̂₁ = 0 and solve for f̂₁.)

This least-squares estimate finds the fundamental frequency that best explains
all detected peaks.

#### Stage 2: Parameter Sweep — Phase Estimation

At the identified resonant speed, perform constant-velocity moves while
sweeping the correction phase ϕₙ from 0 to 2π (with magnitude held constant
at the estimated value).  The vibration response is measured via the same
sliding-window DFT.  The phase value that _minimises_ vibration is the correct
correction phase.

Prusa sweeps through 2 full cycles of phase and uses `find_evenly_spaced_peaks`
to robustly locate the minima (which should repeat every 2π).  The final
phase is the average of all detected minima modulo 2π.

#### Stage 3: Parameter Sweep — Magnitude Estimation

With the phase locked, sweep the magnitude from 0 to 2×(estimated magnitude)
and locate the minimum vibration point.  This gives the precise correction
magnitude.

The three stages are run sequentially for each enabled harmonic (typically
harmonics 2 and 4), with even harmonics calibrated before odd ones.

### 2.3 The Sliding-Window DFT

This is the core signal processing primitive.  It is a **time-frequency
analysis** technique — essentially a short-time Fourier transform (STFT) at
a single frequency bin:

```
class SlidingDftWindow:
    buffer: circular buffer of (sin_corr, cos_corr) pairs
    sin_sum, cos_sum: running accumulators

    push_sample(sample):
        remove oldest from sums
        add newest to sums

    get_magnitude():
        return sqrt(sin_sum² + cos_sum²) · 2/W

    get_windowed_magnitude():
        apply Hann window to buffer
        return sqrt(Σ(h·sin)² + Σ(h·cos)²) · 2/W
```

For each sample at time index k:
1. Compute the expected phase: `arg = 2π · k · f_analysis · T_sample`
2. Correlate: `(sin(arg) · s(k), cos(arg) · s(k))`
3. Push into the sliding window
4. Read out the magnitude

The Hann window variant suppresses spectral leakage when the analysis
frequency doesn't exactly match the signal frequency.

### 2.4 Forward vs Backward Corrections

Prusa maintains **separate correction tables** for forward and backward
movement.  This accounts for direction-dependent effects (mechanical
backlash, different friction profiles, asymmetric motor winding impedances).
During motion, the firmware selects the appropriate LUT based on the current
movement direction.

### 2.5 Fixed-Point LUT for Runtime

The correction is baked into a 1024-entry LUT at init time. For each
microstep index *i*:

1. Compute the phase shift: `δ(i) = Σₙ aₙ · sin(n·i·SIN_FRACTION + ϕₙ)`
2. Apply to the waveform: `I_A = sin(i·SIN_FRACTION + δ), I_B = cos(i·SIN_FRACTION + δ)`

All arithmetic uses fixed-point with `SIN_LUT_FRACTIONAL=15` bits and
`MAG_FRACTIONAL=8` bits, enabling the ISR to run at 40 kHz without floating
point.

---

## 3. Clues and Actionable Insights for U1

### 3.1 Multi-Harmonic Correction (High Priority)

**Prusa's insight:** Motor non-idealities are not a single phase offset but a
periodic distortion with content at multiple harmonics.  Their default config
enables harmonics 2 and 4 (`enabled_harmonics = 0b1010`).

**Implication for U1:** Our current circular-mean approach extracts only the
phase of the fundamental (m=1).  Prusa's data shows that harmonics 2 and 4
are the dominant error sources.  We should:

1. Extend `_compute_phase_offset()` to compute multiple DFT bins, not just
   the circular mean.
2. Store per-harmonic `{magnitude, phase}` corrections instead of a single
   scalar offset.
3. Apply the correction as a phase-shift function δ(θ) at runtime.

Even without an accelerometer, we can extract multiple harmonics from the
SG4_RESULT signal — the DFT math is identical.

### 3.2 Speed-Dependent Calibration (Medium Priority)

**Prusa's insight:** Different motor speeds excite different harmonics
differently.  Their speed sweep identifies the optimal speed for each harmonic.

**Implication for U1:** Our current static sweep (motor at rest, rotating the
field) does not excite speed-dependent effects.  To detect cogging harmonics:

- We could perform slow constant-velocity moves (using Klipper's motion
  planner) while reading SG4_RESULT at each microstep position.
- The SG4 readback rate (~1ms) limits us to slow speeds, but that may be
  sufficient for the dominant harmonics.

### 3.3 Forward/Backward Asymmetry (Medium Priority)

**Prusa's insight:** Corrections differ between forward and backward movement.

**Implication for U1:** We should at minimum calibrate in both directions and
store separate correction values.  This is a straightforward extension of the
existing sweep code.

### 3.4 The Sensor Gap (Critical Constraint)

**Prusa's advantage:** An on-board accelerometer at 1500 Hz provides direct
measurement of vibration amplitude at any motor harmonic.

**U1's capability:** The U1 toolhead has an on-board **LIS2DW** 3-axis
accelerometer (SPI1, CS=e0:PA4, axes\_map: y,x,z) already used for input-shaper
resonance testing.  This gives us near-parity with Prusa's sensor approach.

Available measurement channels for phase stepping calibration:

1. **LIS2DW accelerometer** — on-board, directly measures vibration amplitude.
   Can be used for Prusa-style sliding-window DFT calibration during motor
   sweeps.  Already integrated into Klipper via `klippy/extras/lis2dw.py`.
2. **SG4_RESULT readback** — gives a proxy for motor load/back-EMF at ~1ms
   intervals.  Usable for slow sweeps but aliased at higher harmonics.
   Serves as a fallback when accelerometer data is unavailable.
3. **MSCURACT readback** — reports the actual microstep currents being applied;
   comparing commanded vs actual can reveal phase errors.

**Recommendation:** Use the on-board LIS2DW for accelerometer-based
calibration (similar to Prusa), with SG4\_RESULT as a fallback.

### 3.5 Windowed DFT vs Our Circular Mean

**Prusa's approach:** Sliding-window DFT with Hann window, computed
continuously during movement.  This handles time-varying signals (speed
ramps) and suppresses spectral leakage.

**Our approach:** Circular mean over a complete sweep — equivalent to a
rectangular-windowed DFT at m=1 over the entire data set.

**Upgrade path:**
1. Replace the circular mean with explicit per-bin DFT computation.
2. Use a Hann window to reduce leakage (important when the sweep doesn't
   cover an exact integer number of periods).
3. Compute magnitude as well as phase for each harmonic — magnitude tells us
   _how much_ correction is needed, not just _where_.

### 3.6 Harmonic Peak Fitting

Prusa's `harmonic_peaks_fit()` uses a clever least-squares approach: given
detected peaks at harmonics h₁, h₂, ..., it estimates the fundamental
frequency that best explains all of them. This is more robust than looking at
each harmonic independently.

We should adopt this if we add multi-harmonic support — it cross-validates
the harmonic structure.

### 3.7 Runtime Correction Waveform (Aspirational)

Prusa's firmware replaces the standard step/direction interface with a
phase-corrected current waveform generated at 40 kHz via SPI direct writes.
This is the _ultimate_ use of the calibration data.

**For U1 this would require:**
1. A timer ISR on the toolhead MCU (AT32F415RC at 144 MHz — feasible).
2. Direct SPI writes to the TMC2240 DIRECT_MODE register from the ISR.
3. Position tracking from the Klipper motion planner, forwarded to the
   toolhead MCU via CAN.

This is a significant firmware change but is the path to full Prusa-level
phase stepping on U1.

---

## 4. Summary: Prusa's Key Mathematical Techniques

| Technique | Prusa File | What It Does | Can We Use It? |
|-----------|-----------|-------------|---------------|
| Spectral correction model | `common.hpp` | Multi-harmonic {mag, pha} per motor | ✅ Yes — extend our data model |
| Sliding-window DFT | `calibration.cpp` | Time-frequency analysis of vibration | ✅ Yes — for moving sweeps |
| Hann-windowed DFT | `calibration.cpp` | Suppresses spectral leakage | ✅ Yes — improves accuracy |
| Harmonic peak fitting | `calibration.cpp` | Robustly identifies resonant speeds | ⚠️ Needs accelerometer or slow SG4 sweeps |
| Speed sweep | `calibration.cpp` | Finds optimal calibration speed per harmonic | ⚠️ Needs accelerometer for reliable signal |
| Parameter sweep (phase) | `calibration.cpp` | Sweeps correction phase, finds minimum vibration | ✅ Yes — substitute SG4 for accel |
| Parameter sweep (magnitude) | `calibration.cpp` | Sweeps correction magnitude, finds minimum | ✅ Yes — substitute SG4 for accel |
| Fixed-point LUT | `lut.cpp` | Real-time corrected waveform at 40 kHz | ✅ Yes — if we add ISR-driven direct mode |
| Forward/backward split | `phase_stepping.hpp` | Separate corrections per direction | ✅ Yes — straightforward extension |
| Evenly-spaced peak detection | `calibration.cpp` | Robustly detects periodic minima in sweeps | ✅ Yes — general-purpose utility |

---

## 5. Recommended Roadmap

1. **Immediate** — Extend `_compute_phase_offset()` to extract harmonics 1–4
   via per-bin DFT, storing `{mag, pha}` for each.  Apply a Hann window.
2. **Short-term** — Add forward/backward sweep capability.  Store directional
   corrections.
3. **Medium-term** — Integrate the on-board LIS2DW accelerometer into the
   calibration sweep for Prusa-style vibration-based harmonic extraction.
4. **Long-term** — Implement ISR-driven corrected waveform on the AT32F415RC
   toolhead MCU, modelled on Prusa's `handle_periodic_refresh()`.

---

## 6. File Index — Prusa Phase Stepping

| File | Size | Purpose |
|------|------|---------|
| `phase_stepping_opts.h` | 1 KB | Constants: MOTOR_PERIOD=1024, SIN_PERIOD=4096, CORRECTION_HARMONICS=16 |
| `common.hpp` | 1 KB | `SpectralItem{mag,pha}`, fixed-point converters |
| `lut.hpp` / `lut.cpp` | 3.5/5 KB | `CorrectedCurrentLut` — sin LUT, phase shift computation, runtime current lookup |
| `calibration_config.hpp` | 1.5 KB | Per-printer calibration parameters (speed ranges, enabled harmonics) |
| `calibration.hpp` | 3.7 KB | Public calibration API: `calibrate_axis()`, `CalibrateAxisHooks` |
| `calibration.cpp` | 84 KB | Full calibration pipeline: speed sweep, parameter sweeps, peak fitting |
| `phase_stepping.hpp` | 17 KB | `AxisState`, runtime enable/disable, `MoveTarget` trajectory tracking |
| `phase_stepping.cpp` | 37 KB | ISR handler, step generator integration, TMC direct-mode management |
| `axes.hpp` / `axes.cpp` | 1/2.7 KB | Motor parameter helpers (steps, phase, position conversions) |
| `burst_stepper.cpp` | 6.5 KB | Optimized burst stepping for TMC2130 |
| `quick_tmc_spi.cpp` | 2.7 KB | Fast SPI path for TMC register writes in ISR |
