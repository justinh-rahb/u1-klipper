# chelper/steppersync — Migrate to Upstream syncemitter API

## Tier
Adapt

## Fork Change Summary
The fork's `klippy/chelper/__init__.py` uses the **classic** `steppersync` API:

```c
struct steppersync *steppersync_alloc(struct serialqueue *sq,
    struct stepcompress **sc_list, int sc_num, int move_num);
int steppersync_flush(struct steppersync *ss, uint64_t move_clock,
    uint64_t clear_history_clock);
```

This API is implemented inline in the fork's `stepcompress.c`. The fork does
not have `steppersync.c` or `steppersync.h`.

Upstream Klipper refactored `steppersync` into a separate `steppersync.c`/`steppersync.h`
pair with a `syncemitter`/`steppersyncmgr` architecture that decouples the
per-stepper step emitter from the global sync manager. The Python-side bindings
in `klippy/stepper.py` call the `syncemitter` API.

Because the fork's `stepper.py` and `toolhead.py` were also written against the
older API, this is a coupled migration: chelper, stepper.py, and toolhead.py
must be updated together (see also Adapt B3 — toolhead).

## Upstream Solution
Upstream Klipper `HEAD` (`2f05309d`) provides:
- `klippy/chelper/steppersync.c` — new `syncemitter`/`steppersyncmgr` implementation
- `klippy/chelper/steppersync.h` — public API header
- `klippy/chelper/__init__.py` `defs_steppersync` — `syncemitter_get_stepcompress`, `syncemitter_set_stepper_kinematics`, `syncemitter_queue_msg`, `steppersync_alloc_syncemitter`, `steppersync_setup_movequeue`, `steppersync_free`, `steppersync_flush`
- `klippy/stepper.py` — calls `syncemitter_*` functions

The benefit of the new API is better separation of step generation from
synchronisation, and support for upstream's `MotionQueuing` and `extra_axes`
architecture.

## Migration Path

This migration should be done as part of a combined chelper + stepper + toolhead
refactor. The recommended sequencing is:

1. **Copy `steppersync.c` and `steppersync.h`** from upstream into the fork's `klippy/chelper/`.
2. **Update `klippy/chelper/__init__.py`**:
   - Add `'steppersync.c'` to `SOURCE_FILES`.
   - Replace the old `defs_steppersync` with the upstream `syncemitter`/`steppersyncmgr` definitions.
3. **Update the fork-added `klippy/chelper/Makefile`** to include `steppersync.c` in the source list.
4. **Update `klippy/stepper.py`** to use the new `syncemitter_alloc`/`syncemitter_flush` calls instead of the classic `steppersync_alloc`/`steppersync_flush`. This requires updating all sites in `stepper.py` that create or flush a `steppersync` object.
   - **Note:** The fork's `stepper.py` also adds PLR `type`/`index` fields (item B6 — Tier 4 Keep). These additions must be preserved when migrating the `stepper.py` API.
5. **Update `klippy/toolhead.py`**: the toolhead creates the `steppersync` and manages flush timing. If the toolhead adaptation (B3) is done in parallel, coordinate this change. If done separately, bridge the old and new API temporarily.
6. **Rebuild and test** `c_helper.so` on AArch64.
7. **Testing checkpoints:**
   - Home all axes (`G28`) and confirm motion is correct.
   - Run a short print; verify no `steppersync` flush errors in the log.
   - Confirm PLR `type`/`index` fields in stepper MCU commands are preserved.

### Config implications
None.

### klipper-router / Extended Firmware overlay implications
The `c_helper.so` binary distributed with the Extended Firmware overlay must be
rebuilt after this change. The chelper `Makefile` needs updating to include
`steppersync.c`.

## Risk
**High.** This touches the lowest-level motion execution path. Incorrect
migration of the steppersync API will produce either incorrect step timing
(silent motion errors) or a crash at startup. The U1's PLR fields in `stepper.py`
(item B6) must be carried forward. Thorough motion testing at various speeds and
accelerations is required. Recommend running the upstream test suite
(`test/klippy/`) after migration.
