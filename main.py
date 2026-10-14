import struct, os, sys, json, random

PRINT_ENABLED = True

def log(*args, **kwargs):
    if PRINT_ENABLED:
        print(*args, **kwargs)

name_offset=False
inventory_items=[]
weapons = []
armors = []
goods = []
rings = []


CLASS_MAP = {
    0: "Soldier",
    1: "Knight",
    2: "Hunter",
    3: "Priest",
    4: "Magician",
    5: "Wanderer",
    6: "Barbarian",
    7: "Theif",
    8: "Temple Knight",
    9: "Royalty"
}

REVERSE_CLASS_MAP = {v: k for k, v in CLASS_MAP.items()}

GENDER_MAP = {
    1: "Male",
    0: "Female"
}
REVERSE_GENDER_MAP = {v: k for k, v in GENDER_MAP.items()}

# Set the working directory
# When packaged with PyInstaller (build.bat), the json/ folder is unpacked to a
# temporary folder (sys._MEIPASS) and the working folder is the one with the .exe.
if getattr(sys, 'frozen', False):
    working_directory = os.path.dirname(os.path.abspath(sys.executable))
    resource_directory = getattr(sys, '_MEIPASS', working_directory)
else:
    working_directory = os.path.dirname(os.path.abspath(__file__))
    resource_directory = working_directory
os.chdir(working_directory)


def load_and_copy_json(file_name):
    file_path = os.path.join(resource_directory, "json", file_name)
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)

weapons_json = load_and_copy_json("Weapons.json")
armor_json= load_and_copy_json("Armor.json")
rings_json = load_and_copy_json("Rings.json")
items_json= load_and_copy_json("Items.json")

def write_value_at_offset(data, offset, value, byte_size=4):
    value_bytes = value.to_bytes(byte_size, 'little')
    return data[:offset] + value_bytes + data[offset+byte_size:]


# ---------------------------------------------------------------------------
# Field keys
# ---------------------------------------------------------------------------
# Every value in the save is a 9-byte field:  key(u32) | type(u8) | value(u32)
# The key is FNV-1a32 over the UPPERCASED field name (found in the save reader,
# eboot sub_27550). Example names:
#   "Equipment_Inventory_Count"
#   "Equipment_Inventory%02d_EquipId"
#   "Equipment_Slot%02d_InventoryId"

FIELD_SIZE = 9
FIELD_TYPE_UINT = 0x08
FIELD_TYPE_INT = 0x04


def ds_key(name: str) -> int:
    h = 0x811C9DC5
    for c in name.upper().encode('ascii'):
        h = ((h ^ c) * 0x01000193) & 0xFFFFFFFF
    return h


def find_field(data, name, start=0):
    """Offset of the field whose key is ds_key(name), or -1."""
    return data.find(struct.pack('<I', ds_key(name)), start)


def read_field(data, offset):
    """(key, type, value) at offset."""
    return struct.unpack_from('<IBI', data, offset)


def make_field(name, value, field_type=FIELD_TYPE_UINT):
    return struct.pack('<IBI', ds_key(name), field_type, value & 0xFFFFFFFF)




weapons_by_id = {
    item_id: name
    for name, item_id in weapons_json.items()
}

armor_by_id = {
    item_id: name
    for name, item_id in armor_json.items()
}

rings_by_id = {
    item_id: name
    for name, item_id in rings_json.items()
}

items_by_id = {
    item_id: name
    for name, item_id in items_json.items()
}


##FOR ITEMS THE SLOT SIZE IS 0x48
#distance from name

# souls= -0x25

# vitality= -0xBB
# intelligence= -0xA9
# endurance= -0x97
# strength= -0x85
# dexterity= -0x73
# magic= -0x61
# faith= -0x4F
# luck= -0x37


def open_file(file_path: str): 

    with open(file_path, 'rb')as f:
        data=bytearray(f.read())

    return data

def write_file(out_path: str, data): 

    with open(out_path, 'wb')as f:
        f.write(data)

    return True


def fix_checksum(data):

    #it uses fnv1a32 as checksum at offset 0x04, from 0x10 to EOF.
    check_data=data[0x10:]
    h=0x811C9DC5
    for b in check_data:
        h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF

    struct.pack_into('<I', data, 0x4, h)

    return data


def fix_size(data): # written at offset 0x08

    field=data[0x10:]

    size_field=len(field)

    struct.pack_into('<I', data, 0x8, size_field)

    return data

# ---------------------------------------------------------------------------
# Character fields
# ---------------------------------------------------------------------------
# These fields use constant keys (the hashes are pre-computed in the game, so the
# names are not stored as strings). Finding them by key works no matter how many
# fields come before them - the old fixed offsets broke on saves that have one
# field more or less before the stats.
#
# Field types: 0x08 u32, 0x04 s32, 0x0C u8 (6-byte field), 0x0D string (len byte + bytes)

