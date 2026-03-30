# kinematics/ — Minor Changes (all files except extruder.py and idex_modes.py)

## Summary
A consistent set of small but cross-cutting changes has been applied to every kinematics file in the fork. The changes fall into four recurring themes: (1) a `toolhead.Coord` call-signature fix (positional args / splat instead of a list, plus explicit `e=0.`), (2) mandatory `register_step_generator` calls for each stepper so the toolhead scheduler knows about them, (3) replacement of `clear_homing_state` with per-axis `note_<axis>_not_homed` methods and a `_motor_off` event handler wired to `stepper_enable:motor_off`, and (4) use of integer axis indices everywhere instead of string names like `"xyz"`. Additionally, `corexy.py` gains an `ignore_check_move_limit` safety flag that the Snapmaker U1 uses during certain tool-change manoeuvres, and several files switch from `stepper.LookupRail` to `stepper.PrinterRail` and from `DualCarriages` direct construction to explicit `DualCarriagesRail` wrapper creation.

## Changed From Upstream

| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| `toolhead.Coord([x, y, z])` — passes a list | `toolhead.Coord(*[x,y,z], e=0.)` or `toolhead.Coord(x, y, z, 0.)` — positional args + explicit `e` | Upstream changed `Coord` constructor; fork backports the call-site fix |
| Steppers not explicitly registered with scheduler | `toolhead.register_step_generator(s.get_step_gen())` called for each stepper | Required by the fork's toolhead dispatcher |
| `clear_homing_state()` resets all axes | Per-axis `note_z_not_homed()`, `note_x_not_homed()`, `note_y_not_homed()` methods; `_motor_off` handler resets only what the kinematic owns | Finer-grained homing state tracking |
| `stepper_enable:motor_off` event not handled | Each kinematics registers `_motor_off` callback that resets limits/homed state | Ensures limits are invalidated on motor disable |
| Homing loops iterate over string `"xyz"` | Loops iterate over integer indices `(0, 1, 2)` | Matches new homing-state API |
| `set_position([0,0,0], "")` | `set_position([0,0,0], ())` | Empty tuple instead of empty string for "no homed axes" |
| `homing_axes == "xyz"` | `tuple(homing_axes) == (0, 1, 2)` | Integer-index homing axes API |
| `stepper.LookupRail(...)` | `stepper.PrinterRail(...)` (deltesian, hybrid_corexy, hybrid_corexz, polar, rotary_delta) | `LookupRail` removed/renamed in the fork's stepper layer |
| `DualCarriages(dc_config, rail_0, rail_1, axis)` constructed directly | Explicit `DualCarriagesRail` wrappers created first, then passed in (cartesian, hybrid_corexy, hybrid_corexz) | Required by the fork's simplified `idex_modes.py` API |
| `dc_module.get_primary_rail(axis).get_rail()` called with axis arg | `dc_module.get_primary_rail().get_rail()` — no axis arg | Matches `idex_modes.py` `get_primary_rail()` signature change |
| `dc_module.home(homing_state, axis)` | `dc_module.home(homing_state)` — no axis arg | Matches `idex_modes.py` `home()` signature change |
| `corexy`: no move-limit bypass | `ignore_check_move_limit` flag; `set_ignore_check_move_limit(enable)` method; `check_move`/`check_endstops` skip limits when flag is set | Needed during Snapmaker U1 tool-change to allow out-of-bounds park moves |
| `corexy`: generic error `"Must home axis first"` | `"Must home X axis first"` / `"Must home Y axis first"` / `"Must home Z axis first"` | Clearer error messages |

## Additions

### cartesian.py (61 lines diff)
- `DualCarriagesRail` wrapper objects created before `DualCarriages` construction.
- `toolhead.register_step_generator` calls for each stepper.
- `stepper_enable:motor_off` → `_motor_off` handler (resets position limits).
- `_motor_off` method.

### corexy.py (62 lines diff)
- `ignore_check_move_limit` instance flag (default `False`).
- `set_ignore_check_move_limit(enable)` method.
- `note_z_not_homed()`, `note_x_not_homed()`, `note_y_not_homed()` methods.
- `_motor_off` method; `stepper_enable:motor_off` event registration.
- `register_step_generator` calls.
- Per-axis error messages in `check_move`.

### corexz.py (26 lines diff)
- `register_step_generator` calls.
- `note_z_not_homed()` method.
- `_motor_off` method; `stepper_enable:motor_off` registration.

### delta.py (27 lines diff)
- `register_step_generator` calls.
- `_motor_off` method (resets `limit_xy2` and `need_home`); `stepper_enable:motor_off` registration.

### deltesian.py (36 lines diff)
- `register_step_generator` calls.
- `_motor_off` method; `stepper_enable:motor_off` registration.

### hybrid_corexy.py (57 lines diff)
- `DualCarriagesRail` wrappers before `DualCarriages` construction.
- `register_step_generator` calls.
- `note_z_not_homed()` method.
- `_motor_off` method; `stepper_enable:motor_off` registration.

### hybrid_corexz.py (57 lines diff)
- Identical additions to `hybrid_corexy.py`.

### none.py (7 lines diff)
- (No new methods added; changes are removals/fixes only.)

### polar.py (37 lines diff)
- `register_step_generator` calls.
- `note_z_not_homed()` method.
- `_motor_off` method; `stepper_enable:motor_off` registration.

### rotary_delta.py (39 lines diff)
- `register_step_generator` calls.
- `_motor_off` method; `stepper_enable:motor_off` registration.

### winch.py (14 lines diff)
- `register_step_generator` calls.

