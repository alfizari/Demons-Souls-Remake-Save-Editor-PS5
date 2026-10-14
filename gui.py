"""
Demon's Souls (PS5) save editor - GUI

Run:  python gui.py
Needs main.py and the json/ folder next to it.

Tabs
    Character   name, class, gender, stats, souls, HP/MP/stamina
    Inventory   items filtered by category / search, edit quantity / durability
    Storage     storage box, same filters and editing
    Add Items   pick items (or everything the filters show) and add them to the
                inventory or the storage box; Magic = learn / forget spells & miracles
    Tendency    character and world tendency
"""

import os
import re
import shutil
import struct
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import main as ds

ds.PRINT_ENABLED = False

STAT_NAMES = ['Vitality', 'Intelligence', 'Endurance', 'Strength',
              'Dexterity', 'Magic', 'Faith', 'Luck']

TYPE_NAMES = {ds.ITEM_TYPE_WEAPON: 'Weapon', ds.ITEM_TYPE_ARMOR: 'Armor',
              ds.ITEM_TYPE_RING: 'Ring', ds.ITEM_TYPE_GOOD: 'Good'}

ITEM_TABLES = {'Weapon': ds.weapons_json, 'Armor': ds.armor_json,
               'Ring': ds.rings_json, 'Good': ds.items_json}

NAME_BY_TYPE = {ds.ITEM_TYPE_WEAPON: ds.weapons_by_id, ds.ITEM_TYPE_ARMOR: ds.armor_by_id,
                ds.ITEM_TYPE_RING: ds.rings_by_id, ds.ITEM_TYPE_GOOD: ds.items_by_id}

WORLD_LABELS = [f'World {i:02d}' for i in range(ds.WORLD_COUNT)]

CATEGORIES = ['All', 'Weapon', 'Armor', 'Ring', 'Good']          # inventory / storage filters
ADD_CATEGORIES = CATEGORIES + ['Magic']                          # Add Items: + spells & miracles

UPGRADE_RE = re.compile(r'\+\d+$')                                   # "Long Sword+3"
JUNK_RE = re.compile(r'test|dummy|debug|\?|ERROR|\(Nothing|Invoke Magic', re.IGNORECASE)  # test / placeholder entries


def item_name(item_type, item_id):
    return NAME_BY_TYPE.get(item_type, {}).get(item_id, f'<unknown {item_id}>')


def read_u32(data, off):
    return struct.unpack_from('<I', data, off)[0]


def write_inv_field(data, record, field, value):
    """record = NN in "Equipment_InventoryNN_<field>" (not the slot)."""
    off = ds.find_field(data, ds.inv_field_name(record, field))
    if off < 0:
        raise ValueError(f'{ds.inv_field_name(record, field)} not found')
    struct.pack_into('<I', data, off + 5, value & 0xFFFFFFFF)


def write_box_field(data, slot, field, value):
    off = ds.find_field(data, ds.box_field_name(slot, field))
    if off < 0:
        raise ValueError(f'{ds.box_field_name(slot, field)} not found')
    if field in ('LowQuantity', 'HighQuantity'):
        struct.pack_into('<B', data, off + 5, value & 0xFF)
    else:
        struct.pack_into('<I', data, off + 5, value & 0xFFFFFFFF)


def parse_int(text, what, lo=0, hi=0xFFFFFFFF):
    try:
        v = int(str(text).strip(), 0)
    except ValueError:
        raise ValueError(f'{what}: "{text}" is not a number')
    if not lo <= v <= hi:
        raise ValueError(f'{what} must be between {lo} and {hi}')
    return v


class EditorApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Demon's Souls Save Editor")
        self.geometry('980x640')
        self.minsize(820, 520)

        self.data = None
        self.path = None
        self.dirty = False

        self._build_menu()
        self._build_toolbar()

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill='both', expand=True, padx=6, pady=(0, 6))

        self._build_character_tab()
        self._build_inventory_tab()
        self._build_storage_tab()
        self._build_add_tab()
        self._build_tendency_tab()

        self.status = tk.StringVar(value='Open a USR-DATA file to start.')
        ttk.Label(self, textvariable=self.status, anchor='w', relief='sunken').pack(fill='x', side='bottom')

        self._set_enabled(False)
        self.protocol('WM_DELETE_WINDOW', self._on_close)

    # ------------------------------------------------------------- menu / file
    def _build_menu(self):
        menubar = tk.Menu(self)
        fm = tk.Menu(menubar, tearoff=0)
        fm.add_command(label='Open...', command=self.open_file, accelerator='Ctrl+O')
        fm.add_command(label='Save', command=self.save_file, accelerator='Ctrl+S')
        fm.add_command(label='Save As...', command=self.save_file_as)
        fm.add_separator()
        fm.add_command(label='Exit', command=self._on_close)
        menubar.add_cascade(label='File', menu=fm)
        self.config(menu=menubar)
        self.bind_all('<Control-o>', lambda e: self.open_file())
        self.bind_all('<Control-s>', lambda e: self.save_file())

    def _build_toolbar(self):
        bar = ttk.Frame(self)
        bar.pack(fill='x', padx=6, pady=6)
        ttk.Button(bar, text='Open...', command=self.open_file).pack(side='left')
        self.save_btn = ttk.Button(bar, text='Save', command=self.save_file)
        self.save_btn.pack(side='left', padx=4)
        ttk.Button(bar, text='Save As...', command=self.save_file_as).pack(side='left')
        self.file_label = ttk.Label(bar, text='No file loaded', foreground='gray')
        self.file_label.pack(side='left', padx=12)

    def open_file(self):
        if not self._confirm_discard():
            return
        path = filedialog.askopenfilename(title='Open USR-DATA', initialdir=ds.working_directory)
        if not path:
            return
        try:
            data = bytearray(ds.open_file(path))
            ds.parse_save(data)          # validates that this is a save we understand
        except Exception as e:
            messagebox.showerror('Open failed', f'Could not read this save:\n{e}')
            return
        self.data, self.path, self.dirty = data, path, False
        self._set_enabled(True)
        self.refresh_all()
        self._set_status(f'Loaded {os.path.basename(path)} ({len(data)} bytes)')

    def save_file(self):
        if self.data is None:
            return
        self._write(self.path, backup=True)

    def save_file_as(self):
        if self.data is None:
            return
        path = filedialog.asksaveasfilename(title='Save USR-DATA as', initialfile='USR-DATA',
                                            initialdir=os.path.dirname(self.path))
        if path:
            self._write(path, backup=os.path.exists(path))
            self.path = path

    def _write(self, path, backup):
        try:
            if backup and os.path.exists(path):
                shutil.copy2(path, path + '.bak')
            out = ds.fix_size(bytearray(self.data))
            out = ds.fix_checksum(out)
            ds.write_file(path, out)
            self.data = out
        except Exception as e:
            messagebox.showerror('Save failed', str(e))
            return
        self.dirty = False
        self._update_title()
        extra = ' (old file kept as .bak)' if backup else ''
        self._set_status(f'Saved {os.path.basename(path)}{extra}')

    def _confirm_discard(self):
        if self.dirty:
            return messagebox.askyesno('Unsaved changes', 'Discard unsaved changes?')
        return True

    def _on_close(self):
        if self._confirm_discard():
            self.destroy()

    # ------------------------------------------------------------- helpers
    def _set_status(self, text):
        self.status.set(text)

    def _update_title(self):
        name = os.path.basename(self.path) if self.path else 'No file loaded'
        self.file_label.config(text=(name + ('  *modified*' if self.dirty else '')),
                               foreground='black' if self.path else 'gray')

    def _mark_dirty(self, msg):
        self.dirty = True
        self._update_title()
        self._set_status(msg)

    def _set_enabled(self, on):
        for i in range(len(self.nb.tabs())):
            self.nb.tab(i, state='normal' if on else 'disabled')
        self.save_btn.config(state='normal' if on else 'disabled')

    def _apply(self, fn, success_msg, refresh=True):
        """Run an edit on a copy; only keep it if it works."""
        try:
            new = fn(bytearray(self.data))
            if new is not None:
                ds.parse_save(new)        # sanity check
                self.data = bytearray(new)
        except Exception as e:
            messagebox.showerror('Edit failed', str(e))
            return False
        self._mark_dirty(success_msg)
        if refresh:
            self.refresh_all()
        return True

    def refresh_all(self):
        self.refresh_character()
        self.refresh_inventory()
        self.refresh_storage()
        self.refresh_tendency()
        self._fill_add_list()
        self._update_title()

    @staticmethod
    def _make_tree(parent, columns):
        frame = ttk.Frame(parent)
        tree = ttk.Treeview(frame, columns=[c[0] for c in columns], show='headings', selectmode='browse')
        for cid, title, width, anchor in columns:
            tree.heading(cid, text=title)
            tree.column(cid, width=width, anchor=anchor, stretch=(cid == 'name'))
        sb = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')
        return frame, tree

    # ------------------------------------------------------------- character
    def _build_character_tab(self):
        tab = ttk.Frame(self.nb, padding=12)
        self.nb.add(tab, text='Character')
        self.char_vars = {}

        ident = ttk.LabelFrame(tab, text='Identity', padding=10)
        ident.grid(row=0, column=0, sticky='nsew', padx=(0, 8), pady=(0, 8))
        ttk.Label(ident, text='Name').grid(row=0, column=0, sticky='w', pady=3)
        self.char_vars['name'] = tk.StringVar()
        ttk.Entry(ident, textvariable=self.char_vars['name'], width=22).grid(row=0, column=1, sticky='w')
        ttk.Label(ident, text='Class').grid(row=1, column=0, sticky='w', pady=3)
        self.char_vars['class'] = tk.StringVar()
        ttk.Combobox(ident, textvariable=self.char_vars['class'], state='readonly', width=20,
                     values=list(ds.CLASS_MAP.values())).grid(row=1, column=1, sticky='w')
        ttk.Label(ident, text='Gender').grid(row=2, column=0, sticky='w', pady=3)
        self.char_vars['gender'] = tk.StringVar()
        ttk.Combobox(ident, textvariable=self.char_vars['gender'], state='readonly', width=20,
                     values=['Male', 'Female']).grid(row=2, column=1, sticky='w')
        ttk.Label(ident, text='Souls').grid(row=3, column=0, sticky='w', pady=3)
        self.char_vars['souls'] = tk.StringVar()
        ttk.Entry(ident, textvariable=self.char_vars['souls'], width=22).grid(row=3, column=1, sticky='w')

        stats = ttk.LabelFrame(tab, text='Stats (max 99 in game)', padding=10)
        stats.grid(row=0, column=1, rowspan=2, sticky='nsew', pady=(0, 8))
        for r, name in enumerate(STAT_NAMES):
            ttk.Label(stats, text=name).grid(row=r, column=0, sticky='w', pady=3)
            v = tk.StringVar()
            self.char_vars[name] = v
            ttk.Spinbox(stats, from_=1, to=99, textvariable=v, width=8).grid(row=r, column=1, sticky='w', padx=6)

        pools = ttk.LabelFrame(tab, text='HP / MP / Stamina', padding=10)
        pools.grid(row=1, column=0, sticky='nsew', padx=(0, 8))
        for r, (key, label) in enumerate([('hp', 'HP'), ('mp', 'MP'), ('st', 'Stamina')]):
            ttk.Label(pools, text=label).grid(row=r, column=0, sticky='w', pady=3)
            v = tk.StringVar()
            self.char_vars[key] = v
            ttk.Entry(pools, textvariable=v, width=12).grid(row=r, column=1, sticky='w', padx=6)
        ttk.Label(pools, text='Writes all three copies of each value.',
                  foreground='gray').grid(row=3, column=0, columnspan=2, sticky='w', pady=(6, 0))

        btns = ttk.Frame(tab)
        btns.grid(row=2, column=0, columnspan=2, sticky='w', pady=10)
        ttk.Button(btns, text='Apply character changes', command=self.apply_character).pack(side='left')
        ttk.Button(btns, text='Revert', command=self.refresh_character).pack(side='left', padx=6)
        tab.columnconfigure(0, weight=1)
        tab.columnconfigure(1, weight=1)

    def refresh_character(self):
        if self.data is None:
            return
        d = self.data
        o = ds.parse_save(d)
        size = d[o['player_name_size_off']]
        self.char_vars['name'].set(bytes(d[o['player_name_off']:o['player_name_off'] + size]).decode('utf-8', 'replace'))
        self.char_vars['class'].set(ds.CLASS_MAP.get(read_u32(d, o['class_off']), ''))
        self.char_vars['gender'].set(ds.GENDER_MAP.get(d[o['gender_off_0']], ''))
        self.char_vars['souls'].set(str(read_u32(d, o['souls_off'])))
        for name in STAT_NAMES:
            self.char_vars[name].set(str(read_u32(d, o[name + '_off'])))
        self.char_vars['hp'].set(str(read_u32(d, o['hp_off_2'])))
        self.char_vars['mp'].set(str(read_u32(d, o['mp_off_2'])))
        self.char_vars['st'].set(str(read_u32(d, o['st_off_2'])))

    def apply_character(self):
        v = {k: var.get() for k, var in self.char_vars.items()}

        def edit(d):
            o = ds.parse_save(d)
            old_name = bytes(d[o['player_name_off']:o['player_name_off'] + d[o['player_name_size_off']]]).decode('utf-8', 'replace')
            for name in STAT_NAMES:
                d = ds.update_stats(d, name, parse_int(v[name], name, 1, 999))
            d = ds.update_souls(d, parse_int(v['souls'], 'Souls'))
            d = ds.update_hp(d, parse_int(v['hp'], 'HP'))
            d = ds.update_mp(d, parse_int(v['mp'], 'MP'))
            d = ds.update_st(d, parse_int(v['st'], 'Stamina'))
            if v['class']:
                d = ds.update_class(d, v['class'])
            if v['gender']:
                d = ds.update_gender(d, v['gender'])
            if v['name'] and v['name'] != old_name:
                d = bytearray(ds.update_name(d, v['name']))
            return d

        self._apply(edit, 'Character updated (not saved yet)')

    # ------------------------------------------------------------- shared filter bar
    def _filter_bar(self, parent, on_change, categories=CATEGORIES):
        bar = ttk.Frame(parent)
        bar.pack(fill='x', pady=(0, 6))
        ttk.Label(bar, text='Show').pack(side='left')
        cat = tk.StringVar(value='All')
        cb = ttk.Combobox(bar, textvariable=cat, state='readonly', width=10, values=categories)
        cb.pack(side='left', padx=(4, 12))
        cb.bind('<<ComboboxSelected>>', lambda e: on_change())
        ttk.Label(bar, text='Search').pack(side='left')
        search = tk.StringVar()
        search.trace_add('write', lambda *a: on_change())
        ttk.Entry(bar, textvariable=search, width=30).pack(side='left', padx=4)
        return bar, cat, search

    @staticmethod
    def _passes(category_var, search_var, item_type, name):
        cat = category_var.get()
        if cat != 'All' and TYPE_NAMES.get(item_type) != cat:
            return False
        needle = search_var.get().strip().lower()
        return not needle or needle in name.lower()

    # ------------------------------------------------------------- inventory
    def _build_inventory_tab(self):
        tab = ttk.Frame(self.nb, padding=8)
        self.nb.add(tab, text='Inventory')
        _, self.inv_cat, self.inv_search = self._filter_bar(tab, self.refresh_inventory)
        cols = [('slot', 'Slot', 50, 'center'), ('type', 'Type', 70, 'w'), ('name', 'Name', 260, 'w'),
                ('id', 'Item ID', 80, 'e'), ('qty', 'Qty', 60, 'e'), ('dur', 'Durability', 80, 'e'),
                ('var', 'Variation', 70, 'e'), ('sort', 'Sort', 60, 'e')]
        frame, self.inv_tree = self._make_tree(tab, cols)
        frame.pack(fill='both', expand=True)
        self.inv_tree.bind('<<TreeviewSelect>>', lambda e: self._inv_selected())

        self.inv_info = tk.StringVar()
        ttk.Label(tab, textvariable=self.inv_info, foreground='gray').pack(fill='x', pady=(4, 0))

        edit = ttk.LabelFrame(tab, text='Selected item', padding=8)
        edit.pack(fill='x', pady=(6, 0))
        self.inv_sel_label = ttk.Label(edit, text='(nothing selected)', width=40)
        self.inv_sel_label.pack(side='left')
        ttk.Label(edit, text='Quantity').pack(side='left', padx=(10, 2))
        self.inv_qty = tk.StringVar()
        ttk.Entry(edit, textvariable=self.inv_qty, width=8).pack(side='left')
        ttk.Label(edit, text='Durability').pack(side='left', padx=(10, 2))
        self.inv_dur = tk.StringVar()
        ttk.Entry(edit, textvariable=self.inv_dur, width=8).pack(side='left')
        ttk.Button(edit, text='Apply', command=self.apply_inventory_edit).pack(side='left', padx=10)

    def refresh_inventory(self):
        if self.data is None:
            return
        self.inv_tree.delete(*self.inv_tree.get_children())
        items = ds.parse_inventory(self.data)
        _, _, _, count = ds.get_inv_off(self.data)
        shown = 0
        for it in items:
            name = item_name(it.item_type, it.item_id)
            if not self._passes(self.inv_cat, self.inv_search, it.item_type, name):
                continue
            shown += 1
            # iid = record number (NN in the field names); "Slot" column = the item's real slot
            self.inv_tree.insert('', 'end', iid=str(it.name_index), values=(
                it.slot, TYPE_NAMES.get(it.item_type, hex(it.item_type)), name,
                it.item_id, it.quantity, it.durability, it.variation_id, it.sort_id))
        info = f'showing {shown} of {len(items)} items'
        free = sorted(set(range(max((it.slot for it in items), default=-1) + 1)) - {it.slot for it in items})
        if free:
            info += f' - free slots: {free}'
        if count != len(items):
            info += f' - count field says {count}, will be fixed to {len(items)} on the next add'
        self.inv_info.set(info)
        self.inv_sel_label.config(text='(nothing selected)')
        self.inv_qty.set('')
        self.inv_dur.set('')

    def _inv_selected(self):
        sel = self.inv_tree.selection()
        if not sel:
            return
        vals = self.inv_tree.item(sel[0], 'values')
        self.inv_sel_label.config(text=f'Slot {vals[0]}: {vals[2]}')
        self.inv_qty.set(vals[4])
        self.inv_dur.set(vals[5])

    def apply_inventory_edit(self):
        sel = self.inv_tree.selection()
        if not sel:
            messagebox.showinfo('No item', 'Select an item first.')
            return
        rec = int(sel[0])
        slot = self.inv_tree.item(sel[0], 'values')[0]
        qty, dur = self.inv_qty.get(), self.inv_dur.get()

        def edit(d):
            write_inv_field(d, rec, 'Quantity', parse_int(qty, 'Quantity', 1, 9999))
            write_inv_field(d, rec, 'Durability_Current', parse_int(dur, 'Durability'))
            return d

        if self._apply(edit, f'Inventory slot {slot} updated (not saved yet)'):
            if self.inv_tree.exists(str(rec)):
                self.inv_tree.selection_set(str(rec))

    # ------------------------------------------------------------- storage
    def _build_storage_tab(self):
        tab = ttk.Frame(self.nb, padding=8)
        self.nb.add(tab, text='Storage Box')
        _, self.box_cat, self.box_search = self._filter_bar(tab, self.refresh_storage)
        cols = [('slot', 'Slot', 50, 'center'), ('type', 'Type', 70, 'w'), ('name', 'Name', 300, 'w'),
                ('id', 'Item ID', 80, 'e'), ('qty', 'Qty', 60, 'e'), ('dur', 'Durability', 80, 'e'),
                ('sort', 'Sort', 60, 'e')]
        frame, self.box_tree = self._make_tree(tab, cols)
        frame.pack(fill='both', expand=True)
        self.box_tree.bind('<<TreeviewSelect>>', lambda e: self._box_selected())

        self.box_info = tk.StringVar()
        ttk.Label(tab, textvariable=self.box_info, foreground='gray').pack(fill='x', pady=(4, 0))

        edit = ttk.LabelFrame(tab, text='Selected entry', padding=8)
        edit.pack(fill='x', pady=(6, 0))
        self.box_sel_label = ttk.Label(edit, text='(nothing selected)', width=40)
        self.box_sel_label.pack(side='left')
        ttk.Label(edit, text=f'Quantity (max {ds.BOX_MAX_QUANTITY})').pack(side='left', padx=(10, 2))
        self.box_qty = tk.StringVar()
        ttk.Entry(edit, textvariable=self.box_qty, width=8).pack(side='left')
        ttk.Label(edit, text='Durability').pack(side='left', padx=(10, 2))
        self.box_dur = tk.StringVar()
        ttk.Entry(edit, textvariable=self.box_dur, width=8).pack(side='left')
        ttk.Button(edit, text='Apply', command=self.apply_storage_edit).pack(side='left', padx=10)

    def refresh_storage(self):
        if self.data is None:
            return
        self.box_tree.delete(*self.box_tree.get_children())
        items, _ = ds.parse_storage_box(self.data)
        shown = 0
        for it in items:
            name = item_name(it.item_type, it.item_id)
            if not self._passes(self.box_cat, self.box_search, it.item_type, name):
                continue
            shown += 1
            self.box_tree.insert('', 'end', iid=str(it.slot), values=(
                it.slot, TYPE_NAMES.get(it.item_type, hex(it.item_type)), name,
                it.item_id, it.quantity, it.durability, it.sort_id))
        self.box_info.set(f'showing {shown} of {len(items)} entries')
        self.box_sel_label.config(text='(nothing selected)')
        self.box_qty.set('')
        self.box_dur.set('')

    def _box_selected(self):
        sel = self.box_tree.selection()
        if not sel:
            return
        vals = self.box_tree.item(sel[0], 'values')
        self.box_sel_label.config(text=f'Box {vals[0]}: {vals[2]}')
        self.box_qty.set(vals[4])
        self.box_dur.set(vals[5])

    def apply_storage_edit(self):
        sel = self.box_tree.selection()
        if not sel:
            messagebox.showinfo('No entry', 'Select a storage entry first.')
            return
        slot = int(sel[0])
        qty, dur = self.box_qty.get(), self.box_dur.get()

        def edit(d):
            q = parse_int(qty, 'Quantity', 1, ds.BOX_MAX_QUANTITY)
            write_box_field(d, slot, 'LowQuantity', q & 0xFF)
            write_box_field(d, slot, 'HighQuantity', (q >> 8) & 3)
            write_box_field(d, slot, 'Durability', parse_int(dur, 'Durability'))
            return d

        if self._apply(edit, f'Storage entry {slot} updated (not saved yet)'):
            if self.box_tree.exists(str(slot)):
                self.box_tree.selection_set(str(slot))

    # ------------------------------------------------------------- add items
    def _build_add_tab(self):
        tab = ttk.Frame(self.nb, padding=8)
        self.nb.add(tab, text='Add Items')

        _, self.add_cat, self.add_search = self._filter_bar(tab, self._fill_add_list, ADD_CATEGORIES)
        bar = ttk.Frame(tab)
        bar.pack(fill='x')
        self.add_hide_upgrades = tk.BooleanVar(value=True)
        self.add_hide_junk = tk.BooleanVar(value=True)
        self.add_hide_owned = tk.BooleanVar(value=False)
        for text, var in (('Hide upgraded (+1, +2...)', self.add_hide_upgrades),
                          ('Hide test/dummy', self.add_hide_junk),
                          ('Hide items I own', self.add_hide_owned)):
            ttk.Checkbutton(bar, text=text, variable=var, command=self._fill_add_list).pack(side='left', padx=(0, 16))

        cols = [('type', 'Type', 70, 'w'), ('name', 'Name', 360, 'w'), ('id', 'Item ID', 90, 'e'),
                ('owned', 'Owned / learned', 120, 'e')]
        frame, self.add_tree = self._make_tree(tab, cols)
        self.add_tree.configure(selectmode='extended')
        frame.pack(fill='both', expand=True, pady=6)
        self.add_tree.bind('<<TreeviewSelect>>', lambda e: self._add_selected())
        self.add_tree.bind('<Double-1>', lambda e: self.add_selected_items())

        self.add_info = tk.StringVar()
        ttk.Label(tab, textvariable=self.add_info, foreground='gray').pack(fill='x')

        opts = ttk.LabelFrame(tab, text='Add', padding=8)
        opts.pack(fill='x', pady=(4, 0))
        row = ttk.Frame(opts)
        row.pack(fill='x')
        ttk.Label(row, text='To').pack(side='left')
        self.add_dest = tk.StringVar(value='Inventory')
        ttk.Radiobutton(row, text='Inventory', variable=self.add_dest, value='Inventory').pack(side='left', padx=4)
        ttk.Radiobutton(row, text='Storage box', variable=self.add_dest, value='Storage').pack(side='left', padx=4)
        ttk.Label(row, text='Quantity').pack(side='left', padx=(16, 2))
        self.add_qty = tk.StringVar(value='1')
        ttk.Entry(row, textvariable=self.add_qty, width=8).pack(side='left')
        ttk.Label(row, text='Durability').pack(side='left', padx=(16, 2))
        self.add_dur = tk.StringVar()
        ttk.Entry(row, textvariable=self.add_dur, width=8).pack(side='left')
        ttk.Button(row, text='Add selected', command=self.add_selected_items).pack(side='left', padx=(16, 4))
        self.add_all_btn = ttk.Button(row, text='Add all listed', command=self.add_all_listed)
        self.add_all_btn.pack(side='left', padx=4)
        ttk.Button(row, text='Forget selected spells', command=self.forget_selected_spells).pack(side='left', padx=4)
        ttk.Label(opts, foreground='gray', wraplength=900, justify='left', text=(
            'Ctrl/Shift-click to select several. "Add all listed" adds everything the filters show. '
            'Durability: empty = copy it from a copy you already own; weapons/armor you do not own need a value '
            '(their max durability) or they arrive broken. Goods/rings always get 0. '
            'When adding several, Quantity is used for goods and 1 for everything else. '
            'Magic: adding a spell/miracle marks it as learned (To / Quantity / Durability are ignored).')).pack(fill='x', pady=(6, 0))
        self._fill_add_list()

    def _owned_map(self):
        """{(type, id): durability} for everything in the inventory and storage box."""
        owned = {}
        if self.data is None:
            return owned
        box, _ = ds.parse_storage_box(self.data)
        for it in list(box) + ds.parse_inventory(self.data):
            owned[(it.item_type, it.item_id)] = it.durability
        return owned

    def _learned_spells(self):
        if self.data is None:
            return set()
        return {sid for sid, st in ds.get_magic_states(self.data).items() if ds.is_learned(st)}

    def _catalog_rows(self):
        """[(category, name, id)] after the Add-tab filters."""
        cat = self.add_cat.get()
        needle = self.add_search.get().strip().lower()
        owned = self._owned_map() if self.add_hide_owned.get() else {}
        learned = self._learned_spells() if self.add_hide_owned.get() else set()
        rows = []
        for category in (ADD_CATEGORIES[1:] if cat == 'All' else [cat]):
            table = ds.spells_json if category == 'Magic' else ITEM_TABLES[category]
            for name, item_id in table.items():
                if needle and needle not in name.lower():
                    continue
                if self.add_hide_upgrades.get() and UPGRADE_RE.search(name):
                    continue
                if self.add_hide_junk.get() and JUNK_RE.search(name):
                    continue
                if self.add_hide_owned.get():
                    if category == 'Magic' and item_id in learned:
                        continue
                    if category != 'Magic' and (ds.ITEM_TYPES[category], item_id) in owned:
                        continue
                rows.append((category, name, item_id))
        return rows

    def _fill_add_list(self):
        self.add_tree.delete(*self.add_tree.get_children())
        owned = self._owned_map()
        learned = self._learned_spells()
        rows = self._catalog_rows()
        for category, name, item_id in rows:
            if category == 'Magic':
                shown = 'learned' if item_id in learned else ''
            else:
                dur = owned.get((ds.ITEM_TYPES[category], item_id))
                shown = '' if dur is None else dur
            self.add_tree.insert('', 'end', iid=f'{category}|{name}',
                                 values=(category, name, item_id, shown))
        self.add_info.set(f'{len(rows)} items listed')
        self.add_all_btn.config(text=f'Add all listed ({len(rows)})')

    def _add_selected(self):
        sel = self.add_tree.selection()
        if len(sel) != 1:
            return
        category, _name, _id, owned = self.add_tree.item(sel[0], 'values')
        if category == 'Magic':
            return
        if owned != '':
            self.add_dur.set(owned)
        elif category in ('Good', 'Ring'):
            self.add_dur.set('0')
        else:
            self.add_dur.set('')

    def add_selected_items(self):
        sel = self.add_tree.selection()
        if not sel:
            messagebox.showinfo('No item', 'Select one or more items from the list first.')
            return
        self._add_items([tuple(iid.split('|', 1)) for iid in sel])

    def add_all_listed(self):
        rows = self._catalog_rows()
        if not rows:
            messagebox.showinfo('Nothing listed', 'The list is empty - change the filters first.')
            return
        where = 'storage box' if self.add_dest.get() == 'Storage' else 'inventory'
        n_magic = sum(1 for c, _, _ in rows if c == 'Magic')
        parts = []
        if len(rows) - n_magic:
            parts.append(f'add {len(rows) - n_magic} items to the {where}')
        if n_magic:
            parts.append(f'learn {n_magic} spells/miracles')
        if not messagebox.askyesno('Add all listed', ' and '.join(parts).capitalize() + '?'):
            return
        self._add_items([(c, n) for c, n, _ in rows])

    def _add_items(self, picks):
        """picks: [(category, name)]"""
        spells = [ds.spells_json[n] for c, n in picks if c == 'Magic']
        picks = [(c, n) for c, n in picks if c != 'Magic']
        if spells and not picks:
            self._apply(lambda d: ds.learn_spells(d, spells),
                        f'Learned {len(spells)} spell(s)/miracle(s) (not saved yet)')
            return
        dest = self.add_dest.get()
        qty_text, dur_text = self.add_qty.get(), self.add_dur.get().strip()
        max_q = ds.BOX_MAX_QUANTITY if dest == 'Storage' else 99
        try:
            qty = parse_int(qty_text, 'Quantity', 1, max_q)
            dur = parse_int(dur_text, 'Durability') if dur_text else None
        except ValueError as e:
            messagebox.showerror('Bad value', str(e))
            return

        owned = self._owned_map()
        single = len(picks) == 1
        requests, broken = [], []
        for category, name in picks:
            type_bits = ds.ITEM_TYPES[category]
            item_id = ITEM_TABLES[category][name]
            if category in ('Good', 'Ring'):
                d = 0 if not single or dur is None else dur
            elif (type_bits, item_id) in owned and (dur is None or not single):
                d = owned[(type_bits, item_id)]
            else:
                d = dur
                if d is None:
                    broken.append(name)
            q = qty if (single or category == 'Good') else 1
            requests.append({'name': name, 'type': category, 'quantity': q,
                             'durability': d if d is not None else 0})

        if broken:
            sample = ', '.join(broken[:5]) + (' ...' if len(broken) > 5 else '')
            if not messagebox.askyesno('No durability', f'{len(broken)} weapon/armor item(s) have no durability '
                                       f'set and you do not own a copy to copy it from ({sample}).\n'
                                       'They will arrive broken (durability 0). Add anyway?'):
                return

        def edit(d):
            if dest == 'Storage':
                d = ds.spawn_items_storage(d, requests)
            else:
                d = ds.spawn_items(d, requests)
            if spells:
                d = ds.learn_spells(d, spells)
            return d

        where = 'storage box' if dest == 'Storage' else 'inventory'
        what = f'{picks[0][1]} x{qty}' if single else f'{len(picks)} items'
        extra = f' and learned {len(spells)} spell(s)' if spells else ''
        self._apply(edit, f'Added {what} to the {where}{extra} (not saved yet)')

    def forget_selected_spells(self):
        spells = [ds.spells_json[iid.split('|', 1)[1]] for iid in self.add_tree.selection()
                  if iid.startswith('Magic|')]
        if not spells:
            messagebox.showinfo('No spells', 'Select one or more spells/miracles (Show: Magic) first.')
            return
        self._apply(lambda d: ds.forget_spells(d, spells), f'Forgot {len(spells)} spell(s) (not saved yet)')


    # ------------------------------------------------------------- tendency
    def _build_tendency_tab(self):
        tab = ttk.Frame(self.nb, padding=12)
        self.nb.add(tab, text='Tendency')
        ttk.Label(tab, foreground='gray', wraplength=760, justify='left', text=(
            'Tendency values are floats. New characters start at 0.0. The range is probably -1.0 to 1.0 and '
            'the world numbering is not confirmed yet - test small changes in game first.')).grid(
            row=0, column=0, columnspan=3, sticky='w', pady=(0, 10))

        ttk.Label(tab, text='', width=14).grid(row=1, column=0)
        ttk.Label(tab, text='Black / White').grid(row=1, column=1)
        ttk.Label(tab, text='Left / Right').grid(row=1, column=2)

        self.tend_vars = {}
        rows = [('character', 'Character')] + [(f'world{i:02d}', WORLD_LABELS[i]) for i in range(ds.WORLD_COUNT)]
        for r, (key, label) in enumerate(rows, start=2):
            ttk.Label(tab, text=label).grid(row=r, column=0, sticky='w', pady=3)
            for c, field in enumerate(('BlackWhite', 'LeftRight'), start=1):
                v = tk.StringVar()
                self.tend_vars[(key, field)] = v
                ttk.Spinbox(tab, from_=-1.0, to=1.0, increment=0.1, textvariable=v, width=10).grid(
                    row=r, column=c, padx=8)

        btns = ttk.Frame(tab)
        btns.grid(row=len(rows) + 2, column=0, columnspan=3, sticky='w', pady=12)
        ttk.Button(btns, text='Apply tendency', command=self.apply_tendency).pack(side='left')
        ttk.Button(btns, text='Revert', command=self.refresh_tendency).pack(side='left', padx=6)

    def refresh_tendency(self):
        if self.data is None:
            return
        try:
            t = ds.get_tendency(self.data)
        except Exception as e:
            self._set_status(f'Tendency not readable: {e}')
            return
        for (key, field), var in self.tend_vars.items():
            var.set(f'{t[key][field]:.3f}')

    def apply_tendency(self):
        vals = {}
        try:
            for k, var in self.tend_vars.items():
                vals[k] = float(var.get())
        except ValueError:
            messagebox.showerror('Bad value', 'Tendency values must be numbers like 0.5 or -1.0')
            return

        def edit(d):
            ds.set_character_tendency(d, vals[('character', 'BlackWhite')], vals[('character', 'LeftRight')])
            for w in range(ds.WORLD_COUNT):
                ds.set_world_tendency(d, w, vals[(f'world{w:02d}', 'BlackWhite')], vals[(f'world{w:02d}', 'LeftRight')])
            return d

        self._apply(edit, 'Tendency updated (not saved yet)')


if __name__ == '__main__':
    EditorApp().mainloop()
