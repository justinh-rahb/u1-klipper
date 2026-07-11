# Motor Phase Calibration — Mathematical Reference

This document describes the model used by `klippy/extras/motor_phase_calibrate.py`
and the runtime LUT engine in `src/motor_phase_calibrate.c`.

The short version: this is not TMC Autotune.  Autotune chooses better driver
parameters for the TMC's own chopper/current loop.  Motor phase correction
measures periodic force/torque error and applies a synchronized correction to
the commanded phase-current waveform through TMC2240 `DIRECT_MODE`.

---

## 1. Physical Model

A two-phase stepper is driven by winding currents

$$
\mathbf{i}(\theta) =
\begin{bmatrix}
I_A(\theta) \\
I_B(\theta)
\end{bmatrix}
$$

where $\theta$ is the electrical angle.  With the normal ideal microstep table:

$$
I_A = I_0\cos\theta,\qquad I_B = I_0\sin\theta
$$

The motor does not care about complex numbers.  The physical quantities are
real currents, rotor flux, magnetic force, torque, stiffness, friction, and
mechanical acceleration.

For small errors, the useful first-order picture is the Lorentz/torque
interaction between the commanded stator field and the rotor field:

$$
\tau \propto \mathbf{\psi}_r \times \mathbf{i}
$$

Equivalently, if the stator field is slightly ahead of or behind the useful
tangential direction, the torque error is approximately linear in that small
angle error.  This module therefore represents the correction as a small
tangential field-angle perturbation:

$$
\delta(\theta) = \sum_{n \in H} a_n \sin(n\theta + \phi_n)
$$

and commands:

$$
I_A = I_0\cos(\theta + \delta(\theta)),\qquad
I_B = I_0\sin(\theta + \delta(\theta))
$$

That keeps the current magnitude approximately constant and changes the field
angle only.  This is a deliberate v1 restriction: it can correct tangential
phase/torque ripple, but it cannot independently correct radial force or
current-amplitude ripple.  A fuller model would allow both angle and radius:

$$
\mathbf{i}'(\theta) =
(I_0 + \rho(\theta))
\begin{bmatrix}
\cos(\theta + \delta(\theta)) \\
\sin(\theta + \delta(\theta))
\end{bmatrix}
$$

where $\rho(\theta)$ is a radial/current-magnitude correction.  The current
implementation sets $\rho(\theta)=0$.

---

## 2. Coordinate Domains

The code uses three coordinate languages, but each has a narrow job:

| Domain | What it means here |
|--------|--------------------|
| Planar | The actual TMC `DIRECT_MODE` DAC values: `(cur_a, cur_b)` |
| Polar | A convenient way to preserve current magnitude while shifting angle |
| Phasor/vector coefficients | A compact representation of sinusoid amplitude and phase |

The phasor representation is only bookkeeping for real sine/cosine
coefficients.  The fitted signal is:

$$
y(\theta) \approx c_0 +
\sum_{n \in H}\left(c_n\cos(n\theta) + s_n\sin(n\theta)\right)
$$

and the stored magnitude/phase form is just:

$$
c_n\cos(n\theta) + s_n\sin(n\theta)
= A_n\cos(n\theta + p_n)
$$

with:

$$
A_n = \sqrt{c_n^2+s_n^2},\qquad
p_n = \mathrm{atan2}(-s_n, c_n)
$$

No physical step in the model depends on a complex-valued motor.

---

## 3. Measurement

Calibration runs constant-speed moves on one axis while collecting
accelerometer samples.  During the trimmed cruise window, electrical angle is
known from stepper position and speed:

$$
\theta(t) = \theta_0 + \omega_e t
$$

where:

$$
\omega_e = 2\pi f_e,\qquad
f_e = \frac{\text{step pulses per second}}{4\cdot\text{microsteps}}
$$

The measured acceleration along the moving axis is fit against the real
harmonic basis:

$$
a_\text{meas}(\theta) \approx c_0 +
\sum_{n \in H}\left(c_n\cos(n\theta) + s_n\sin(n\theta)\right)
$$

`extract_harmonics()` solves this with least squares.  For perfect uniform
integer-period sampling it gives the same answer as reading DFT bins.  For the
actual calibration case, where the accelerometer samples are merely close to
uniform and the trimmed window may not span an exact integer number of
electrical cycles, least squares is the cleaner estimator.

The default harmonic set is `{2, 4}` because those are the dominant components
seen in production phase-stepping work and in stepper periodic force errors:
half-electrical-period and full-step/quarter-period effects.

---

## 4. From Acceleration To Phase Correction

For one fitted acceleration harmonic:

$$
a_n(\theta) = A_n\cos(n\theta + p_n)
$$

with $\theta=\omega_e t$, double integration gives the corresponding position
ripple:

$$
x_n(\theta) =
-\frac{A_n}{(n\omega_e)^2}\cos(n\theta+p_n)
$$

Let $\lambda_e$ be axis travel per electrical period:

$$
\lambda_e = 4 \cdot \text{full-step distance}
$$

Converting a position ripple to electrical radians:

$$
\Delta\theta_x = \frac{2\pi x}{\lambda_e}
$$

The compensating phase correction should oppose the measured position ripple:

$$
\delta_n(\theta) =
-\Delta\theta_x =
\frac{A_n}{(n\omega_e)^2}
\frac{2\pi}{\lambda_e}
\cos(n\theta+p_n)
$$

The code stores corrections in sine convention:

$$
\delta_n(\theta) = b_n\sin(n\theta + q_n)
$$

so:

$$
b_n =
\frac{A_n}{(n\omega_e)^2}
\frac{2\pi}{\lambda_e},
\qquad
q_n = p_n + \frac{\pi}{2}
$$

The correction is measured independently for forward and reverse motion,
because friction and belt/load asymmetry can change the observed harmonic
phase.

---

## 5. Objective Function

The real objective is not "find a pretty Fourier series."  It is:

$$
\min_{\delta}
J(\delta)
$$

where a practical v1 objective is weighted harmonic acceleration energy after
applying the correction:

$$
J(\delta) =
\sum_{n\in H} w_n |A_n(\delta)|^2
$$

The current implementation uses the closed-form acceleration-to-position
conversion above as a first candidate, applies it, remeasures, and saves the
result only if measured vibration improves by the configured threshold.

That validation step matters.  The closed-form conversion assumes:

- small angular correction,
- mostly tangential force error,
- constant speed during the measured window,
- linear mechanical response around the calibration speed,
- accelerometer axis aligned well enough with the motion axis.

Those assumptions are useful, but not sacred.

A future gradient refinement pass should treat the closed-form coefficient set
as the initial point and then perturb each coefficient while remeasuring:

$$
\frac{\partial J}{\partial a_i}
\approx
\frac{J(a_i+\epsilon)-J(a_i-\epsilon)}{2\epsilon}
$$

Then update:

$$
\mathbf{a}_{k+1} = \mathbf{a}_k - \eta\nabla J
$$

or use a small coordinate-search variant that is more tolerant of measurement
noise.  That is the right place to capture motor, belt, frame, and driver
nonlinearities that the first-order model misses.

---

## 6. Runtime LUT

After calibration, the host builds a 512-entry default LUT:

$$
\theta_i = \frac{2\pi i}{512}
$$

$$
\delta_i = \sum_{n\in H} a_n\sin(n\theta_i+\phi_n)
$$

$$
cur_a(i) = \mathrm{round}(A\cos(\theta_i+\delta_i))
$$

$$
cur_b(i) = \mathrm{round}(A\sin(\theta_i+\delta_i))
$$

The MCU runtime indexes this LUT from the stepper position:

$$
\text{electrical pulses} = 4\cdot\text{microsteps}
$$

$$
\text{phase} = (\text{phase offset} \pm \text{stepper position})
\bmod \text{electrical pulses}
$$

and writes the corresponding `(cur_a, cur_b)` pair to the TMC2240
`DIRECT_MODE` register at the configured update rate.

The MCU writes SPI from task context, not from the step ISR.  The timer only
marks work pending.  `MOTOR_PHASE_BENCH` measures whether the target MCU/SPI
path can sustain the configured update rate before runtime correction is
allowed.

---

## 7. Practical Limits

- TMC2240 `DIRECT_MODE` is required; UART TMC2208/2209-style drivers cannot
  use this runtime path.
- The v1 LUT is phase-only and constant-magnitude.
- Too coarse an update rate or LUT can create quantization sidebands.  This is
  one reason the runtime uses a 512-entry LUT and a high update rate.
- The calibration is speed-sensitive.  The stored coefficients are averaged
  across configured calibration speeds, but a production-quality version should
  eventually model speed dependence.
- Any runtime fault disables the correction and requires re-homing before
  printing.

---

## 8. References

1. Trinamic TMC2240 datasheet, section "Direct Mode" — `DIRECT_MODE` register
   layout and `GCONF.direct_mode`.
2. Prusa Research, `Prusa-Firmware-Buddy` phase-stepping implementation —
   production example of accelerometer-calibrated multi-harmonic current
   correction.  See `research/prusa-phase-stepping-analysis.md`.
3. S.M. Kay, *Fundamentals of Statistical Signal Processing: Estimation
   Theory*, Prentice Hall, 1993 — sinusoidal parameter estimation.
4. P.C. Krause et al., *Analysis of Electric Machinery and Drive Systems* —
   real-domain current vector and torque modeling background.