FIELD_TYPE_U8 = 0x0C
FIELD_TYPE_STRING = 0x0D

CHAR_FIELD_KEYS = {
    #  name            key         type
    'Vitality':     (0xF059AB80, FIELD_TYPE_UINT),
    'Intelligence': (0x14795A91, FIELD_TYPE_UINT),
    'Endurance':    (0xD02FD40F, FIELD_TYPE_UINT),
    'Strength':     (0x5078FC63, FIELD_TYPE_UINT),
    'Dexterity':    (0xA144D982, FIELD_TYPE_UINT),
    'Magic':        (0xB06E4ED9, FIELD_TYPE_UINT),
    'Faith':        (0xD6A72566, FIELD_TYPE_UINT),
    'Luck':         (0x7B664AD3, FIELD_TYPE_UINT),
    'souls':        (0x76FD62AF, FIELD_TYPE_UINT),
    'hp_0':         (0xEC506126, FIELD_TYPE_UINT),
    'hp_1':         (0x8B499D3C, FIELD_TYPE_UINT),
    'hp_2':         (0x72FDBAEA, FIELD_TYPE_UINT),
    'mp_0':         (0xFA49BB6B, FIELD_TYPE_UINT),
    'mp_1':         (0x99416481, FIELD_TYPE_UINT),
    'mp_2':         (0x310A1EF7, FIELD_TYPE_UINT),
    'st_0':         (0xF68A5C75, FIELD_TYPE_UINT),
    'st_1':         (0x8D63E3DF, FIELD_TYPE_UINT),
    'st_2':         (0x1D100FA9, FIELD_TYPE_UINT),
    'class':        (0x45B54344, FIELD_TYPE_UINT),
    'gender_0':     (0xDF236D58, FIELD_TYPE_U8),
    'gender_1':     (0xA3C2D71A, FIELD_TYPE_U8),
    'player_name':  (0x324FEFCE, FIELD_TYPE_STRING),
}


def find_value_off(data, name):
    """Offset of the value of a character field (key + type byte + 5)."""
    key, ftype = CHAR_FIELD_KEYS[name]
    off = data.find(struct.pack('<IB', key, ftype))
    if off < 0:
        raise ValueError(f'field {name} ({key:08X}) not found in save')
    return off + 5


def parse_save(data):

    o = {name: find_value_off(data, name) for name in CHAR_FIELD_KEYS}

    save_offsets = {
        'Vitality_off':     o['Vitality'],
        'Intelligence_off': o['Intelligence'],
        'Endurance_off':    o['Endurance'],
        'Strength_off':     o['Strength'],
        'Dexterity_off':    o['Dexterity'],
        'Magic_off':        o['Magic'],
        'Faith_off':        o['Faith'],
        'Luck_off':         o['Luck'],

        'souls_off': o['souls'],

        # string field: length byte, then the bytes
        'player_name_size_off': o['player_name'],
        'player_name_off':      o['player_name'] + 1,

        'hp_off_0': o['hp_0'],
        'hp_off_1': o['hp_1'],
        'hp_off_2': o['hp_2'],

        'mp_off_0': o['mp_0'],
        'mp_off_1': o['mp_1'],
        'mp_off_2': o['mp_2'],

        'st_off_0': o['st_0'],
        'st_off_1': o['st_1'],
        'st_off_2': o['st_2'],

        'class_off':    o['class'],
        'gender_off_0': o['gender_0'],
        'gender_off_1': o['gender_1'],

        # value of the "Equipment_Inventory_Count" field
        'inventory_counter_off': find_field(data, 'Equipment_Inventory_Count') + 5,
    }

    log('class off', hex(save_offsets['class_off']))
    log('gender off 0:', hex(save_offsets['gender_off_0']))
    log('gender off 1:', hex(save_offsets['gender_off_1']))

    return save_offsets

# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------
# "Equipment_Inventory_Count" (= number of records) is followed by the records,
# 8 fields each (0x48 bytes), named 00..N-1 with no gaps:
#   Equipment_Inventory%02d_Index                       the item's real slot (can have gaps)
#   Equipment_Inventory%02d_Type                        category (see ITEM_TYPE_*)
#   Equipment_Inventory%02d_EquipId                     item id
#   Equipment_Inventory%02d_Quantity                    field type 0x04
#   Equipment_Inventory%02d_VariationId                 handle into the durability table
#   Equipment_Inventory%02d_DisplayId                   VariationId | (sortId << 16)
#   Equipment_Inventory%02d_Durability_Current
#   Equipment_Inventory%02d_Durability_AccumulatedHits
# Right after the list come the "Equipment_Slot%02d_InventoryId/_EquipmentId" pairs.

ITEM_TYPE_WEAPON = 0x00000000
ITEM_TYPE_ARMOR  = 0x10000000
ITEM_TYPE_RING   = 0x20000000
ITEM_TYPE_GOOD   = 0x40000000

