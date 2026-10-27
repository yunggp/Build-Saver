"""
Build Saver v4.0 (formerly Skill Saver) - Borderlands 4 (oak2-mod-manager)
Internal names stay "SkillSaver" (sdkmod, pak, save files, bridge) so saves and the desktop app keep working.

Saves your complete skill setup (skill points, action skill, augments, capstone, specialization
skills) under a name and loads it again - anywhere, no respec station needed.
Everything is controlled from the Encore Teleport desktop app (page "Skills"): save new, load,
overwrite, rename, delete, reset tree. v1.2: no keybinds and no mod options any more.
v1.3: every save also lists the equipped gear (text only - gear is NOT equipped on load) and the
equipped specialization skills, so the app can show what belongs to a build.
v1.4: real item names. The item serial (@U...) is read from InventoryIdentity memory (pointer at
+0xA0, length +0xB0, level +0xC4 - offsets as used by Matt's SDK Boosting Tools / Oak2LiveObjectViewer).
If "Matt's SDK Boosting Tools" (MIT, github.com/funkyoushift/MattsSDKBoostingTools) is installed, its
item_serial_reader is used to turn the serial into the in-game name (live item card or the GZO parts
map that ships with that mod). Nothing of that mod is copied here; without it the name falls back
to manufacturer / type / rarity read from the asset paths.
v1.5: the GZO part map often only knows internal code names ("Flap"). The serial is now also matched
against the Lootlemon catalog that ships with Matt's mod (real item names + serials): same item type
and a part that only that catalog item has (legendary barrel, unique augment, class mod name ...),
or the exact same set of main parts (legendaries like enhancements are named by their core combo).
Self-test: all 379 catalog serials map back to their own name.
v1.6: firmware and element are decoded from the serial parts (part_firmware_*, part_<element>) and
added to every item - non-legendary items (no catalog name) at least show what matters for a build.
v1.7: in-game names for action skill, augment, capstone and specialization skills (table below, taken
from the game's tooltip data / progress graphs as extracted in Matt's editor data: modifier graph
nodes 0-4 = augments 1-5, nodes 5-7 = capstones 1-3). Load order fixed: augments / capstones are
applied AFTER all skill points (they unlock through points in the trunk / branches), failed
activations are retried once at the end.
v1.8-v1.11: augment fix. The game stores action skill / augment / capstone with ActivationLevel 0
(for specialization skills the level is the slot 1-3). Loading used to send at least 1, which left the
augment "activated" but not equipped. Now: level 0 there, the saved slot for specialization skills;
augments are activated in group 0, capstones in group 1 (modifier graph template).
v2.0: diagnostics removed again (function spy, state dumps, off/on refresh). Gear entries have
separate "title", "element" and "firmware" fields for the compact app display.
v2.1: - character detection from the skill tree names (pawn.Class.Name is only "OakCharacter" for
        everyone): corpohacker / darksiren / exosoldier / gravitar / paladin / robodealer
      - SkillSaver_gear_now.json (every ~5 s): serials of the equipped items and of the backpack, so the
        app can show which saved gear you are wearing, carrying or no longer have
      - every load first saves the current setup as "undo" (SkillSaver_undo.json, "Before last load")
v2.2: performance - tree type / pool per graph is cached (it was read from a big repr() of the graph
      definition for ~20 graphs every second), the gear check only runs while the app shows the Skills
      page (heartbeat file SkillSaver_app.json), the in-memory log is capped and repeated tick errors
      are reported once.
v2.3: PRIVATE build option. If the sub folder SkillSaver/_names exists (serial decoder + name data copied
      from Matt's SDK Boosting Tools - MIT code, data from GZO / Lootlemon), real names work without
      Matt's mod. The public release is built WITHOUT _names (that data may not be redistributed);
      there Matt's mod stays the optional add-on.
v2.4: IN-GAME MENU. A "Skill Saver" panel inside the game's menu (file SkillSaverUI_1001_P.pak in
      OakGame/Content/Paks). The panel is HTML/JS in the game's own UI engine (Coherent Gameface) and
      talks to this mod over 127.0.0.1:19417 (ingame.py). The HTTP thread never touches Unreal objects:
      commands are queued and run here on the game thread. Second tick hook on the UI widget tick,
      because the camera tick may stop while a menu pauses the game.
      Panel actions: save new (automatic name), overwrite, load, undo load, reset tree, delete
      (deleted builds are moved to sdk_mods/SkillSaver_trash). The desktop app keeps working as before.
v2.5-v3.13: research into equipping gear without the inventory menu (equip tests, menu switching,
      copies via Matt's native insertion, function lists, native code dumps). Kept out of the release.
v4.0: LOAD EQUIPS THE GEAR (gear.py). The items of the build are moved from the backpack into the equip
      slots with the game's own internal "container -> equip slot" function (found in EquipItem's native
      code): no menu, no copies, nothing created or deleted. The old items go back to the backpack.
      Build-gated by code hashes - after a game update gear equipping switches itself off, skills keep
      working. Works for the in-game panel, the desktop app and "Undo last load". No other mod needed.
      In-game panel: Rename. The game does not pass keys to its menu, so ONLY while the rename field is open
      kbd.py reads the keyboard for that field (see kbd.py / KEYBOARD.md; option "Keyboard typing in Rename"
      switches it off - the on-screen keyboard always works).
Files: sdk_mods/SkillSaver_<id>.json (one file per saved build)

How it works
  Save: reads every skill tree (GbxProgressGraph on pawn.GbxProgressionManager.ProgressGraphs):
        points per node (ProgressPointsSpent) for point trees, activated nodes for the action skill /
        augment / capstone / specialization skill trees.
  Load: 1) reset like Respec Anywhere: Server_ResetSpentPoints on every point tree +
           ServerResetProgressState('CharacterProgressPoints'), Server_ResetActivations on the
           activation trees that are restored
        2) re-apply in the game's own tree order (action skill first, trunk before branches, nodes in
           index order): Server_ActivateNodeInGroup / Server_SpendProgressPoints
        Every call is checked against the tree state afterwards; the result goes to
        sdk_mods/SkillSaver_log.txt.

Confirmed signatures (2026-10-07, first test: 24/24 entries restored):
  Server_SpendProgressPoints(InNodeIndex: int, InPoints: int)
  Server_ActivateNodeInGroup(InGroupIndex: int, InNodeIndex: int, InActivate: bool, ActivationLevel: int)
  Server_ResetActivations()
The mod still reads the signatures at runtime and fills them by name, so a game patch that renames a
parameter is reported in SkillSaver_signatures.txt (only written when something fails).
Bonus points from gear are not saved (they come from the gear itself).
Only works as host / in single player.

v1.1 - desktop app bridge (Encore Teleport app v5.0, "Skills" page):
  SkillSaver_status.json   written ~1x/s: version, time, character, points spent, last message
  SkillSaver_command.json  written by the app: {"id", "action": save|load|reset, "slot", "name"}
  Every save is one file SkillSaver_<id>.json (old K/L saves "slot1".."slot5" keep working in the
  app). The app renames / deletes save files itself.
  "reset" = reset the skill tree like Respec Anywhere (points only, choices stay).
"""

import ctypes
import importlib
import json
import pkgutil
import re
import sys
import time
from pathlib import Path

import unrealsdk
from mods_base import BoolOption, build_mod, get_pc, hook

from . import ingame

VERSION = "4.0"
TAG = "[BuildSaver]"
POOL = "CharacterProgressPoints"
SKILL_GRAPHS = ("progressgraph_specializations_skills",)   # activation trees outside the point pool
F_SPEND = "/Script/GbxGame.GbxProgressGraph:Server_SpendProgressPoints"
F_ACTIVATE = "/Script/GbxGame.GbxProgressGraph:Server_ActivateNodeInGroup"
F_RESET_ACT = "/Script/GbxGame.GbxProgressGraph:Server_ResetActivations"


