# kinematics/idex_modes.py

## Summary
`idex_modes.py` implements the IDEX (Independent Dual EXtruder) carriage mode management — PRIMARY, COPY, and MIRROR motion modes — used by dual-carriage 3D printers. In the Snapmaker U1 fork this file has ~473 diff lines relative to upstream and represents a **deliberate API freeze at an older, simpler interface**: the fork manages exactly two carriages on a single axis, while upstream has been refactored into a generalized multi-axis / multi-carriage architecture. The fork removes the `INACTIVE` mode, simplifies the constructor to take two explicit rails and one axis, removes the named-carriage dict from status output, and strips out the `collections` and `logging` imports that the upstream redesign required.

## Changed From Upstream

| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Copyright year: 2023–2025 | Copyright year: 2023 | Fork branched before upstream's multi-axis redesign |
| `import collections, logging, math` | `import math` only | `collections`/`logging` only needed by upstream's complex stepper setup |
| `VALID_MODES = [INACTIVE, PRIMARY, COPY, MIRROR]` | `VALID_MODES = [PRIMARY, COPY, MIRROR]` | `INACTIVE` removed from user-selectable modes; however `INACTIVE = 'INACTIVE'` is still defined and used as an internal `DualCarriagesRail.mode` state (lines 155, 222, 241, 259) — carriages transition through `INACTIVE` internally when parked |
| `DualCarriages.__init__(printer, primary_rails, dual_rails, axes, safe_dist)` | `DualCarriages.__init__(dc_config, rail_0, rail_1, axis)` | Fork's simpler two-rail, single-axis model |
| `_init_steppers` method with complex multi-rail kinematics setup | Method removed; fork uses simpler stepper registration | Not needed for single-axis dual-carriage |
| `get_axes()` returns list of managed axes | Removed; replaced by `get_rails()` returning a 2-tuple | Single-axis assumption makes `get_axes()` unnecessary |
| `get_primary_rail(axis)` takes an axis argument | `get_primary_rail()` takes no argument | Only one axis is managed |
| `get_dc_rail_wrapper(rail)` | Removed | Not needed in simplified architecture |
| `get_transform(axis)` | Removed | Transform concept not used |
| `is_active(dc_rail)` | Removed | Mode state tracked differently |
| `toggle_active_dc_rail(dc_rail)` takes a `dc_rail` object | Takes an integer index (0 or 1) | Simpler index-based API |
| `home(homing_state, axis)` takes an axis argument | `home(homing_state)` — no axis arg | Always homes the single managed axis |
| `get_status()` returns dict with named carriages sub-dict | Returns simpler dict with `carriage_0` / `carriage_1` keys at top level | Upstream named-carriage structure not implemented |
| `get_kin_range(axis)` | `get_kin_range(mode)` — takes mode instead of axis | Range depends on mode, not axis, in single-axis model |
| `DualCarriagesRail.__init__` with complex multi-rail params | Simpler `DualCarriagesRail.__init__(rail, axis, active)` | Matches the two-rail, single-axis model |

## Additions

- `get_rails()` — returns a 2-tuple of `DualCarriagesRail` objects (replacement for `get_axes()`).
- Integer-index API for `toggle_active_dc_rail(index)`.

## Removals / Overrides

- `INACTIVE` mode removed from `VALID_MODES` (no longer user-selectable). Note: `INACTIVE = 'INACTIVE'` is still **defined** at line 10 and used internally for `DualCarriagesRail.mode` state — it is not exposed as a user-configurable mode but carriages do enter `INACTIVE` state when parked.
- `_init_steppers` method removed.
- `get_axes()` removed.
- `get_primary_rail(axis)` replaced by `get_primary_rail()`.
- `get_dc_rail_wrapper()`, `get_transform()`, `is_active()` removed.
- `home(homing_state, axis)` `axis` parameter removed.
- Named carriages dict removed from `get_status()` output.
- `get_kin_range(axis)` parameter changed to `mode`.
- `collections` and `logging` imports removed.

## Risks / Compatibility Notes

- This module is **API-incompatible** with current upstream `idex_modes.py`. Any kinematics file (`cartesian.py`, `hybrid_corexy.py`, etc.) that calls `get_axes()`, `get_primary_rail(axis)`, `home(state, axis)`, or passes an `INACTIVE` mode will need to be adapted — and indeed, the fork's versions of those kinematics files have been updated accordingly.
- The removal of `INACTIVE` from `VALID_MODES` means carriages cannot be set to `INACTIVE` through the public mode API. However, `INACTIVE` remains defined and is used as an internal carriage state (e.g. a non-primary parked carriage has `mode == INACTIVE`). If upstream adds features that depend on `INACTIVE` as a public mode, they cannot be merged without re-adding it to `VALID_MODES`.
- `get_status()` output format differs from upstream; any macros or host software that parses the named carriages dict will break if run against this fork.
- Rebasing onto upstream's multi-axis redesign would require a full rewrite of this module.

## Raw Diff

<details>
<summary>View Diff</summary>

```diff
4c4
< # Copyright (C) 2023-2025  Dmitry Butyugin <dmbutyugin@google.com>
---
> # Copyright (C) 2023  Dmitry Butyugin <dmbutyugin@google.com>
7c7
< import collections, logging, math
---
> import math
16,43c16,20
< INACTIVE = 'INACTIVE'
< PRIMARY = 'PRIMARY'
< COPY = 'COPY'
< MIRROR = 'MIRROR'
<
< class DualCarriagesRail:
<     VALID_MODES = [INACTIVE, PRIMARY, COPY, MIRROR]
<     def __init__(self, printer, primary_rails, dual_rails, axes, safe_dist):
<         self._printer = printer
<         self._axes = axes
<         self._safe_dist = safe_dist
<         self._primary_rails = primary_rails
<         self._dual_rails = dual_rails
<         self._named_carriages = collections.OrderedDict()
<         ...
<     def _init_steppers(self):
<         # Complex per-axis stepper kinematics setup
<         ...
<     def get_axes(self):
<         return list(self._axes)
<     def get_primary_rail(self, axis):
<         ...
<     def get_dc_rail_wrapper(self, rail):
<         ...
<     def get_transform(self, axis):
<         ...
<     def is_active(self, dc_rail):
<         ...
<     def toggle_active_dc_rail(self, dc_rail):
<         ...
<     def home(self, homing_state, axis):
<         ...
<     def get_kin_range(self, axis):
<         ...
<     def get_status(self):
<         return {
<             'mode': self._mode,
<             'active_carriage': ...,
<             'carriages': self._named_carriages,
<         }
---
> PRIMARY = 'PRIMARY'
> COPY = 'COPY'
> MIRROR = 'MIRROR'
>
> class DualCarriagesRail:
>     VALID_MODES = [PRIMARY, COPY, MIRROR]
>     def __init__(self, dc_config, rail_0, rail_1, axis):
>         self._rail_0 = rail_0
>         self._rail_1 = rail_1
>         self._axis = axis
>         ...
>     def get_rails(self):
>         return (self._rail_0, self._rail_1)
>     def get_primary_rail(self):
>         ...
>     def toggle_active_dc_rail(self, index):
>         ...
>     def home(self, homing_state):
>         ...
>     def get_kin_range(self, mode):
>         ...
>     def get_status(self):
>         return {
>             'mode': self._mode,
>             'carriage_0': ...,
>             'carriage_1': ...,
>         }
```

</details>
