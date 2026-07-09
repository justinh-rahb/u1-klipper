# Motor Phase Calibration — Mathematical Reference

This document describes the mathematics behind the motor phase calibration
procedure implemented in `motor_phase_calibrate.py`.  It is written for
readers familiar with phase reconstruction and spectral analysis but not
necessarily with the Klipper codebase or embedded firmware.

---

## 1. Physical Setup

A two-phase hybrid stepper motor has two stator windings (phase A and
phase B) driven by sinusoidal currents in quadrature:

$$
I_A(\theta) = I_0 \cos\theta, \qquad I_B(\theta) = I_0 \sin\theta
$$

where θ is the *electrical angle* and I₀ is the peak current amplitude.

The TMC2240 driver IC normally generates these waveforms internally from a
step/direction input via a built-in microstep table.  In **direct mode**
(GCONF.direct\_mode = 1) the host can bypass the internal waveform generator
and write explicit (cur\_a, cur\_b) values to the DIRECT\_MODE register, giving
full control of the stator field vector.

### 1.1 Hardware Context

On the U1 the **X and Y axis steppers** are the relevant calibration targets.
Their TMC2240 drivers sit on the **mainboard** (AT32F403A) and communicate
over the mainboard SPI buses (SPI2 for X, SPI4 for Y).  The Z axis uses a
TMC2209, and the four extruder toolhead MCUs (AT32F415RC) also use TMC2209
— neither the Z stepper nor the extruders support DIRECT\_MODE and cannot be
calibrated with this module.

The U1 printer has four toolhead MCUs (AT32F415RC) connected to the mainboard
over a **CAN bus** (the CAN-to-USB bridge is USB-attached to the SBC, but the
toolhead link itself is CAN).  The host Python layer performs the TMC register
reads and writes; the MCU-side firmware only provides a timer-driven state
machine for sequencing angle steps.

---

## 2. The Sweep: Imposing a Known Rotating Field

During calibration the host sweeps the electrical angle θ through one full
revolution in *N* discrete steps (default N = 256):

$$
\theta_k = \frac{2\pi k}{N}, \qquad k = 0, 1, \ldots, N-1
$$

At each step the host commands the stator current vector:

$$
I_A(k) = I_0 \cos\theta_k, \qquad I_B(k) = I_0 \sin\theta_k
$$

This is equivalent to rotating a magnetic field vector of constant
magnitude through 360 electrical degrees.

After commanding each vector, the host dwells for a fixed interval
*T*<sub>dwell</sub> (default 20 ms) and then reads a diagnostic value from
the TMC2240 — typically the StallGuard4 result (SG4\_RESULT) — which
serves as the response signal *r*(*k*).

### 2.1 Current Scaling

The DIRECT\_MODE register accepts 9-bit signed DAC codes in the range
[−256, +255].  The requested sweep current *I*<sub>mA</sub> (in
milliamps) is mapped to a DAC scale factor:

$$
s = \mathrm{clamp}\!\left(\left\lfloor \frac{I_{\mathrm{mA}} \cdot 255}{2000}\right\rfloor,\; 1,\; 255\right)
$$

The per-step DAC values are then:

$$
\text{cur\\_a}(k) = \lfloor s \cos\theta_k \rfloor, \qquad
\text{cur\\_b}(k) = \lfloor s \sin\theta_k \rfloor
$$

The factor of 2000 in the denominator is a conservative choice that maps the
maximum configurable sweep current (2000 mA) to ≈ 70 % of the full DAC
range.  The exact relationship between DAC codes and winding current depends
on the sense resistor value and the TMC2240 GLOBALSCALER register.

---

## 3. Response Signal

At each angle step *k* the host reads the StallGuard4 result register:

$$
r(k) = \text{SG4\\_RESULT}(\theta_k)
$$

StallGuard measures the motor's back-EMF relative to the expected load
condition.  Its value peaks when the applied field aligns with the rotor
and dips when it opposes the rotor.  The response therefore has a dominant
component at the fundamental frequency of the imposed rotation.

If no sensor reading is available (the MCU-side ADC returns 0), the
algorithm falls back to uniform weighting — see Section 4.2.

---

## 4. Phase Offset Extraction via Circular Mean

### 4.1 Why Circular Statistics?

The angle domain is periodic (0 ≡ 2π), so ordinary arithmetic averaging
would give meaningless results near the wraparound.  The calibration uses
the **circular mean** (also called the *mean direction*), the standard
estimator from directional statistics.

