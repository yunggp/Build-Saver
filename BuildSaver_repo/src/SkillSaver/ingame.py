"""
Build Saver - in-game menu bridge (v4.0)

The in-game panel (ui.js in SkillSaverUI_1001_P.pak) talks to this module over a small HTTP
server on 127.0.0.1 (never reachable from other computers).

Thread rule: the HTTP thread only reads/writes plain Python data and files. It NEVER touches
Unreal objects - this module does not even import unrealsdk. Everything that needs the game
(save, load, reset ...) is put into a queue and run by the mod's tick on the game thread.

Endpoints (prefix /skillsaver-ui-v1):
  GET  /state   status, saved builds (with gear check marks), undo point, last result
  POST /cmd     {"action": save|overwrite|load|undo|reset|rename|delete, "id": "...", "name": "..."}
  POST /trace   {"kind": "...", "data": ...}  diagnostics from the panel -> SkillSaver_ui_log.txt
  GET  /kb, POST /kb {"cmd": start|set|stop, "text": "..."}  typing a build name with the real keyboard while the
                rename field is open (kbd.py, KEYBOARD.md)
Requests that come from a normal web page (Origin http/https) are refused, so a website in your
browser can not load or delete builds.
"""

import json
import re
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

PORT = 19417
PREFIX = "/skillsaver-ui-v1"
ACTIONS = ("save", "overwrite", "load", "undo", "reset", "rename", "delete")
# file names the mod / app use for other things - never treated as a build
RESERVED = {"status", "command", "gear_now", "app", "undo", "log", "signatures", "ui_log"}
TRACE_MAX = 300

_lock = threading.Lock()
_queue: deque = deque()
_srv = {"server": None, "dir": None, "version": "", "enabled": False, "error": ""}
_status: dict = {}
_result = {"done": 0, "msg": "", "ok": True, "time": 0.0}
_seen = {"poll": 0.0, "next_id": 0}
_cache: dict = {}
_trace = {"count": 0}


# ---------------------------------------------------------------- called by the mod (game thread)
def start(sdk_mods: Path | None, version: str, log) -> None:
    """Start the HTTP server once. A second start (mod re-enabled) only switches it on again."""
    with _lock:
        _srv["dir"], _srv["version"], _srv["enabled"] = sdk_mods, version, True
    if _srv["server"] is not None:
        return
    try:
        server = HTTPServer(("127.0.0.1", PORT), _Handler)
    except OSError as ex:
        _srv["error"] = f"port {PORT} busy: {ex}"
        log(f"In-game menu disabled - {_srv['error']} (restart the game if you reloaded the mod).")
        return
    server.timeout = 1
    _srv["server"] = server
    threading.Thread(target=server.serve_forever, name="SkillSaver-UI", daemon=True).start()
    log(f"In-game menu bridge on 127.0.0.1:{PORT}.")


def stop() -> None:
    """The server keeps running (a port can not be freed safely while the game runs) but answers 'disabled'."""
    with _lock:
        _srv["enabled"] = False
        _queue.clear()
    try:
        from . import kbd
        kbd.stop()
    except Exception:  # noqa: BLE001
        pass


def pop_commands() -> list:
    with _lock:
        out = list(_queue)
        _queue.clear()
    return out


def finish(cid: int, msg: str, ok: bool = True) -> None:
    with _lock:
        _result.update(done=cid, msg=msg, ok=ok, time=time.time())


def set_status(st: dict) -> None:
    with _lock:
        _status.clear()
        _status.update(st)


def watching() -> bool:
    """True while the in-game panel is open (it polls every second)."""
    return time.time() - _seen["poll"] < 15.0


def is_reserved(slot: str) -> bool:
    return not slot or slot.lower() in RESERVED


def clean_slot(slot) -> str:
    return "".join(ch for ch in str(slot or "") if ch.isalnum() or ch in "_-")[:40]


# ---------------------------------------------------------------- build list (HTTP thread, files only)
def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return None


def _gear_label(g: dict) -> str:
    """Same rules as the desktop app (Get-GearName)."""
    slot = str(g.get("slot", ""))
    if "title" in g:
        n = g.get("name") or g.get("title") or "-"
        if g.get("element") and slot.startswith(("Weapon", "Ordnance")):
            n += f"  ({g['element']})"
        return str(n)
    name, auto = g.get("name"), g.get("auto")
    if name and auto and name != auto:
        return f"{name}  ({auto})"
    return str(name or auto or "-")


