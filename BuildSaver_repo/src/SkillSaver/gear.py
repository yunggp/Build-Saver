"""
Build Saver - equip the saved gear on Load (v4.0)

Moves the build's ORIGINAL items from the backpack into the equip slots - no menu, no copies, nothing
created or deleted:
  1. the item in the slot goes to the backpack: OakCharacterFunctionLibrary.UnequipItem(pawn, slot, False)
     (works by slot number - reliable)
  2. the build's item goes from the backpack into the slot: the game's internal function that
     OakCharacterFunctionLibrary.EquipItem uses for that step (inventory transaction op 5,
     "container -> equip slot"), called with the handle of the backpack row.
  Slots that were empty when the build was saved are emptied too (their item goes to the backpack).

Found by disassembling EquipItem on Steam build 26007962 (2026-10-27):
  EquipFromContainer(manager, &handle, &ownerB, &ownerA, &containerName, slot)     RVA 0x3DB6682
  ownerA / ownerB = pawn->GetInterfaceObject(class) (vtable +0x288) for the interface classes returned by
  RVA 0x119F41E / 0x131A30E, made into {UObject*, interface*} pairs; manager = ownerA->vtable[+0x10].
Before anything is called, the code bytes of these functions are compared with the analysed build (same idea
as Matt's build gates). After a game update the check fails and gear equipping switches itself off; skills
keep working. Host / single player only.
"""

import ctypes as C
import hashlib
import struct

import unrealsdk
from mods_base import get_pc

SLOT_NUM = {"Weapon 1": 0, "Weapon 2": 1, "Weapon 3": 2, "Weapon 4": 3, "Shield": 4, "Ordnance": 5,
            "Repkit": 6, "Enhancement": 7, "Class Mod": 8}

# name: (RVA, bytes checked, sha256 of those bytes) - Steam build 26007962
NATIVE = {
    "equip_from_container": (0x3DB6682, 0x60, "451bdb8887b5103686aa180375fdc374e755992ccebe4e7e3abf159fa32900bb"),
    "iface_class_a": (0x119F41E, 0x20, "1e5c33aa2085d2bfc6d1de5441544792c1feafe8bfdc3b4df57f1b0b1f3dca16"),
    "iface_class_b": (0x131A30E, 0x20, "03a192129ac910be4cc08e6010972c7c69c091705727d9136e250ef6e7be7ecc"),
    "get_iface": (0x4718840, 0x30, "6db787a7898706eadb313d81c1fe554533a3fbc824dca94a0966f9dfb1bf0334"),
}
_nat: dict = {}


# ---------------------------------------------------------------- native binding (checked once per game start)
def _reader():
    """ReadProcessMemory on our own process: a bad address returns b'' instead of crashing."""
    k = C.WinDLL("kernel32", use_last_error=True)
    k.GetCurrentProcess.restype = C.c_void_p
    k.ReadProcessMemory.argtypes = [C.c_void_p, C.c_void_p, C.c_void_p, C.c_size_t, C.POINTER(C.c_size_t)]
    k.GetModuleHandleW.restype = C.c_void_p
    k.GetModuleHandleW.argtypes = [C.c_wchar_p]
    proc = k.GetCurrentProcess()

    def read(addr: int, size: int) -> bytes:
        buf, got = C.create_string_buffer(size), C.c_size_t(0)
        if not k.ReadProcessMemory(proc, C.c_void_p(addr), buf, size, C.byref(got)):
            return b""
        return buf.raw[:got.value]
    return read, int(k.GetModuleHandleW(None))


def native() -> dict:
    if _nat.get("ok"):
        return _nat
    if _nat.get("error"):
        raise RuntimeError(_nat["error"])
    read, base = _reader()
    hdr = read(base, 0x1000)
    pe = struct.unpack_from("<I", hdr, 0x3C)[0]
    size = struct.unpack_from("<I", hdr, pe + 0x18 + 0x38)[0]
    for rva, n, digest in NATIVE.values():
        if hashlib.sha256(read(base + rva, n)).hexdigest() != digest:
            _nat["error"] = "this game version is not supported yet (game code changed)"
            raise RuntimeError(_nat["error"])
    P = C.c_void_p
    _nat.update(
        ok=True, base=base, end=base + size, read=read,
        equip=C.CFUNCTYPE(None, P, P, P, P, P, C.c_int32)(base + NATIVE["equip_from_container"][0]),
        cls_a=C.CFUNCTYPE(P)(base + NATIVE["iface_class_a"][0]),
        cls_b=C.CFUNCTYPE(P)(base + NATIVE["iface_class_b"][0]),
        get_iface=C.CFUNCTYPE(P, P, P)(base + NATIVE["get_iface"][0]),
    )
    return _nat