## Removals / Overrides

- `clear_homing_state()` removed from all kinematics files (replaced by `_motor_off` and per-axis `note_<axis>_not_homed` methods).
- `none.py`: `clear_homing_state` stub removed; `Coord` list form removed.
- `delta.py`, `rotary_delta.py`: `homing_axes == "xyz"` string comparison removed.

## Risks / Compatibility Notes

- The `ignore_check_move_limit` flag in `corexy.py` **disables XY and Z move-limit detection** when set. If it is left enabled accidentally (e.g., after a failed tool-change), subsequent moves will not be bounds-checked, which could cause crashes. The fork must ensure this flag is always cleared after the manoeuvre that requires it.
- Replacing `clear_homing_state` with per-axis `note_<axis>_not_homed` means that if any kinematics file still calls `clear_homing_state` after a merge it will raise `AttributeError` at runtime.
- The `stepper.LookupRail` → `stepper.PrinterRail` change is load-bearing; if upstream renames `PrinterRail` or changes its constructor the affected files (deltesian, hybrid_*, polar, rotary_delta) will break.
- `register_step_generator` calls are required by the fork's toolhead; omitting them for any stepper (e.g., after adding a new stepper) will cause silent scheduling issues.
- Integer homing-axis indices are incompatible with any upstream code that still passes string names; merging upstream homing changes requires careful review.
- All changes are self-consistent within the fork but represent a significant divergence from upstream in every kinematics file, making future rebases labour-intensive.

## Raw Diff

<details>
<summary>View Diff — cartesian.py (representative excerpt)</summary>

```diff
# cartesian.py
-        self.axes_min = toolhead.Coord([rail.get_range()[0] for rail in rails] + [0.])
-        self.axes_max = toolhead.Coord([rail.get_range()[1] for rail in rails] + [0.])
+        self.axes_min = toolhead.Coord(*[rail.get_range()[0] for rail in rails], e=0.)
+        self.axes_max = toolhead.Coord(*[rail.get_range()[1] for rail in rails], e=0.)

-        dc = idex_modes.DualCarriages(dc_config, rail, dc_rail, axis)
+        dc_rail_0 = idex_modes.DualCarriagesRail(dc_config, rail, axis, True)
+        dc_rail_1 = idex_modes.DualCarriagesRail(dc_config, dc_rail, axis, False)
+        dc = idex_modes.DualCarriages(dc_config, dc_rail_0, dc_rail_1, axis)

+        for s in self.get_steppers():
+            toolhead.register_step_generator(s.get_step_gen())

+        self.printer.register_event_handler("stepper_enable:motor_off",
+                                            self._motor_off)

-            pos = dc_module.get_primary_rail(axis).get_rail().get_homing_info()
+            pos = dc_module.get_primary_rail().get_rail().get_homing_info()

-        dc_module.home(homing_state, axis)
+        dc_module.home(homing_state)

+    def _motor_off(self, print_time):
+        self.limits = [(1.0, -1.0)] * 3
```

</details>

<details>
<summary>View Diff — corexy.py (representative excerpt)</summary>

```diff
# corexy.py
+        self.ignore_check_move_limit = False
+        self.printer.register_event_handler("stepper_enable:motor_off",
+                                            self._motor_off)

+    def set_ignore_check_move_limit(self, enable):
+        self.ignore_check_move_limit = enable

     def check_move(self, move):
+        if not self.ignore_check_move_limit:
             limits = self.limits
             xpos, ypos = move.end_pos[:2]
             if (xpos < limits[0][0] or xpos > limits[0][1]
                 or ypos < limits[1][0] or ypos > limits[1][1]):
-                self._check_endstops(move)
+                self._check_endstops(move)  # only when limit checking enabled

-                raise self.printer.command_error("Must home axis first")
+                raise self.printer.command_error("Must home X axis first")

+    def note_x_not_homed(self):
+        self.limits[0] = (1., -1.)
+    def note_y_not_homed(self):
+        self.limits[1] = (1., -1.)
+    def note_z_not_homed(self):
+        self.limits[2] = (1., -1.)
+    def _motor_off(self, print_time):
+        self.limits = [(1.0, -1.0)] * 3
```

</details>

<details>
<summary>View Diff — delta.py / rotary_delta.py (representative excerpt)</summary>

```diff
# delta.py
-        self.set_position([0., 0., 0.], "")
+        self.set_position([0., 0., 0.], ())

-        if homing_axes == "xyz":
+        if tuple(homing_axes) == (0, 1, 2):

-    def clear_homing_state(self, axes):
-        ...
+    def _motor_off(self, print_time):
+        self.limit_xy2 = -1.
+        self.need_home = True
```

</details>

<details>
<summary>View Diff — deltesian.py / polar.py / rotary_delta.py (LookupRail → PrinterRail)</summary>

```diff
-        self.rails = [stepper.LookupRail(config, 'stepper_x'),
-                      stepper.LookupRail(config, 'stepper_y')]
+        self.rails = [stepper.PrinterRail(config.getsection('stepper_x')),
+                      stepper.PrinterRail(config.getsection('stepper_y'))]
```

</details>

<details>
<summary>View Diff — none.py</summary>

```diff
-        self.axes_min = toolhead.Coord((0., 0., 0.))
-        self.axes_max = toolhead.Coord((0., 0., 0.))
+        self.axes_min = toolhead.Coord(0., 0., 0., 0.)
+        self.axes_max = toolhead.Coord(0., 0., 0., 0.)

-    def clear_homing_state(self, axes):
-        pass
```

</details>
