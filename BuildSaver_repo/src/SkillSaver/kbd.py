"""
Build Saver - typing a build name with the real keyboard in the game menu (v4.0)

WHY: the game does not pass keyboard input to its HTML menu, so a text field there can not be typed into.

WHAT: only while the panel's Rename field is open, this module installs a Windows low-level keyboard hook
(SetWindowsHookEx WH_KEYBOARD_LL, in its own thread) that
  * turns key presses into the build name (ToUnicodeEx: keyboard layout, Shift, AltGr, umlauts),
  * keeps those keys away from the game (so Q / E / Esc do not switch or close the menu),
  * Enter = save, Esc = cancel, Backspace = delete; the old name counts as selected - the first key replaces it.

LIMITS (by design):
  * only keys pressed while the GAME window is in front are read - typing in any other program is ignored;
  * modifier keys, the Windows key and anything with Alt (Alt+Tab) are always passed on;
  * the text lives in memory only (max 60 characters) until the panel saves it as the build name;
    nothing is written to a log or a file and nothing is sent anywhere - the panel reads it over 127.0.0.1;
  * the hook removes itself on Enter / Esc, when the panel stops asking for 3 s (menu closed), when the option
    "Keyboard typing in Rename" is switched off, and after 5 minutes at the latest.
Nothing here touches Unreal objects.
"""

import ctypes as C
import ctypes.wintypes as W
import threading
import time

WH_KEYBOARD_LL, WM_KEYDOWN, WM_SYSKEYDOWN, WM_QUIT = 13, 0x0100, 0x0104, 0x0012
VK_BACK, VK_RETURN, VK_ESCAPE, VK_SHIFT, VK_CONTROL, VK_MENU, VK_CAPITAL = 0x08, 0x0D, 0x1B, 0x10, 0x11, 0x12, 0x14
PASS = {0x10, 0x11, 0x12, 0x14, 0x5B, 0x5C, 0x5D, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0x90, 0x91}   # modifiers, Win, locks
MAX_LEN, IDLE, LIFETIME = 60, 3.0, 300.0

_lock = threading.RLock()        # re-entrant: state() is also called while holding it
_kb = {"active": False, "text": "", "seq": 0, "end": "", "poll": 0.0, "start": 0.0, "tid": 0, "error": "",
       "fresh": False}      # fresh: the old name is "selected" - the first key replaces it


class _KBD(C.Structure):
    _fields_ = [("vkCode", W.DWORD), ("scanCode", W.DWORD), ("flags", W.DWORD), ("time", W.DWORD),
                ("dwExtraInfo", C.c_size_t)]


LRESULT = C.c_ssize_t
HOOKPROC = getattr(C, "WINFUNCTYPE", C.CFUNCTYPE)(LRESULT, C.c_int, W.WPARAM, W.LPARAM)
_api: dict = {}


def _bind() -> dict:
    if _api:
        return _api
    u, k = C.WinDLL("user32", use_last_error=True), C.WinDLL("kernel32", use_last_error=True)
    u.SetWindowsHookExW.argtypes = [C.c_int, HOOKPROC, W.HINSTANCE, W.DWORD]
    u.SetWindowsHookExW.restype = W.HHOOK
    u.CallNextHookEx.argtypes = [W.HHOOK, C.c_int, W.WPARAM, W.LPARAM]
    u.CallNextHookEx.restype = LRESULT
    u.UnhookWindowsHookEx.argtypes = [W.HHOOK]
    u.GetMessageW.argtypes = [C.POINTER(W.MSG), W.HWND, W.UINT, W.UINT]
    u.PostThreadMessageW.argtypes = [W.DWORD, W.UINT, W.WPARAM, W.LPARAM]
    u.GetForegroundWindow.restype = W.HWND
    u.GetWindowThreadProcessId.argtypes = [W.HWND, C.POINTER(W.DWORD)]
    u.GetWindowThreadProcessId.restype = W.DWORD
    u.GetKeyboardLayout.argtypes = [W.DWORD]
    u.GetKeyboardLayout.restype = C.c_void_p
    u.GetAsyncKeyState.argtypes = [C.c_int]
    u.GetAsyncKeyState.restype = C.c_short
    u.GetKeyState.argtypes = [C.c_int]
    u.GetKeyState.restype = C.c_short
    u.ToUnicodeEx.argtypes = [W.UINT, W.UINT, C.c_void_p, C.c_void_p, C.c_int, W.UINT, C.c_void_p]
    k.GetModuleHandleW.argtypes = [W.LPCWSTR]
    k.GetModuleHandleW.restype = W.HMODULE
    _api.update(u=u, k=k, pid=k.GetCurrentProcessId())
    return _api


def _game_in_front() -> tuple:
    a = _api
    hwnd = a["u"].GetForegroundWindow()
    pid = W.DWORD(0)
    tid = a["u"].GetWindowThreadProcessId(hwnd, C.byref(pid)) if hwnd else 0
    return pid.value == a["pid"], tid