def _char_of(d: dict) -> str:
    c = str(d.get("character", "")).lower()
    for k in ("corpohacker", "darksiren", "exosoldier", "gravitar", "paladin", "robodealer"):
        if k in c:
            return k
    for g in d.get("graphs", []) or []:
        n = str(g.get("name", "")).lower()
        if "actionskill" not in n.replace("_", "") and "_mods_" not in n:
            continue
        for k, key in (("corpohacker", "corpohacker"), ("darksiren", "darksiren"), ("_exo_", "exosoldier"),
                       ("_grav_", "gravitar"), ("paladin", "paladin"), ("_robo_", "robodealer")):
            if k in n:
                return key
    return ""


def _summary(slot: str, d: dict) -> dict:
    pts = d.get("points")
    if pts is None:
        pts = sum(int(n.get("spent", 0)) for g in d.get("graphs", []) if g.get("kind") == "points"
                  for n in g.get("nodes", []))
    gear, fw = [], {}
    for g in d.get("gear", []) or []:
        if not isinstance(g, dict) or not (g.get("auto") or g.get("name") or g.get("title")):
            continue
        gear.append({"slot": str(g.get("slot", "")), "label": _gear_label(g), "serial": str(g.get("serial", "")),
                     "title": str(g.get("name") or g.get("title") or ""), "auto": str(g.get("auto", "")),
                     "element": str(g.get("element") or ""), "firmware": str(g.get("firmware") or "")})
        if g.get("firmware"):
            fw.setdefault(str(g["firmware"]), []).append(str(g.get("slot", "")))
    spec = []
    for s in d.get("spec", []) or []:
        if isinstance(s, dict):
            spec.append({"tree": str(s.get("tree", "")),
                         "name": str(s.get("name") or (f"Skill {s.get('skill')}" if s.get("skill") is not None else "-"))})
    lo = d.get("loadout") or {}
    m = re.match(r"slot(\d)$", slot)
    return {"id": slot, "name": str(d.get("name") or (f"Slot {m.group(1)}" if m else slot)),
            "saved": str(d.get("saved", "")), "char": _char_of(d), "points": int(pts or 0),
            "action_skill": str(lo.get("action_skill", "")), "augments": [str(x) for x in lo.get("augments", []) if x],
            "capstones": [str(x) for x in lo.get("capstones", []) if x], "spec": spec, "gear": gear,
            "firmware": [{"set": k, "count": len(v), "slots": v} for k, v in fw.items()],
            "notes": str(d.get("notes", ""))}


def _builds(sdk_mods: Path) -> tuple:
    out, seen = [], set()
    for f in sorted(sdk_mods.glob("SkillSaver_*.json")):
        slot = f.stem[len("SkillSaver_"):]
        if is_reserved(slot):
            continue
        try:
            st = f.stat()
        except OSError:
            continue
        seen.add(f)
        stamp = (st.st_mtime_ns, st.st_size)
        c = _cache.get(f)
        if c is None or c[0] != stamp:
            d = _read_json(f)
            c = (stamp, _summary(slot, d) if isinstance(d, dict) and d.get("graphs") else None)
            _cache[f] = c
        if c[1] is not None:
            out.append(c[1])
    for f in [k for k in _cache if k not in seen]:
        del _cache[f]
    out.sort(key=lambda b: b["saved"], reverse=True)
    undo = None
    u = _read_json(sdk_mods / "SkillSaver_undo.json")
    if isinstance(u, dict) and u.get("graphs"):
        undo = {"name": str(u.get("name", "")), "of": str(u.get("undo_of", "")), "saved": str(u.get("saved", ""))}
    return out, undo


def _gear_marks(sdk_mods: Path) -> dict | None:
    g = _read_json(sdk_mods / "SkillSaver_gear_now.json")
    if not isinstance(g, dict) or time.time() - float(g.get("time", 0)) > 30:
        return None
    return {"equipped": set(str(s) for s in (g.get("equipped") or {}).values()),
            "backpack": set(str(s) for s in g.get("backpack") or [])}