ITEM_TYPES = {
    'Weapon': ITEM_TYPE_WEAPON,
    'Armor':  ITEM_TYPE_ARMOR,
    'Ring':   ITEM_TYPE_RING,
    'Good':   ITEM_TYPE_GOOD,
}

INV_FIELDS = ['Index', 'Type', 'EquipId', 'Quantity', 'VariationId',
              'DisplayId', 'Durability_Current', 'Durability_AccumulatedHits']
INV_REC_SIZE = len(INV_FIELDS) * FIELD_SIZE      # 0x48


def inv_field_name(i, field):
    return f'Equipment_Inventory{i:02d}_{field}'


class INVENTORY:
    """
    One inventory record.
      name_index  NN in "Equipment_InventoryNN_*" - the game numbers written
                  records 0,1,2... with no gaps (sub_2DE30, the save writer)
      slot        value of the _Index field = the item's real in-memory slot.
                  Slots CAN have gaps (an item used up / dropped frees its slot).
    Equipment_Slot%02d_InventoryId and Equipment_EquipItem%02d refer to `slot`.
    """

    def __init__(self, slot, item_type, item_id, quantity, variation_id,
                 display_id, durability, durability_hits, offset=None, name_index=None):
        self.slot = slot
        self.item_type = item_type
        self.item_id = item_id
        self.quantity = quantity
        self.variation_id = variation_id
        self.display_id = display_id
        self.durability = durability
        self.durability_hits = durability_hits
        self.offset = offset          # offset of the _Index field
        self.name_index = name_index
        self.size = INV_REC_SIZE

    @property
    def sort_id(self):
        return self.display_id >> 16

    @classmethod
    def from_bytes(cls, data, offset, name_index):
        values = []
        for j, field in enumerate(INV_FIELDS):
            key, _type, value = read_field(data, offset + j * FIELD_SIZE)
            if key != ds_key(inv_field_name(name_index, field)):
                log(f'WARNING: unexpected key for {inv_field_name(name_index, field)}: {key:08x}')
            values.append(value)
        return cls(*values, offset=offset, name_index=name_index)

    def to_bytes(self, name_index):
        vals = {'Index': self.slot, 'Type': self.item_type, 'EquipId': self.item_id,
                'Quantity': self.quantity, 'VariationId': self.variation_id,
                'DisplayId': self.display_id, 'Durability_Current': self.durability,
                'Durability_AccumulatedHits': self.durability_hits}
        return b''.join(
            make_field(inv_field_name(name_index, f), vals[f],
                       FIELD_TYPE_INT if f == 'Quantity' else FIELD_TYPE_UINT)
            for f in INV_FIELDS)

    def as_tuple(self):
        return (self.item_type, self.item_id, self.quantity,
                self.variation_id, self.display_id, self.offset)


def get_inv_off(data):
    """
    (first_record_off, end_off, counter_value_off, count)

    "Equipment_Inventory_Count" = number of records the game wrote. Records follow
    the count field directly and the list ends where "Equipment_Slot00_InventoryId"
    starts. (Saves edited by older scripts can have a count that does not match;
    the list end is what counts.)
    """
    count_field = find_field(data, 'Equipment_Inventory_Count')
    if count_field < 0:
        raise ValueError('Equipment_Inventory_Count not found')
    counter_off = count_field + 5
    count = struct.unpack_from('<I', data, counter_off)[0]
    log('inv counter value', count)

    inv_start_off = count_field + FIELD_SIZE
    inv_end_off = find_field(data, 'Equipment_Slot00_InventoryId', inv_start_off)
    if inv_end_off < 0 or (inv_end_off - inv_start_off) % INV_REC_SIZE:
        raise ValueError('inventory list end (Equipment_Slot00_InventoryId) not found')
    log('inv start off', hex(inv_start_off), 'inv end off', hex(inv_end_off))
    return inv_start_off, inv_end_off, counter_off, count


def parse_inventory(data):
    inv_start_off, inv_end_off, _, count = get_inv_off(data)
    items = [INVENTORY.from_bytes(data, off, n)
             for n, off in enumerate(range(inv_start_off, inv_end_off, INV_REC_SIZE))]
    if len(items) != count:
        log(f'inventory: count field says {count} but {len(items)} records are present')
    return items


def write_inventory(data, items):
    """
    Rewrite the whole inventory list the way the game's writer does:
    records sorted by slot, named 00..N-1, count = N.
    """
    data = bytearray(data)
    inv_start_off, inv_end_off, counter_off, _ = get_inv_off(data)
    items = sorted(items, key=lambda it: it.slot)
    if len({it.slot for it in items}) != len(items):
        raise ValueError('two inventory items use the same slot')
    blob = b''.join(it.to_bytes(n) for n, it in enumerate(items))
    data[inv_start_off:inv_end_off] = blob
    struct.pack_into('<I', data, counter_off, len(items))
    return data