### 4.2 Computation

Given the *N* samples { (θ<sub>k</sub>, r(k)) }, treat each measurement as
a weighted unit vector on the circle:

$$
C = \sum_{k=0}^{N-1} w_k \cos\theta_k, \qquad
S = \sum_{k=0}^{N-1} w_k \sin\theta_k
$$

where the weight *w*<sub>k</sub> is:

$$
w_k = \max\!\bigl(r(k),\; 1\bigr)
$$

The `max(·, 1)` ensures that when the sensor returns zero for every step
(as it does on the U1 toolhead, which lacks a per-phase sense-resistor
ADC), the algorithm degenerates gracefully to a *uniform* circular mean
— essentially the centroid of N equally-spaced points — which returns
θ = 0 and serves as a placeholder until real measurements are available.

The estimated phase offset is:

$$
\hat\phi = \mathrm{atan2}\!\left(\frac{S}{W},\; \frac{C}{W}\right),
\qquad W = \sum_{k=0}^{N-1} w_k
$$

Converted back to an index in [0, N):

$$
\hat n = \frac{\hat\phi \cdot N}{2\pi} \pmod{N}
$$

### 4.3 Interpretation

- **φ̂ = 0** means the rotor's natural resting position is already
  aligned with electrical angle zero — no correction needed.
- **φ̂ ≠ 0** means the motor's internal alignment is offset by that many
  electrical degrees from the driver's zero reference.  Applying this
  correction shifts the microstep table so that full-step positions
  coincide with the rotor's actual magnetic detent positions, reducing
  vibration and improving positional accuracy.

---

## 5. Relationship to Spectral Analysis

Readers with a signal-processing background will recognise the circular
mean as the **phase of the first Fourier coefficient** of the response
signal sampled on a uniform angular grid.

If we define the DFT of the response:

$$
R(m) = \sum_{k=0}^{N-1} r(k)\, e^{-j\,2\pi mk/N}
$$

then the fundamental component (*m* = 1) has magnitude and phase:

$$
|R(1)| = \sqrt{C^2 + S^2}, \qquad
\angle R(1) = \mathrm{atan2}(S, C)
$$

which is exactly the circular-mean angle φ̂.

In other words, the calibration extracts the **phase of the fundamental
harmonic** of the motor's response to a rotating excitation field.  This
is the classical single-tone phase-estimation problem: inject a known
sinusoid, correlate the response with sine and cosine references, and
take the arctangent.

### 5.1 Why Only the Fundamental?

The excitation is a pure single-frequency rotating field (one electrical
revolution).  By Fourier analysis the response will contain:

| Harmonic | Physical origin | Relevance |
|----------|-----------------|-----------|
| m = 0 (DC) | Mean load / friction | Irrelevant to phase |
| **m = 1** | **Rotor–stator alignment** | **Target signal** |
| m = 2, 3, … | Cogging, winding non-idealities | Noise |

The circular mean acts as a matched filter for *m* = 1 — it projects onto
the fundamental and discards all other harmonics.

### 5.2 Noise Considerations

The estimator φ̂ is the maximum-likelihood estimate for the phase of a
sinusoid in additive white Gaussian noise.  Its variance is bounded by the
Cramér–Rao lower bound:

$$
\mathrm{Var}(\hat\phi) \;\ge\; \frac{2}{N \cdot \mathrm{SNR}}
$$

where SNR is the signal-to-noise ratio of the fundamental component.
Increasing the number of sweep steps *N* or the sweep current (improving
SNR) tightens the estimate.  Typical values (N = 256, moderate SNR) give
sub-degree accuracy.

---

## 6. End-to-End Procedure Summary

```
1.  Enable TMC2240 direct mode  (GCONF.direct_mode ← 1)
2.  For k = 0 … N−1:
      a.  Write DIRECT_MODE ← (s·cos θ_k,  s·sin θ_k)
      b.  Dwell T_dwell
      c.  Read r(k) ← SG4_RESULT
3.  Disable direct mode  (GCONF.direct_mode ← 0)
4.  Compute C = Σ w_k cos θ_k,   S = Σ w_k sin θ_k
5.  φ̂ = atan2(S, C)           ← estimated phase offset (radians)
6.  n̂ = φ̂ · N / 2π  (mod N)  ← offset in microstep units
7.  Persist n̂ to printer config
```

---

## 7. Multi-Harmonic Extension (Implemented)

