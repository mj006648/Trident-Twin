"""Trident Twin Isaac Sim extension — live Lakehouse binding.

Polls twin-hub /api/twin/state every POLL_INTERVAL_SECONDS and applies the
returned trident:* attribute snapshot to matching USD prims.

Environment variables (set before launching Isaac Sim):
  TWIN_HUB_URL          twin-hub base URL (default: http://localhost:8765)
  TWIN_POLL_INTERVAL    poll cadence in seconds (default: 10)

How entity_id → USD prim path mapping works:
  The scene generator (create_scene.py) stamps every prim with a
  trident:entity_id custom attribute.  On first poll this extension walks the
  stage and builds a {entity_id: prim_path} index so subsequent polls are O(1)
  attribute lookups, not tree walks.

RAW BUCKET box visibility:
  entity_id "raw.object.NN" prims are shown/hidden based on the live
  object_count returned for the raw.objects.aggregate entity (if present) or
  derived from the number of raw iceberg_table entities.

Pipeline step status colouring:
  entity_id "operation.NN.*" prims have a trident:status attribute.  When the
  live state reports status="done" the extension sets trident:live_status so
  downstream visualisation shaders or Omniverse rules can react.
"""
from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request
from typing import Any

import omni.ext
import omni.ui as ui
import omni.usd
from pxr import Gf, Sdf, UsdGeom

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEFAULT_TWIN_HUB_URL = "http://localhost:8765"
DEFAULT_POLL_INTERVAL = 10.0
RAW_BOX_COUNT = 20  # total RawObject_NN prims created by create_scene.py


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, default))
    except ValueError:
        return default


# ---------------------------------------------------------------------------
# USD attribute helpers (mirror of create_scene.py set_trident_attrs)
# ---------------------------------------------------------------------------
_TYPE_MAP = {
    bool: Sdf.ValueTypeNames.Bool,
    int: Sdf.ValueTypeNames.Int,
    float: Sdf.ValueTypeNames.Float,
    str: Sdf.ValueTypeNames.String,
}


def _set_attr(prim, name: str, value: Any) -> None:
    if not name.startswith("trident:"):
        name = f"trident:{name}"
    if isinstance(value, bool):
        t = Sdf.ValueTypeNames.Bool
    elif isinstance(value, int):
        t = Sdf.ValueTypeNames.Int
        value = int(value)
    elif isinstance(value, float):
        t = Sdf.ValueTypeNames.Float
        value = float(value)
    else:
        t = Sdf.ValueTypeNames.String
        value = str(value)
    attr = prim.GetAttribute(name)
    if not attr:
        attr = prim.CreateAttribute(name, t)
    attr.Set(value)


# ---------------------------------------------------------------------------
# twin-hub HTTP client
# ---------------------------------------------------------------------------

def _fetch_state(base_url: str, timeout: float = 5.0) -> dict[str, Any] | None:
    url = base_url.rstrip("/") + "/api/twin/state"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def _fetch_health(base_url: str, timeout: float = 3.0) -> dict[str, Any] | None:
    url = base_url.rstrip("/") + "/api/twin/health"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Stage index builder
# ---------------------------------------------------------------------------

def _build_entity_index(stage) -> dict[str, str]:
    """Walk USD stage and return {entity_id: prim_path} for all trident:entity_id prims."""
    index: dict[str, str] = {}
    for prim in stage.Traverse():
        attr = prim.GetAttribute("trident:entity_id")
        if attr and attr.IsValid():
            eid = attr.Get()
            if eid:
                index[str(eid)] = prim.GetPath().pathString
    return index


# ---------------------------------------------------------------------------
# Live state applicator
# ---------------------------------------------------------------------------

def _apply_state(stage, entity_index: dict[str, str], state_payload: dict[str, Any]) -> int:
    """Apply twin-hub state snapshot to USD prims. Returns number of updated prims."""
    entities: dict[str, dict[str, Any]] = state_payload.get("entities", {})
    updated = 0

    for entity_id, attrs in entities.items():
        prim_path = entity_index.get(entity_id)
        if not prim_path:
            continue
        prim = stage.GetPrimAtPath(prim_path)
        if not prim or not prim.IsValid():
            continue
        for key, value in attrs.items():
            if value is None:
                continue
            _set_attr(prim, key, value)
        updated += 1

    # RAW BUCKET visibility: show N boxes based on object_count from raw entities
    _apply_raw_bucket_visibility(stage, entity_index, entities)

    # Pipeline step status
    _apply_pipeline_status(stage, entity_index, entities)

    return updated


def _apply_raw_bucket_visibility(stage, entity_index: dict[str, str], entities: dict[str, dict]) -> None:
    """Show/hide RawObject_NN prims to match live raw object count."""
    # Sum object_count across all raw_object entities from live state
    live_count = 0
    for eid, attrs in entities.items():
        if attrs.get("trident:entity_type") in ("raw_object", "dataset") and \
                attrs.get("trident:stage") in ("raw", "raw_bucket", None):
            cnt = attrs.get("trident:object_count", 0)
            if isinstance(cnt, (int, float)) and cnt > 0:
                live_count += int(cnt)

    # If no live count found, keep all boxes visible (fixture mode)
    if live_count == 0:
        return

    # Map live_count → number of boxes to show (cap at RAW_BOX_COUNT)
    boxes_to_show = min(max(1, live_count), RAW_BOX_COUNT)

    for i in range(1, RAW_BOX_COUNT + 1):
        eid = f"raw.object.{i:02d}"
        prim_path = entity_index.get(eid)
        if not prim_path:
            continue
        prim = stage.GetPrimAtPath(prim_path)
        if not prim or not prim.IsValid():
            continue
        imageable = UsdGeom.Imageable(prim)
        if i <= boxes_to_show:
            imageable.MakeVisible()
        else:
            imageable.MakeInvisible()


