import json
from pathlib import Path

import omni.ext
import omni.ui as ui
import omni.usd
from pxr import Gf, UsdGeom, Sdf


class TridentTwinExtension(omni.ext.IExt):
    """Minimal Isaac Sim extension skeleton for Trident Twin.

    This version intentionally starts simple:
    - Opens a small control window.
    - Loads mock events from data/mock_twin_events.json.
    - Applies the selected event to /World/Datasets/DatasetPackage001.

    Later this should be replaced by Stats Service /api/twin/events or WebSocket state stream.
    """

    def on_startup(self, ext_id):
        self._ext_id = ext_id
        self._event_index = 0
        self._events = []
        self._window = ui.Window("Trident Twin", width=360, height=180)
        with self._window.frame:
            with ui.VStack(spacing=8):
                ui.Label("Trident Lakehouse Twin PoC")
                ui.Button("Load Mock Events", clicked_fn=self._load_events)
                ui.Button("Apply Next Event", clicked_fn=self._apply_next_event)
                self._status = ui.Label("idle")

    def on_shutdown(self):
        self._window = None
        self._events = []

    def _load_events(self):
        # Extension is normally under <repo>/exts/trident.twin/trident/twin/extension.py
        repo_root = Path(__file__).resolve().parents[4]
        event_file = repo_root / "data" / "mock_twin_events.json"
        with event_file.open("r", encoding="utf-8") as f:
            self._events = json.load(f)["timeline"]
        self._event_index = 0
        self._status.text = f"loaded {len(self._events)} events"

    def _apply_next_event(self):
        if not self._events:
            self._load_events()
        if not self._events:
            self._status.text = "no events"
            return
        event = self._events[self._event_index % len(self._events)]
        ctx = omni.usd.get_context()
        stage = ctx.get_stage()
        if stage is None:
            self._status.text = "no open USD stage"
            return
        prim = stage.GetPrimAtPath("/World/Datasets/DatasetPackage001")
        if not prim:
            self._status.text = "DatasetPackage001 not found"
            return

        UsdGeom.XformCommonAPI(prim).SetTranslate(Gf.Vec3d(*event["position"]))
        for name, value, type_name in [
            ("trident:stage", event["stage"], Sdf.ValueTypeNames.String),
            ("trident:zone", event["zone"], Sdf.ValueTypeNames.String),
            ("trident:metadata_status", event.get("metadata_status", "none"), Sdf.ValueTypeNames.String),
            ("trident:sharing_status", event.get("sharing_status", "private"), Sdf.ValueTypeNames.String),
            ("trident:last_event", event["event"], Sdf.ValueTypeNames.String),
        ]:
            attr = prim.GetAttribute(name) or prim.CreateAttribute(name, type_name)
            attr.Set(value)

        self._status.text = f"applied {event['event']}"
        self._event_index += 1
