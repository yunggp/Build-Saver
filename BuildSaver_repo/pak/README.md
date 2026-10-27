# The UI pak

`SkillSaverUI_1001_P.pak` (legacy pak format v8, uncompressed, mount point `../../../`) contains two files:

| Path in the pak | Source |
|---|---|
| `OakGame/Content/uiresources/_skillsaver/ui.js` | `src/ui/ui.js` from this repository |
| `OakGame/Content/uiresources/menu_bigmap/menu_bigmap.html` | the game's own file with **one added line** |

The added line goes directly before the closing `</widget-bigmap>` tag:

```html
<script src="coui://uiresources/_skillsaver/ui.js"></script>
```

`menu_bigmap.html` belongs to the game and is not included here. Extract it from your game files, for
example with FModel (`OakGame/Content/uiresources/menu_bigmap/menu_bigmap.html`). Then run:

```
python tools/build_release.py --menu-html path/to/menu_bigmap.html --out dist
```

Any other mod that also replaces `menu_bigmap.html` conflicts with this pak.