def _apply_pipeline_status(stage, entity_index: dict[str, str], entities: dict[str, dict]) -> None:
    """Write trident:live_status to pipeline operation prims based on live state."""
    for eid, attrs in entities.items():
        if not eid.startswith("operation."):
            continue
        prim_path = entity_index.get(eid)
        if not prim_path:
            continue
        prim = stage.GetPrimAtPath(prim_path)
        if not prim or not prim.IsValid():
            continue
        status = attrs.get("trident:status", "observed")
        _set_attr(prim, "live_status", str(status))


# ---------------------------------------------------------------------------
# Extension
# ---------------------------------------------------------------------------

class TridentTwinExtension(omni.ext.IExt):

    def on_startup(self, ext_id: str) -> None:
        self._ext_id = ext_id
        self._hub_url = os.environ.get("TWIN_HUB_URL", DEFAULT_TWIN_HUB_URL)
        self._poll_interval = _env_float("TWIN_POLL_INTERVAL", DEFAULT_POLL_INTERVAL)
        self._running = False
        self._thread: threading.Thread | None = None
        self._entity_index: dict[str, str] = {}
        self._last_source = "—"
        self._last_updated = 0
        self._poll_errors = 0

        self._window = ui.Window("Trident Twin Live", width=400, height=220)
        self._build_ui()

    def on_shutdown(self) -> None:
        self._stop_polling()
        self._window = None

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        with self._window.frame:
            with ui.VStack(spacing=6):
                ui.Label("Trident Lakehouse Twin — Live Binding", style={"font_size": 14})
                with ui.HStack(spacing=4):
                    ui.Label("twin-hub:", width=70)
                    self._url_field = ui.StringField()
                    self._url_field.model.set_value(self._hub_url)
                with ui.HStack(spacing=4):
                    ui.Label("Interval (s):", width=70)
                    self._interval_field = ui.StringField()
                    self._interval_field.model.set_value(str(int(self._poll_interval)))
                with ui.HStack(spacing=4):
                    self._start_btn = ui.Button("Start Live", clicked_fn=self._on_start, width=100)
                    self._stop_btn = ui.Button("Stop", clicked_fn=self._stop_polling, width=80)
                    ui.Button("Rebuild Index", clicked_fn=self._rebuild_index, width=110)
                self._status_label = ui.Label("idle — not connected")
                self._detail_label = ui.Label("", style={"color": 0xFF8888AA})

    def _refresh_status(self, msg: str, detail: str = "") -> None:
        try:
            self._status_label.text = msg
            self._detail_label.text = detail
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Controls
    # ------------------------------------------------------------------

    def _on_start(self) -> None:
        self._hub_url = self._url_field.model.get_value_as_string().strip() or DEFAULT_TWIN_HUB_URL
        try:
            self._poll_interval = max(2.0, float(self._interval_field.model.get_value_as_string()))
        except ValueError:
            self._poll_interval = DEFAULT_POLL_INTERVAL

        health = _fetch_health(self._hub_url)
        if health is None:
            self._refresh_status(
                f"Cannot reach twin-hub at {self._hub_url}",
                "Check TWIN_HUB_URL and that uvicorn is running.",
            )
            return

        mode = health.get("mode", "unknown")
        self._refresh_status(
            f"Connected — mode: {mode}",
            f"dataset_count={health.get('dataset_count', '?')}  pipeline_runs={health.get('pipeline_run_count', '?')}",
        )

        self._rebuild_index()
        self._start_polling()

    def _rebuild_index(self) -> None:
        ctx = omni.usd.get_context()
        stage = ctx.get_stage()
        if stage is None:
            self._refresh_status("No open USD stage — open the twin USDA first.")
            return
        self._entity_index = _build_entity_index(stage)
        self._refresh_status(
            f"Index built: {len(self._entity_index)} entities mapped",
            f"hub={self._hub_url}",
        )

    # ------------------------------------------------------------------
    # Polling thread
    # ------------------------------------------------------------------

    def _start_polling(self) -> None:
        if self._running:
            return
        self._running = True
        self._poll_errors = 0
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def _stop_polling(self) -> None:
        self._running = False
        self._thread = None
        self._refresh_status("Stopped.")

    def _poll_loop(self) -> None:
        import time
        while self._running:
            self._do_poll()
            time.sleep(self._poll_interval)

    def _do_poll(self) -> None:
        state = _fetch_state(self._hub_url)
        if state is None:
            self._poll_errors += 1
            self._refresh_status(
                f"Poll failed ({self._poll_errors}x) — twin-hub unreachable",
                f"url={self._hub_url}",
            )
            return

        ctx = omni.usd.get_context()
        stage = ctx.get_stage()
        if stage is None:
            self._refresh_status("No open USD stage.")
            return

        if not self._entity_index:
            self._entity_index = _build_entity_index(stage)

        updated = _apply_state(stage, self._entity_index, state)
        self._poll_errors = 0
        source = state.get("source", "?")
        entity_count = len(state.get("entities", {}))
        self._last_source = source
        self._last_updated = updated
        self._refresh_status(
            f"Live — {updated}/{entity_count} prims updated  [source: {source}]",
            f"interval={self._poll_interval:.0f}s  index={len(self._entity_index)} entities",
        )
