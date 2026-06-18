"""Graphical settings editor (Tkinter, standard library only).

Provides sliders and dropdowns to tune sensitivity, gesture thresholds,
smoothing parameters, theme and history length, then persists the result back
to a profile via :class:`~visionos.config.settings.ConfigManager`. Tkinter is
chosen over PyQt so the project has zero extra GUI dependencies and the editor
runs anywhere Python does.

Run standalone::

    python -m visionos.ui.settings_window --profile General
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from typing import Callable, Optional

from visionos.config.settings import AppConfig, ConfigManager
from visionos.ui.themes import theme_names
from visionos.utils.logger import get_logger

logger = get_logger("ui.settings_window")

OnSave = Callable[[AppConfig], None]


class SettingsWindow:
    """A modal Tkinter window for editing one :class:`AppConfig`."""

    def __init__(self, config: AppConfig, on_save: Optional[OnSave] = None) -> None:
        self.config = config
        self.on_save = on_save
        self._vars: dict = {}

    def _slider(self, parent, tk, label, frm, to, value, resolution=0.01):
        import tkinter.ttk as ttk

        row = tk.Frame(parent)
        row.pack(fill="x", padx=12, pady=4)
        tk.Label(row, text=label, width=22, anchor="w").pack(side="left")
        var = tk.DoubleVar(value=value)
        scale = ttk.Scale(row, from_=frm, to=to, variable=var, orient="horizontal")
        scale.pack(side="left", fill="x", expand=True, padx=8)
        readout = tk.Label(row, width=6)
        readout.pack(side="right")

        def _update(*_):
            readout.config(text=f"{var.get():.2f}")

        var.trace_add("write", _update)
        _update()
        return var

    def run(self) -> None:
        """Build and display the window (blocks until closed)."""
        try:
            import tkinter as tk
            from tkinter import messagebox, ttk
        except Exception as exc:  # pragma: no cover - no display/Tk
            logger.error("Tkinter unavailable: %s", exc)
            return

        c = self.config
        root = tk.Tk()
        root.title(f"VisionOS Settings — {c.profile_name}")
        root.geometry("440x560")

        tk.Label(root, text="Gesture Control Settings", font=("TkDefaultFont", 13, "bold")).pack(pady=10)

        v = self._vars
        v["sensitivity"] = self._slider(root, tk, "Cursor sensitivity", 0.5, 3.5, c.smoothing.sensitivity)
        v["min_cutoff"] = self._slider(root, tk, "Smoothing (min cutoff)", 0.2, 3.0, c.smoothing.min_cutoff)
        v["beta"] = self._slider(root, tk, "Responsiveness (beta)", 0.0, 0.05, c.smoothing.beta, 0.001)
        v["pinch"] = self._slider(root, tk, "Pinch threshold", 0.2, 0.6, c.thresholds.pinch)
        v["spread"] = self._slider(root, tk, "Spread threshold", 0.6, 1.2, c.thresholds.spread)
        v["scroll"] = self._slider(root, tk, "Scroll speed", 40, 300, c.controls.scroll_speed, 1)
        v["history"] = self._slider(root, tk, "History length", 4, 16, c.ui.history_length, 1)

        # Theme dropdown
        theme_row = tk.Frame(root)
        theme_row.pack(fill="x", padx=12, pady=8)
        tk.Label(theme_row, text="Theme", width=22, anchor="w").pack(side="left")
        theme_var = tk.StringVar(value=c.ui.theme)
        ttk.Combobox(theme_row, textvariable=theme_var, values=theme_names(), state="readonly").pack(
            side="left", fill="x", expand=True, padx=8
        )

        def _save() -> None:
            new = replace(
                c,
                smoothing=replace(
                    c.smoothing,
                    sensitivity=round(v["sensitivity"].get(), 3),
                    min_cutoff=round(v["min_cutoff"].get(), 3),
                    beta=round(v["beta"].get(), 4),
                ),
                thresholds=replace(
                    c.thresholds,
                    pinch=round(v["pinch"].get(), 3),
                    spread=round(v["spread"].get(), 3),
                ),
                controls=replace(c.controls, scroll_speed=int(v["scroll"].get())),
                ui=replace(c.ui, theme=theme_var.get(), history_length=int(v["history"].get())),
            )
            ConfigManager().save(new)
            if self.on_save is not None:
                self.on_save(new)
            messagebox.showinfo("Saved", f"Profile '{new.profile_name}' saved.")
            root.destroy()

        btns = tk.Frame(root)
        btns.pack(side="bottom", pady=16)
        ttk.Button(btns, text="Save", command=_save).pack(side="left", padx=8)
        ttk.Button(btns, text="Cancel", command=root.destroy).pack(side="left", padx=8)

        root.mainloop()


def main() -> None:
    parser = argparse.ArgumentParser(description="VisionOS settings editor")
    parser.add_argument("--profile", default="General", help="Profile name to edit")
    args = parser.parse_args()
    config = ConfigManager().load(args.profile)
    SettingsWindow(config).run()


if __name__ == "__main__":
    main()
