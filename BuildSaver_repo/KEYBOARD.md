# Keyboard typing in Rename: what it does and what it doesn't

Build Saver uses a Windows keyboard hook. Keyloggers use the same API, so this page explains exactly what it
is used for. All of it is in one file: [`src/SkillSaver/kbd.py`](src/SkillSaver/kbd.py), about 200 lines.

## Why

The game's menus are HTML pages (Coherent Gameface), and **the game does not pass keyboard input to them**.
A text field in the menu therefore can't be typed into. Without help you could only rename a build with
the on-screen keyboard.

## When it is active

The hook (`SetWindowsHookEx(WH_KEYBOARD_LL)`) is installed **only while the Rename field of the Build Saver
panel is open**. It removes itself:

- when you press **Enter** (save) or **Esc** (cancel),
- when you click Save / Cancel or select another build,
- when the panel stops asking for the text for 3 seconds, for example because the menu was closed,
- when the option "Keyboard typing in Rename" is switched off,
- after **5 minutes** at the latest.

At any other time, including normal play, the mod has no keyboard hook installed.

## What it does while active

- It reads only key presses made **while the Borderlands 4 window is in front**. Keys typed in any other
  program pass through untouched.
- It never touches Shift, Ctrl, Alt, Caps Lock, the Windows key or anything pressed with Alt (Alt+Tab).
  These are always passed on.
- It turns the other keys into characters using your keyboard layout (`ToUnicodeEx`) and adds them to the
  build name. The name has at most **60 characters**. Backspace deletes, Enter saves, Esc cancels.
- It keeps those keys away from the game, so Q, E and Esc don't switch or close the menu while you type.

## What it never does

- It does not write keys to any log or file. The only thing that gets saved is the final build name,
  into that build's `SkillSaver_<id>.json`, the same as renaming in the desktop app.
- It does not send anything over the network. The panel in the game reads the current text from the mod
  over `127.0.0.1` (this computer only). Requests from web pages are refused.
- It does not run in the background and does not start with Windows. It exists only inside the game
  process, only while you rename.

## How to check

- Read `src/SkillSaver/kbd.py`.
  - `start()` installs the hook, `_proc()` is the hook callback, `_on_key()` builds the text, and
    `_watchdog()` removes the hook.
  - The only other places that use it are the `/kb` handlers in `src/SkillSaver/ingame.py` and
    `editorView()` / `startKbPoll()` in `src/ui/ui.js`.
- Search the code for `open(`, `write`, `socket`, `urllib` or `requests`. The keyboard module uses none of
  them.

## How to switch it off

Mod manager → Build Saver → option **"Keyboard typing in Rename"** → Off.

Rename then works with the on-screen keyboard (mouse or controller). Everything else is unchanged.