def inventory_log(data):
    global weapons, armors, goods, rings, inventory_items

    inventory_items = []
    weapons = []
    armors = []
    goods = []
    rings = []

    lookups = {
        ITEM_TYPE_WEAPON: ('weapon', weapons_by_id, weapons),
        ITEM_TYPE_ARMOR:  ('armor',  armor_by_id,   armors),
        ITEM_TYPE_RING:   ('ring',   rings_by_id,   rings),
        ITEM_TYPE_GOOD:   ('good',   items_by_id,   goods),
    }

    for item in parse_inventory(data):
        inventory_items.append(item.as_tuple())
        kind, by_id, bucket = lookups.get(item.item_type, ('unknown type', {}, None))
        name = by_id.get(item.item_id)
        if name:
            log(f'{kind} name: ', name, ':', item.item_id, 'x', item.quantity)
        else:
            log(f'unk {kind} id////:', item.item_id)
        if bucket is not None:
            bucket.append(item.as_tuple())

    return


# ---------------------------------------------------------------------------
# Generic field walker
# ---------------------------------------------------------------------------
# The whole save from 0x10 to EOF is one stream of fields: key(u32) | type(u8) | value
# Value size depends on the type:
#   0x02 u8    0x06 u8    0x0C u8/bool   0x03 u16
#   0x04 s32   0x08 u32   0x0A float32   0x0F 16 bytes (4 floats)
#   0x0D string: length byte + bytes
#   0x0E varint (LEB128). For the blob keys below it is a byte length followed by raw data.

FIELD_TYPE_U8_B = 0x02
FIELD_TYPE_U16 = 0x03
FIELD_TYPE_FLOAT = 0x0A
FIELD_TYPE_VARINT = 0x0E

_FIELD_SIZES = {0x02: 1, 0x03: 2, 0x04: 4, 0x06: 1, 0x08: 4, 0x0A: 4, 0x0C: 1, 0x0F: 16}
_BLOB_KEYS = {0x522AD995, 0x0AF4946A, 0x78A5C2D7, 0xB98A1BFF, 0xE56C5A97,
              0x2B87B29A, 0x94A8D348, 0x6D87F588}


def _read_varint(data, p):
    value = shift = 0
    while True:
        b = data[p]
        p += 1
        value |= (b & 0x7F) << shift
        shift += 7
        if b < 0x80:
            return value, p


def iter_fields(data, start=0x10):
    """Yield (offset, key, type, value, size) for every field in the save."""
    p = start
    while p + 5 <= len(data):
        key, ftype = struct.unpack_from('<IB', data, p)
        if ftype in _FIELD_SIZES:
            n = _FIELD_SIZES[ftype]
            raw = bytes(data[p + 5:p + 5 + n])
            value = struct.unpack('<f', raw)[0] if ftype == FIELD_TYPE_FLOAT else int.from_bytes(raw, 'little')
            size = 5 + n
        elif ftype == FIELD_TYPE_STRING:
            n = data[p + 5]
            value, size = bytes(data[p + 6:p + 6 + n]), 6 + n
        elif ftype == FIELD_TYPE_VARINT:
            value, q = _read_varint(data, p + 5)
            if key in _BLOB_KEYS:
                value, q = bytes(data[q:q + value]), q + value
            size = q - p
        else:
            raise ValueError(f'unknown field type {ftype:#x} at {p:#x}')
        yield p, key, ftype, value, size
        p += size


def find_key(data, key, ftype):
    """Offset of the field with this key+type, walking the stream (no false matches)."""
    for off, k, t, _v, _s in iter_fields(data):
        if k == key and t == ftype:
            return off
    return -1


# ---------------------------------------------------------------------------
# Storage box
# ---------------------------------------------------------------------------
# Entries are written first, then "Equipment_StorageBox_Count".
# Entry i (contiguous, 0..count-1, max 0x800), keys "Equipment_StorageBox%02d_...":
#   EquipTypeId                 u32   Type | EquipId   (e.g. 0x400003E8 = goods 1000)
#   DisplayId                   u32   copied from the inventory item (VariationId | sortId << 16)
#   LowQuantity                 u8    (type 0x02)
#   HighQuantity                u8    (type 0x02, 2 bits)   quantity = low | high << 8
#   Durability                  u32   current durability (0 for goods)
#   Durability_AccumulatedHits  u32

BOX_FIELDS = ['EquipTypeId', 'DisplayId', 'LowQuantity', 'HighQuantity',
              'Durability', 'Durability_AccumulatedHits']
BOX_MAX_QUANTITY = 0x3FF
BOX_MAX_ENTRIES = 0x800


def box_field_name(i, field):
    return f'Equipment_StorageBox{i:02d}_{field}'