# ---- in-game names (game tooltip data): graph name -> names by node index
NAMES = {
 "modifiers": {
  "Progress_Corpohacker_ActionSkill_Modifiers_Contagion": [
   "Recursion",
   "d://File",
   "Lag Switch",
   "Burst Finish",
   "Host Compromise",
   "replicat.exe",
   "fulminat.exe",
   "proliferat.exe"
  ],
  "Progress_Corpohacker_ActionSkill_Modifiers_VPN": [
   "Stack Overflow",
   "Bash Script",
   "sudo kill",
   "Swarm",
   "CTRL/ALT/DEL",
   "accelerat.exe",
   "synchroniz.exe",
   "engag.exe"
  ],
  "Progress_Corpohacker_ActionSkill_Modifiers_Manifestation": [
   "Solid State Destruction",
   "Intelligent Artifice",
   "Hard Crash",
   "Dark Web",
   "Giga Bite",
   "barrag.exe",
   "nuk.exe",
   "enrag.exe"
  ],
  "Progress_DarkSiren_ActionSkill_Modifiers_PhaseFamiliar": [
   "Violent Outburst",
   "Blink Strike",
   "Hexus Nexus",
   "Vorpal Fang",
   "Beast Mode",
   "Trouble Bubble",
   "Double Trouble",
   "Unsealed"
  ],
  "Progress_DarkSiren_ActionSkill_Modifiers_PhaseAvatar": [
   "Geistwave",
   "Energy Vampire",
   "Iron Maiden",
   "Witchy Trigger Finger",
   "Grave Harvest",
   "Desecration",
   "Vibe Check",
   "Heartpiercer"
  ],
  "Progress_DarkSiren_ActionSkill_Modifiers_PhaseShard": [
   "Ghast Blaster",
   "Coven",
   "Wither",
   "Banshee's Wail",
   "Hellish Harvest",
   "Heirloom",
   "Grim Reaper",
   "Dark Pact"
  ],
  "progress_graph_exo_mods_auto_lock": [
   "Unmissable Missiles",
   "Instinto",
   "Insta-Fort Battle System",
   "Bullet-Buddy Deluxe",
   "Hell in a Shell",
   "Double-Ought Autoshot",
   "Beam Team",
   "Volatile Hollowpoints"
  ],
  "progress_graph_exo_mods_heavy_arms": [
   "Acid Drop",
   "Dead Man Walking",
   "Thundercutter",
   "Altered Cabr\u00f3n",
   "Parting Gift",
   "Hurac\u00e1n Especial",
   "Inferno Protocol",
   "Galvanic Panic"
  ],
  "progress_graph_exo_mods_buster": [
   "Engorged Bore",
   "Gibistruct Module",
   "Ojo Rojo",
   "Battery Subscription Service",
   "Sangre por Sangre",
   "PROJECT: Gorgon",
   "PROJECT: Raiju",
   "PROJECT: Basilisk"
  ],
  "Progress_Paladin_ActionSkill_Modifiers_Scourge": [
   "Blastchill",
   "Cryonic Thrum",
   "Molten Rebuke",
   "Eternal Winter",
   "Stormlance",
   "Ring of Frostfire",
   "Glacial Rapture",
   "Wrathfall"
  ],
  "Progress_Paladin_ActionSkill_Modifiers_Warforge": [
   "Axe and Stone",
   "Endless War",
   "Hour of the Hammer",
   "Blade Tempest",
   "Searing Cold",
   "Snowmaul",
   "Storm Surge",
   "Conflangarang"
  ],
  "Progress_Paladin_ActionSkill_Modifiers_WeaponMaster": [
   "Pyroclast",
   "Thermal Diffusion",
   "Fellfrost",
   "Force of Nature",
   "Fulminating Fist",
   "Hoarcleave",
   "Molten Roil",
   "Stormcutter"
  ],
  "progress_robo_mods_cleromancy": [
   "Heavenly Sevens",
   "Five is Alive",
   "Three's Company",
   "Dirty Dozen",
   "Mighty Nine",
   "Commotion's Eleven",
   "Eights of Hel",
   "Easy Sixes"
  ],
  "progress_robo_mods_crossFire": [
   "And Hell Followed With Him",
   "Midnight Showdown",
   "Show Your Marrow",
   "Desperado",
   "Sawed-Off",
   "Slick Thunder",
   "Reckoning",
   "I Like Those Odds"
  ],
  "progress_robo_mods_sleightOfHand": [
   "Thunder the Table",
   "Cowboy",
   "Big Pull",
   "Bet on Red",
   "Sweeten the Pot",
   "The Cooler",
   "Dead Man's Hand",
   "Furious Fingers"
  ]
 },
 "actionskills": {
  "Progress_Corpohacker_ActionSkills": [
   "Plague Star",
   "Visual Paradox Nexus",
   "Malignant Construct"
  ],
  "Progress_DarkSiren_ActionSkills": [
   "Phase Phamiliar",
   "Incarnate",
   "Dead Ringer"
  ],
  "progress_graph_exo_action_skills": [
   "Peacebreaker Cannons",
   "Arc-Knives",
   "APOPHIS Lance"
  ],
  "progress_graph_grav_action_skills": [
   "Zero-Point",
   "CHROMA Accelerator",
   "Flux Generator"
  ],
  "Progress_Paladin_ActionSkills": [
   "Scourge",
   "Crucible",
   "Onslaughter"
  ],
  "progress_robo_action_skills": [
   "Cleromancy",
   "Cross-Fire",
   "Sleight of Hand"
  ]
 },
 "spec": {
  "Survivor_1": "Sturdy Stuff",
  "Survivor_2": "Bullets Are Scared Of Me",
  "Survivor_3": "The Best Defense",
  "Artificer_1": "Tripwire",
  "Artificer_2": "Full Spectrum Arsenal",
  "Artificer_3": "Fragmentation Payload",
  "Enforcer_1": "Lead or Alive",
  "Enforcer_2": "CQC",
  "Enforcer_3": "Riddle You This",
  "Slayer_1": "Contamination",
  "Slayer_2": "Compounding Afflictions",
  "Slayer_3": "Overkill",
  "Hunter_1": "Down But Not Out",
  "Hunter_2": "In The Zone",
  "Hunter_3": "One Shot, One Kill",
  "Adventurer_1": "Now With Caffeine",
  "Adventurer_2": "I Am A Gun",
  "Adventurer_3": "A Honed Mind",
  "Wanderer_1": "Bear Arms",
  "Wanderer_2": "Bullet Train",
  "Wanderer_3": "Groundbreaker"
 },
 "spec_trees": {
  "Survivor": "Survivor",
  "Artificer": "Gadgeteer",
  "Enforcer": "Brute",
  "Slayer": "Killer",
  "Hunter": "Sharpshooter",
  "Adventurer": "Daredevil",
  "Wanderer": "Runner"
 },
 "mods_by_as": {
  "Progress_Corpohacker_ActionSkills": [
   "Progress_Corpohacker_ActionSkill_Modifiers_Contagion",
   "Progress_Corpohacker_ActionSkill_Modifiers_VPN",
   "Progress_Corpohacker_ActionSkill_Modifiers_Manifestation"
  ],
  "Progress_DarkSiren_ActionSkills": [
   "Progress_DarkSiren_ActionSkill_Modifiers_PhaseFamiliar",
   "Progress_DarkSiren_ActionSkill_Modifiers_PhaseAvatar",
   "Progress_DarkSiren_ActionSkill_Modifiers_PhaseShard"
  ],
  "progress_graph_exo_action_skills": [
   "progress_graph_exo_mods_auto_lock",
   "progress_graph_exo_mods_heavy_arms",
   "progress_graph_exo_mods_buster"
  ],
  "Progress_Paladin_ActionSkills": [
   "Progress_Paladin_ActionSkill_Modifiers_Scourge",
   "Progress_Paladin_ActionSkill_Modifiers_Warforge",
   "Progress_Paladin_ActionSkill_Modifiers_WeaponMaster"
  ],
  "progress_robo_action_skills": [
   "progress_robo_mods_cleromancy",
   "progress_robo_mods_crossFire",
   "progress_robo_mods_sleightOfHand"
  ]
 }
}



_report: list = []


REPORT_MAX = 400          # in-memory log lines kept for SkillSaver_log.txt
_errors_seen: set = set()


