"""
FULL MAME / HYPERSPIN DATABASE PIPELINE
FINAL – COMPLETE – STABLE – DYNAMIC INJECTION
OPTIMIZED VERSION
"""

# =================================================
# IMPORTS
# =================================================
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict
import re
import shutil

# =================================================
# PATHS
# =================================================
BASE = Path(r"C:\Users\PC\Desktop\test")

MAME_EXE = BASE / "mame.exe"

# NEW: List of XML files to inject into the MAME database
INJECT_XMLS = [
    BASE / "ddpsdoj.xml",
    BASE / "ketmatsuri.xml"
]

# NEW: List of game ROM names to add from ALL_GAMES_XML
GAMES_TO_ADD = [
    "sbugger"
]

DB = BASE / "databases"
DB.mkdir(exist_ok=True)

MAME_XML = BASE / "mame.xml" 
HS_XML = BASE / "Mame 0.284.xml"
ALL_GAMES_XML = BASE / "Mame 0.284 All games.xml"

VERTICAL_XML = DB / "Mame 0.284 Vertical.xml"
NAOMI_XML = DB / "Naomi_Vertical.xml"
CLRMAME_XML = BASE / "MAMEclrmame.xml"

# =================================================
# DIRECTORY PATHS (CONSTANTS)
# =================================================
DIR_GENRES_VERTICAL = DB / "genres - vertical"
DIR_MANUFACTURER_VERTICAL = DB / "manufacturer - vertical"
DIR_MANUFACTURER_SHMUPS = DB / "manufacturer - shmups"
DIR_MANUFACTURER_BY_GENRES = DB / "manufacturer - vertical by genres"
DIR_GENRES_NAOMI = DB / "genres - naomi"
DIR_FINAL = DB / "!Final"

DIRS = [
    DIR_GENRES_VERTICAL,
    DIR_MANUFACTURER_VERTICAL,
    DIR_MANUFACTURER_SHMUPS,
    DIR_MANUFACTURER_BY_GENRES,
    DIR_GENRES_NAOMI
]
for d in DIRS: 
    d.mkdir(exist_ok=True)

# =================================================
# CONSTANTS & CONFIG
# =================================================
PRIORITY = [
    "Capcom","Cave","Data East","Gaelco",
    "Irem","Kaneko","Konami","Namco",
    "Nichibutsu","Nintendo","Sega",
    "Seibu Kaihatsu","SNK","Taito"
]

REMOVE_NAOMI = {"quizqgd","shors2k1","shorse","shorsep","shorsepr"}
REMOVE_GAMES = {
    "kbh", "kbm", "kbm2nd", "kbm3rd", "cmpmx10", "jammin",
    "rockn", "rockn2", "rockn3", "rockn4", "rockna",
    "re900", "re800v1a", "re800v3", "jantotsu", "daifugo",
    "cdsteljn", "ron2", "luckyrlt", "msjiken", "telmahjn",
    "aerofgtsg", "brvbladeg", "cburnrub2", "cruisin5", "cdiscon1",
    "kas89", "cpsoccerj", "cpsoccer", "cptennis", "cptennisj",
    "sidewndr", "spellbnd", "supdrapob", "setaroul",
    "sidampkr", "sidampkra", "39in1", "4in1", "decodark16",
    "decomult", "sspacaho", "twinbeeb", "shikigama", "re800v1",
    "re800ea", "rcirulet", "multiped", "decodark15", "decodark",
    "supdrapo", "supdrapoa", "cbtime", "cburnrubj", "clocknchj",
    "mag_time", "20pacgal", "20pacgalr0", "20pacgalr1", "20pacgalr2",
    "20pacgalr3", "20pacgalr4", "25pacmano", "solarwar", "invqix",
    "setaroula", "atetrisc", "atetrisc2", "bronx", "25pacmano",
    "chamburger", "csweetht", "25pacman", "cyclshtg"
}

IGNORE_ORPHAN_FIX = {"ddp3", "ddpdojblk"}

# =================================================
# HELPERS
# =================================================
def clean_filename(text):
    return re.sub(r'[\\/:*?"<>|]', '', (text or "").strip()) or "Unknown"

