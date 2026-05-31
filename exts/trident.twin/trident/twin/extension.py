"""Trident Twin Isaac Sim extension — live Lakehouse binding.

Polls twin-hub /api/twin/state using Kit's update loop (no threading).
Uses omni.kit.app.get_app().get_update_event_stream() so HTTP calls
happen on the main Kit thread, avoiding the threading + urllib crash.

Environment variables:
  TWIN_HUB_URL         twin-hub base URL (default: http://localhost:8765)
  TWIN_POLL_INTERVAL   poll cadence in seconds (default: 10)
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

import carb
import omni.ext
import omni.kit.app
import omni.ui as ui
import omni.usd
from pxr import Sdf, UsdGeom

DEFAULT_TWIN_HUB_URL = "http://localhost:8765"
DEFAULT_POLL_INTERVAL = 10.0
RAW_BOX_COUNT = 20


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, default))
    except ValueError:
        return default


def _set_attr(prim, name: str, value: Any) -> None:
    if not name.startswith("trident:"):
        name = f"trident:{name}"
    if isinstance(value, bool):
        t = Sdf.ValueTypeNames.Bool
    elif isinstance(value, int):
        t, value = Sdf.ValueTypeNames.Int, int(value)
    elif isinstance(value, float):
        t, value = Sdf.ValueTypeNames.Float, float(value)
    else:
        t, value = Sdf.ValueTypeNames.String, str(value)
    attr = prim.GetAttribute(name)
    if not attr:
        attr = prim.CreateAttribute(name, t)
    attr.Set(value)


def _fetch_state(base_url: str) -> dict[str, Any] | None:
    try:
        req = urllib.request.Request(base_url.rstrip("/") + "/api/twin/state")
        with urllib.request.urlopen(req, timeout=4.0) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        carb.log_warn(f"[trident.twin] fetch failed: {e}")
        return None


def _build_index(stage) -> dict[str, str]:
    index: dict[str, str] = {}
    for prim in stage.Traverse():
        attr = prim.GetAttribute("trident:entity_id")
        if attr and attr.IsValid():
            eid = attr.Get()
            if eid:
                index[str(eid)] = prim.GetPath().pathString
    return index


def _apply_state(stage, index: dict[str, str], payload: dict[str, Any]) -> int:
    entities: dict[str, dict] = payload.get("entities", {})
    updated = 0
    for eid, attrs in entities.items():
        path = index.get(eid)
        if not path:
            continue
        prim = stage.GetPrimAtPath(path)
        if not prim or not prim.IsValid():
            continue
        for k, v in attrs.items():
            if v is not None:
                _set_attr(prim, k, v)
        updated += 1

    # RAW BUCKET visibility
    live_count = sum(
        int(a.get("trident:object_count", 0))
        for eid, a in entities.items()
        if a.get("trident:entity_type") in ("raw_object", "dataset")
        and a.get("trident:stage") in ("raw", "raw_bucket", None)
        and isinstance(a.get("trident:object_count", 0), (int, float))
        and a.get("trident:object_count", 0) > 0
    )
    if live_count > 0:
        show = min(max(1, live_count), RAW_BOX_COUNT)
        for i in range(1, RAW_BOX_COUNT + 1):
            p = index.get(f"raw.object.{i:02d}")
            if not p:
                continue
            prim = stage.GetPrimAtPath(p)
            if prim and prim.IsValid():
                img = UsdGeom.Imageable(prim)
                img.MakeVisible() if i <= show else img.MakeInvisible()

    # Pipeline status
    for eid, attrs in entities.items():
        if not eid.startswith("operation."):
            continue
        p = index.get(eid)
        if not p:
            continue
        prim = stage.GetPrimAtPath(p)
        if prim and prim.IsValid():
            _set_attr(prim, "live_status", str(attrs.get("trident:status", "observed")))

    return updated


class TridentTwinExtension(omni.ext.IExt):

    def on_startup(self, ext_id: str) -> None:
        self._hub_url = os.environ.get("TWIN_HUB_URL", DEFAULT_TWIN_HUB_URL)
        self._poll_interval = _env_float("TWIN_POLL_INTERVAL", DEFAULT_POLL_INTERVAL)
        self._running = False
        self._index: dict[str, str] = {}
        self._elapsed = 0.0
        self._sub = None

        self._window = ui.Window("Trident Twin Live", width=420, height=200)
        self._build_ui()

    def on_shutdown(self) -> None:
        self._stop()
        self._window = None

    def _build_ui(self) -> None:
        with self._window.frame:
            with ui.VStack(spacing=6):
                ui.Label("Trident Lakehouse Twin — Live Binding",
                         style={"font_size": 14})
                with ui.HStack(spacing=4):
                    ui.Label("twin-hub:", width=70)
                    self._url_field = ui.StringField()
                    self._url_field.model.set_value(self._hub_url)
                with ui.HStack(spacing=4):
                    ui.Label("Interval (s):", width=70)
                    self._int_field = ui.StringField()
                    self._int_field.model.set_value(str(int(self._poll_interval)))
                with ui.HStack(spacing=4):
                    ui.Button("Start Live", clicked_fn=self._start, width=100)
                    ui.Button("Stop", clicked_fn=self._stop, width=80)
                    ui.Button("Rebuild Index", clicked_fn=self._rebuild, width=110)
                self._status = ui.Label("idle")
                self._detail = ui.Label("", style={"color": 0xFF8888AA})

    def _set_status(self, msg: str, detail: str = "") -> None:
        try:
            self._status.text = msg
            self._detail.text = detail
        except Exception:
            pass

    def _start(self) -> None:
        self._hub_url = self._url_field.model.get_value_as_string().strip() or DEFAULT_TWIN_HUB_URL
        try:
            self._poll_interval = max(2.0, float(self._int_field.model.get_value_as_string()))
        except ValueError:
            self._poll_interval = DEFAULT_POLL_INTERVAL

        self._rebuild()
        if self._running:
            return
        self._running = True
        self._elapsed = self._poll_interval  # poll immediately on first tick
        app = omni.kit.app.get_app()
        self._sub = app.get_update_event_stream().create_subscription_to_pop(
            self._on_update, name="trident_twin_poll"
        )
        self._set_status(f"Live polling {self._hub_url} every {self._poll_interval:.0f}s")

    def _stop(self) -> None:
        self._running = False
        self._sub = None
        self._set_status("Stopped.")

    def _rebuild(self) -> None:
        ctx = omni.usd.get_context()
        stage = ctx.get_stage()
        if stage is None:
            self._set_status("No open USD stage — open the twin USDA first.")
            return
        self._index = _build_index(stage)
        self._set_status(f"Index: {len(self._index)} entities mapped", f"hub={self._hub_url}")

    def _on_update(self, event) -> None:
        if not self._running:
            return
        dt = event.payload.get("dt", 0.016)
        self._elapsed += dt
        if self._elapsed < self._poll_interval:
            return
        self._elapsed = 0.0

        state = _fetch_state(self._hub_url)
        if state is None:
            self._set_status("Poll failed — twin-hub unreachable", f"url={self._hub_url}")
            return

        ctx = omni.usd.get_context()
        stage = ctx.get_stage()
        if stage is None:
            return
        if not self._index:
            self._index = _build_index(stage)

        updated = _apply_state(stage, self._index, state)
        source = state.get("source", "?")
        total = len(state.get("entities", {}))
        self._set_status(
            f"Live — {updated}/{total} prims updated  [source: {source}]",
            f"interval={self._poll_interval:.0f}s  index={len(self._index)}",
        )