class STORAGE_ITEM:

    def __init__(self, slot, item_type, item_id, display_id, quantity,
                 durability, durability_hits, offset):
        self.slot = slot
        self.item_type = item_type
        self.item_id = item_id
        self.display_id = display_id
        self.quantity = quantity
        self.durability = durability
        self.durability_hits = durability_hits
        self.offset = offset

    @property
    def sort_id(self):
        return self.display_id >> 16


def parse_storage_box(data):
    """(items, count_field_off). Items are read by key, so field order does not matter."""
    count_off = find_field(data, 'Equipment_StorageBox_Count')
    if count_off < 0:
        return [], -1
    count = read_field(data, count_off)[2]
    values = {}
    offsets = {}
    for off, k, _t, v, _s in iter_fields(data):
        values[k] = v
        offsets.setdefault(k, off)
    items = []
    for i in range(count):
        f = {name: values.get(ds_key(box_field_name(i, name))) for name in BOX_FIELDS}
        if f['EquipTypeId'] is None:
            log(f'WARNING: storage box entry {i} missing')
            continue
        items.append(STORAGE_ITEM(
            i,
            f['EquipTypeId'] & 0xF0000000,
            f['EquipTypeId'] & 0x0FFFFFFF,
            f['DisplayId'] or 0,
            (f['LowQuantity'] or 0) | ((f['HighQuantity'] or 0) & 3) << 8,
            f['Durability'] if f['Durability'] is not None else 0xFFFFFFFF,
            f['Durability_AccumulatedHits'] or 0,
            offsets[ds_key(box_field_name(i, 'EquipTypeId'))],
        ))
    return items, count_off


def storage_box_log(data):
    names = {ITEM_TYPE_WEAPON: weapons_by_id, ITEM_TYPE_ARMOR: armor_by_id,
             ITEM_TYPE_RING: rings_by_id, ITEM_TYPE_GOOD: items_by_id}
    items, _ = parse_storage_box(data)
    log(f'storage box: {len(items)} entries')
    for it in items:
        name = names.get(it.item_type, {}).get(it.item_id, f'unknown id {it.item_id}')
        log(f'  box {it.slot:02d}: {name} x{it.quantity} (durability {it.durability})')
    return items


def spawn_items_storage(data, requests):
    """
    Add several items straight into the storage box in one pass.
    requests: list of dicts {name, type, quantity=1, durability=None, sort_id=None}
    New entries go before "Equipment_StorageBox_Count", numbered after the existing ones.
    durability / sort_id: copied from a copy of the same item in the box or inventory,
    else 0. Weapons/armor need a real durability.
    """
    data = bytearray(data)
    items, count_off = parse_storage_box(data)
    if count_off < 0:
        raise ValueError('Equipment_StorageBox_Count not found')
    count = read_field(data, count_off)[2]

    owned = {(it.item_type, it.item_id): it for it in parse_inventory(data)}
    owned.update({(it.item_type, it.item_id): it for it in items})

    entry = bytearray()
    for req in requests:
        item_type = req['type']
        item_id = _item_id(req['name'], item_type)
        type_bits = ITEM_TYPES[item_type]
        quantity = max(1, min(req.get('quantity', 1), BOX_MAX_QUANTITY))

        same = owned.get((type_bits, item_id))
        durability = req.get('durability')
        if durability is None:
            durability = same.durability if same else 0
            if not same and item_type in ('Weapon', 'Armor'):
                log('WARNING: no durability given for', req['name'], '- storing with 0')
        sort_id = req.get('sort_id')
        if sort_id is None:
            sort_id = same.sort_id if same else 0

        i = count
        count += 1
        values = {
            'EquipTypeId':                type_bits | item_id,
            'DisplayId':                  (sort_id & 0xFFFF) << 16,
            'LowQuantity':                quantity & 0xFF,
            'HighQuantity':               (quantity >> 8) & 3,
            'Durability':                 durability,
            'Durability_AccumulatedHits': 0,
        }
        for f in BOX_FIELDS:
            if f in ('LowQuantity', 'HighQuantity'):
                entry += struct.pack('<IBB', ds_key(box_field_name(i, f)), FIELD_TYPE_U8_B, values[f])
            else:
                entry += make_field(box_field_name(i, f), values[f])
        log(f'stored {req["name"]} x{quantity} in box slot {i}')

    data[count_off:count_off] = entry                       # entries sit before the count
    struct.pack_into('<I', data, count_off + len(entry) + 5, count)
    return data


def spawn_item_storage(data, item_name: str, item_type: str, quantity=1,
                       durability=None, sort_id=None):
    """Add one item straight into the storage box (see spawn_items_storage)."""
    return spawn_items_storage(data, [{'name': item_name, 'type': item_type, 'quantity': quantity,
                                       'durability': durability, 'sort_id': sort_id}])