def _char(vk: int, scan: int, tid: int) -> str:
    a = _api
    state = (C.c_ubyte * 256)()
    for key in (VK_SHIFT, VK_CONTROL, VK_MENU, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5):
        if a["u"].GetAsyncKeyState(key) & 0x8000:
            state[key] = 0x80
    if a["u"].GetKeyState(VK_CAPITAL) & 1:
        state[VK_CAPITAL] = 0x01
    buf = C.create_unicode_buffer(8)
    n = a["u"].ToUnicodeEx(vk, scan, C.addressof(state), C.addressof(buf), 8, 4,
                           a["u"].GetKeyboardLayout(tid))                          # 4: keep dead-key state
    return buf.value[:n] if n > 0 else ""


def _on_key(vk: int, scan: int, tid: int) -> None:
    with _lock:
        if vk == VK_RETURN:
            _kb["end"] = "enter"
        elif vk == VK_ESCAPE:
            _kb["end"] = "esc"
        elif vk == VK_BACK:
            _kb["text"] = "" if _kb["fresh"] else _kb["text"][:-1]
            _kb["fresh"] = False
        else:
            ch = _char(vk, scan, tid)
            if not ch or not ch.isprintable():
                return
            base = "" if _kb["fresh"] else _kb["text"]
            if len(base) >= MAX_LEN:
                return
            _kb["text"], _kb["fresh"] = (base + ch)[:MAX_LEN], False
        _kb["seq"] += 1


def _proc(code, wparam, lparam):
    a = _api
    try:
        if code == 0 and _kb["active"] and not _kb["end"]:
            k = C.cast(lparam, C.POINTER(_KBD)).contents
            front, tid = _game_in_front()
            alt = bool(a["u"].GetAsyncKeyState(VK_MENU) & 0x8000) and not (a["u"].GetAsyncKeyState(VK_CONTROL) & 0x8000)
            if front and k.vkCode not in PASS and not alt:
                if wparam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                    _on_key(int(k.vkCode), int(k.scanCode), tid)
                return 1                                     # the game never sees this key
    except Exception:  # noqa: BLE001
        pass
    return a["u"].CallNextHookEx(None, code, wparam, lparam)


_PROC = HOOKPROC(_proc)       # module level: must stay alive while the hook exists


def _thread() -> None:
    a = _api
    hook = a["u"].SetWindowsHookExW(WH_KEYBOARD_LL, _PROC, a["k"].GetModuleHandleW(None), 0)
    if not hook:
        with _lock:
            _kb.update(active=False, error=f"keyboard hook failed ({C.get_last_error()})")
        return
    try:
        msg = W.MSG()
        while a["u"].GetMessageW(C.byref(msg), None, 0, 0) > 0:
            pass
    finally:
        a["u"].UnhookWindowsHookEx(hook)
        with _lock:
            _kb["active"] = False
            _kb["stopping"] = False
            _kb["tid"] = 0


def _watchdog() -> None:
    while True:
        time.sleep(0.25)
        with _lock:
            if not _kb["active"]:
                return
            now = time.time()
            stop = bool(_kb["end"]) or now - _kb["poll"] > IDLE or now - _kb["start"] > LIFETIME
            tid = _kb["tid"]
            if stop and tid:
                _kb["stopping"] = True          # decided under the lock: start() waits for this hook to end
        if stop and tid:
            _api["u"].PostThreadMessageW(tid, WM_QUIT, 0, 0)
            return


def start(text: str) -> dict:
    """Start reading the keyboard for the rename field. Returns the state for the panel."""
    try:
        _bind()
    except Exception as ex:  # noqa: BLE001
        return {"active": False, "error": f"no keyboard hook: {type(ex).__name__}"}
    for _ in range(100):                    # the previous hook is still shutting down: wait for it
        with _lock:
            if not (_kb["active"] and _kb.get("stopping")):
                break
        time.sleep(0.01)
    with _lock:
        _kb.update(text=str(text)[:MAX_LEN], end="", poll=time.time(), fresh=bool(text), error="")
        _kb["seq"] += 1
        if _kb["active"]:
            return state()
        _kb.update(active=True, start=time.time())
    t = threading.Thread(target=_thread, name="SkillSaverKeyboard", daemon=True)
    t.start()
    for _ in range(50):                     # wait for the thread id (needed to stop the message loop)
        if t.native_id:
            break
        time.sleep(0.01)
    with _lock:
        _kb["tid"] = t.native_id or 0
    threading.Thread(target=_watchdog, name="SkillSaverKeyboardWatch", daemon=True).start()
    return state()


def set_text(text: str) -> dict:
    """The on-screen keyboard changed the text."""
    with _lock:
        _kb["text"] = str(text)[:MAX_LEN]
        _kb["seq"] += 1
        _kb["poll"] = time.time()
        _kb["fresh"] = False
    return state()


def stop() -> dict:
    with _lock:
        _kb["end"] = _kb["end"] or "stop"
        _kb["poll"] = 0.0
    return state()


def state(touch: bool = False) -> dict:
    with _lock:
        if touch:
            _kb["poll"] = time.time()
        return {"active": _kb["active"], "text": _kb["text"], "seq": _kb["seq"], "end": _kb["end"],
                "error": _kb["error"], "fresh": _kb["fresh"]}
