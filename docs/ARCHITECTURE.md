# Architecture

VisionOS Gesture Control is built as a **layered pipeline** with a strict
dependency direction: each layer depends only on the ones beneath it, and the
single heavyweight dependency (MediaPipe) is quarantined behind one module so
the rest of the system stays testable without a camera or GPU.

```
                ┌─────────────────────────────────────────────┐
                │                  app.py                       │
                │   VisionOSApp — main loop & orchestration      │
                └───────────────┬─────────────────┬────────────┘
                                │                 │
                 ┌──────────────▼──────┐   ┌──────▼───────────────┐
                 │   Perception        │   │   Presentation        │
                 │  core/hand_tracker  │   │  ui/dashboard         │
                 │  core/landmark      │   │  ui/themes            │
                 │  core/smoothing     │   │  ui/settings_window   │
                 └──────────┬──────────┘   └──────────────────────┘
                            │
                 ┌──────────▼──────────┐
                 │   Interpretation    │
                 │  gestures/rules     │
                 │  gestures/classifier│
                 │  gestures/ml (stub) │
                 └──────────┬──────────┘
                            │
                 ┌──────────▼──────────┐
                 │   Actuation         │
                 │  controllers/*      │
                 │  (mouse, volume,    │
                 │   brightness, media,│
                 │   screenshot)       │
                 └─────────────────────┘

      Cross-cutting:  config/settings   utils/{logger,metrics,exceptions}
```

## Layers

### 1. Perception (`core/`)
- **`hand_tracker.py`** is the *only* module that imports MediaPipe. It converts
  a raw BGR frame into a list of `HandLandmarks`. Isolating MediaPipe here means
  every layer above can be unit-tested with synthetic landmarks.
- **`landmark.py`** defines the immutable `HandLandmarks` value object and all
  geometry helpers (distances, finger-extension tests, palm centre, hand-scale
  normalisation, 63-D feature vector). Normalising by hand scale makes gestures
  robust to how close the hand is to the camera.
- **`smoothing.py`** implements the **One Euro Filter** (Casiez et al., CHI 2012)
  for adaptive cursor smoothing: heavy smoothing when the hand is slow (precision)
  and light smoothing when it moves fast (responsiveness).

### 2. Interpretation (`gestures/`)
- **`rules.py`** is a pure function `detect(hand, thresholds) → GestureResult`.
  Deterministic and side-effect-free, so it is exhaustively unit-tested.
- **`classifier.py`** wraps a swappable backend behind the `GestureBackend` ABC
  and adds **temporal logic**: a majority-vote stabilisation window to kill
  single-frame flicker, and double-click promotion within a short time window.
- **`ml/model.py`** is a documented stub implementing the same `GestureBackend`
  interface, so a future trained model drops in via `classifier.set_backend(...)`
  with zero changes elsewhere.

### 3. Actuation (`controllers/`)
- Every controller extends `BaseController` and exposes an `available` property.
  If its OS backend is missing (e.g. `pycaw` on Linux), the controller disables
  itself and logs a warning instead of crashing — **graceful degradation**.
- **`dispatcher.py`** is the bridge: it maps a `GestureResult` onto concrete
  controller calls, firing discrete actions on the *rising edge* only and
  streaming continuous actions (cursor, volume, brightness) every frame.

### 4. Presentation (`ui/`)
- **`dashboard.py`** renders the live HUD overlay (FPS, CPU/mem, confidence,
  current gesture, action banner, gesture history, volume/brightness bars,
  hand skeleton) directly onto the OpenCV frame.
- **`settings_window.py`** is a dependency-free Tkinter panel for live tuning.

### Cross-cutting concerns
- **`config/settings.py`** — a tree of typed dataclasses (no stringly-typed dict
  access) with JSON persistence and three shipped profiles (General / Gamer /
  Designer).
- **`utils/`** — namespaced colour logging, rolling-window performance metrics,
  and a small exception hierarchy rooted at `VisionOSError`.

## Design principles

| Principle | Where it shows up |
|-----------|-------------------|
| **Single Responsibility** | One concern per module; tracker ≠ classifier ≠ controller. |
| **Dependency Inversion** | `GestureClassifier` depends on the `GestureBackend` abstraction, not on rules or ML concretely. |
| **Open/Closed** | New gestures = new rule branch + enum value; new backends = new `GestureBackend` subclass. |
| **Fail-soft** | Optional dependencies degrade to disabled features, never hard crashes. |
| **Testability** | MediaPipe quarantined; pure geometry + rules + temporal logic tested with synthetic hands. |

See [`DATAFLOW.md`](DATAFLOW.md) for the per-frame execution trace.