def log(msg: str) -> None:
    print(f"{TAG} {msg}")
    _report.append(msg)
    if len(_report) > REPORT_MAX:
        del _report[: len(_report) - REPORT_MAX]


_SDK_MODS: list = []


def _sdk_mods():
    if not _SDK_MODS:                               # looked up once
        _SDK_MODS.append(next((p for p in Path(__file__).parents if p.name.lower() == "sdk_mods"), None))
    return _SDK_MODS[0]


def _slot_file(slot: str | None = None) -> Path | None:
    d = _sdk_mods()
    slot = "".join(ch for ch in str(slot) if ch.isalnum() or ch in "_-")[:40] or "slot1"
    return None if d is None else d / f"SkillSaver_{slot}.json"


_state = {"msg": "", "cmd": 0, "tick": 0.0, "poll": 0.0, "status": 0.0, "gear": 0.0}


def _say(msg: str) -> None:
    log(msg)
    _state["msg"] = msg


def _write_text(name: str, lines: list) -> None:
    d = _sdk_mods()
    if d is not None:
        (d / name).write_text(f"Build Saver v{VERSION}  {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n" + "\n".join(lines),
                              encoding="utf-8")


# ---------------------------------------------------------------- tree access
def _progression():
    try:
        pawn = get_pc().K2_GetPawn()
        pm = pawn.GbxProgressionManager
        return pawn, pm, pm.DataMgr
    except Exception:  # noqa: BLE001
        return None, None, None


_GRAPH_INFO: dict = {}   # graph object name -> (name, kind, pool); a graph never changes its definition


def _graph_info(g) -> tuple:
    """(name, kind 'points'/'activation', pool name) - cached per graph object."""
    key = str(g.Name)
    hit = _GRAPH_INFO.get(key)
    if hit is not None:
        return hit
    info = _graph_info_uncached(g)
    if len(_GRAPH_INFO) > 2000:     # new objects after every map change - keep the cache small
        _GRAPH_INFO.clear()
    _GRAPH_INFO[key] = info
    return info


def _graph_info_uncached(g) -> tuple:
    d = repr(g.ProgressGraphDef)
    name = d.split("'")[1] if "'" in d else str(g.Name)
    kind = "activation" if "GroupNodeActivation" in d[:400] else "points"
    pool = ""
    marker = "PointPool: FGbxDefPtr('"
    if marker in d[:2000]:
        pool = d.split(marker, 1)[1].split("'", 1)[0]
    return name, kind, pool


def _wanted(name: str, kind: str, pool: str) -> bool:
    return pool == POOL or name.lower() in SKILL_GRAPHS


# ---------------------------------------------------------------- signatures
def _props(obj) -> list:
    it = getattr(obj, "_properties", None) or getattr(obj, "_fields")
    return list(it())


def _signature(path: str) -> list:
    """[{name, type, out, struct, fields}] for every parameter except the return value."""
    fn = unrealsdk.find_object("Function", path)
    sig = []
    for p in _props(fn):
        name = str(p.Name)
        if name == "ReturnValue":
            continue
        ptype = type(p).__name__
        flags = 0
        try:
            flags = int(p.PropertyFlags)
        except Exception:  # noqa: BLE001
            pass
        entry = {"name": name, "type": ptype, "out": bool(flags & 0x100) and not bool(flags & 0x8000000),
                 "struct": None, "fields": []}
        if "Struct" in ptype:
            try:
                st = p.Struct
                entry["struct"] = str(st.Name)
                entry["fields"] = [(str(f.Name), type(f).__name__) for f in _props(st)]
            except Exception:  # noqa: BLE001
                pass
        sig.append(entry)
    return sig


def _dump_signatures(write: bool = False) -> dict:
    sigs, lines = {}, []
    for path in (F_SPEND, F_ACTIVATE, F_RESET_ACT):
        try:
            sigs[path] = _signature(path)
            lines.append(f"{path}")
            for e in sigs[path]:
                extra = f" struct {e['struct']} {e['fields']}" if e["struct"] else ""
                lines.append(f"    {e['name']}: {e['type']}{' (out)' if e['out'] else ''}{extra}")
        except Exception as ex:  # noqa: BLE001
            lines.append(f"{path}: not readable ({type(ex).__name__}: {ex})")
    if write:
        _write_text("SkillSaver_signatures.txt", lines)
    return sigs


def _guess(name: str, ptype: str, ctx: dict):
    n = name.lower()
    if "group" in n:
        return ctx.get("group", 0)
    if "node" in n or "index" in n or n in ("idx", "id"):
        return ctx["node"]
    if any(k in n for k in ("point", "amount", "count", "num", "level", "value", "rank")):
        return ctx.get("points", 1)
    if "Bool" in ptype:
        return True
    return None


def _build_kwargs(sig: list, ctx: dict) -> dict | None:
    kwargs = {}
    for e in sig:
        if e["out"]:
            continue
        if e["struct"]:
            fields = {}
            for fname, ftype in e["fields"]:
                v = _guess(fname, ftype, ctx)
                if v is not None:
                    fields[fname] = v
            if not fields:
                return None
            kwargs[e["name"]] = unrealsdk.make_struct(e["struct"], **fields)
            continue
        v = _guess(e["name"], e["type"], ctx)
        if v is None:
            return None
        kwargs[e["name"]] = v
    return kwargs


def _call(graph, path: str, sig: list, ctx: dict) -> str:
    fname = path.rsplit(":", 1)[1]
    kwargs = _build_kwargs(sig, ctx)
    if kwargs is None:
        return f"signature not supported: {[(e['name'], e['type']) for e in sig]}"
    try:
        getattr(graph, fname)(**kwargs)
        return "ok"
    except Exception as ex:  # noqa: BLE001
        return f"{type(ex).__name__}: {ex}"


# ---------------------------------------------------------------- gear + specialization (text only)
GEAR_SLOTS = ("Weapon 1", "Weapon 2", "Weapon 3", "Weapon 4", "Shield", "Ordnance", "Repkit",
              "Enhancement", "Class Mod")
MANUFACTURERS = {"TOR": "Torgue", "VLA": "Vladof", "JAK": "Jakobs", "MAL": "Maliwan", "DAD": "Daedalus",
                 "BOR": "Ripper", "ORD": "Order", "TED": "Tediore", "ATL": "Atlas", "COV": "CoV",
                 "HYP": "Hyperion"}
WEAPON_TYPES = {"PS": "Pistol", "SM": "SMG", "AR": "Assault Rifle", "SG": "Shotgun", "SR": "Sniper Rifle",
                "HW": "Heavy Weapon"}
KIND_BY_CLASS = {"shield": "Shield", "grenade": "Ordnance", "repairkit": "Repkit", "repkit": "Repkit",
                 "enhancement": "Enhancement", "classmod": "Class Mod", "heavy": "Heavy Weapon"}
ELEMENTS = (("incendiary", "Incendiary"), ("fire", "Incendiary"), ("shock", "Shock"), ("cryo", "Cryo"),
            ("corrosive", "Corrosive"), ("radiation", "Radiation"))
_SKIP_ATTRS = ("Outer", "Class", "Owner", "owner", "instigator", "OwningCharacter", "WeaponUser", "BodyOwner",
               "WeaponTargetLock", "AttachState", "PendingAttachState", "UberGraphFrame")
_NAME_SKIP = ("Name", "NetDriverName", "CurrentState")


# ---- item serial straight from memory (InventoryIdentity +0xA0 / +0xB0 / +0xC4)
SERIAL_PTR_OFFSET, SERIAL_LEN_OFFSET, ITEM_LEVEL_OFFSET = 0xA0, 0xB0, 0xC4


class _MBI(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", ctypes.c_ulong), ("PartitionId", ctypes.c_ushort),
                ("RegionSize", ctypes.c_size_t), ("State", ctypes.c_ulong), ("Protect", ctypes.c_ulong),
                ("Type", ctypes.c_ulong)]


