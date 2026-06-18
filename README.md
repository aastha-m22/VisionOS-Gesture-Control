<div align="center">

# 🖐️ VisionOS Gesture Control

**Control your computer with your bare hands — no mouse, no touchscreen, just a webcam.**

Real-time, touchless human–computer interaction powered by computer vision.
Move the cursor, click, drag, scroll, adjust volume and brightness, take
screenshots and control media — entirely through hand gestures.

[Features](#-features) · [Demo](#-demo) · [Install](#-installation) · [Usage](#-usage) · [Gestures](#-gesture-reference) · [Architecture](#-architecture) · [Roadmap](#-roadmap)

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![OpenCV](https://img.shields.io/badge/OpenCV-4.8%2B-green)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10%2B-orange)
![License](https://img.shields.io/badge/license-MIT-lightgrey)
![Tests](https://img.shields.io/badge/tests-33%20passing-brightgreen)

</div>

---

## ✨ Features

- **Adaptive cursor control** — index-finger pointing drives the cursor, smoothed
  by a **One Euro Filter** (Casiez et al., CHI 2012): heavy smoothing when your
  hand is still (jitter-free precision), light smoothing when it moves fast
  (low-latency tracking). This is the single biggest difference between a
  usable gesture cursor and a frustrating one.
- **Full click suite** — left-click (thumb–index pinch), right-click
  (thumb–middle pinch), and **double-click** (two rapid pinches, detected by
  temporal promotion).
- **Drag & drop** — make a fist to grab, move to drag, open your hand to drop.
- **Two-finger scroll** — natural vertical scrolling.
- **Volume & brightness** — pinch-spread gestures with on-screen bars; volume on
  thumb–index, brightness on thumb–pinky.
- **Screenshots** — a three-finger gesture saves a timestamped PNG.
- **Media controls** — play/pause and track skip via dedicated poses.
- **Live HUD dashboard** — FPS, CPU/memory, detection confidence, current
  gesture, an action banner, a rolling gesture-history strip, and the hand
  skeleton, all rendered over the camera feed.
- **User profiles** — ship-ready **General / Gamer / Designer** profiles
  (JSON-backed), hot-swappable at runtime with number keys.
- **In-app settings** — a dependency-free Tkinter panel for live tuning of
  sensitivity, smoothing, and gesture thresholds.
- **ML-ready by design** — gesture classification sits behind a swappable
  backend interface, with a dataset-collection utility and a documented model
  stub so a trained CNN/LSTM can drop in without touching the rest of the system.
- **Robust engineering** — typed dataclasses, namespaced logging, a domain
  exception hierarchy, graceful degradation when an OS backend is missing, and a
  synthetic-hand test suite that runs **without a camera**.

## 🎬 Demo

> _Add a short screen-capture GIF here once recorded — drop it in `assets/` and
> reference it below._

```
assets/demo.gif
```

| Cursor & click | Volume control | Live dashboard |
|:--:|:--:|:--:|
| _screenshot_ | _screenshot_ | _screenshot_ |

## 📦 Installation

**Requirements:** Python 3.9+, a webcam.

```bash
# 1. Clone
git clone https://github.com/aastha-m22/visionos-gesture-control.git
cd visionos-gesture-control

# 2. Create an isolated environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

Optional OS-specific backends are installed automatically where relevant
(`pycaw`/`comtypes` are Windows-only); if any optional backend is missing on your
platform, the corresponding feature simply disables itself with a warning rather
than crashing.

## 🚀 Usage

```bash
# Run with the default (General) profile
python main.py

# Pick a profile
python main.py --profile Gamer

# List available profiles
python main.py --list-profiles

# Override the camera index and enable verbose logs
python main.py --camera 1 --debug

# Run without the HUD overlay (lighter on CPU)
python main.py --no-dashboard
```

### Verify your install first (recommended)

Before plugging in the camera, confirm everything works end-to-end — this runs
the full pipeline on synthetic frames with **no webcam needed** and prints a
pass/fail checklist:

```bash
python main.py --selftest
```

```
  VisionOS self-test
  ----------------------------------------------
  [PASS] OpenCV import          cv2 available
  [PASS] MediaPipe import       v0.10.14
  [PASS] End-to-end pipeline    30/30 frames processed
  ----------------------------------------------
  All checks passed. Run `python main.py` to start.
```

### Safe preview (no OS control)

Want to watch the gesture detection on your webcam *without* it moving your real
mouse or changing volume? Use simulate / dry-run mode:

```bash
python main.py --simulate     # webcam preview, OS control disabled
python main.py --dry-run      # same, usable with any profile
```

If you install the package (`pip install -e .`) you also get a `visionos`
console command and `python -m visionos`, both equivalent to `python main.py`.

### Keyboard controls (while running)

| Key | Action |
|-----|--------|
| `Q` / `Esc` | Quit |
| `P` | Pause / resume tracking |
| `S` | Open the settings panel |
| `1` / `2` / `3` | Switch to General / Gamer / Designer profile |

## 🤚 Gesture reference

The cursor always follows your **index fingertip**, so pointing works no matter
which gesture is active. Rules are evaluated by priority (a fist is tested before
a pinch, so a closed hand is never misread as a click).

| Gesture | Hand pose | Type |
|---------|-----------|------|
| **Move cursor** | Index finger only, pointing | Continuous |
| **Left click** | Thumb + index pinch | Discrete |
| **Right click** | Thumb + middle pinch | Discrete |
| **Double click** | Two rapid left-click pinches (< 0.4 s) | Discrete |
| **Drag & drop** | Closed fist (grab → move → open to drop) | Hybrid |
| **Scroll** | Index + middle extended | Continuous |
| **Volume** | Thumb + index spread apart | Continuous |
| **Brightness** | Thumb + pinky spread apart | Continuous |
| **Screenshot** | Index + middle + ring extended | Discrete |
| **Play / Pause** | Open palm (all fingers + thumb) | Discrete |
| **Skip track** | Pinky only | Discrete |

Single-frame misfires are suppressed by a majority-vote stabilisation window, so
the gesture that actually fires is the one you're *holding*, not a momentary
flicker.

## 🧠 Architecture

A layered pipeline with a strict downward dependency direction. MediaPipe — the
one heavyweight dependency — is quarantined in a single module so every layer
above it is unit-testable with synthetic hands.

```
 Perception        Interpretation       Actuation
 ───────────       ──────────────       ─────────
 hand_tracker  ─►  rules           ─►   mouse / volume / brightness
 landmark          classifier            media / screenshot
 smoothing         ml (stub)             (via dispatcher)
       │                 │                     │
       └──────── app.py main loop ─────────────┘
            HUD dashboard · typed config · logging · metrics
```

- **Perception** (`core/`) — frame → 21 hand landmarks → normalised geometry;
  cursor smoothed by the One Euro Filter.
- **Interpretation** (`gestures/`) — pure rule-based `detect()` plus a temporal
  classifier (anti-flicker stabilisation + double-click promotion) behind a
  swappable `GestureBackend` interface.
- **Actuation** (`controllers/`) — cross-platform mouse/volume/brightness/media/
  screenshot controllers, each degrading gracefully if its OS backend is absent.
- **Presentation** (`ui/`) — OpenCV HUD overlay and a Tkinter settings panel.

Full details in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and a per-frame
trace in [`docs/DATAFLOW.md`](docs/DATAFLOW.md).

### Project structure

```
visionos-gesture-control/
├── main.py                     # CLI entry point (runs from a bare checkout)
├── src/visionos/
│   ├── app.py                  # VisionOSApp — capture→track→classify→act loop
│   ├── cli.py                  # argument parsing & launch
│   ├── core/                   # hand_tracker, landmark geometry, smoothing
│   ├── gestures/               # rules, classifier, gesture types, ml/ (stub)
│   ├── controllers/            # mouse, volume, brightness, media, screenshot
│   ├── ui/                     # dashboard, themes, settings_window
│   ├── config/                 # typed settings + ConfigManager
│   ├── data/                   # dataset collector (for ML training)
│   ├── integrations/           # eye-tracking / voice / ROS2 stubs
│   └── utils/                  # logger, metrics, exceptions
├── config/profiles/            # general.json, gamer.json, designer.json
├── tests/                      # synthetic-hand unit tests (no camera needed)
├── docs/                       # ARCHITECTURE, DATAFLOW, CONTRIBUTING
├── requirements.txt
└── pyproject.toml
```

## 🧪 Testing

Gesture logic, smoothing, configuration and metrics are covered by unit tests
that build **synthetic hand poses**, so the suite runs anywhere — no webcam, no
MediaPipe download:

```bash
pip install -e ".[dev]"
pytest -q
```

```
33 passed
```

## 🛠️ Troubleshooting

**`AttributeError: module 'mediapipe' has no attribute 'solutions'`**
You have a very new MediaPipe build that removed the legacy API. The tracker
auto-falls-back to the newer Tasks API, but the simplest fix is to install the
tested version:
```bash
pip install "mediapipe<0.10.15"
```

**The window freezes when I press `S` (settings).** Fixed — the settings editor
now runs on the main thread and pauses capture while open (Tkinter is not
thread-safe). Update to this version if you saw freezes previously.

**`Cannot open camera index 0`.** Another app may be using the camera, or it's on
a different index. Try `python main.py --camera 1`.

**The cursor moves but I don't want it to yet.** Use `python main.py --simulate`
to preview detection without controlling the OS.

**A feature is silently disabled (e.g. brightness).** That OS backend isn't
installed for your platform; the app logs a warning and keeps running. Run with
`--debug` to see which controller was disabled and why.

## 🗺️ Roadmap

- [ ] **Learned gesture model** — train a CNN/LSTM on collected landmark data and
      load it through the existing `GestureBackend` interface (zero changes
      elsewhere). Dataset utility already included.
- [ ] **Eye-tracking fusion** — gaze for coarse pointing + hand for fine control
      (stub in `integrations/eye_tracking.py`).
- [ ] **Voice commands** — multimodal "click", "scroll down", etc.
      (stub in `integrations/voice_control.py`).
- [ ] **ROS2 bridge** — publish gestures as ROS2 topics for robot teleoperation
      (stub in `integrations/ros2_bridge.py`).
- [ ] **Two-handed gestures** — zoom / rotate / multi-cursor.
- [ ] **Gesture macro recorder** — bind custom poses to custom actions.

## 🤝 Contributing

Contributions are welcome! See [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) for
setup, conventions, and step-by-step guides to adding a new gesture or plugging
in an ML backend.

## 📄 License

Released under the [MIT License](LICENSE) © 2026 Aastha Mahajan.

---

<details>
<summary><strong>Résumé / portfolio bullet points</strong> (click to expand)</summary>

ATS-friendly bullets describing this project:

- Built a real-time, touchless computer-control system in **Python** using
  **OpenCV** and **MediaPipe**, translating webcam hand gestures into mouse,
  scroll, volume, brightness, screenshot and media actions at interactive frame
  rates.
- Engineered an **adaptive cursor pipeline** with the **One Euro Filter** to
  resolve the precision-vs-latency trade-off, plus a temporal gesture classifier
  (majority-vote stabilisation and double-click promotion) to eliminate
  single-frame misfires.
- Designed a **layered, SOLID architecture** isolating the MediaPipe dependency
  behind one module, enabling a **synthetic-hand unit-test suite (33 tests)** that
  runs in CI without a camera.
- Implemented **cross-platform OS controllers** (Windows/macOS/Linux) with
  graceful degradation, **typed JSON-backed user profiles**, a live OpenCV HUD
  dashboard, and a Tkinter settings panel.
- Built the gesture classifier behind a **swappable backend interface** with a
  dataset-collection utility, making the system **ML-ready** for a future trained
  model with no changes to the surrounding pipeline.

</details>
