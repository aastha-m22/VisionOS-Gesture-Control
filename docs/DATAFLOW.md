# Data Flow

This document traces a single frame from camera to OS action, then describes the
two stateful subsystems that span multiple frames (temporal gesture logic and
adaptive smoothing).

## Per-frame pipeline

```
 webcam ──► [1] capture ──► [2] flip ──► [3] track ──► [4] geometry
                                                            │
   OS action ◄── [8] dispatch ◄── [7] classify ◄── [5] detect rule
                     │                                      ▲
                     └──────► [6] render HUD ───────────────┘
```

1. **Capture** — `VisionOSApp.run()` reads a BGR frame from OpenCV
   (`cv2.VideoCapture`). A failed read raises `CameraError`.
2. **Flip** — the frame is mirrored horizontally (`camera.flip_horizontal`) so
   moving your hand right moves the cursor right; this matches user intuition.
3. **Track** — `HandTracker.process(frame)` runs MediaPipe Hands and returns a
   list of `HandLandmarks` (empty if no hand is visible).
4. **Geometry** — `landmark.py` derives scale-normalised distances and
   finger-extension booleans from the 21 raw landmarks. Normalising by
   hand-scale (`wrist → middle MCP`) makes thresholds distance-invariant.
5. **Detect (rule)** — `rules.detect()` maps the geometry to a single
   `GestureResult(gesture, confidence, cursor, magnitude)`. Branch order matters:
   fist/drag is tested **before** pinch so a closed fist is never misread as a
   click.
6. **Render** — the `Dashboard` overlays metrics, the active gesture, an action
   banner, the gesture-history strip, volume/brightness bars and the hand
   skeleton onto the frame, which is then shown with `cv2.imshow`.
7. **Classify (temporal)** — `GestureClassifier` consumes the per-frame raw
   gesture and applies stabilisation + double-click promotion (see below),
   emitting the *stable* gesture actually acted upon.
8. **Dispatch** — `ActionDispatcher` translates the stable `GestureResult` into
   controller calls: continuous gestures (cursor / volume / brightness) every
   frame, discrete gestures (clicks / screenshot / media) only on the rising
   edge.

## Stateful subsystem A — temporal gesture logic

A raw per-frame classification flickers (MediaPipe jitter, momentary finger
occlusion). `GestureClassifier` smooths this in two ways:

- **Stabilisation window** (`stabilise_window = 4`): the emitted gesture is the
  majority vote over the last *N* raw gestures. A one-frame spurious "click" in
  the middle of a cursor move is outvoted and discarded.
- **Double-click promotion** (`double_click_window = 0.4 s`): two distinct
  left-click rising edges inside the window are promoted to a single
  `double_click`, rather than firing two separate clicks.

```
raw:    cursor cursor LCLICK cursor cursor      → majority vote → cursor (flicker rejected)
raw:    LCLICK ........ LCLICK   (Δt < 0.4 s)    → promote        → DOUBLE_CLICK
```

## Stateful subsystem B — adaptive cursor smoothing

The index-fingertip position feeds a `PointSmoother` (two One Euro filters, one
per axis). The One Euro Filter raises its cutoff frequency with hand speed:

```
hand nearly still  → low cutoff  → heavy smoothing → jitter-free precision
hand moving fast   → high cutoff → light smoothing → low-latency tracking
```

The smoothed point is then mapped from the camera frame to screen coordinates by
`MouseController._map_to_screen`, which applies an edge dead-band (so the corners
of the screen are reachable without your hand leaving the frame) and a
sensitivity gain about the frame centre.

## Discrete vs continuous gestures

| Kind | Examples | Firing rule |
|------|----------|-------------|
| **Continuous** | `cursor_move`, `volume`, `brightness`, `scroll` | Applied every frame while active. |
| **Discrete** | `left_click`, `right_click`, `double_click`, `screenshot`, `play_pause`, `next_track`, `prev_track` | Fired once on the transition into the gesture (rising edge), with per-controller cooldowns to debounce. |

`drag` is a hybrid: a fist *begins* a drag (rising edge), movement *updates* it
(continuous), and opening the hand *ends* it (falling edge).
