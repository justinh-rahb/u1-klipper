# setup.py

## Summary
`setup.py` is a standard Python `setuptools` build script placed inside `klippy/extras/` to compile the `flow_calculator.pyx` Cython extension that is required by `flow_calibrator.py`. It calls `cythonize("flow_calculator.pyx")` and registers the resulting C extension with setuptools. This file is not a Klipper extra and has no `load_config` entry point; it exists solely to support the `python setup.py build_ext --inplace` workflow needed to build the `flow_calculator` shared library before Klipper can import `flow_calibrator`.

## Changed From Upstream
| Upstream Behaviour | Fork Behaviour | Likely Reason |
|---|---|---|
| Not present | New file: `setuptools`/`Cython` build script for the `flow_calculator` C extension | The flow calibration algorithm is performance-sensitive and implemented in Cython; this file provides the standard build mechanism |

## Additions

### Build Configuration
- **`cythonize("flow_calculator.pyx")`** — Compiles `flow_calculator.pyx` to a C extension.
- `include_dirs=[]` — No NumPy headers included by default (NumPy include path is commented out with a note that it can be added for local testing).
- `zip_safe=False`

### No Classes, G-code Commands, or Config Options
This file is purely a build artifact; it defines no Klipper objects.

## Removals / Overrides
- N/A (new file)

## Risks / Compatibility Notes
- Requires `Cython` and a C compiler in the build environment; the standard Klipper deployment process does not include a Cython build step.
- If `flow_calculator.pyx` is not compiled before Klipper starts, `flow_calibrator.py` will fail to import with `ModuleNotFoundError: No module named 'flow_calculator'`.
- The `setup.py` is placed inside `klippy/extras/` rather than the repository root, making `python setup.py build_ext --inplace` the expected invocation from that directory.
- The file is empty of any `install_requires` or version metadata, making it unsuitable as a distributable package; it is purely for in-place builds.

## Raw Diff
<details>
<summary>View Diff</summary>

```diff
+from setuptools import setup
+from Cython.Build import cythonize
+
+# for local test
+# import numpy as np
+# include_dirs=[np.get_include()]
+include_dirs=[]
+
+setup(
+    ext_modules=cythonize("flow_calculator.pyx"),
+    include_dirs=include_dirs,
+    zip_safe=False,
+)
```
</details>
