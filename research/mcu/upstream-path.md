# AT32 Upstream Contributability Assessment

## Summary

This fork adds AT32F403A and AT32F415 support to Klipper via separate HAL
files, explicit Kconfig entries, and Makefile additions. An existing upstream
PR ([Klipper3d/klipper#6626](https://github.com/Klipper3d/klipper/pull/6626))
covers AT32F415/F413 with a lighter, inline approach. This document evaluates
what can go upstream, what must stay fork-only, and proposes a concrete
contribution plan.

---

## Existing Upstream Activity: PR #6626

| Field | Detail |
|-------|--------|
| **PR** | [Klipper3d/klipper#6626](https://github.com/Klipper3d/klipper/pull/6626) — "add support for at32f415 and at32f413" |
| **Author** | vcore85 |
| **Status** | Open since 2024-06-23, labeled "reviewer needed", 3 comments |
| **Chips** | AT32F415, AT32F413 at 120 MHz (not 144 MHz) |
| **Approach** | Modifies `src/stm32/stm32f1.c` directly; runtime AT32 detection via reserved register bits |
| **Key technique** | Sets `RCC_CFGR_PLLRANGE` bit (reserved on STM32F103) for AT32F413 when PLL > 72 MHz; AT32F415 does not need this bit |
| **USB** | USB FS and CAN support; uses `RCC_CFGR_USBPRE_DIV2_5` at bit 23 (reserved on STM32F103) |
| **I2C** | Timing adjustments for 120 MHz clock |
| **DCO** | Signed-off-by present |
| **No Kconfig entries** | Detection is runtime, not compile-time |

## What This Fork Has That PR #6626 Does Not

| Capability | This Fork | PR #6626 |
|------------|-----------|----------|
| AT32F403A support | ✅ | ❌ (F415/F413 only) |
| 240 MHz operation | ✅ | ❌ (120 MHz max) |
| ACC (Auto Clock Calibration) for crystal-free USB | ✅ | ❌ |
| Separate HAL library inclusion | ✅ | ❌ (STM32 CMSIS only) |
| USB OTG for AT32F415 | ✅ | ❌ (USB FS on F413 only) |
| Novel hardware modules (`inductance_coil`, `power_loss_check`) | ✅ (U1-specific) | N/A |

---

## Tiered Assessment of Fork Files

### Tier 1 — Directly Contributable (Minimal Changes)

These files are clean, well-structured, and follow Klipper conventions closely
enough to submit with minor edits.

| File / Area | What It Does | Required Changes for Upstream |
|-------------|-------------|-------------------------------|
| `src/stm32/Kconfig` — AT32 entries | Processor choice, `CLOCK_FREQ`, `FLASH_SIZE`, `RAM_SIZE` | Reconcile with PR #6626. This fork's explicit Kconfig approach is more standard for Klipper than #6626's runtime detection. |
| `src/stm32/Makefile` — AT32 additions | Source file lists, compiler flags (`-DAT32F403Axx`, `-DAT32F415xx`) | Straightforward; follows existing Makefile patterns. |
| `src/stm32/at32f415rc.c` / `at32f415rc.h` | Clock setup for AT32F415 | Remove debug UART code. Otherwise clean and minimal. |

### Tier 2 — Contributable with Moderate Work

These files carry unique value but need cleanup or documentation before
submission.

| File / Area | What It Does | Required Changes for Upstream |
|-------------|-------------|-------------------------------|
| `src/stm32/at32f403a.c` / `at32f403a.h` | Clock setup with ACC (Auto Clock Calibration) | Remove debug UART output, `LOG` macros. ACC implementation is novel and valuable — no other Klipper MCU uses USB SOF clock calibration. |
| `src/stm32/usbotg.c` — AT32F415 conditionals | Routes AT32F415 to USB OTG path | Clean, follows existing `#if CONFIG_MACH_*` conditional pattern. |
| `src/stm32/can.c` — AT32F403A conditionals | CAN2 support on AT32F403A | Well-isolated; necessary because AT32F403A maps CAN differently. |
| `src/stm32/spi.c` — AT32F403A conditionals | SPI pin differences | Pin mapping differences need clear documentation in commit message. |

### Tier 3 — U1-Specific, Not Suitable for Upstream

These files are product-specific Snapmaker U1 features. They should remain in
this fork only.

| File / Area | Reason Not Upstream |
|-------------|---------------------|
| `klippy/extras/inductance_coil.c` | Product-specific sensor hardware |
| `klippy/extras/power_loss_check.c` | Product-specific power-loss recovery |
| `src/stm32/stepper.c` modifications (`move_line`, `print_act` tracking) | Tightly coupled to `power_loss_check` |
| `USB_PRODUCT_SUFFIX` in `Kconfig` / `usb_cdc.c` | Snapmaker device identification string |
| `src/stm32/serial.c` USART5 PB8/PB9 option | Technically clean but extremely niche; low value for upstream |

---

## ACC USB SOF Clock — Upstream Precedent Analysis

- **No exact precedent** in upstream Klipper. No supported MCU uses USB SOF
  for clock calibration today.
- STM32L0/F0 have CRS (Clock Recovery System), which is conceptually similar,
  but Klipper does not use it.
- The AT32 ACC approach is valuable because it enables **crystal-free USB
  operation**, reducing BOM cost.
- Klipper currently assumes a stable external crystal for USB MCUs.
- If `HEXT→PLL` provides the system clock (crystal-based), ACC is only
  relevant for USB timing, not step timing — this limits the blast radius.
- **Upstream argument:** ACC is self-contained in `at32f403a.c`, does not
  affect step timing, and can be documented as AT32-specific behavior.

---

## Minimum Viable Upstream Contribution

The smallest useful PR that adds AT32 support to upstream Klipper:

### Files to Include

1. **`src/stm32/Kconfig`** — New `config MACH_AT32F415` and
   `config MACH_AT32F403A` entries with explicit `CLOCK_FREQ`, `FLASH_SIZE`,
   `RAM_SIZE` values.

2. **`src/stm32/at32f415rc.c`** / **`at32f415rc.h`** — Clock setup, debug
   UART removed.

3. **`src/stm32/at32f403a.c`** / **`at32f403a.h`** — Clock setup with ACC,
   debug UART and `LOG` macros removed.

4. **`lib/at32f415/` and `lib/at32f403a/`** — HAL library subsets trimmed to
   only the modules Klipper actually uses (~10 files per chip):
   - `at32f4xx_crm.c/h` (clock/reset)
   - `at32f4xx_gpio.c/h`
   - `at32f4xx_usart.c/h`
   - `at32f4xx_spi.c/h`
   - `at32f4xx_can.c/h`
   - `at32f4xx_usb.c/h`
   - `at32f4xx_flash.c/h`
   - `at32f4xx_misc.c/h` (NVIC)
   - System/startup files

5. **`src/stm32/Makefile`** — Source file lists and compiler flags for AT32
   targets.

6. **`src/stm32/stm32f1.c`** — AT32 clock setup conditionals (call into
   `at32f403a.c` / `at32f415rc.c` instead of inline STM32 clock init).

7. **`src/stm32/usbfs.c`** / **`src/stm32/usbotg.c`** — AT32 USB routing
   conditionals.

8. **`src/stm32/can.c`** — AT32F403A CAN2 conditionals.

### Files to Exclude

- `inductance_coil.c`, `power_loss_check.c` — U1-specific
- `stepper.c` modifications — power-loss integration
- `USB_PRODUCT_SUFFIX` — Snapmaker branding
- `serial.c` USART5 PB8/PB9 — too niche

---

## Required Changes Before Submission

### 1. Code Cleanup

| Change | Files Affected | Effort |
|--------|---------------|--------|
| Remove debug UART initialization and output | `at32f403a.c`, `at32f415rc.c` | Small — delete `uart_init()` calls and related code |
| Remove `LOG` macros | `at32f403a.c` | Small — replace with nothing; Klipper MCU firmware does not log to UART |
| Trim HAL libraries to used modules only | `lib/at32f415/`, `lib/at32f403a/` | Medium — identify which `.c`/`.h` files are actually `#include`d or called |

### 2. Architecture Decision: Separate Files vs. Inline

| Approach | This Fork | PR #6626 |
|----------|-----------|----------|
| Strategy | Explicit Kconfig entries + separate `.c`/`.h` files per AT32 variant | Runtime detection via reserved register bits, all in `stm32f1.c` |
| Pro | Cleaner, more maintainable, follows Klipper's pattern for STM32F0/F4/H7/G0 | Smaller diff, no new files |
| Con | More files to review | Fragile — relies on reserved bits staying reserved |

**Recommendation:** Use this fork's approach (explicit Kconfig + separate
files). Upstream Klipper uses separate files for each STM32 family
(`stm32f0.c`, `stm32f1.c`, `stm32f4.c`, `stm32h7.c`, `stm32g0.c`). Adding
`at32f403a.c` and `at32f415rc.c` follows established convention. PR #6626's
inline detection is clever but non-standard for the codebase.

### 3. License Review: Artery BSP

The Artery BSP license states files are:

> "authorized for use in conjunction with Artery microcontrollers"

This is compatible with Klipper's use case (firmware runs on AT32 chips), but
the interaction with GPLv3 needs legal review:

- **Question:** Can GPLv3-licensed Klipper link against Artery's BSP headers
  and source files?
- **Precedent:** Klipper already includes STMicroelectronics HAL files under
  BSD-3-Clause in `lib/stm32f1/`. Artery's license is more restrictive.
- **Action required:** Contact Artery Technology to clarify redistribution
  terms, or rewrite the minimal register definitions from the datasheet
  (registers are facts, not copyrightable expression).
- **Alternative:** Use only CMSIS-style register definitions (addresses and
  bit masks) which are functional facts derivable from the datasheet, avoiding
  the HAL library entirely. PR #6626 takes this approach.

### 4. Hardware Testing

Upstream Klipper requires testing reports before merging MCU support.

| Chip | Test Hardware | Availability |
|------|--------------|--------------|
| AT32F403A | Snapmaker U1 main board, or standalone AT32F403A dev board (Artery AT-START-F403A) | U1 community can provide testing; dev boards ~$15 |
| AT32F415 | Used in several budget 3D printers (some Creality boards), Artery AT-START-F415 dev board | More widely available than F403A |

**Testing protocol:**
- Compile test (can be automated in CI — add AT32 to Klipper's build matrix)
- Flash and boot on real hardware
- Verify USB CDC communication (`ls /dev/serial/by-id/`)
- Run basic print moves (stepper timing validation)
- CAN bus communication test (if applicable)
- Thermal stability at target clock speed (240 MHz for F403A, 144 MHz for
  F415)

### 5. CI/CD Integration

AT32 builds can be added to Klipper's compile-test matrix without hardware:

```yaml
# Example addition to .github/workflows/ci.yaml
- name: Build AT32F403A
  run: |
    cp ${PWD}/test/configs/at32f403a.config .config
    make olddefconfig
    make
- name: Build AT32F415
  run: |
    cp ${PWD}/test/configs/at32f415.config .config
    make olddefconfig
    make
```

---

## Coordination Strategy with PR #6626

The most pragmatic path is to **coordinate with PR #6626's author (vcore85)**
rather than submit a competing PR.

### Proposed Combined Approach

| Aspect | Source | Rationale |
|--------|--------|-----------|
| Kconfig entries (explicit chip selection) | This fork | Standard Klipper pattern; cleaner than runtime detection |
| AT32F415 support | Both (merge) | PR #6626 has working F415 support; this fork adds USB OTG |
| AT32F413 support | PR #6626 | This fork does not cover F413 |
| AT32F403A support | This fork | PR #6626 does not cover F403A |
| 120 MHz clock configuration | PR #6626 | Proven, simpler |
| 240 MHz clock configuration | This fork | Only needed for AT32F403A |
| ACC (crystal-free USB) | This fork | Novel, unique to AT32F403A |
| HAL library approach | Negotiate | PR #6626 uses CMSIS only (avoids license issues); this fork uses Artery HAL (richer but license-encumbered) |

### Outreach Steps

1. **Comment on PR #6626** with a link to this fork's AT32 work, noting:
   - This fork adds AT32F403A (not covered by #6626)
   - This fork uses explicit Kconfig entries (different architectural choice)
   - Offer to collaborate on a combined PR
2. **Propose the combined Kconfig+separate-file approach** as the merge
   strategy
3. **Offer U1 community hardware testing** for AT32F403A validation
4. **Resolve the HAL license question** before any submission — if Artery's
   license is incompatible with GPLv3, adopt PR #6626's CMSIS-only approach
   for all AT32 variants

---

## Concrete Action Items

### Phase 1: Preparation (Before Any PR)

- [ ] Remove debug UART code from `at32f403a.c` and `at32f415rc.c`
- [ ] Remove `LOG` macros from `at32f403a.c`
- [ ] Audit HAL library files: list exactly which `.c`/`.h` files are
      referenced by Klipper's AT32 code paths
- [ ] Trim HAL libraries to the minimum set
- [ ] Verify Artery BSP license compatibility with GPLv3 (contact Artery or
      rewrite as CMSIS-only register definitions)
- [ ] Create `test/configs/at32f403a.config` and `test/configs/at32f415.config`
      for CI compile tests

### Phase 2: Coordination

- [ ] Comment on [PR #6626](https://github.com/Klipper3d/klipper/pull/6626)
      proposing collaboration
- [ ] Agree on architectural approach (Kconfig+separate files vs. inline
      detection)
- [ ] Agree on HAL strategy (Artery HAL subset vs. CMSIS-only)

### Phase 3: Submission

- [ ] Prepare a single PR covering AT32F415, AT32F413, and AT32F403A
- [ ] Include `Signed-off-by` trailer (required by Klipper)
- [ ] Provide hardware testing reports for AT32F403A (U1 board) and AT32F415
- [ ] Add AT32 targets to compile-test CI matrix
- [ ] Respond to reviewer feedback (expect multiple review cycles — Klipper
      reviews are thorough)

### Phase 4: Post-Merge

- [ ] Maintain U1-specific features (`inductance_coil`, `power_loss_check`,
      `stepper.c` modifications) as a thin fork layer on top of upstream
- [ ] Rebase fork onto upstream after AT32 support merges
- [ ] Contribute bug fixes discovered via U1 community back to upstream

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Artery BSP license incompatible with GPLv3 | Medium | High — blocks HAL inclusion | Rewrite as CMSIS-only register definitions (PR #6626 proves this works) |
| Upstream maintainers prefer PR #6626's approach | Medium | Medium — requires rework | Engage early in PR #6626 discussion; be willing to adapt |
| No reviewer picks up the PR | High | High — Klipper has a review backlog | PR #6626 has been open since June 2024 with "reviewer needed" label; be persistent, provide excellent testing reports |
| 240 MHz clock stability concerns | Low | Medium — could block F403A | Document thermal testing results; 240 MHz is within AT32F403A's rated spec |
| ACC implementation rejected as too complex | Low | Low — ACC is optional | ACC can be a follow-up PR; initial PR can use crystal-only configuration |

---

## File-Level Diff Estimate

Approximate upstream PR size if submitting combined AT32 support:

| Category | Files | Lines Added | Lines Modified |
|----------|-------|-------------|----------------|
| Kconfig entries | 1 | ~60 | ~10 |
| Makefile additions | 1 | ~30 | ~5 |
| Clock setup (new files) | 4 | ~400 | 0 |
| USB conditionals | 2 | ~30 | ~10 |
| CAN conditionals | 1 | ~15 | ~5 |
| SPI conditionals | 1 | ~10 | ~5 |
| HAL library files | ~20 | ~3000 | 0 |
| Test configs | 2 | ~30 | 0 |
| **Total** | **~32** | **~3575** | **~35** |

The HAL library files dominate the line count. If the CMSIS-only approach is
adopted (eliminating the HAL), the total drops to ~600 lines added across ~12
files — a much more reviewable PR.