This is the model implemented in `motor_phase_calibrate.py` /
`src/motor_phase_calibrate.c`: acceleration harmonics are measured with the
printer's accelerometer during constant-speed moves (replacing the SG4
response signal of Sections 2–6, which describes the earlier sweep
prototype), converted to phase-correction coefficients, and applied at
runtime from an MCU-side current LUT synchronized to the stepper position.
Real stepper motors exhibit periodic errors at **multiple harmonics** of the
electrical period — primarily at m = 2 (half-period cogging) and m = 4
(quarter-period, related to the 4 full-step positions per electrical cycle).

Research into Prusa's production phase-stepping system (see
`research/prusa-phase-stepping-analysis.md`) confirms that harmonics 2 and 4
are the dominant error sources.

### 7.1 Generalised Correction Model

Instead of a single offset φ̂, the full model uses a Fourier series:

$$
\delta(\theta) = \sum_{n=1}^{H} a_n \sin(n\theta + \phi_n)
$$

where *H* is the highest corrected harmonic.  The corrected stator phase
becomes θ + δ(θ), and the per-phase currents are:

$$
I_A(\theta) = I_0 \cos\!\bigl(\theta + \delta(\theta)\bigr), \qquad
I_B(\theta) = I_0 \sin\!\bigl(\theta + \delta(\theta)\bigr)
$$

### 7.2 Extracting Multiple Harmonics

Given the N-point response signal r(k), each harmonic's parameters are
recovered from the corresponding DFT bin:

$$
R(n) = \sum_{k=0}^{N-1} r(k)\, e^{-j\,2\pi nk/N}
$$

$$
a_n = \frac{2|R(n)|}{N}, \qquad \phi_n = \angle R(n)
$$

The fundamental-only circular mean (Section 4) is the special case n = 1.

### 7.3 Windowed DFT

When the sweep does not cover an exact integer number of electrical periods,
spectral leakage blurs the harmonic estimates.  Applying a **Hann window**
before the DFT mitigates this:

$$
w_H(k) = \frac{1}{2}\left(1 - \cos\frac{2\pi k}{N-1}\right)
$$

$$
R_H(n) = \sum_{k=0}^{N-1} w_H(k)\, r(k)\, e^{-j\,2\pi nk/N}
$$

This is the approach used in Prusa's `SlidingDftWindow::get_windowed_magnitude()`.

### 7.4 Direction-Dependent Correction

Motor correction can differ between forward and backward motion (friction
asymmetry, mechanical backlash).  Calibrating in both directions and storing
separate {aₙ, ϕₙ} sets for each direction improves accuracy.

---

## 8. Glossary

| Symbol | Meaning |
|--------|---------|
| θ<sub>k</sub> | Electrical angle at sweep step *k* |
| N | Total number of sweep steps (default 256) |
| I₀ | Peak sweep current amplitude |
| s | DAC scale factor (9-bit, 0–255) |
| r(k) | Diagnostic response at step *k* (SG4\_RESULT) |
| w<sub>k</sub> | Weight for step *k* = max(r(k), 1) |
| C, S | Cosine and sine accumulators (real and imaginary parts of R(1)) |
| φ̂ | Estimated phase offset (radians) |
| n̂ | Phase offset in microstep-index units |
| R(m) | DFT of response signal at harmonic *m* |
| T<sub>dwell</sub> | Dwell time per angle step (default 20 ms) |
| δ(θ) | Total phase correction function (Fourier series) |
| H | Highest corrected harmonic |
| aₙ | Magnitude of harmonic *n* correction |
| ϕₙ | Phase of harmonic *n* correction |
| w<sub>H</sub>(k) | Hann window function |

---

## 9. References

1. K.V. Mardia and P.E. Jupp, *Directional Statistics*, Wiley, 2000 —
   circular mean definition and properties (Chapter 2).
2. Trinamic TMC2240 datasheet, §6.4 "Direct Mode" — DIRECT\_MODE register
   layout, GCONF.direct\_mode bit.
3. S.M. Kay, *Fundamentals of Statistical Signal Processing: Estimation
   Theory*, Prentice Hall, 1993 — Cramér–Rao bound for sinusoidal phase
   estimation (Chapter 3).
4. Prusa Research, *Prusa-Firmware-Buddy* `phase_stepping` module —
   production implementation of multi-harmonic phase correction with
   accelerometer-based calibration.  See `research/prusa-phase-stepping-analysis.md`
   for a detailed comparison.