def _vcall(obj: int, off: int, *args):
    """obj->vtable[off / 8](obj, *args) -> pointer; the target must lie inside the game's code."""
    n = _nat
    vt = struct.unpack("<Q", n["read"](obj, 8))[0]
    fn = struct.unpack("<Q", n["read"](vt + off, 8))[0]
    if not n["base"] < fn < n["end"]:
        raise RuntimeError(f"virtual function {off:#x} is outside the game code")
    return C.CFUNCTYPE(C.c_void_p, C.c_void_p, *[C.c_void_p] * len(args))(fn)(obj, *args)


class _Owner(C.Structure):          # TScriptInterface: {UObject*, interface*}
    _fields_ = [("obj", C.c_void_p), ("iface", C.c_void_p)]


class _Context:
    """Everything EquipFromContainer needs that does not change between slots (built once per load)."""

    def __init__(self, pawn):
        n = native()
        p = pawn._get_address()
        self.owners = {}
        for key in ("a", "b"):
            cls = n["cls_" + key]()
            o = _vcall(p, 0x288, cls)                         # pawn->GetInterfaceObject(class)
            i = n["get_iface"](o, cls) if o else None
            if not i:
                raise RuntimeError(f"inventory owner {key.upper()} not found")
            self.owners[key] = _Owner(_vcall(i, 0x8), i)       # interface->_getUObject()
        self.manager = _vcall(self.owners["a"].iface, 0x10)
        if not self.manager:
            raise RuntimeError("inventory manager not found")
        from unrealsdk.unreal import WrappedStruct   # type: ignore[import-not-found]
        stat = unrealsdk.find_class("OakInventoryStatics").ClassDefaultObject
        self._name = WrappedStruct(stat.GetNumItemsInContainer.func, ContainerType="Backpack")  # keeps the FName alive
        self.backpack = self._name._get_address() + self._name._type._find_prop("ContainerType").Offset_Internal

    def equip(self, handle: int, slot: int) -> None:
        h = C.c_int32(handle)
        _nat["equip"](self.manager, C.addressof(h), C.addressof(self.owners["b"]), C.addressof(self.owners["a"]),
                      self.backpack, slot)


# ---------------------------------------------------------------- inventory
def _rows(ps, serial_of) -> list:
    """(serial, equip slot, handle) of every inventory row - decodes every serial, so once per load."""
    out = []
    for r in ps.BackpackItems.items:
        ii = r.InventoryItem
        try:
            out.append((serial_of(ii.Item.data.Identity)[0], int(ii.EquipSlot), int(ii.Handle.Handle)))
        except Exception:  # noqa: BLE001
            continue
    return out


def _slot_handles(ps, slot: int) -> list:
    """Handles of the rows in one equip slot (no serial decoding - fast)."""
    out = []
    for r in ps.BackpackItems.items:
        ii = r.InventoryItem
        try:
            if int(ii.EquipSlot) == slot:
                out.append(int(ii.Handle.Handle))
        except Exception:  # noqa: BLE001
            continue
    return out


def _in_backpack(ps, handle: int) -> bool:
    for r in ps.BackpackItems.items:
        try:
            if int(r.InventoryItem.Handle.Handle) == handle:
                return int(r.InventoryItem.EquipSlot) < 0
        except Exception:  # noqa: BLE001
            continue
    return False


