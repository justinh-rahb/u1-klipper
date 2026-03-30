# kinematics — Coord and API Signature Reversion

## Tier
Adapt

## Fork Change Summary
All 11 non-extruder kinematics files (`cartesian.py`, `corexy.py`, `delta.py`,
`corexz.py`, `polar.py`, `rotary_delta.py`, `winch.py`, `hybrid_corexy.py`,
`hybrid_corexz.py`, `deltesian.py`, `none.py`) differ from upstream due to
accumulated API snapshot reversions. The primary divergences are:

1. **`Coord` namedtuple vs upstream `Coord` class**: Upstream changed `Coord`
   from a `namedtuple` to a custom tuple subclass in `klippy/gcode.py`. All
   kinematics files that construct or decompose `Coord` objects are affected.
2. **`_motor_off()` signature changes**: Method signatures across kinematics
   differ between fork and upstream.
3. **Homing index handling**: `PrinterRail` homing index parameter differences.
4. **Minor method renames/removals**: e.g. `ToolHead.set_commanded_position()`
   vs `ToolHead.set_position()` in some files.

`kinematics/extruder.py` (item E1 — Tier 4 Keep) is excluded from this
migration because it has significant U1-specific additions.
`kinematics/idex_modes.py` (item E2 — Tier 3 Layer) is separate.

## Upstream Solution
Upstream Klipper `HEAD` (`2f05309d`) provides all 11 kinematics files with the
current `Coord` class, `_motor_off()` signatures, and `PrinterRail` API.

The `Coord` class change is in `klippy/gcode.py`:
```python
class Coord(tuple):
    # Upstream custom tuple subclass
    ...
```
All kinematics files create `Coord` objects via positional constructor calls
that work with both the old namedtuple and the new class, so this is largely
transparent. The main friction is any code that accesses `.x`, `.y`, `.z`, `.e`
attributes — these are present in both the namedtuple and the upstream subclass.

## Migration Path

This is a systematic, low-risk migration best done in one pass.

1. **For each of the 11 kinematics files**: diff the fork's version against
   upstream and apply only the API-reversion changes (Coord, _motor_off,
   homing index). Do not carry over any U1-specific additions if any exist —
   these files are documented as pure snapshot regressions.
2. **Apply changes in alphabetical order** to simplify review.
3. **Verify `gcode.py` Coord compatibility**: The fork's `gcode.py` (item B4)
   retains the `Coord` class definition. Confirm it is compatible with upstream's
   Coord usage pattern. If the fork's Coord class differs, align it.
4. **Testing checkpoints:**
   - `G28` all axes (homing): confirms `_motor_off`, homing index, and Coord
     construction all work correctly
   - `G0 X100 Y100 F3000`: basic XY motion
   - `G0 Z10`: Z motion
   - For delta/polar/rotary_delta: run a test move to confirm inverse kinematics
     produce correct step counts
5. **`kinematics/none.py`**: trivial; test by configuring a printer with no kinematics.

### Config implications
None — kinematics are selected by `[printer] kinematics: corexy` etc.
No config key changes required.

### klipper-router / Extended Firmware overlay implications
None.

## Risk
**Low-Medium.** Each file is a self-contained kinematics implementation.
The changes are mechanical (signature updates, Coord class) rather than
algorithmic. Risk is primarily human error when applying 11 simultaneous
file changes. Recommend applying and testing one file at a time, starting
with `corexy.py` (the U1's actual kinematics).
