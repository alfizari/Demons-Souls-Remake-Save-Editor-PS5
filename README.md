# Demon's Souls (PS5) Save Editor

A save editor for **Demon's Souls (PS5, 2020)** decrypted `USR-DATA` saves, with a tabbed GUI.
Built and tested against game version **1.007**.

> Always keep a backup of your save. The editor writes a `.bak` of the previous file every time you save,
> but test edited saves on a non-important character first.

## Features

| Tab | What you can do |
|---|---|
| **Character** | Name, class, gender, souls, the 8 stats, HP / MP / stamina |
| **Inventory** | List items with filters (All / Weapon / Armor / Ring / Good) and search, edit quantity and durability |
| **Storage Box** | Same as the inventory, for the storage box (quantities up to 1023) |
| **Add Items** | Add one, several (Ctrl/Shift-click) or **all listed** items to the inventory or straight into the storage box. Filters for category, search, upgraded versions (+1…+10), test/dummy entries and items you already own. **Magic**: learn / forget spells and miracles |
| **Tendency** | Character tendency and world tendency (7 worlds) |

Every save fixes the file size field and the FNV-1a checksum automatically.

## Requirements

- Python 3.9+ with Tkinter (included in the normal Windows installer from python.org)
- A **decrypted** `USR-DATA` save from the PS5 (this tool does not decrypt or re-encrypt saves)

## Running

```bat
python gui.py
```

Then **File → Open** your `USR-DATA`, edit, and **Save** (or **Save As**).

`main.py` can also be used on its own as a library / script (see the `if __name__ == '__main__':` block at the bottom).

## Building an .exe

Double-click **`build.bat`**. It installs PyInstaller and creates:

```
dist\DeSSaveEditor.exe
```

A single file with no console window. The item lists are built in, so the exe can be copied anywhere.
Windows SmartScreen may warn about a new unsigned exe; choose *More info → Run anyway*.

## Project layout

```
gui.py          GUI (tkinter)
main.py         save parsing / editing
build.bat       builds dist\DeSSaveEditor.exe
json\           item / armor / ring / goods / spell name -> id tables
saves\          your saves (not required)
scripts\        helper scripts (checksum check, json generation)
```

## Notes and limits

- **Durability**: the editor has no table of each weapon's / armor's max durability yet. When you add a weapon
  or armor you do not already own, enter a durability, otherwise it arrives with 0 (broken). If you already own
  a copy, its durability is copied automatically.
- **Sort order**: new items get the sort order of a copy you own, otherwise 0 (affects menu sorting only).
- **Tendency**: values are floats (new characters start at 0.0). The value range and which world number is which
  world are not confirmed yet - change one world a little and check in game.
- **Inventory size**: the editor does not limit how many items you add.

## How the save works (short version)

- From offset `0x10` to the end, the save is one stream of fields: `key (u32) | type (u8) | value`.
- The **key** is **FNV-1a32 of the upper-cased field name**, e.g. `EQUIPMENT_INVENTORY03_EQUIPID`.
  Fixed fields (stats, souls, name, ...) use pre-computed constant keys.
- Header: `0x04` = FNV-1a32 checksum of `data[0x10:]`, `0x08` = `len(file) - 0x10`.
- **Inventory**: `Equipment_Inventory_Count` = number of records; records are named `00..N-1` with no gaps,
  sorted by slot; each record's `_Index` field holds its real slot (slots can have gaps). 8 fields per item:
  `Index, Type, EquipId, Quantity, VariationId, DisplayId, Durability_Current, Durability_AccumulatedHits`.
  Type: `0x00000000` weapon, `0x10000000` armor, `0x20000000` ring, `0x40000000` goods.
- **Storage box**: entries `Equipment_StorageBoxNN_*` followed by `Equipment_StorageBox_Count`;
  quantity = `LowQuantity | HighQuantity << 8`.
- **Magic**: `Magic_State<spell id>`; bit `0x2` = learned (value 3), 1 = not learned.
- **Tendency**: float fields `Tendency_WorldNN_BlackWhite` / `_LeftRight`, plus two for the character.

The save layout was worked out from the game's own save reader / writer in the 1.007 executable.

## Credits

- Item, armor, ring, goods and spell IDs from **[Wulf2k / DeS-SaveEdit](https://github.com/Wulf2k/DeS-SaveEdit)**.
