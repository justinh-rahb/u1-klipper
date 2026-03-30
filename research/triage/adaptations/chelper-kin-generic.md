# chelper/kin_generic — Restore Upstream Generic Kinematics

## Tier
Drop

## Fork Change Summary
The fork removed `klippy/chelper/kin_generic.c` from the source file list in
`klippy/chelper/__init__.py`. This file implements generic/fallback stepper
kinematics in the C helper layer (`c_helper.so`). The fork's `chelper/__init__.py`
`SOURCE_FILES` list does not include `'kin_generic.c'`.

The motivation was purely passive: `kin_generic.c` was added to upstream Klipper
after the fork's divergence point (mid-2024). Because the fork never received
the upstream update, the file is simply absent rather than deliberately removed.

## Upstream Solution
Upstream Klipper `HEAD` (`2f05309d`, file `klippy/chelper/__init__.py`) includes
`kin_generic.c` in `SOURCE_FILES`:

```python
SOURCE_FILES = [
    ...
    'kin_extruder.c', 'kin_shaper.c', 'kin_idex.c', 'kin_generic.c'
]
```

The file `klippy/chelper/kin_generic.c` is present in upstream and provides
generic stepper kinematics that allow external Klipper plugins to define custom
kinematic systems without modifying core files.

Upstream reference: `klippy/chelper/kin_generic.c` at commit `2f05309d`.

## Migration Path

1. **Copy `kin_generic.c` from upstream** into `klippy/chelper/kin_generic.c` in the fork.
2. **Update `klippy/chelper/__init__.py`** `SOURCE_FILES` to add `'kin_generic.c'` at the end of the kinematics list:
   ```python
   'kin_extruder.c', 'kin_shaper.c', 'kin_idex.c', 'kin_generic.c'
   ```
3. **Update `klippy/chelper/Makefile`** (the fork-added cross-compile Makefile) to add `kin_generic.c` to its source list so the AArch64 cross-compiled `c_helper.so` also includes it.
4. **Rebuild `c_helper.so`** on both x86 (dev) and AArch64 (U1 host) to verify the new file compiles cleanly.
5. **Testing checkpoint:** No functional change is expected — `kin_generic.c` provides an interface used only by plugins that declare custom kinematics. Confirm that existing U1 motion tests pass.

### Config implications
None. No U1 config sections reference `[generic_kinematics]` so this is additive.

### klipper-router / Extended Firmware overlay implications
The AArch64 cross-compiled `c_helper.so` distributed with the U1 Extended
Firmware overlay must be rebuilt after this change. The Makefile change in step 3
ensures this is captured.

## Risk
**Low.** `kin_generic.c` is a passive addition: it registers an interface but
does nothing unless a plugin explicitly references it. No existing U1 config or
module uses generic kinematics. The only risk is a compile error if the file has
upstream API dependencies not present in the fork's chelper headers — inspect
for any `#include` of `steppersync.h` (absent in fork). Current upstream
`kin_generic.c` does not include `steppersync.h`, so this should compile cleanly
against the fork's older chelper API.