# ---------------------------------------------------------------------------
# World / character tendency
# ---------------------------------------------------------------------------
# float32 fields (type 0x0A). The game defaults them to 0.5 when missing.
#   character: two constant keys (below)
#   worlds:    "Tendency_World%02d_BlackWhite" / "Tendency_World%02d_LeftRight", worlds 00..06

CHAR_TENDENCY_KEYS = {'BlackWhite': 0xCD98E106, 'LeftRight': 0x80205423}
WORLD_COUNT = 7


def _float_field_off(data, key):
    off = data.find(struct.pack('<IB', key, FIELD_TYPE_FLOAT))
    if off < 0:
        raise ValueError(f'tendency field {key:08X} not found')
    return off + 5


def get_tendency(data):
    out = {'character': {n: struct.unpack_from('<f', data, _float_field_off(data, k))[0]
                         for n, k in CHAR_TENDENCY_KEYS.items()}}
    for w in range(WORLD_COUNT):
        out[f'world{w:02d}'] = {
            n: struct.unpack_from('<f', data, _float_field_off(data, ds_key(f'Tendency_World{w:02d}_{n}')))[0]
            for n in ('BlackWhite', 'LeftRight')}
    return out


def set_world_tendency(data, world: int, black_white=None, left_right=None):
    for n, v in (('BlackWhite', black_white), ('LeftRight', left_right)):
        if v is not None:
            struct.pack_into('<f', data, _float_field_off(data, ds_key(f'Tendency_World{world:02d}_{n}')), float(v))
    return data


def set_character_tendency(data, black_white=None, left_right=None):
    for n, v in (('BlackWhite', black_white), ('LeftRight', left_right)):
        if v is not None:
            struct.pack_into('<f', data, _float_field_off(data, CHAR_TENDENCY_KEYS[n]), float(v))
    return data


# ---------------------------------------------------------------------------
# Magic
# ---------------------------------------------------------------------------
# "Magic_State%08d" (spell id from spells.json), u32. The reader loops over every
# magic param id and looks the field up by key. Seen values:
#   1 = baseline (the same 11 spells on every character - not learned)
#   3 = learned          (a Magician starts with Flame Toss + Water Veil = 3)
# so bit 1 (value 2) is the "learned" flag.
# The fields sit right after the storage box, in spell-id order, followed by the
# currently selected spell (key C37EAA59) and the attunement fields.

MAGIC_LEARNED_BIT = 0x2
MAGIC_SELECTED_KEY = 0xC37EAA59

spells_json = load_and_copy_json("spells.json")
spells_by_id = {spell_id: name for name, spell_id in spells_json.items()}


def magic_key(spell_id):
    return ds_key(f'Magic_State{spell_id:08d}')


def get_magic_states(data):
    """{spell_id: state} for every Magic_State field present."""
    wanted = {magic_key(sid): sid for sid in spells_by_id}
    return {wanted[k]: v for _o, k, _t, v, _s in iter_fields(data) if k in wanted}


def is_learned(state):
    return state is not None and bool(state & MAGIC_LEARNED_BIT)


def set_magic_states(data, new_states):
    """
    new_states: {spell_id: state}. Existing fields are updated in place; missing
    ones are inserted in spell-id order inside the magic block.
    """
    data = bytearray(data)
    by_key = {magic_key(sid): sid for sid in spells_by_id}
    present = {}                                  # spell_id -> field offset
    selected_off = -1
    for off, k, t, _v, _s in iter_fields(data):
        if k in by_key and t == FIELD_TYPE_UINT:
            present[by_key[k]] = off
        elif k == MAGIC_SELECTED_KEY and t == FIELD_TYPE_UINT:
            selected_off = off

    # update existing fields first (no offsets move)
    missing = {}
    for sid, state in new_states.items():
        if sid in present:
            struct.pack_into('<I', data, present[sid] + 5, state & 0xFFFFFFFF)
        else:
            missing[sid] = state

    # insert missing ones from the highest id down, so earlier offsets stay valid
    for sid in sorted(missing, reverse=True):
        after = [s for s in present if s > sid]
        if after:
            at = present[min(after)]              # before the next higher spell id
        elif present:
            last = max(present)
            at = present[last] + FIELD_SIZE       # after the highest spell id
        elif selected_off >= 0:
            at = selected_off                     # no Magic_State at all yet
        else:
            raise ValueError('magic block not found in save')
        data[at:at] = make_field(f'Magic_State{sid:08d}', missing[sid])
        # shift recorded offsets that are at/after the insert point
        present = {s: (o + FIELD_SIZE if o >= at else o) for s, o in present.items()}
        present[sid] = at
    return data


def learn_spells(data, spell_ids):
    states = get_magic_states(data)
    return set_magic_states(data, {sid: (states.get(sid, 1) | MAGIC_LEARNED_BIT | 1)
                                   for sid in spell_ids})