def _state() -> dict:
    with _lock:
        d, enabled = _srv["dir"], _srv["enabled"]
        st, res, busy = dict(_status), dict(_result), len(_queue)
    out = {"ok": True, "version": _srv["version"], "enabled": enabled, "time": time.time(), "busy": busy,
           "result": res, "character": st.get("character", ""), "points": st.get("points"),
           "in_game": bool(st.get("character")), "builds": [], "undo": None, "gear_check": False}
    if not enabled or d is None:
        return out
    builds, undo = _builds(d)
    marks = _gear_marks(d)
    if marks is not None:
        out["gear_check"] = True
        for b in builds:
            for g in b["gear"]:
                s = g["serial"]
                g["mark"] = "" if not s else ("worn" if s in marks["equipped"] else
                                              "backpack" if s in marks["backpack"] else "missing")
    out["builds"], out["undo"] = builds, undo
    return out


def _enqueue(data: dict) -> dict:
    action = str(data.get("action", ""))
    if action not in ACTIONS:
        return {"queued": False, "error": "unknown action"}
    slot = clean_slot(data.get("id"))
    if action in ("overwrite", "load", "rename", "delete") and is_reserved(slot):
        return {"queued": False, "error": "invalid build"}
    name = str(data.get("name", ""))[:60].strip()
    with _lock:
        if not _srv["enabled"]:
            return {"queued": False, "error": "mod disabled"}
        if len(_queue) >= 5:
            return {"queued": False, "error": "busy"}
        _seen["next_id"] = max(_seen["next_id"], _result["done"]) + 1
        cid = _seen["next_id"]
        _queue.append({"id": cid, "action": action, "slot": slot, "name": name})
    return {"queued": True, "id": cid}


def set_keyboard(on: bool) -> None:
    """Mod option "Keyboard typing in Rename"."""
    with _lock:
        _srv["keyboard"] = bool(on)
    if not on:
        try:
            from . import kbd
            kbd.stop()
        except Exception:  # noqa: BLE001
            pass


def _write_trace(data: dict) -> None:
    d = _srv["dir"]
    if d is None or _trace["count"] >= TRACE_MAX:
        return
    _trace["count"] += 1
    line = json.dumps({"t": time.strftime("%H:%M:%S"), "kind": str(data.get("kind", ""))[:40],
                       "data": data.get("data")}, ensure_ascii=False)[:4000]
    with _lock:
        mode = "w" if _trace["count"] == 1 else "a"     # new file every game start
        with (d / "SkillSaver_ui_log.txt").open(mode, encoding="utf-8") as f:
            f.write(line + "\n")


# ---------------------------------------------------------------- HTTP
def _origin_ok(origin: str | None) -> bool:
    if not origin or origin == "null":
        return True
    o = origin.lower()
    return o.startswith("coui://") or o.startswith("file://")


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # no console spam
        pass

    def _reply(self, code: int, data) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _guard(self) -> bool:
        if not _origin_ok(self.headers.get("Origin")):
            self.send_response(403)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return False
        return True

    def do_OPTIONS(self):
        if not self._guard():
            return
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if not self._guard():
            return
        if self.path == PREFIX + "/kb":                  # rename field: keyboard text (light, polled often)
            from . import kbd
            return self._reply(200, kbd.state(touch=True))
        if self.path != PREFIX + "/state":
            return self._reply(404, {})
        _seen["poll"] = time.time()
        try:
            self._reply(200, _state())
        except Exception as ex:  # noqa: BLE001
            self._reply(500, {"ok": False, "error": f"{type(ex).__name__}: {ex}"})

    def do_POST(self):
        if not self._guard():
            return
        if self.path not in (PREFIX + "/cmd", PREFIX + "/trace", PREFIX + "/kb"):
            return self._reply(404, {})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 16000:
                return self._reply(413, {})
            data = json.loads(self.rfile.read(size).decode("utf-8"))
            if not isinstance(data, dict):
                return self._reply(400, {})
            if self.path == PREFIX + "/trace":
                _write_trace(data)
                return self._reply(200, {})
            if self.path == PREFIX + "/kb":
                from . import kbd
                text, cmd = str(data.get("text", ""))[:60], str(data.get("cmd", ""))
                if cmd == "start":
                    if not _srv["enabled"]:
                        return self._reply(200, {"active": False, "error": "mod disabled"})
                    if not _srv.get("keyboard", True):
                        return self._reply(200, {"active": False, "error": "switched off in the mod options"})
                    return self._reply(200, kbd.start(text))
                if cmd == "set":
                    return self._reply(200, kbd.set_text(text))
                return self._reply(200, kbd.stop())
            return self._reply(200, _enqueue(data))
        except (ValueError, OSError, UnicodeDecodeError):
            return self._reply(400, {})
