# klippy/chelper — C Helper Layer Changes

## Summary
The `chelper` directory contains the C extension library that Klipper compiles into `c_helper.so` for performance-critical path planning. The fork diverges from upstream in two key ways: it removes the newer `steppersync` refactor (reverting to the older `steppersync_alloc`/`flush` API) and drops `kin_generic.c`, while adding a standalone `Makefile` for cross-compilation targeting the U1's AArch64 host processor.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Uses `steppersync.c`/`steppersync.h` with `syncemitter`, `steppersyncmgr` API | Uses older `steppersync_alloc`/`steppersync_free`/`steppersync_flush` API inline in `stepcompress.c` | Fork is based on older Klipper; the steppersync refactor was not backported |
| Includes `kin_generic.c` (generic stepper kinematics) | No `kin_generic.c` | Generic kinematics module added to upstream after fork diverged |
| chelper compiled only via Python `__init__.py` build system | Fork-exclusive `Makefile` for cross-compilation with `CROSS_COMPILE=` override | Needed to produce `c_helper.so` for AArch64 U1 host without Python build env |
| `defs_steppersync` uses `syncemitter`/`steppersyncmgr` structs | Uses classic `steppersync_alloc(sq, sc_list, sc_num, move_num)` | API revert to match older `stepcompress.c` |
| `stepcompress_fill` takes `(sc, oid, max_error, ...)` | Takes `(sc, max_error, ...)` — no `oid` param | Signature regression from older code |
| `itersolve_get_gen_steps_count()` / window functions present | These functions absent | Upstream added performance monitoring; fork does not have them |

## Additions
- **`klippy/chelper/Makefile`** (fork-exclusive): Standalone GNU Makefile that compiles all chelper C sources directly. Key features:
  - `CROSS_COMPILE` variable to set AArch64 cross-compiler prefix
  - `PROJECT := Klippy chelper`, `TARGET := c_helper.so`
  - `V=1` verbose mode toggle
  - `clean` and `disclean` targets
  - Compiles exactly the same source list as `__init__.py`'s `SOURCE_FILES`

## Removals / Overrides
- `steppersync.c` and `steppersync.h` removed (upstream-only)
- `kin_generic.c` removed (upstream-only)
- `defs_steppersync` in `__init__.py` reverted to older API (no `syncemitter`, no `steppersyncmgr`)
- `check_build_c_library()` function differs — fork has simpler build path
- Most chelper `.c`/`.h` file differences are small downstream divergences from an earlier upstream snapshot (e.g. copyright dates, minor refactors that occurred after the fork point)

## Risks / Compatibility Notes
- Any plugin or klippy module using `steppersync` must use the old API — **incompatible with upstream `stepper.py`** which expects the new `steppersyncmgr` API
- The `Makefile` hard-codes the source file list; if new `.c` files are added to `__init__.py`, the `Makefile` must be updated manually
- Cross-compiled `c_helper.so` is AArch64 binary; cannot be used on x86 dev machines without recompiling

## Raw Diff
<details>
<summary>View Diff (chelper/__init__.py)</summary>

```diff
--- a/klippy/chelper/__init__.py
+++ b/klippy/chelper/__init__.py
@@ -17,16 +17,16 @@
 SOURCE_FILES = [
-    'pyhelper.c', 'serialqueue.c', 'stepcompress.c', 'steppersync.c',
-    'itersolve.c', 'trapq.c', 'pollreactor.c', 'msgblock.c', 'trdispatch.c',
+    'pyhelper.c', 'serialqueue.c', 'stepcompress.c', 'itersolve.c', 'trapq.c',
+    'pollreactor.c', 'msgblock.c', 'trdispatch.c',
     'kin_cartesian.c', 'kin_corexy.c', 'kin_corexz.c', 'kin_delta.c',
     'kin_deltesian.c', 'kin_polar.c', 'kin_rotary_delta.c', 'kin_winch.c',
-    'kin_extruder.c', 'kin_shaper.c', 'kin_idex.c', 'kin_generic.c'
+    'kin_extruder.c', 'kin_shaper.c', 'kin_idex.c',
 ]
 # defs_steppersync reverted from syncemitter/steppersyncmgr to classic API
-    struct syncemitter *steppersync_alloc_syncemitter(...)
-    int32_t steppersyncmgr_gen_steps(...)
+    struct steppersync *steppersync_alloc(struct serialqueue *sq,
+        struct stepcompress **sc_list, int sc_num, int move_num);
+    int steppersync_flush(struct steppersync *ss, uint64_t move_clock,
+        uint64_t clear_history_clock);
```
</details>