def forget_spells(data, spell_ids):
    """Clear the learned bit (back to the baseline state). Missing fields are left alone."""
    states = get_magic_states(data)
    return set_magic_states(data, {sid: states[sid] & ~MAGIC_LEARNED_BIT
                                   for sid in spell_ids if sid in states})


def magic_log(data):
    states = get_magic_states(data)
    for sid, state in sorted(states.items()):
        log(f'  magic {sid}: {spells_by_id.get(sid)} state={state}'
            f'{" (learned)" if is_learned(state) else ""}')
    return states



def load_data(data):


    save_offsets=parse_save(data)

    log()

    log('-------------------player stats-------------------')
    log()

    player_name_size=struct.unpack_from('<B', data, save_offsets['player_name_size_off'])[0]

    raw_name = data[save_offsets['player_name_off']:save_offsets['player_name_off'] +player_name_size]
    char_name = raw_name.decode("utf-8", errors="ignore")

    log('player name: ', char_name)

    vitality_val=struct.unpack_from('<H',data, save_offsets['Vitality_off'] )[0]
    log('vitality_val = ', vitality_val)

    Intelligence_val=struct.unpack_from('<H',data, save_offsets['Intelligence_off'] )[0]
    log('Intelligence_val = ', Intelligence_val)

    Endurance_val=struct.unpack_from('<H',data, save_offsets['Endurance_off'] )[0]
    log('Endurance_val = ', Endurance_val)

    Strength_val=struct.unpack_from('<H',data, save_offsets['Strength_off'] )[0]
    log('Strength_val = ', Strength_val)

    Dexterity_val=struct.unpack_from('<H',data, save_offsets['Dexterity_off'] )[0]
    log('Dexterity_val = ', Dexterity_val)
    
    Magic_val=struct.unpack_from('<H',data, save_offsets['Magic_off'] )[0]
    log('Magic_val = ', Magic_val)

    Faith_val=struct.unpack_from('<H',data, save_offsets['Faith_off'] )[0]
    log('Faith_val = ', Faith_val)

    Luck_val=struct.unpack_from('<H',data, save_offsets['Luck_off'] )[0]
    log('Luck_val = ', Luck_val)

    souls_val=struct.unpack_from('<I',data, save_offsets['souls_off'] )[0]
    log('souls_val = ', souls_val)

    class_val=struct.unpack_from('<H',data, save_offsets['class_off'] )[0]
    log('class_val = ', class_val, 'class name = ', CLASS_MAP.get(class_val))

    gender_val=struct.unpack_from('<B',data, save_offsets['gender_off_0'] )[0]
    log('gender_val = ', gender_val, 'gender name = ', GENDER_MAP.get(gender_val))

    hp_val=struct.unpack_from('<I',data, save_offsets['hp_off_2'] )[0]
    log('hp_val = ', hp_val)

    mp_val=struct.unpack_from('<I',data, save_offsets['mp_off_2'] )[0]
    log('mp_val = ', mp_val)

    st_val=struct.unpack_from('<I',data, save_offsets['st_off_2'] )[0]
    log('st_val = ', st_val)



    return


def update_name(data, new_name):
    """
    The name is a string field: key | 0x0D | length byte | bytes.
    The old bytes are replaced, so every field after the name shifts by the
    length difference (fix_size / fix_checksum update the header on save).
    """
    save_offsets = parse_save(data)

    encoded = new_name.encode("utf-8")
    while len(encoded) > 16:                       # trim to 16 bytes without cutting a character
        new_name = new_name[:-1]
        encoded = new_name.encode("utf-8")
    if not encoded:
        raise ValueError('name cannot be empty')

    size_off = save_offsets['player_name_size_off']
    name_off = save_offsets['player_name_off']
    old_size = data[size_off]

    data = bytearray(data)
    data[size_off] = len(encoded)
    data[name_off:name_off + old_size] = encoded
    return data


def update_souls(data, new_souls):

    save_offset=parse_save(data)

    if new_souls>0xff_ff_ff_ff:
        new_souls=0xff_ff_ff_ff

    struct.pack_into('<I', data, save_offset['souls_off'], new_souls)


    return data


def update_stats(data, stat_name: str, new_value):

    save_offset = parse_save(data)

    stat_name = stat_name.strip()

    if new_value > 999:
        new_value = 999

    struct.pack_into(
        '<H',
        data,
        save_offset[stat_name + '_off'],
        new_value
    )

    return data

def update_gender(data, gender:str):

    save_offset=parse_save(data)

    if gender=='Male':
        gender_val=1

    elif gender=='Female':
        gender_val=0

    struct.pack_into(
        '<B',
        data,
        save_offset['gender_off_0'],
        gender_val
    )

    struct.pack_into(
        '<B',
        data,
        save_offset['gender_off_1'],
        gender_val
    )


    return data