def normalize(text):
    return re.sub(r"\s*\(.*?\)", "", (text or "").strip())

def pick_manufacturer(raw):
    if not raw:
        return None
    mfg_text = raw.lower().strip()
    for p in PRIORITY:
        if p.lower() in mfg_text:
            return p
    return None

def indent(elem, level=0):
    """Format XML with proper indentation"""
    i = "\n" + level * "    "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "    "
        for c in elem:
            indent(c, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    elif level and (not elem.tail or not elem.tail.strip()):
        elem.tail = i

def write_xml(filepath, root, verbose=True):
    """Wrapper: indent + write XML in one operation"""
    indent(root)
    ET.ElementTree(root).write(filepath, encoding="utf-8", xml_declaration=True)
    if verbose:
        print(f"  ✔ Written to {filepath.name}")

def create_game_node(machine, lookup=None):
    """
    UNIFIED function: convert MAME machine or game element to HyperSpin game node
    lookup: optional dict to find genre if not in machine
    """
    name = machine.get("name")
    g = ET.Element("game", name=name, index="", image="")
    
    for t in ("description", "manufacturer", "year"):
        ET.SubElement(g, t).text = machine.findtext(t) or ""
    
    genre = machine.findtext("genre") or ""
    if not genre and lookup:
        genre = lookup.get(name, "Shoot-'Em-Up")
    elif not genre:
        genre = "Shoot-'Em-Up"
    
    ET.SubElement(g, "genre").text = genre
    ET.SubElement(g, "cloneof").text = machine.get("cloneof") or ""
    ET.SubElement(g, "crc").text = ""
    ET.SubElement(g, "rating").text = ""
    ET.SubElement(g, "enabled").text = "Yes"
    
    return g

def validate_xml_file(filepath):
    """Check if XML file exists and is readable"""
    if not filepath.exists():
        print(f"  ⚠ WARNING: {filepath.name} not found, skipping...")
        return False
    try:
        ET.parse(filepath)
        return True
    except ET.ParseError as e:
        print(f"  ⚠ WARNING: {filepath.name} is malformed: {e}, skipping...")
        return False

# =================================================
# 1) GENERATE & PATCH MAME.XML
# =================================================
print("Generating mame.xml...")
with open(MAME_XML, "w", encoding="utf-8") as f:
    subprocess.run([MAME_EXE, "-listxml"], stdout=f, stderr=subprocess.DEVNULL, check=True)

mame_tree = ET.parse(MAME_XML)
mame_root = mame_tree.getroot()

# Track injected elements to add them to HyperSpin later
injected_nodes_for_hs = []

for xml_path in INJECT_XMLS:
    if validate_xml_file(xml_path):
        print(f"Patching {xml_path.name} into MAME database...")
        inject_element = ET.parse(xml_path).getroot() 
        game_name = inject_element.get('name')
        
        if mame_root.find(f".//machine[@name='{game_name}']") is None:
            mame_root.append(inject_element)
            injected_nodes_for_hs.append(inject_element)
            print(f"  ✔ {game_name} injected successfully.")
        else:
            print(f"  ⚠ {game_name} already exists in MAME database, skipping...")

write_xml(MAME_XML, mame_root, verbose=False)

# =================================================
# LOAD COMPLETE GAME LOOKUP (ONE TIME ONLY)
# =================================================
print("Loading complete game database for lookups...")
if not validate_xml_file(ALL_GAMES_XML):
    print("ERROR: Cannot load ALL_GAMES_XML, aborting...")
    exit(1)

all_games_tree = ET.parse(ALL_GAMES_XML)
all_games_root = all_games_tree.getroot()

# Create single lookup dict
lookup = {g.get("name"): g.findtext("genre") for g in all_games_root.findall("game")}
all_games_dict = {g.get("name"): g for g in all_games_root.findall("game")}

# =================================================
# 2) BUILD NAOMI & ATOMISWAVE LIST
# =================================================
print("Building Naomi and Atomiswave lists...")
naomi_menu = ET.Element("menu")
atomis_list = []

for m in mame_root.findall("machine"):
    source = m.get("sourcefile", "").lower()
    disp = m.find("display")
    if disp is None or disp.get("rotate") not in ("90", "270"):
        continue

    if source.endswith("naomi.cpp") and m.get("name") not in REMOVE_NAOMI:
        naomi_menu.append(create_game_node(m, lookup))
    
    if source == "sega/dc_atomiswave.cpp":
        atomis_list.append(create_game_node(m, lookup))

# Save Naomi Vertical DB
write_xml(NAOMI_XML, naomi_menu)

# Pre-compute vertical names set for section 4
vertical_names = {m.get("name") for m in mame_root.findall("machine") 
                  if m.find("display") is not None and m.find("display").get("rotate") in ("90", "270")}

# =================================================
# 3) MERGE INTO MAIN HS DB & SORT
# =================================================
print("Merging all sources into main HyperSpin DB...")
hs_tree = ET.parse(HS_XML)
hs_root = hs_tree.getroot()
existing = {g.get("name") for g in hs_root.findall("game")}

# A) Add CUSTOM INJECTED games (ddpsdoj, ketmatsuri)
for node in injected_nodes_for_hs:
    if node.get("name") not in existing:
        hs_root.append(create_game_node(node, lookup))
        existing.add(node.get("name"))

# B) Add Naomi games
for g in naomi_menu.findall("game"):
    if g.get("name") not in existing:
        hs_root.append(g)
        existing.add(g.get("name"))

# C) Add Atomiswave games
for g in atomis_list:
    if g.get("name") not in existing:
        hs_root.append(g)
        existing.add(g.get("name"))

# =================================================
# 3.4) ADD CUSTOM GAMES FROM GAMES_TO_ADD
# =================================================
print("Adding custom games from GAMES_TO_ADD...")

for rom_name in GAMES_TO_ADD:
    if rom_name in all_games_dict:
        if rom_name not in existing:
            game_elem = all_games_dict[rom_name]
            hs_root.append(create_game_node(game_elem, lookup))
            existing.add(rom_name)
            print(f"  ✔ Added '{rom_name}' to database")
        else:
            print(f"  ⚠ '{rom_name}' already exists in database, skipping")
    else:
        print(f"  ❌ '{rom_name}' NOT FOUND in {ALL_GAMES_XML.name}")

# =================================================
# 3.5) FIX MISSING PARENTS IN HS XML
# =================================================
print("Checking for missing parents in HyperSpin database...")

hs_games = {g.get("name"): g for g in hs_root.findall("game")}
missing_parents = []

for game_name, game_elem in hs_games.items():
    parent_name = (game_elem.findtext("cloneof") or "").strip()
    
    if parent_name and parent_name not in hs_games:
        if parent_name in all_games_dict:
            missing_parents.append((game_name, parent_name, all_games_dict[parent_name]))

for child_name, parent_name, parent_elem in missing_parents:
    hs_root.append(create_game_node(parent_elem, lookup))
    hs_games[parent_name] = parent_elem
    print(f"  ✔ Added missing parent '{parent_name}' (needed by '{child_name}')")

if not missing_parents:
    print("  ✔ No missing parents found")

# --- RESTRUCTURE DDP RELATIONSHIPS ---
print("Applying DDP Parent/Clone swap in HyperSpin XML...")
NEW_PARENT = "ddpdojblk"
OLD_PARENT = "ddp3"

for g in hs_root.findall("game"):
    name = g.get("name")
    clone_node = g.find("cloneof")
    
    if name == NEW_PARENT:
        if clone_node is not None:
            clone_node.text = ""
    elif name == OLD_PARENT:
        if clone_node is not None:
            clone_node.text = NEW_PARENT
    elif clone_node is not None and clone_node.text == OLD_PARENT:
        clone_node.text = NEW_PARENT

# Sort everything alphabetically
sorted_games = sorted(hs_root.findall("game"), key=lambda x: x.get("name").lower())
new_hs_root = ET.Element("menu")
for g in sorted_games:
    new_hs_root.append(g)

write_xml(HS_XML, new_hs_root, verbose=False)

# =================================================
# 4) FILTER VERTICAL (INCLUDES INJECTED DDPSDOJ)
# =================================================
print("Creating Vertical Database...")

final_vertical_menu = ET.Element("menu")
for g in new_hs_root.findall("game"):
    name = g.get("name")
    parent = (g.findtext("cloneof") or "").strip() or name
    
    if (parent in vertical_names or name in vertical_names) and name not in REMOVE_GAMES:
        final_vertical_menu.append(g)

write_xml(VERTICAL_XML, final_vertical_menu, verbose=False)

# =================================================
# 4.5) FIX ORPHAN CLONES (VERTICAL ONLY)
# =================================================
print("Fixing orphan clones inside Vertical database...")

# Build official clone groups (MAME order preserved)
official_clone_groups = defaultdict(list)
for machine in mame_root.findall("machine"):
    name = machine.get("name")
    parent = machine.get("cloneof")
    if parent:
        official_clone_groups[parent].append(name)

# Build quick lookup for vertical games
vertical_games = {g.get("name"): g for g in final_vertical_menu.findall("game")}

unique_promoted = []
multi_groups = {}

for parent, clones in official_clone_groups.items():
    if parent in IGNORE_ORPHAN_FIX:
        continue

    present_clones = [c for c in clones if c in vertical_games]

    if present_clones and parent not in vertical_games:
        if len(present_clones) == 1:
            node = vertical_games[present_clones[0]]
            clone_node = node.find("cloneof")
            if clone_node is not None:
                clone_node.text = ""
            unique_promoted.append(present_clones[0])
        else:
            new_parent = present_clones[0]
            node = vertical_games[new_parent]
            clone_node = node.find("cloneof")
            if clone_node is not None:
                clone_node.text = ""
            
            for c in present_clones[1:]:
                node = vertical_games[c]
                clone_node = node.find("cloneof")
                if clone_node is not None:
                    clone_node.text = new_parent
            
            multi_groups[new_parent] = present_clones[1:]

print("  ✔ Orphan fix complete.")

print("\n--- UNIQUE ORPHANS PROMOTED ---")
if unique_promoted:
    for name in sorted(unique_promoted):
        print("  ", name)
else:
    print("  None")

print("\n--- MULTI-ORPHAN GROUPS REBUILT ---")
if multi_groups:
    for parent, children in multi_groups.items():
        print(f"\n  New Parent: {parent}")
        for c in children:
            print("     -", c)
else:
    print("  None")

print(f"\nTotal unique promoted: {len(unique_promoted)}")
print(f"Total multi groups rebuilt: {len(multi_groups)}")

write_xml(VERTICAL_XML, final_vertical_menu, verbose=False)

# =================================================
# 5) UNIFIED SPLITS (GENRE / MANUFACTURER) - SINGLE PASS
# =================================================
print("Creating split databases (single pass)...")

root = final_vertical_menu

# Pre-compute all categorizations in one pass
by_genre = defaultdict(list)
by_manu = defaultdict(list)
shmup_games = []
manu_by_genre = defaultdict(lambda: defaultdict(list))

for g in root.findall("game"):
    name = g.get("name")
    genre = g.findtext("genre") or "Unknown"
    manu = pick_manufacturer(g.findtext("manufacturer"))
    
    # Genre vertical split
    by_genre[clean_filename(genre)].append(g)
    
    # Manufacturer vertical split
    if manu:
        by_manu[manu].append(g)
    
    # Shmups by manufacturer (only if Shoot-'Em-Up)
    if "Shoot-'Em-Up" in genre:
        shmup_games.append((manu, g))
    
    # Manufacturer -> Genre structure
    if manu:
        manu_by_genre[manu][genre].append(g)

# Write Genre splits
for genre, games in by_genre.items():
    menu = ET.Element("menu")
    for g in games:
        menu.append(g)
    write_xml(DIR_GENRES_VERTICAL / f"{genre}.xml", menu, verbose=False)

# Write Manufacturer splits
for manu, games in by_manu.items():
    menu = ET.Element("menu")
    for g in games:
        menu.append(g)
    write_xml(DIR_MANUFACTURER_VERTICAL / f"{manu}.xml", menu, verbose=False)

# Write Shmups by Manufacturer splits
shmup_by_manu = defaultdict(list)
for manu, g in shmup_games:
    if manu:
        shmup_by_manu[manu].append(g)

for manu, games in shmup_by_manu.items():
    menu = ET.Element("menu")
    for g in games:
        menu.append(g)
    write_xml(DIR_MANUFACTURER_SHMUPS / f"{manu}.xml", menu, verbose=False)

# Write Manufacturer -> Genre subfolders
for manu, genres in manu_by_genre.items():
    d = DIR_MANUFACTURER_BY_GENRES / manu
    d.mkdir(exist_ok=True)
    for genre, games in genres.items():
        menu = ET.Element("menu")
        for g in games:
            menu.append(g)
        write_xml(d / f"{clean_filename(genre)}.xml", menu, verbose=False)

# Write Naomi genres
by_genre_naomi = defaultdict(list)
for g in naomi_menu.findall("game"):
    by_genre_naomi[clean_filename(g.findtext("genre"))].append(g)

for genre, games in by_genre_naomi.items():
    menu = ET.Element("menu")
    for g in games:
        menu.append(g)
    write_xml(DIR_GENRES_NAOMI / f"{genre}.xml", menu, verbose=False)

# =================================================
# 6) FINAL CLEANUP & ORGANIZATION
# =================================================
print("Organizing final output structure...")

DIR_FINAL.mkdir(exist_ok=True)

# Move MAME Vertical
m_dir = DIR_FINAL / "MAME"
m_dir.mkdir(exist_ok=True)
shutil.copy2(VERTICAL_XML, m_dir / "MAME.xml")
for f in DIR_GENRES_VERTICAL.glob("*.xml"):
    shutil.copy2(f, m_dir / f.name)

# Move Naomi
n_dir = DIR_FINAL / "Sega Naomi"
n_dir.mkdir(exist_ok=True)
shutil.copy2(NAOMI_XML, n_dir / "Sega Naomi.xml")
for f in DIR_GENRES_NAOMI.glob("*.xml"):
    shutil.copy2(f, n_dir / f.name)

# Move Shmups folder
s_dir = DIR_FINAL / "Shoot-'Em-Up"
s_dir.mkdir(exist_ok=True)
shmup_file = DIR_GENRES_VERTICAL / "Shoot-'Em-Up.xml"
if shmup_file.exists():
    shutil.copy2(shmup_file, s_dir / "Shoot-'Em-Up.xml")
for f in DIR_MANUFACTURER_SHMUPS.glob("*.xml"):
    shutil.copy2(f, s_dir / f.name)

# Move Manufacturer folders
for xml_file in DIR_MANUFACTURER_VERTICAL.glob("*.xml"):
    target = DIR_FINAL / xml_file.stem
    target.mkdir(exist_ok=True)
    shutil.copy2(xml_file, target / xml_file.name)

if DIR_MANUFACTURER_BY_GENRES.exists():
    shutil.copytree(DIR_MANUFACTURER_BY_GENRES, DIR_FINAL, dirs_exist_ok=True)

# =================================================
# 7) CLRMAMEPRO XML (ROM INTEGRITY FIX)
# =================================================
print("Generating MAMEclrmame.xml with Parent Integrity...")

# 1. Games to actually play (Vertical + Naomi + Atomiswave)
allowed_names = {g.get("name") for g in final_vertical_menu.findall("game")}
for g in naomi_menu.findall("game"):
    allowed_names.add(g.get("name"))

# 2. Find every parent required by these games
required_parents = set()
for machine in mame_root.findall("machine"):
    name = machine.get("name")
    if name in allowed_names:
        p_name = machine.get("cloneof")
        if p_name:
            required_parents.add(p_name)

# 3. Combine
total_set = allowed_names.union(required_parents)

# 4. Build XML
new_mame_root = ET.Element("mame", mame_root.attrib)
for machine in mame_root.findall("machine"):
    if machine.get("name") in total_set:
        new_mame_root.append(machine)

write_xml(CLRMAME_XML, new_mame_root, verbose=False)

print(f"✔ DAT generated with {len(total_set)} total entries.")
print(f"  ({len(required_parents - allowed_names)} hidden parents added to ensure Merged sets run correctly.)")

print("\n✔ ALL STEPS COMPLETE")
