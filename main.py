"""
FULL MAME / HYPERSPIN DATABASE PIPELINE
FINAL – COMPLETE – STABLE – DYNAMIC INJECTION
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
BASE = Path(r"C:\Users\PC\OneDrive\Perso\buy\HS2026\files")

MAME_EXE = BASE / "mame.exe"

# NEW: List of XML files to inject into the MAME database
INJECT_XMLS = [
    BASE / "ddpsdoj.xml",
    BASE / "ketmatsuri.xml"
]

DB = BASE / "databases"
DB.mkdir(exist_ok=True)

MAME_XML = BASE / "mame.xml" 
HS_XML = BASE / "Mame 0.284.xml"
ALL_GAMES_XML = BASE / "Mame 0.284 All games.xml"

VERTICAL_XML = DB / "Mame 0.284 Vertical.xml"
NAOMI_XML = DB / "Naomi_Vertical.xml"

# Directory setup
DIRS = [
    DB / "genres - vertical",
    DB / "manufacturer - vertical",
    DB / "manufacturer - shmups",
    DB / "manufacturer - vertical by genres",
    DB / "genres - naomi"
]
for d in DIRS: d.mkdir(exist_ok=True)

# =================================================
# CONSTANTS & CONFIG
# =================================================
PRIORITY = [
    "Capcom","Cave","Data East","Gaelco",
    "Irem","Kaneko","Konami","Namco",
    "Nichibutsu","Nintendo","Sega",
    "Seibu Kaihatsu","SNK","Taito"
]

#"Atari","Bally","IGS","Jaleco",,"Midway","Psikyo","Sammy"

REMOVE_NAOMI = {"quizqgd","shors2k1","shorse","shorsep","shorsepr"}
REMOVE_GAMES = {
    "kbh", "kbm", "kbm2nd", "kbm3rd", "cmpmx10", "jammin",
    "rockn", "rockn2", "rockn3", "rockn4", "rockna",
    "re900", "re800v1a", "re800v3", "jantotsu", "daifugo",
    "cdsteljn", "ron2", "luckyrlt", "msjiken", "telmahjn",
    "aerofgtsg", "brvbladeg", "cburnrub2", "cruisin5", "cdiscon1",
    "kas89", "cpsoccerj", "cpsoccer", "cptennis", "cptennisj",
    "sidewndr", "spellbnd", "sdtennis", "supdrapob", "setaroul",
    "sidampkr", "sidampkra", "39in1", "4in1", "decodark16",
    "decomult", "sspacaho", "twinbeeb", "shikigama", "re800v1",
    "re800ea", "rcirulet", "multiped", "decodark15", "decodark",
    "supdrapo", "supdrapoa", "cbtime", "cburnrubj", "clocknchj",
    "mag_time", "20pacgal", "20pacgalr0", "20pacgalr1", "20pacgalr2",
    "20pacgalr3", "20pacgalr4", "25pacmano", "solarwar", "invqix",
    "setaroula", "atetrisc", "atetrisc2", "bronx", "25pacmano",
    "chamburger", "csweetht"
}

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
    
    # We use lower() to ensure "DATA EAST" and "Data East" both match
    mfg_text = raw.lower().strip()
    
    for p in PRIORITY:
        # This catches "Data East", "Data East USA", "Export / Data East", etc.
        if p.lower() in mfg_text:
            return p
    return None

def indent(elem, level=0):
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
    if xml_path.exists():
        print(f"Patching {xml_path.name} into MAME database...")
        inject_element = ET.parse(xml_path).getroot() 
        game_name = inject_element.get('name')
        
        if mame_root.find(f".//machine[@name='{game_name}']") is None:
            mame_root.append(inject_element)
            # Store this for the HyperSpin merge in Section 3
            injected_nodes_for_hs.append(inject_element)
            print(f"  ✔ {game_name} injected successfully.")

indent(mame_root)
mame_tree.write(MAME_XML, encoding="utf-8", xml_declaration=True)

# Load master lookup for Genres
lookup = {g.get("name"): g.findtext("genre") for g in ET.parse(ALL_GAMES_XML).getroot().findall("game")}

# Helper to convert MAME machine node to HyperSpin game node
def create_hs_node(machine):
    name = machine.get("name")
    g = ET.Element("game", name=name, index="", image="")
    for t in ("description", "manufacturer", "year"):
        ET.SubElement(g, t).text = machine.findtext(t) or ""
    # Use lookup, but if not found (like for injected games), check if the injected XML has a genre
    ET.SubElement(g, "genre").text = lookup.get(name) or machine.findtext("genre") or "Shoot-'Em-Up"
    ET.SubElement(g, "cloneof").text = machine.get("cloneof") or ""
    ET.SubElement(g, "crc").text = ""
    ET.SubElement(g, "rating").text = ""
    ET.SubElement(g, "enabled").text = "Yes"
    return g

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

    def create_game_node(machine):
        g = ET.Element("game", name=machine.get("name"), index="", image="")
        for t in ("description", "manufacturer", "year"):
            ET.SubElement(g, t).text = machine.findtext(t) or ""
        ET.SubElement(g, "genre").text = lookup.get(machine.get("name"), "")
        ET.SubElement(g, "cloneof").text = machine.get("cloneof") or ""
        ET.SubElement(g, "crc").text = ""
        ET.SubElement(g, "rating").text = ""
        ET.SubElement(g, "enabled").text = "Yes"
        return g

    if source.endswith("naomi.cpp") and m.get("name") not in REMOVE_NAOMI:
        naomi_menu.append(create_game_node(m))
    
    if source == "sega/dc_atomiswave.cpp":
        atomis_list.append(create_game_node(m))

# Save Naomi Vertical DB and splits
indent(naomi_menu)
ET.ElementTree(naomi_menu).write(NAOMI_XML, encoding="utf-8", xml_declaration=True)
by_genre_n = defaultdict(list)
for g in naomi_menu.findall("game"):
    by_genre_n[clean_filename(g.findtext("genre"))].append(g)
for genre, games in by_genre_n.items():
    m_sub = ET.Element("menu")
    for g in games: m_sub.append(g)
    ET.ElementTree(m_sub).write(DB / "genres - naomi" / f"{genre}.xml", encoding="utf-8", xml_declaration=True)

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
        hs_root.append(create_hs_node(node))
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

# --- RESTRUCTURE DDP RELATIONSHIPS ---
print("Applying DDP Parent/Clone swap in HyperSpin XML...")
NEW_PARENT = "ddpdojblk"
OLD_PARENT = "ddp3"

for g in hs_root.findall("game"):
    name = g.get("name")
    clone_node = g.find("cloneof")
    
    if name == NEW_PARENT:
        # Make ddpdojblk the parent (clear cloneof)
        if clone_node is not None:
            clone_node.text = ""
            
    elif name == OLD_PARENT:
        # Make ddp3 a clone of ddpdojblk
        if clone_node is not None:
            clone_node.text = NEW_PARENT
            
    elif clone_node is not None and clone_node.text == OLD_PARENT:
        # All other sub-clones (ddpdoja, ddpdojp, etc) now point to ddpdojblk
        clone_node.text = NEW_PARENT
# -------------------------------------

# Sort everything alphabetically
sorted_games = sorted(hs_root.findall("game"), key=lambda x: x.get("name").lower())
new_hs_root = ET.Element("menu")
for g in sorted_games:
    new_hs_root.append(g)

indent(new_hs_root)
ET.ElementTree(new_hs_root).write(HS_XML, encoding="utf-8", xml_declaration=True)

# =================================================
# 4) FILTER VERTICAL (INCLUDES INJECTED DDPSDOJ)
# =================================================
print("Creating Vertical Database...")
# Build a set of vertical machine names from the MAME XML
vertical_names = set()
for m in mame_root.findall("machine"):
    d = m.find("display")
    if d is not None and d.get("rotate") in ("90", "270"):
        vertical_names.add(m.get("name"))

# Filter HS_XML based on the vertical list
final_vertical_menu = ET.Element("menu")
for g in new_hs_root.findall("game"):
    name = g.get("name")
    parent = (g.findtext("cloneof") or "").strip() or name
    
    # ddpsdoj is now in 'vertical_names' because we injected its display/rotate info!
    if (parent in vertical_names or name in vertical_names) and name not in REMOVE_GAMES:
        final_vertical_menu.append(g)

indent(final_vertical_menu)
ET.ElementTree(final_vertical_menu).write(VERTICAL_XML, encoding="utf-8", xml_declaration=True)

# =================================================
# 4.5) FIX ORPHAN CLONES (VERTICAL ONLY)
# =================================================
print("Fixing orphan clones inside Vertical database...")

# Ignore DDP completely
IGNORE_ORPHAN_FIX = {"ddp3", "ddpdojblk"}

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

    # Parent missing but clones present → orphan case
    if present_clones and parent not in vertical_games:

        if len(present_clones) == 1:
            # UNIQUE ORPHAN
            node = vertical_games[present_clones[0]]
            clone_node = node.find("cloneof")
            if clone_node is not None:
                clone_node.text = ""

            unique_promoted.append(present_clones[0])

        else:
            # MULTIPLE ORPHANS
            # First in MAME order becomes parent
            new_parent = present_clones[0]

            # Promote first
            node = vertical_games[new_parent]
            clone_node = node.find("cloneof")
            if clone_node is not None:
                clone_node.text = ""

            # Others point to new parent
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

print("\nTotal unique promoted:", len(unique_promoted))
print("Total multi groups rebuilt:", len(multi_groups))

# Rewrite Vertical XML after orphan fixes
indent(final_vertical_menu)
ET.ElementTree(final_vertical_menu).write(
    VERTICAL_XML,
    encoding="utf-8",
    xml_declaration=True
)

# =================================================
# 5) SPLITS (GENRE / MANUFACTURER)
# =================================================
root = final_vertical_menu
# Vertical by Genre
by_genre = defaultdict(list)
for g in root.findall("game"):
    by_genre[clean_filename(g.findtext("genre"))].append(g)
for genre, games in by_genre.items():
    m = ET.Element("menu")
    for g in games: m.append(g)
    ET.ElementTree(m).write(DB / "genres - vertical" / f"{genre}.xml", encoding="utf-8", xml_declaration=True)

# Vertical by Manufacturer
for manu in PRIORITY:
    games = [g for g in root.findall("game") if pick_manufacturer(g.findtext("manufacturer")) == manu]
    if games:
        m = ET.Element("menu")
        for g in games: m.append(g)
        ET.ElementTree(m).write(DB / "manufacturer - vertical" / f"{manu}.xml", encoding="utf-8", xml_declaration=True)

# Shmups by Manufacturer
shmup_file = DB / "genres - vertical" / "Shoot-'Em-Up.xml"
if shmup_file.exists():
    shmups = ET.parse(shmup_file).getroot()
    for manu in PRIORITY:
        games = [g for g in shmups.findall("game") if pick_manufacturer(g.findtext("manufacturer")) == manu]
        if games:
            m = ET.Element("menu")
            for g in games: m.append(g)
            ET.ElementTree(m).write(DB / "manufacturer - shmups" / f"{manu}.xml", encoding="utf-8", xml_declaration=True)

# Manufacturer -> Genre subfolders
bucket = defaultdict(lambda: defaultdict(list))
for g in root.findall("game"):
    manu = pick_manufacturer(g.findtext("manufacturer"))
    if manu:
        bucket[manu][g.findtext("genre") or "Unknown"].append(g)
for manu, genres in bucket.items():
    d = DB / "manufacturer - vertical by genres" / manu
    d.mkdir(exist_ok=True)
    for genre, games in genres.items():
        m = ET.Element("menu")
        for g in games: m.append(g)
        ET.ElementTree(m).write(d / f"{clean_filename(genre)}.xml", encoding="utf-8", xml_declaration=True)

# =================================================
# 6) FINAL CLEANUP & ORGANIZATION
# =================================================
# Fix &apos;
replacements = {"<genre>Shoot-'Em-Up</genre>": "<genre>Shoot-&apos;Em-Up</genre>", 
                "<genre>Beat-'Em-Up</genre>": "<genre>Beat-&apos;Em-Up</genre>"}
for xml in DB.rglob("*.xml"):
    text = xml.read_text(encoding="utf-8")
    for old, new in replacements.items(): text = text.replace(old, new)
    xml.write_text(text, encoding="utf-8")

# Final move to !Final
FINAL_DIR = DB / "!Final"
FINAL_DIR.mkdir(exist_ok=True)

# Move MAME Vertical
m_dir = FINAL_DIR / "MAME"
m_dir.mkdir(exist_ok=True)
shutil.copy2(VERTICAL_XML, m_dir / "MAME.xml")
for f in (DB / "genres - vertical").glob("*.xml"): shutil.copy2(f, m_dir / f.name)

# Move Naomi
n_dir = FINAL_DIR / "Sega Naomi"
n_dir.mkdir(exist_ok=True)
shutil.copy2(NAOMI_XML, n_dir / "Sega Naomi.xml")
for f in (DB / "genres - naomi").glob("*.xml"): shutil.copy2(f, n_dir / f.name)

# Move Shmups folder
s_dir = FINAL_DIR / "Shoot-'Em-Up"
s_dir.mkdir(exist_ok=True)
if shmup_file.exists(): shutil.copy2(shmup_file, s_dir / "Shoot-'Em-Up.xml")
for f in (DB / "manufacturer - shmups").glob("*.xml"): shutil.copy2(f, s_dir / f.name)

# Move Manufacturer folders
for xml_file in (DB / "manufacturer - vertical").glob("*.xml"):
    target = FINAL_DIR / xml_file.stem
    target.mkdir(exist_ok=True)
    shutil.copy2(xml_file, target / xml_file.name)
if (DB / "manufacturer - vertical by genres").exists():
    shutil.copytree(DB / "manufacturer - vertical by genres", FINAL_DIR, dirs_exist_ok=True)

# =================================================
# 7) CLRMAMEPRO XML (ROM INTEGRITY FIX)
# =================================================
print("Generating MAMEclrmame.xml with Parent Integrity...")
CLRMAME_XML = BASE / "MAMEclrmame.xml"

# 1. Start with the games you actually want to play (Vertical + Naomi + Atomiswave)
# We use the names from your finalized vertical menu (which already includes sbugger/ddp fixes)
allowed_names = {g.get("name") for g in final_vertical_menu.findall("game")}

# 2. Add Naomi/Atomiswave names if they aren't already in the vertical menu
for g in naomi_menu.findall("game"):
    allowed_names.add(g.get("name"))

# 3. Find every parent required by these games to ensure Merged sets work in RomVault
# We scan the raw MAME XML to find what 'cloneof' parents these games need
required_parents = set()
for machine in mame_root.findall("machine"):
    name = machine.get("name")
    if name in allowed_names:
        p_name = machine.get("cloneof")
        if p_name:
            required_parents.add(p_name)

# 4. Combine them (Played Games + Required Parents)
total_set = allowed_names.union(required_parents)

# 5. Build the XML tree for RomVault/CLRMamePro
new_mame_root = ET.Element("mame", mame_root.attrib)
for machine in mame_root.findall("machine"):
    if machine.get("name") in total_set:
        new_mame_root.append(machine)

indent(new_mame_root)
ET.ElementTree(new_mame_root).write(CLRMAME_XML, encoding="utf-8", xml_declaration=True)

print(f"✔ DAT generated with {len(total_set)} total entries.")
print(f"  ({len(required_parents - allowed_names)} hidden parents added to ensure Merged sets run correctly.)")

print("\n✔ ALL STEPS COMPLETE")