def update_class(data, new_class:str):

    save_offset=parse_save(data)

    class_val= REVERSE_CLASS_MAP.get(new_class)

    struct.pack_into(
        '<B',
        data,
        save_offset['class_off'],
        class_val
    )

    return data


def update_hp(data, new_hp:int):

    save_offset=parse_save(data)
    
    if new_hp>0xff_ff_ff_ff:
        new_hp=0xff_ff_ff_ff
    
    struct.pack_into('<I', data, save_offset['hp_off_0'], new_hp)
    struct.pack_into('<I', data, save_offset['hp_off_1'], new_hp)
    struct.pack_into('<I', data, save_offset['hp_off_2'], new_hp)
    
    return data


def update_mp(data, new_mp:int):

    save_offset=parse_save(data)
    
    if new_mp>0xff_ff_ff_ff:
        new_mp=0xff_ff_ff_ff
    
    struct.pack_into('<I', data, save_offset['mp_off_0'], new_mp)
    struct.pack_into('<I', data, save_offset['mp_off_1'], new_mp)
    struct.pack_into('<I', data, save_offset['mp_off_2'], new_mp)
    
    return data


def update_st(data, new_st:int):

    save_offset=parse_save(data)
    
    if new_st>0xff_ff_ff_ff:
        new_st=0xff_ff_ff_ff
    
    struct.pack_into('<I', data, save_offset['st_off_0'], new_st)
    struct.pack_into('<I', data, save_offset['st_off_1'], new_st)
    struct.pack_into('<I', data, save_offset['st_off_2'], new_st)
    
    return data

def _item_id(item_name, item_type):
    if item_type not in ITEM_TYPES:
        raise ValueError(f'type not known: {item_type}')
    src = {'Weapon': weapons_json, 'Armor': armor_json,
           'Good': items_json, 'Ring': rings_json}[item_type]
    item_id = src.get(item_name)
    if item_id is None:
        raise ValueError(f'item not found: {item_name}')
    return item_id


def spawn_items(data, requests, quantity_over=False):
    """
    Add several items to the inventory in one pass.
    requests: list of dicts {name, type, quantity=1, durability=None, sort_id=None}

    Same rules as the game (EquipGameData::AddInventoryEquip -> sub_43DC00, written
    out by sub_2DE30):
      slot (_Index) = first free slot
      VariationId   = new handle (max existing + 1)
      DisplayId     = VariationId | (sortId << 16)
    then the list is rewritten sorted by slot, records named 00..N-1, count = N.
    durability / sort_id come from the item's param row in the game. The editor has
    no param tables yet, so if they are not given they are copied from an existing
    copy of the same item, otherwise 0. Weapons/armor need a real durability or they
    will spawn broken.
    """
    data = bytearray(data)
    items = parse_inventory(data)
    used = {it.slot for it in items}
    next_free = 0
    variation_id = max((it.variation_id for it in items if it.variation_id != 0xFFFFFFFF),
                       default=-1)
    owned = {(it.item_type, it.item_id): it for it in items}

    for req in requests:
        item_type = req['type']
        item_id = _item_id(req['name'], item_type)
        type_bits = ITEM_TYPES[item_type]
        qty = req.get('quantity', 1)
        quantity = min(qty, 9999) if quantity_over else min(qty, 99)

        same = owned.get((type_bits, item_id))
        durability = req.get('durability')
        if durability is None:
            durability = same.durability if same else 0
            if not same and item_type in ('Weapon', 'Armor'):
                log('WARNING: no durability given for', req['name'], '- spawning with 0')
        sort_id = req.get('sort_id')
        if sort_id is None:
            sort_id = same.sort_id if same else 0

        while next_free in used:
            next_free += 1
        slot = next_free
        used.add(slot)
        variation_id += 1

        new = INVENTORY(slot, type_bits, item_id, quantity, variation_id,
                        ((sort_id & 0xFFFF) << 16) | (variation_id & 0xFFFF), durability, 0)
        items.append(new)
        owned.setdefault((type_bits, item_id), new)
        log(f'spawned {req["name"]} in slot {slot}')

    return write_inventory(data, items)


def spawn_item(data, item_name: str, item_type: str, new_quantity=1,
               quantity_over=False, durability=None, sort_id=None):
    """Add one item to the inventory (see spawn_items for the rules)."""
    return spawn_items(data, [{'name': item_name, 'type': item_type, 'quantity': new_quantity,
                               'durability': durability, 'sort_id': sort_id}],
                       quantity_over=quantity_over)


if __name__ == '__main__':
    data = bytearray(open_file('saves/USR-DATA'))

    # data=update_name(data, 'newahmed')

    data = update_souls(data, 33222)
    data=spawn_item(data, 'Crescent Axe', 'Weapon')
    data=spawn_item(data, 'Dragon Short Sword+1', 'Weapon')

    data = fix_checksum(data)
    data = fix_size(data)
    inventory_log(data)
    write_file('USR-DATA', data)