def _readable(addr: int, size: int) -> bool:
    if addr < 0x10000 or addr > 0x00007FFFFFFFFFFF or size <= 0 or sys.platform != "win32":
        return False
    try:
        mbi = _MBI()
        if not ctypes.windll.kernel32.VirtualQuery(ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
            return False
        if int(mbi.State) != 0x1000 or int(mbi.Protect) & (0x01 | 0x100):   # committed, not NOACCESS/GUARD
            return False
        start = int(mbi.BaseAddress or 0)
        return start <= addr and addr + size <= start + int(mbi.RegionSize)
    except Exception:  # noqa: BLE001
        return False


def _peek(addr: int, size: int) -> bytes | None:
    return ctypes.string_at(addr, size) if _readable(addr, size) else None


def _u64(addr: int) -> int | None:
    raw = _peek(addr, 8)
    return int.from_bytes(raw, "little") if raw else None


def _serial_of_identity(identity) -> tuple:
    """('@U...', level) or ('', -1)"""
    try:
        base = int(identity._get_address())
    except Exception:  # noqa: BLE001
        return "", -1
    ptr, length = _u64(base + SERIAL_PTR_OFFSET), _u64(base + SERIAL_LEN_OFFSET)
    if not ptr or not length or length < 2 or length > 4096:
        return "", -1
    raw = _peek(ptr, int(length))
    if not raw:
        return "", -1
    serial = raw.split(b"\x00", 1)[0].decode("ascii", "replace")
    if not serial.startswith("@U"):
        return "", -1
    lvl = _peek(base + ITEM_LEVEL_OFFSET, 4)
    return serial, (int.from_bytes(lvl, "little") if lvl else -1)


def _equipped_serials() -> dict:
    """{equip slot: (serial, level)} from PlayerState.BackpackItems (equipped rows have EquipSlot >= 0)."""
    out = {}
    try:
        rows = list(get_pc().PlayerState.BackpackItems.items)
    except Exception:  # noqa: BLE001
        return out
    for row in rows:
        try:
            inv = row.InventoryItem
            slot = int(inv.EquipSlot)
            if 0 <= slot < 16 and slot not in out:
                serial, level = _serial_of_identity(inv.Item.data.Identity)
                if serial:
                    out[slot] = (serial, level)
        except Exception:  # noqa: BLE001
            continue
    return out


# ---- where the serial decoder / name data come from: Matt's mod, else the private _names folder
_NAME_PKGS = ("MattsSDKBoostingTools", __name__ + "._names")


def _names_module(mod: str):
    for pkg in _NAME_PKGS:
        try:
            return importlib.import_module(f"{pkg}.{mod}")
        except Exception:  # noqa: BLE001
            continue
    raise ImportError(mod)


def _names_data(fname: str) -> bytes:
    for pkg in _NAME_PKGS:
        try:
            blob = pkgutil.get_data(pkg, fname)
            if blob:
                return blob
        except Exception:  # noqa: BLE001
            continue
    raise FileNotFoundError(fname)


def _matt_names(serials: dict | None = None) -> dict:
    """{equip slot: entry} via Matt's SDK Boosting Tools if it is installed (display_name, rarity, ...)."""
    try:
        reader = importlib.import_module("MattsSDKBoostingTools.item_serial_reader")
    except Exception:  # noqa: BLE001
        reader = None
    if reader is None:                      # no Matt mod: decode the serials ourselves (private _names)
        try:
            meta = _names_module("serial_item_meta")
        except Exception:  # noqa: BLE001
            return {}
        out = {}
        for slot, (serial, level) in (serials or {}).items():
            try:
                e = {"serial": serial, "label": "", "level": level, "slot": slot}
                meta.enrich_entry(e)
                out[slot] = e
            except Exception:  # noqa: BLE001
                continue
        return out
    try:
        entries = reader.read_equipped_serials_for_player_state(get_pc().PlayerState, preserve_duplicates=True)
    except Exception as ex:  # noqa: BLE001
        log(f"Matt's item reader failed: {type(ex).__name__}: {ex}")
        return {}
    out = {}
    for e in entries or []:
        try:
            slot = int(e.get("slot", -1))
        except Exception:  # noqa: BLE001
            continue
        if slot >= 0 and slot not in out:
            out[slot] = e
    return out


# ---- real names from the Lootlemon catalog shipped with Matt's SDK Boosting Tools
_CAT = {"loaded": False, "types": {}}
_ITEM_TYPE_NAMES = {"classmod": "Class Mod", "repkit": "Repkit", "sniper": "Sniper Rifle"}


def _serial_sig(conv, serial: str):
    """(item type id, {main part ids}, {all part ids}) decoded with Matt's serial_converter."""
    human = conv.serial_to_human(serial)
    m = re.match(r"\s*(\d+)\s*,", human)
    if not m:
        return None
    body = human.split("||", 1)[1] if "||" in human else human
    main, allp = set(), set()
    for tok in re.findall(r"\{([^}]*)\}", body):
        if ":" in tok:
            grp, nums = tok.split(":", 1)
            for n in re.findall(r"\d+", nums):
                allp.add(f"{grp.strip()}:{n}")
        else:
            main.add(tok.strip())
            allp.add(tok.strip())
    return int(m.group(1)), main, allp


def _catalog():
    if _CAT["loaded"]:
        return _CAT["types"], _CAT.get("conv")
    _CAT["loaded"] = True
    try:
        conv = _names_module("serial_converter")
        blob = _names_data("MattsSDKBoostingTools_lootlemon_codes.json")
        entries = json.loads(blob.decode("utf-8", "replace")).get("entries", [])
    except Exception as ex:  # noqa: BLE001
        log(f"Item catalog not available ({type(ex).__name__}) - install Matt's SDK Boosting Tools for real names.")
        return {}, None
    types: dict = {}
    for e in entries:
        try:
            sig = _serial_sig(conv, str(e.get("serial") or ""))
        except Exception:  # noqa: BLE001
            continue
        if sig:
            types.setdefault(sig[0], []).append({"name": str(e.get("name") or ""), "rarity": str(e.get("rarity") or ""),
                                                 "main": sig[1], "all": sig[2]})
    _CAT["types"], _CAT["conv"] = types, conv
    log(f"Item catalog: {sum(len(v) for v in types.values())} named items.")
    return types, conv


def _catalog_name(serial: str) -> dict:
    types, conv = _catalog()
    if not types or not serial:
        return {}
    try:
        sig = _serial_sig(conv, serial)
    except Exception:  # noqa: BLE001
        return {}
    if not sig or sig[0] not in types:
        return {}
    _, main, allp = sig
    cands = types[sig[0]]
    freq: dict = {}
    for c in cands:
        for x in c["all"]:
            freq[x] = freq.get(x, 0) + 1
    best, best_key = None, (0, 0, 0)
    for c in cands:
        unique_hits = sum(1 for x in c["all"] if freq[x] == 1 and x in allp)
        exact_main = 1 if c["main"] == main else 0
        key = (unique_hits, exact_main, len(c["all"] & allp))
        if (unique_hits or exact_main) and key > best_key:
            best, best_key = c, key
    if best is None:
        return {}
    return {"name": best["name"], "rarity": best["rarity"], "match": "unique part" if best_key[0] else "same parts"}


_ELEMENT_PARTS = {"radiation": "Radiation", "fire": "Incendiary", "incendiary": "Incendiary", "shock": "Shock",
                  "cryo": "Cryo", "corrosive": "Corrosive"}


def _serial_extras(serial: str) -> dict:
    """{'firmware': 'Reel Big Fist', 'element': 'Radiation'} from the serial's parts. Main parts {n} are
    looked up in the item type's table, group parts {g:n} in table g (Matt's GZO part map)."""
    try:
        conv = _names_module("serial_converter")
        meta = _names_module("serial_item_meta")
        human = conv.serial_to_human(serial)
        index = meta._type_id_index()
    except Exception:  # noqa: BLE001
        return {}
    m = re.match(r"\s*(\d+)\s*,", human)
    if not m:
        return {}
    own = int(m.group(1))
    body = human.split("||", 1)[1] if "||" in human else human
    names = []
    for tok in re.findall(r"\{([^}]*)\}", body):
        grp, nums = (tok.split(":", 1) if ":" in tok else (str(own), tok))
        try:
            table = index.get(int(grp.strip()), ("", {}))[1]
        except ValueError:
            continue
        names += [table.get(n, "") for n in re.findall(r"\d+", nums)]
    out = {}
    for n in names:
        leaf = str(n or "").rsplit(".", 1)[-1].lower()
        f = re.match(r"part_firmware_(.+)", leaf)
        if f and "firmware" not in out:
            out["firmware"] = " ".join(w.capitalize() for w in f.group(1).split("_"))
        e = re.match(r"part_(radiation|fire|incendiary|shock|cryo|corrosive)(?:$|_)", leaf)
        if e and "element" not in out:
            out["element"] = _ELEMENT_PARTS[e.group(1)]
    return out

def _matt_label(e: dict) -> str:
    name = str(e.get("display_name") or "").strip()
    rarity = str(e.get("rarity") or "").strip()
    manu = str(e.get("manufacturer") or "").strip()
    kind = str(e.get("item_type") or "").strip()
    dmg = str(e.get("damage_type") or "").strip()
    info = " ".join(x for x in (rarity, manu, kind) if x)
    if dmg and dmg.lower() not in ("none", "kinetic", "normal"):
        info = f"{info}, {dmg}" if info else dmg
    if not name:
        return info
    if not info or name.lower() == " ".join(x for x in (manu, kind) if x).lower():
        return " ".join(x for x in (rarity, name) if x) if name.lower() not in info.lower() else info
    return f"{name} ({info})"


def _paths_and_names(actor, debug: list) -> tuple:
    """Collects every /Game/... asset path and every string field with 'name'/'title' in it."""
    paths, names = [], []
    try:
        attrs = [a for a in dir(actor) if not a.startswith("_") and a not in _SKIP_ATTRS]
    except Exception:  # noqa: BLE001
        attrs = []
    for a in attrs:
        try:
            v = getattr(actor, a)
        except Exception:  # noqa: BLE001
            continue
        if callable(v) or v is None or isinstance(v, (bool, int, float)):
            continue
        if isinstance(v, str):
            low = a.lower()
            if v and v != "None" and a not in _NAME_SKIP and ("name" in low or "title" in low):
                debug.append(f"    text {a} = {v!r}")
                if any(k in low for k in ("display", "itemname", "uniquename", "title", "inventoryname")):
                    names.append(v)
            continue
        r = repr(v)
        found = re.findall(r"/Game/[A-Za-z0-9_/\.]+", r[:4000])
        if found:
            paths.extend(found)
            debug.append(f"    {a} = {r[:300]}")
    # mesh parts can carry unique part names
    try:
        for c in list(getattr(actor, "BlueprintCreatedComponents", []) or [])[:6]:
            for a in ("SkeletalMesh", "SkeletalMeshAsset", "StaticMesh"):
                try:
                    m = getattr(c, a)
                except Exception:  # noqa: BLE001
                    continue
                if m is not None:
                    paths.extend(re.findall(r"/Game/[A-Za-z0-9_/\.]+", repr(m)))
                    debug.append(f"    {c.Name}.{a} = {repr(m)[:200]}")
    except Exception:  # noqa: BLE001
        pass
    return paths, names


def _describe(actor, slot_label: str, debug: list) -> str:
    cls = str(actor.Class.Name)
    debug.append(f"  [{slot_label}] {cls}  {actor.Name}")
    paths, names = _paths_and_names(actor, debug)
    blob = " ".join(paths)
    manu, wtype = "", ""
    m = re.search(r"Body_([A-Z]{3})_([A-Z]{2})\b", blob)
    if m:
        manu, wtype = MANUFACTURERS.get(m.group(1), m.group(1)), WEAPON_TYPES.get(m.group(2), m.group(2))
    else:
        for code, full in MANUFACTURERS.items():
            if re.search(rf"[/_]{code}[/_]", blob):
                manu = full
                break
    low = blob.lower()
    rarity = ""
    if "pearlescent" in low or "/pearl" in low:
        rarity = "Pearlescent"
    elif "_leg_" in low or "legendary" in low:
        rarity = "Legendary"
    else:
        for r in ("Epic", "Rare", "Uncommon", "Common"):
            if f"_{r.lower()}" in low or f"/{r.lower()}" in low:
                rarity = r
                break
    kind = wtype
    if not kind:
        lc = cls.lower()
        kind = next((v for k, v in KIND_BY_CLASS.items() if k in lc), "") or slot_label
    element = ""
    scripts = " ".join(p for p in paths if "script" in p.lower()).lower()
    for key, label in ELEMENTS:
        if key in scripts:
            element = label
            break
    desc = " ".join(x for x in (rarity, manu, kind) if x)
    extra = [element] if element else []
    m = re.search(r"InvScript_([A-Za-z0-9]+)", blob)          # e.g. shield InvScript_Angel
    if m:
        extra.insert(0, re.sub(r"(?<=[a-z])(?=[A-Z])", " ", m.group(1)))
    try:                                                      # class mod: skill it attaches to the character
        for sk in list(getattr(actor, "AttachedSkills", []) or [])[:2]:
            for sc in list(sk.SkillScripts or [])[:2]:
                if sc is not None:
                    debug.append(f"    attached skill script = {sc.Class.Name}")
    except Exception:  # noqa: BLE001
        pass
    if extra:
        desc += f" ({', '.join(extra)})"
    real = next((n for n in names if len(n) > 2), "")
    debug.append(f"    -> {real + ' - ' if real else ''}{desc}")
    return f"{real} - {desc}" if real else desc


def _capture_gear(pawn) -> list:
    gear, debug = [], []
    try:
        items = list(pawn.EquippedInventorySlots.items)
    except Exception as ex:  # noqa: BLE001
        log(f"Gear not readable: {type(ex).__name__}: {ex}")
        return gear
    serials = {}
    try:
        serials = _equipped_serials()
    except Exception as ex:  # noqa: BLE001
        debug.append(f"serial read failed: {type(ex).__name__}: {ex}")
    matt = _matt_names(serials)
    debug.append(f"serials read: {len(serials)}   Matt's SDK Boosting Tools names: "
                 f"{len(matt) if matt else 'not installed / none'}")
    for i, label in enumerate(GEAR_SLOTS):
        if i >= len(items):
            break
        actor = items[i].InstancedInventory
        if actor is None:
            gear.append({"slot": label, "auto": "", "name": ""})
            continue
        try:
            auto = _describe(actor, label, debug)
        except Exception as ex:  # noqa: BLE001
            auto = "(not readable)"
            debug.append(f"  [{label}] error {type(ex).__name__}: {ex}")
        entry = {"slot": label, "auto": auto, "name": ""}
        serial, level = serials.get(i, ("", -1))
        if i in matt:
            e = matt[i]
            entry["auto"] = _matt_label(e) or auto
            entry["source"] = "msbt"
            serial = serial or str(e.get("serial") or "")
            if level < 0:
                try:
                    level = int(e.get("level", -1))
                except Exception:  # noqa: BLE001
                    level = -1
            debug.append(f"    Matt: {e.get('display_name')!r} rarity={e.get('rarity')!r} "
                         f"source={e.get('meta_source')!r}")
        if i in matt:
            e = matt[i]
            nm = str(e.get("display_name") or "").strip()
            manu, kind = str(e.get("manufacturer") or ""), str(e.get("item_type") or "")
            if nm.lower() in ("", " ".join(x for x in (manu, kind) if x).lower()):   # no real name
                kind = _ITEM_TYPE_NAMES.get(kind.lower(), kind) or label
                entry["title"] = " ".join(x for x in (str(e.get("rarity") or ""), manu, kind) if x)
            else:
                entry["title"] = nm
            dmg = str(e.get("damage_type") or "")
            if dmg and dmg.lower() not in ("none", "kinetic", "normal"):
                entry["element"] = dmg
        hit = _catalog_name(serial) if serial else {}
        if hit:
            e = matt.get(i, {})
            rarity = hit["rarity"] or str(e.get("rarity") or "")
            manu = str(e.get("manufacturer") or "")
            kind = str(e.get("item_type") or "")
            kind = _ITEM_TYPE_NAMES.get(kind.lower(), kind)
            dmg = str(e.get("damage_type") or "")
            info = " ".join(x for x in (rarity, manu, kind) if x)
            if dmg and dmg.lower() not in ("none", "kinetic", "normal"):
                info = f"{info}, {dmg}" if info else dmg
            entry["auto"] = f"{hit['name']} ({info})" if info else hit["name"]
            entry["title"] = hit["name"]
            if dmg and dmg.lower() not in ("none", "kinetic", "normal"):
                entry["element"] = dmg
            entry["source"] = "catalog"
            debug.append(f"    catalog: {hit['name']!r} ({hit['match']})")
        if not entry.get("title"):
            entry["title"] = auto
        if serial:
            ex = _serial_extras(serial)
            if ex.get("element") and not entry.get("element"):
                entry["element"] = ex["element"]
            if ex.get("element") and ex["element"].lower() not in entry["auto"].lower():
                entry["auto"] = entry["auto"][:-1] + f", {ex['element']})" if entry["auto"].endswith(")") \
                    else f"{entry['auto']} ({ex['element']})"
            if ex.get("firmware"):
                entry["firmware"] = ex["firmware"]
                entry["auto"] += f" - Firmware: {ex['firmware']}"
                debug.append(f"    firmware: {ex['firmware']}")
            entry["serial"] = serial
        if level >= 0:
            entry["level"] = level
        debug.append(f"    serial: {serial or '-'}  level {level}")
        gear.append(entry)
    _write_text("SkillSaver_gear_debug.txt", debug)
    return gear


def _capture_specialization(pawn) -> list:
    """Equipped specialization skills = GbxSkill objects on the pawn with a
    SkillScript_Specializations_<Tree>_Skill_<N> script (the *_Base scripts are always there)."""
    spec = []
    try:
        pawn_path = pawn._path_name()
    except Exception:  # noqa: BLE001
        pawn_path = str(pawn.Name)
    for sk in unrealsdk.find_all("GbxSkill", False):
        try:
            outer = sk.Outer
            if outer is None or (outer._path_name() if hasattr(outer, "_path_name") else str(outer.Name)) != pawn_path:
                continue
            for script in list(sk.SkillScripts):
                if script is None:
                    continue
                cname = str(script.Class.Name)
                m = re.match(r"SkillScript_Specializations_([A-Za-z]+)_Skill_(\d+)", cname)
                if not m:
                    continue
                tree, num = m.group(1), int(m.group(2))
                hint = ""
                for a in dir(script):
                    if a.endswith("_Handle"):
                        try:
                            row = str(getattr(script, a).RowName)
                        except Exception:  # noqa: BLE001
                            continue
                        row = re.sub(rf"^Specializations_{tree}_", "", row)
                        row = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", row).replace("_", " ").strip()
                        if row and row != "None":
                            hint = row
                            break
                spec.append({"tree": NAMES["spec_trees"].get(tree, tree), "skill": num, "hint": hint,
                             "name": NAMES["spec"].get(f"{tree}_{num}", ""), "id": f"{tree}_{num}"})
        except Exception:  # noqa: BLE001
            continue
    spec.sort(key=lambda e: (e["tree"], e["skill"]))
    return spec


def _graph_names(graph_name: str) -> list:
    low = graph_name.lower()
    for table in (NAMES["modifiers"], NAMES["actionskills"]):
        for k, v in table.items():
            if k.lower() == low:
                return v
    return []


def _loadout(graphs: list) -> dict:
    """{'action_skill', 'augments', 'capstones'} named from the saved activation graphs.
    Only the modifier graph that belongs to the equipped action skill counts."""
    out = {"action_skill": "", "augments": [], "capstones": []}
    by_name = {g["name"].lower(): g for g in graphs if g["kind"] == "activation"}
    for as_graph, mod_graphs in NAMES["mods_by_as"].items():
        g = by_name.get(as_graph.lower())
        if not g:
            continue
        as_names = NAMES["actionskills"][as_graph]
        for n in g["nodes"]:
            i = n["i"]
            if i < len(as_names):
                out["action_skill"] = as_names[i]
                if i < len(mod_graphs):
                    mg = by_name.get(mod_graphs[i].lower())
                    mod_names = NAMES["modifiers"].get(mod_graphs[i], [])
                    for m in (mg or {}).get("nodes", []):
                        j = m["i"]
                        if j < len(mod_names):
                            (out["augments"] if j < 5 else out["capstones"]).append(mod_names[j])
    return out

def _act_level(graph_name: str, node: dict) -> int:
    """ActivationLevel to send: the slot (1-3) for specialization skills, 0 for everything else
    (action skill, augment, capstone - the game itself stores 0 there)."""
    if "specialization" in graph_name.lower():
        return int(node.get("lvl", 0))
    return 0


# ---- character from the skill tree names
_CHAR_KEYS = (("corpohacker", "corpohacker"), ("darksiren", "darksiren"), ("_exo_", "exosoldier"),
              ("exosoldier", "exosoldier"), ("_grav_", "gravitar"), ("gravitar", "gravitar"),
              ("paladin", "paladin"), ("_robo_", "robodealer"), ("robodealer", "robodealer"))


def _char_key(graph_names) -> str:
    for n in graph_names:
        low = str(n).lower()
        if "actionskill" not in low.replace("_", "") and "action_skill" not in low and "_mods_" not in low:
            continue
        for needle, key in _CHAR_KEYS:
            if needle in low:
                return key
    return ""


def _live_char_key(pm) -> str:
    names = []
    for g in pm.ProgressGraphs:
        if g is not None:
            try:
                names.append(_graph_info(g)[0])
            except Exception:  # noqa: BLE001
                pass
    return _char_key(names)


def _saved_char_key(data: dict) -> str:
    c = str(data.get("character") or "").lower()
    for _needle, key in _CHAR_KEYS:
        if key in c:
            return key
    return _char_key(g.get("name", "") for g in data.get("graphs", []))


# ---------------------------------------------------------------- save
def _capture():
    pawn, pm, _ = _progression()
    if pm is None:
        return None
    graphs = []
    for g in pm.ProgressGraphs:
        if g is None:
            continue
        try:
            name, kind, pool = _graph_info(g)
            if not _wanted(name, kind, pool):
                continue
            nodes = []
            for i, n in enumerate(g.nodes):
                spent, act, lvl = int(n.ProgressPointsSpent), bool(n.bIsActivated), int(n.ActivationLevel)
                if (kind == "points" and spent > 0) or (kind == "activation" and act):
                    nodes.append({"i": i, "spent": spent, "act": act, "lvl": lvl})
            graphs.append({"name": name, "kind": kind, "pool": pool, "groups": len(g.Groups), "nodes": nodes})
        except Exception as ex:  # noqa: BLE001
            log(f"Could not read a tree: {type(ex).__name__}: {ex}")
    points = sum(n["spent"] for g in graphs if g["kind"] == "points" for n in g["nodes"])
    choices = sum(len(g["nodes"]) for g in graphs if g["kind"] == "activation")
    try:
        spec = _capture_specialization(pawn)
    except Exception as ex:  # noqa: BLE001
        spec = []
        log(f"Specialization not readable: {type(ex).__name__}: {ex}")
    return {"mod": "SkillSaver", "version": 1, "saved": time.strftime("%Y-%m-%d %H:%M:%S"),
            "character": _char_key(g["name"] for g in graphs) or str(pawn.Class.Name), "points": points, "choices": choices, "graphs": graphs,
            "gear": _capture_gear(pawn), "spec": spec, "loadout": _loadout(graphs)}


def _save_slot(slot: str | None = None, name: str = "") -> None:
    _report.clear()
    data = _capture()
    if data is None:
        _say("No character - load into the game first.")
        return
    f = _slot_file(slot)
    if f is None:
        _say("sdk_mods folder not found.")
        return
    old_name, old = "", {}
    if f.exists():
        try:
            old = json.loads(f.read_text(encoding="utf-8-sig"))
            old_name = old.get("name", "")
        except Exception:  # noqa: BLE001
            pass
    # names typed in the app stay as long as the same kind of item sits in that slot
    old_gear = {g.get("slot"): g for g in old.get("gear", []) if isinstance(g, dict)}
    for g in data["gear"]:
        prev = old_gear.get(g["slot"])
        if prev and prev.get("name") and prev.get("auto") == g["auto"]:
            g["name"] = prev["name"]
    if old.get("notes"):
        data["notes"] = old["notes"]
    data["name"] = name or old_name or _default_name(data)
    f.write_text(json.dumps(data, indent=1), encoding="utf-8")
    gear_n = sum(1 for g in data["gear"] if g["auto"])
    _say(f"Saved '{data['name']}': {data['points']} skill points, {data['choices']} choices, "
         f"{gear_n} gear items, {len(data['spec'])} specialization skills.")


def _default_name(data: dict) -> str:
    skill = (data.get("loadout") or {}).get("action_skill") or "Build"
    return f"{skill} {time.strftime('%m-%d %H:%M')}"


def _rename_slot(slot: str, name: str) -> None:
    f = _slot_file(slot)
    if f is None or not f.exists():
        _say(f"Save '{slot}' not found.")
        return
    if not name:
        _say("Rename: the new name is empty.")
        return
    data = json.loads(f.read_text(encoding="utf-8-sig"))
    data["name"] = name
    f.write_text(json.dumps(data, indent=1), encoding="utf-8")
    _say(f"Renamed to '{name}'.")


def _delete_slot(slot: str) -> None:
    """Moves the save into sdk_mods/SkillSaver_trash (the app only lists sdk_mods itself)."""
    f = _slot_file(slot)
    if f is None or not f.exists():
        _say(f"Save '{slot}' not found.")
        return
    try:
        name = json.loads(f.read_text(encoding="utf-8-sig")).get("name", slot)
    except Exception:  # noqa: BLE001
        name = slot
    trash = f.parent / "SkillSaver_trash"
    trash.mkdir(exist_ok=True)
    target = trash / f.name
    if target.exists():
        target = trash / f"{f.stem}_{time.strftime('%Y%m%d_%H%M%S')}.json"
    f.replace(target)
    _say(f"Deleted '{name}' (moved to SkillSaver_trash).")


def _reset_tree() -> None:
    _, pm, dm = _progression()
    if pm is None:
        _say("No character - load into the game first.")
        return
    trees = 0
    for g in pm.ProgressGraphs:
        if g is None:
            continue
        name, kind, pool = _graph_info(g)
        if kind == "points" and pool == POOL:
            try:
                g.Server_ResetSpentPoints()
                trees += 1
            except Exception as ex:  # noqa: BLE001
                log(f"Reset failed on {name}: {ex}")
    try:
        dm.ServerResetProgressState(POOL)
    except Exception as ex:  # noqa: BLE001
        _say(f"Point pool reset failed: {ex}")
        return
    _say(f"Skill tree reset ({trees} trees) - spend the points again in the skill menu.")


# ---------------------------------------------------------------- load
def _load_slot(slot: str | None = None) -> None:
    _report.clear()
    f = _slot_file(slot)
    if f is None or not f.exists():
        _say(f"Save '{slot}' not found.")
        return
    data = json.loads(f.read_text(encoding="utf-8-sig"))
    pawn, pm, dm = _progression()
    if pm is None:
        _say("No character - load into the game first.")
        return
    want, have = _saved_char_key(data), _live_char_key(pm)
    if want and have and want != have:
        _say(f"Save belongs to {want}, current character is {have} - not loaded.")
        return
    try:                                            # undo point: the setup before this load
        before = _capture()
        if before is not None:
            before["name"] = f"Before last load ({time.strftime('%H:%M')})"
            before["undo_of"] = data.get("name", slot)
            uf = _slot_file("undo")
            if uf is not None:
                uf.write_text(json.dumps(before, indent=1), encoding="utf-8")
    except Exception as ex:  # noqa: BLE001
        log(f"Undo point not written: {type(ex).__name__}: {ex}")

    sigs = _dump_signatures()
    live = {}
    for g in pm.ProgressGraphs:
        if g is not None:
            try:
                live[_graph_info(g)[0]] = g
            except Exception:  # noqa: BLE001
                pass

    # 1) reset
    for g in pm.ProgressGraphs:
        if g is None:
            continue
        name, kind, pool = _graph_info(g)
        if kind == "points" and pool == POOL:
            try:
                g.Server_ResetSpentPoints()
            except Exception as ex:  # noqa: BLE001
                log(f"Reset failed on {name}: {ex}")
    try:
        dm.ServerResetProgressState(POOL)
    except Exception as ex:  # noqa: BLE001
        log(f"Point pool reset failed: {ex}")
    for sg in data["graphs"]:
        if sg["kind"] == "activation" and sg["name"] in live:
            try:
                live[sg["name"]].Server_ResetActivations()
            except Exception as ex:  # noqa: BLE001
                log(f"Reset of choices failed on {sg['name']}: {ex}")

    # 2) re-apply. Order: action skill (+ other choices that need no points) -> all skill points ->
    #    augments / capstones (they unlock through points in the trunk / branches) -> retry failures.
    def is_mod(sg):
        n = sg["name"].lower()
        return sg["kind"] == "activation" and ("modifier" in n or "_mods_" in n)

    def activate(sg, g, node) -> tuple:
        i, res = node["i"], ""
        groups = list(range(max(1, sg.get("groups", 1))))
        if is_mod(sg) and len(groups) >= 2:            # template: group 0 = augments 1-5, group 1 = capstones
            first = 0 if i < 5 else 1
            groups = [first] + [x for x in groups if x != first]
        for grp in groups:
            res = _call(g, F_ACTIVATE, sigs.get(F_ACTIVATE, []),
                        {"node": i, "group": grp, "points": _act_level(sg["name"], node)})
            try:
                if bool(g.nodes[i].bIsActivated):
                    return True, res
            except Exception:  # noqa: BLE001
                pass
        return False, res

    def spend(g, node) -> tuple:
        i, want = node["i"], node["spent"]
        res = _call(g, F_SPEND, sigs.get(F_SPEND, []), {"node": i, "points": want})
        have = int(g.nodes[i].ProgressPointsSpent)
        while have < want and res == "ok":          # function may spend one point per call
            res = _call(g, F_SPEND, sigs.get(F_SPEND, []), {"node": i, "points": 1})
            new = int(g.nodes[i].ProgressPointsSpent)
            if new == have:
                break
            have = new
        return have >= want, f"{have}/{want} points ({res})"

    passes = ([sg for sg in data["graphs"] if sg["kind"] == "activation" and not is_mod(sg)],
              [sg for sg in data["graphs"] if sg["kind"] != "activation"],
              [sg for sg in data["graphs"] if is_mod(sg)])
    ok, todo = 0, []
    for group in passes:
        for sg in group:
            g = live.get(sg["name"])
            if g is None:
                log(f"Tree {sg['name']} not found on this character - skipped.")
                continue
            for node in sg["nodes"]:
                done, res = activate(sg, g, node) if sg["kind"] == "activation" else spend(g, node)
                if done:
                    ok += 1
                else:
                    todo.append((sg, g, node, res))
    failed, other, skipped = 0, 0, set()
    for sg, g, node, _res in todo:                  # second chance (unlocks that came later)
        done, res = activate(sg, g, node) if sg["kind"] == "activation" else spend(g, node)
        if done:
            ok += 1
        elif is_mod(sg) and res == "ok":
            # the game keeps augment / capstone choices of every action skill; those of the action skills
            # that are not equipped cannot be activated - expected, not an error
            other += 1
            skipped.add((sg["name"], node["i"]))
            log(f"{sg['name']} node {node['i']}: belongs to an action skill that is not equipped - skipped.")
        else:
            failed += 1
            log(f"{sg['name']} node {node['i']}: not applied ({res})")
    # final check: something activated early may have been switched off again while locked
    for sg in data["graphs"]:
        g = live.get(sg["name"])
        if g is None or sg["kind"] != "activation":
            continue
        for node in sg["nodes"]:
            if (sg["name"], node["i"]) in skipped:
                continue
            try:
                if not bool(g.nodes[node["i"]].bIsActivated):
                    done, res = activate(sg, g, node)
                    log(f"{sg['name']} node {node['i']}: was off again - re-activated: {done}")
            except Exception:  # noqa: BLE001
                pass
    lo = data.get("loadout") or {}
    if lo.get("augments") or lo.get("capstones"):
        log(f"Augment: {', '.join(lo.get('augments') or ['-'])}   Capstone: {', '.join(lo.get('capstones') or ['-'])}")
    loaded = (f"Loaded '{data.get('name', slot)}': {ok} entries applied"
              + (f", {failed} failed - see SkillSaver_log.txt." if failed else "."))

    try:
        from . import gear as _gear
        gear_msg = _gear.equip(data, _serial_of_identity, log)
    except Exception as ex:  # noqa: BLE001
        gear_msg = f"Gear failed: {type(ex).__name__}: {ex}"
        log(gear_msg)
    _say(loaded + (f" {gear_msg}" if gear_msg else ""))
    _write_text("SkillSaver_log.txt", _report)
    if failed:
        _dump_signatures(write=True)


# ---------------------------------------------------------------- desktop app bridge
def _write_json(name: str, data: dict) -> None:
    d = _sdk_mods()
    if d is None:
        return
    tmp = d / (name + ".tmp")
    tmp.write_text(json.dumps(data), encoding="utf-8")
    tmp.replace(d / name)


def _write_status() -> None:
    st = {"version": VERSION, "time": time.time(), "msg": _state["msg"], "cmd": _state["cmd"]}
    try:
        pawn, pm, _ = _progression()
        if pm is not None:
            st["character"] = _live_char_key(pm) or str(pawn.Class.Name)
            spent = 0
            for g in pm.ProgressGraphs:
                if g is None:
                    continue
                name, kind, pool = _graph_info(g)
                if kind == "points" and pool == POOL:
                    spent += sum(int(n.ProgressPointsSpent) for n in g.nodes)
            st["points"] = spent
    except Exception:  # noqa: BLE001
        pass
    _write_json("SkillSaver_status.json", st)
    ingame.set_status(st)


def _app_watching() -> bool:
    """True while the desktop app shows the Skills page (it touches SkillSaver_app.json every few seconds)."""
    d = _sdk_mods()
    if d is None:
        return False
    try:
        return time.time() - (d / "SkillSaver_app.json").stat().st_mtime < 15.0
    except OSError:
        return False


def _write_gear_now() -> None:
    """Serials of equipped items (by slot) and of everything in the backpack, for the app's gear check."""
    try:
        rows = list(get_pc().PlayerState.BackpackItems.items)
    except Exception:  # noqa: BLE001
        return
    equipped, bag = {}, []
    for row in rows:
        try:
            inv = row.InventoryItem
            serial, _lvl = _serial_of_identity(inv.Item.data.Identity)
            if not serial:
                continue
            slot = int(inv.EquipSlot)
            if 0 <= slot < 16:
                equipped[str(slot)] = serial
            else:
                bag.append(serial)
        except Exception:  # noqa: BLE001
            continue
    _write_json("SkillSaver_gear_now.json", {"time": time.time(), "equipped": equipped, "backpack": bag})


def _poll_command() -> None:
    d = _sdk_mods()
    if d is None:
        return
    f = d / "SkillSaver_command.json"
    if not f.exists():
        return
    try:
        cmd = json.loads(f.read_text(encoding="utf-8-sig"))
    except Exception:  # noqa: BLE001
        return  # still being written
    try:
        f.unlink()
    except Exception:  # noqa: BLE001
        pass
    cid = int(cmd.get("id", 0))
    if cid <= _state["cmd"]:
        return
    _state["cmd"] = cid
    action, slot, name = cmd.get("action", ""), cmd.get("slot") or None, cmd.get("name", "")
    try:
        if action == "save":
            _save_slot(slot, name)
        elif action == "load":
            _load_slot(slot)
        elif action == "reset":
            _reset_tree()
        else:
            _say(f"Unknown app command: {action}")
    except Exception as ex:  # noqa: BLE001
        _say(f"{action} failed: {type(ex).__name__}: {ex}")
        _write_text("SkillSaver_log.txt", _report)


_FAIL_WORDS = ("failed", "not found", "not loaded", "No character", "empty", "not readable")


def _run_ui_command(cmd: dict) -> None:
    """One command from the in-game panel (queued by ingame.py, run here on the game thread)."""
    cid, action, slot, name = cmd["id"], cmd["action"], cmd["slot"], cmd["name"]
    _state["msg"] = ""
    try:
        if action == "save":
            slot = "s" + time.strftime("%Y%m%d_%H%M%S")
            n = 2
            while (_slot_file(slot) or Path("x")).exists():
                slot = "s" + time.strftime("%Y%m%d_%H%M%S") + f"_{n}"
                n += 1
            _save_slot(slot, name)
        elif action == "overwrite":
            f = _slot_file(slot)
            if f is None or not f.exists():
                _say(f"Save '{slot}' not found.")
            else:
                _save_slot(slot, "")                # keeps the saved name
        elif action == "load":
            _load_slot(slot)
        elif action == "undo":
            _load_slot("undo")
        elif action == "reset":
            _reset_tree()
        elif action == "rename":
            _rename_slot(slot, name)
        elif action == "delete":
            _delete_slot(slot)
        msg = _state["msg"] or "Done."
        # "Loaded 'x': 28 entries applied, 3 failed." is a successful load (single modifier nodes can be skipped)
        ok = msg.startswith("Loaded '") or not any(w in msg for w in _FAIL_WORDS)
        ingame.finish(cid, msg, ok)
    except Exception as ex:  # noqa: BLE001
        _say(f"{action} failed: {type(ex).__name__}: {ex}")
        _write_text("SkillSaver_log.txt", _report)
        ingame.finish(cid, _state["msg"], False)


@hook("/Script/Engine.CameraModifier:BlueprintModifyPostProcess")
def _frame_tick(obj, args, _r, _f):
    _tick()


@hook("/Script/GbxUIUMG.GbxUIUMGTickWidget:BP_TickWidget")
def _ui_tick(obj, args, _r, _f):
    _tick()


def _tick() -> None:
    now = time.monotonic()
    if now - _state["tick"] < 0.2:
        return
    _state["tick"] = now
    try:
        if now - _state["poll"] > 0.3:
            _state["poll"] = now
            _poll_command()
            for cmd in ingame.pop_commands():
                _run_ui_command(cmd)
        if now - _state["gear"] > 5.0:
            _state["gear"] = now
            if _app_watching() or ingame.watching():
                _write_gear_now()
        if now - _state["status"] > 1.0:
            _state["status"] = now
            _write_status()
    except Exception as ex:  # noqa: BLE001
        msg = f"App bridge error: {type(ex).__name__}: {ex}"
        if msg not in _errors_seen and len(_errors_seen) < 100:   # each distinct error once
            _errors_seen.add(msg)
            log(msg)


keyboard_option = BoolOption(
    "Keyboard typing in Rename",
    True,
    description="The game does not pass the keyboard to its menu. While the Rename field of the Build Saver panel "
                "is open, the mod reads the keyboard for that field (only while the game window is in front) and "
                "keeps those keys away from the game. Nothing is stored or sent anywhere. Off: use the on-screen keys.",
    on_change_anytime=lambda _opt, value: ingame.set_keyboard(value),
)


def _on_enable() -> None:
    ingame.start(_sdk_mods(), VERSION, log)
    ingame.set_keyboard(keyboard_option.value)


def _on_disable() -> None:
    ingame.stop()


log(f"v{VERSION} loaded - control it in the game menu (Build Saver panel) or from the Encore Teleport app.")

mod = build_mod(
    options=[keyboard_option],
    name="Build Saver",
    description="Save and load complete builds - skills and gear - in the game menu (needs SkillSaverUI_1001_P.pak) "
                "or from the Encore Teleport app (page 'Skills'). Formerly Skill Saver.",
    on_enable=_on_enable,
    on_disable=_on_disable,
)