def equip(data: dict, serial_of, log) -> str:
    """Equips the gear of a saved build. Returns a one-line summary for the status message."""
    entries = [g for g in data.get("gear", []) if isinstance(g, dict) and g.get("slot") in SLOT_NUM]
    gear = [g for g in entries if g.get("serial")]
    # slots that were EMPTY when the build was saved (saved as {"slot", "auto": "", "name": ""}); an entry
    # with a description but no serial (serial not readable) is left alone
    empty = [g for g in entries if not g.get("serial") and not any(g.get(k) for k in ("auto", "name", "label", "title"))]
    if not gear and not empty:
        return ""
    pc = get_pc()
    pawn, ps = pc.K2_GetPawn(), pc.PlayerState
    if pawn is None or ps is None:
        return "Gear not equipped: no character."
    try:
        if int(pc.Role) != 3:                           # ROLE_Authority: single player or host only
            return "Gear not equipped: only the host can equip gear in co-op (skills were loaded)."
    except Exception:  # noqa: BLE001
        pass
    try:
        ctx = _Context(pawn)
    except Exception as ex:  # noqa: BLE001
        log(f"Gear: {ex}")
        return f"Gear not equipped: {ex}"
    lib = unrealsdk.find_class("OakCharacterFunctionLibrary").ClassDefaultObject
    rows = _rows(ps, serial_of)
    worn = {es: (s, h) for s, es, h in rows if es >= 0}
    free: dict = {}                                   # serial -> backpack handles
    for s, es, h in rows:
        if es < 0:
            free.setdefault(s, []).append(h)
    done, same, missing, failed = 0, 0, [], []
    # which slots change, and is the wanted item available (backpack, or worn in a slot that changes)?
    todo, avail = [], {k: len(v) for k, v in free.items()}
    for g in gear:
        slot, serial = SLOT_NUM[g["slot"]], g["serial"]
        cur = worn.get(slot)
        if cur and cur[0] == serial:
            same += 1
        else:
            todo.append((g, slot, serial, g.get("name") or g.get("title") or g["slot"], cur))
            if cur:
                avail[cur[0]] = avail.get(cur[0], 0) + 1
    clear = [(g, SLOT_NUM[g["slot"]]) for g in empty if worn.get(SLOT_NUM[g["slot"]])]
    for g, slot in clear:                             # their items can be used by other slots
        cur = worn[slot]
        avail[cur[0]] = avail.get(cur[0], 0) + 1
    plan = []
    for g, slot, serial, title, cur in todo:
        if avail.get(serial, 0) > 0:
            avail[serial] -= 1
            plan.append((g, slot, serial, title, cur))
        else:
            missing.append(title)
            log(f"Gear {g['slot']}: '{title}' is not in your inventory - skipped.")
    # one slot after the other (old item out, build item in) so the backpack only needs 1-2 free places;
    # an item the build wants from another slot is taken off there first
    taken, warn = set(), []
    clear_slots = {slot for g, slot in clear}
    plan_slots = {slot for g, slot, serial, title, cur in plan}

    def take_off(slot: int, label: str) -> bool:
        cur = worn.get(slot)
        if not cur or slot in taken:
            return True
        try:
            lib.UnequipItem(pawn, slot, False)                 # by slot number -> backpack
        except Exception as ex:  # noqa: BLE001
            log(f"Gear {label}: UnequipItem failed: {type(ex).__name__}: {ex}")
        if _slot_handles(ps, slot):
            log(f"Gear {label}: the item did not leave the slot (backpack full?).")
            return False
        if not _in_backpack(ps, cur[1]):                     # never seen - but if the game dropped it, say so
            log(f"Gear {label}: the old item is not in the backpack - if your backpack was full it may be on the ground.")
            warn.append(label)
        taken.add(slot)
        free.setdefault(cur[0], []).append(cur[1])
        return True

    stop = False
    for g, slot, serial, title, cur in plan:
        if stop:
            failed.append(title)
            continue
        if not take_off(slot, g["slot"]):
            failed.append(title)
            continue
        if not free.get(serial):                               # worn in a slot that changes or is emptied?
            for other, (s2, h2) in worn.items():
                if s2 == serial and other != slot and other not in taken and (other in plan_slots or other in clear_slots):
                    take_off(other, f"slot {other + 1}")
                    break
        if not free.get(serial):
            missing.append(title)
            log(f"Gear {g['slot']}: '{title}' is not in the backpack any more - skipped.")
            continue
        handle = free[serial].pop(0)
        try:
            ctx.equip(handle, slot)
        except Exception as ex:  # noqa: BLE001
            failed.append(title)
            log(f"Gear {g['slot']}: '{title}' failed: {type(ex).__name__}: {ex}")
            stop = True
            continue
        if handle in _slot_handles(ps, slot):
            done += 1
            log(f"Gear {g['slot']}: '{title}' equipped.")
        else:
            failed.append(title)
            log(f"Gear {g['slot']}: '{title}' (handle {handle}) did not arrive in the slot - stopping.")
            stop = True
    # slots that are empty in the build
    cleared = 0
    for g, slot in clear:
        if slot in taken:
            cleared += 1
            continue
        if take_off(slot, g["slot"]):
            cleared += 1
            log(f"Gear {g['slot']}: empty in the build - item moved to the backpack.")
        else:
            failed.append(f"{g['slot']} (empty in build)")
    parts = [f"Gear: {done} equipped"]
    if same:
        parts.append(f"{same} already worn")
    if cleared:
        parts.append(f"{cleared} emptied")
    if missing:
        parts.append(f"not owned: {', '.join(missing)}")
    if failed:
        parts.append(f"failed: {', '.join(failed)}")
    if warn:
        parts.append(f"check the ground - old item of {', '.join(warn)} not in the backpack")
    return ", ".join(parts) + "."
