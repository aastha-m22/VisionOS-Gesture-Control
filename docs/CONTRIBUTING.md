# Contributing

Thanks for your interest in improving VisionOS Gesture Control! This guide covers
local setup, the project conventions, and how to add the two most common kinds of
extension: a new gesture and a new ML backend.

## Local setup

```bash
git clone https://github.com/aastha-m22/visionos-gesture-control.git
cd visionos-gesture-control
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e ".[dev]"        # editable install + pytest
```

Run the test suite (no camera required — gesture logic is tested with synthetic
hands):

```bash
pytest -q
```

## Conventions

- **Python ≥ 3.9**, `from __future__ import annotations` at the top of every
  module.
- **Type hints everywhere**; public functions and classes carry docstrings.
- **No bare `except`** — catch specific exceptions and log via
  `utils.logger.get_logger(...)`. Domain errors derive from `VisionOSError`.
- **Optional dependencies degrade gracefully** — never let a missing OS backend
  crash the pipeline; disable the feature and warn.
- **Keep MediaPipe quarantined** in `core/hand_tracker.py`. Anything above the
  perception layer must work on synthetic `HandLandmarks`.
- Keep functions in `gestures/rules.py` **pure** (no side effects) so they stay
  unit-testable.

## Adding a new gesture

1. Add a value to the `Gesture` enum in `gestures/gesture_types.py`, and list it
   in `DISCRETE_GESTURES` or `CONTINUOUS_GESTURES`.
2. Add a detection branch in `gestures/rules.py`. Mind the **branch order** —
   put more specific / higher-priority poses first (e.g. fist before pinch).
3. Map it to an action in `controllers/dispatcher.py` (and add a controller
   method if it drives new hardware).
4. Add a synthetic-hand test in `tests/` using `tests/helpers.build_hand(...)`.
5. Document it in the README gesture table.

## Adding an ML backend

The classifier is backend-agnostic. To plug in a trained model:

1. Subclass `GestureBackend` (see `gestures/ml/model.py` for the contract:
   `load()`, `classify(hand) → GestureResult`, `feature_names()`).
2. Collect training data with the dataset utility:
   ```bash
   python -m visionos.data.collector --label left_click --out datasets/clicks.csv
   ```
   Each row is the 63-D landmark feature vector plus a label.
3. Train offline, export (ONNX recommended), and load it in your backend.
4. Swap it in at runtime: `classifier.set_backend(MyMLBackend())`. No other code
   changes are required.

## Pull requests

- One logical change per PR; keep the diff focused.
- Add or update tests for behaviour you change. `pytest` must pass.
- Update the relevant docs (`README.md`, `docs/`) when behaviour or the public
  surface changes.
- Describe *what* and *why* in the PR body, not just *how*.

## Reporting issues

Include your OS, Python version, camera model if relevant, the command you ran,
and the full log output (run with `--debug` for verbose logs).
