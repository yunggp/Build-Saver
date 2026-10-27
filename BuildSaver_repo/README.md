# Build Saver for Borderlands 4

*Formerly "Skill Saver".* Save your complete build and load it again later from the game menu: skill points,
action skill, augment, capstone, specialization skills **and your gear**. You don't need a respec station
or the inventory screen.

Build Saver is a Python mod for the [oak2-mod-manager](https://github.com/bl-sdk/oak2-mod-manager)
(unrealsdk / pyunrealsdk) plus a small UI pak that adds a **Build Saver** panel to the skill page of the
game menu.

## Features

- **Save** the current setup under a name (skills, choices, specialization skills, equipped gear).
- **Load** a build:
  - Resets the skill tree and re-applies everything.
  - **Equips the build's gear.** The saved items are moved from your backpack into their slots and the
    items you wore go back to the backpack. Nothing is copied, created or deleted.
  - Slots that were empty when you saved are emptied too.
  - Items you don't own any more are skipped and listed in the status message.
- **Undo last load**, **Overwrite**, **Rename**, **Delete** (deleted builds are moved to
  `sdk_mods/SkillSaver_trash`, not destroyed), **Reset tree**.
- For every build the panel shows the action skill, augment, capstone, specialization, gear (worn / in
  backpack / missing) and firmware sets.

## Requirements

- Borderlands 4 (PC) with the oak2-mod-manager installed.
- Gear equipping calls one internal function of the game (see below). It is checked against
  **Steam build 26007962**. On any other build it switches itself off and the rest of the mod keeps
  working.
- Optional: [Matt's SDK Boosting Tools](https://github.com/funkyoushift/MattsSDKBoostingTools). If it is
  installed, Build Saver uses its item reader to show real item names. Without it, items are named by
  manufacturer, type and rarity.
- Single player or host. A co-op guest can load skills, but not gear.

## Install

1. Close the game.
2. Download the release zip and extract it into your `Borderlands 4` folder. That adds:
   - `sdk_mods/SkillSaver.sdkmod`
   - `OakGame/Content/Paks/SkillSaverUI_1001_P.pak`
3. Start the game, open the menu and go to the skill page. Then click **Build Saver** at the top right.

The file names still say "SkillSaver" so that saves from older versions keep working.

## How it works

### Skills

The mod reads every skill tree (`GbxProgressGraph`) and saves the points and activated nodes. On load it
resets the trees and re-applies them in the game's own order with the game's server functions
(`Server_SpendProgressPoints`, `Server_ActivateNodeInGroup`). Every call is checked afterwards, and the
result goes to `sdk_mods/SkillSaver_log.txt`.

### Gear (`src/SkillSaver/gear.py`)

The game has no script function that moves a backpack item into an equip slot. Build Saver does it in
two steps:

1. The item currently in the slot goes to the backpack with the game's
   `OakCharacterFunctionLibrary.UnequipItem(..., bRemoveFromInventory=False)`.
2. The build's item goes from the backpack into the slot. For this, the mod calls the same internal
   function that `OakCharacterFunctionLibrary.EquipItem` uses for this step: the inventory transaction
   "container → equip slot".

Before it calls anything, the mod compares the code bytes of these functions with the analysed game build
(SHA-256). If they differ, which happens after a game update, gear equipping is switched off. Every slot is
checked after the move, and the mod stops at the first one that does not end up where it should.

### In-game panel (`src/ui/ui.js`, `src/SkillSaver/ingame.py`)

The game menus are HTML/JS (Coherent Gameface). The pak adds one script to the menu. The panel talks to
the mod over **127.0.0.1:19417**:

- Local only. Requests from normal web pages are refused (Origin check).
- The HTTP thread never touches game objects. Commands are queued and run on the game thread.

### Rename and the keyboard (`src/SkillSaver/kbd.py`)

The game does not pass keyboard input to its menu. So **only while the Rename field is open**, the mod
reads the keyboard for that field. It also keeps those keys away from the game, so Q, E and Esc don't
switch or close the menu.

This uses a standard Windows keyboard hook. That is the same API keyloggers use, so it is documented in
detail in **[KEYBOARD.md](KEYBOARD.md)**: when it runs, what it can't do, how to check it in the code, and
how to switch it off. In short:

- It is only active while the Rename field is open.
- It only takes keys while the game window is in front.
- The text stays in memory, max 60 characters, and becomes the build name.
- Nothing is logged, written to a file or sent anywhere.
- You can turn it off in the mod options: **"Keyboard typing in Rename"**. The on-screen keyboard always
  works.

## Files the mod writes (`sdk_mods`)

| File | Content |
|---|---|
| `SkillSaver_<id>.json` | one saved build |
| `SkillSaver_undo.json` | the setup before the last load |
| `SkillSaver_log.txt` | result of the last save / load |
| `SkillSaver_gear_debug.txt` | how the equipped items were identified (last save) |
| `SkillSaver_status.json`, `SkillSaver_gear_now.json` | status for the optional desktop app |
| `SkillSaver_ui_log.txt` | panel diagnostics, new every game start |
| `SkillSaver_trash/` | builds deleted in the panel |

## Building from source

```
python tools/build_release.py --menu-html <original menu_bigmap.html> --out dist
```

- The script builds `SkillSaver.sdkmod` from `src/SkillSaver`. It also builds the UI pak from `src/ui/ui.js`
  plus the game's own `uiresources/menu_bigmap/menu_bigmap.html`, with one added line (see
  [pak/README.md](pak/README.md)).
- That HTML file belongs to the game and is **not** in this repository. Extract it from your own game files.
- `tools/pakv8.py` is a minimal writer for the legacy pak format (v8, uncompressed).

## Credits

- [oak2-mod-manager / unrealsdk / pyunrealsdk](https://github.com/bl-sdk)
- [Matt's SDK Boosting Tools](https://github.com/funkyoushift/MattsSDKBoostingTools) (MIT): serial memory
  layout and the optional item-name reader. No code of it is included here.

## License

MIT, see [LICENSE](LICENSE). Borderlands 4 and its files belong to Gearbox / 2K. This is a fan-made mod.
