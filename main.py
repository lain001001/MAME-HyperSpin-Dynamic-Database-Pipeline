"""
FULL MAME / HYPERSPIN DATABASE PIPELINE
FINAL – COMPLETE – STABLE – DYNAMIC INJECTION – SORTED BY DESCRIPTION
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
    "20pacgalr3", "20pacgalr4", "solarwar", "invqix", "galsnew", "cburnrub",
    "koikoip2", "atetrisc", "atetrisc2", "chamburger", "csweetht",
    "grdnstrmg", "headonn", "setaroula", "turbo", "turbob", "turbobl",
    "turboc", "turbod", "turboe"
}

# =================================================
# HELPERS
# =================================================
def clean_filename(text):
    return re.sub(r'[\\/:*?"<>|]', '', (text or "").strip()) or "Unknown"

def pick_manufacturer(raw):
    if not raw: return None
    mfg_text = raw.lower().strip()
    for p in PRIORITY:
        if p.lower() in mfg_text: return p
    return None

def indent(elem, level=0):
    i = "\n" + level * "    "
    if len(elem):
        if not elem.text or not elem.text.strip(): elem.text = i + "    "
        for c in elem: indent(c, level + 1)
        if not elem.tail or not elem.tail.strip(): elem.tail = i
    elif level and (not elem.tail or not elem.tail.strip()): elem.tail = i

# =================================================
# 1) GENERATE & PATCH MAME.XML
# =================================================
print("Generating mame.xml...")
with open(MAME_XML, "w", encoding="utf-8") as f:
    subprocess.run([MAME_EXE, "-listxml"], stdout=f, stderr=subprocess.DEVNULL, check=True)

mame_tree = ET.parse(MAME_XML)
mame_root = mame_tree.getroot()
injected_nodes_for_hs = []

for xml_path in INJECT_XMLS:
    if xml_path.exists():
        print(f"Patching {xml_path.name} into MAME database...")
        inject_element = ET.parse(xml_path).getroot() 
        game_name = inject_element.get('name')
        if mame_root.find(f".//machine[@name='{game_name}']") is None:
            mame_root.append(inject_element)
            injected_nodes_for_hs.append(inject_element)

indent(mame_root)
mame_tree.write(MAME_XML, encoding="utf-8", xml_declaration=True)

lookup = {g.get("name"): g.findtext("genre") for g in ET.parse(ALL_GAMES_XML).getroot().findall("game")}

def create_hs_node(machine):
    name = machine.get("name")
    g = ET.Element("game", name=name, index="", image="")
    for t in ("description", "manufacturer", "year"):
        ET.SubElement(g, t).text = machine.findtext(t) or ""
    ET.SubElement(g, "genre").text = lookup.get(name) or machine.findtext("genre") or "Shoot-'Em-Up"
    ET.SubElement(g, "cloneof").text = machine.get("cloneof") or ""
    for t in ("crc", "rating"): ET.SubElement(g, t).text = ""
    ET.SubElement(g, "enabled").text = "Yes"
    return g

# =================================================
# 2) BUILD NAOMI & ATOMISWAVE LIST (SORTED)
# =================================================
print("Building Naomi and Atomiswave lists...")
naomi_menu = ET.Element("menu")
atomis_list = []

for m in mame_root.findall("machine"):
    source = m.get("sourcefile", "").lower()
    disp = m.find("display")
    if disp is None or disp.get("rotate") not in ("90", "270"): continue

    if source.endswith("naomi.cpp") and m.get("name") not in REMOVE_NAOMI:
        naomi_menu.append(create_hs_node(m))
    if source == "sega/dc_atomiswave.cpp":
        atomis_list.append(create_hs_node(m))

# SORT NAOMI BY DESCRIPTION
naomi_sorted = sorted(naomi_menu.findall("game"), key=lambda g: (g.findtext("description") or "").lower())
naomi_menu[:] = naomi_sorted

indent(naomi_menu)
ET.ElementTree(naomi_menu).write(NAOMI_XML, encoding="utf-8", xml_declaration=True)

# Split Naomi by Genre
by_genre_n = defaultdict(list)
for g in naomi_menu.findall("game"):
    by_genre_n[clean_filename(g.findtext("genre"))].append(g)
for genre, games in by_genre_n.items():
    m_sub = ET.Element("menu")
    for g in games: m_sub.append(g)
    ET.ElementTree(m_sub).write(DB / "genres - naomi" / f"{genre}.xml", encoding="utf-8", xml_declaration=True)

# =================================================
# 3) MERGE INTO MAIN HS DB
# =================================================
print("Merging all sources into main HyperSpin DB...")
hs_tree = ET.parse(HS_XML)
hs_root = hs_tree.getroot()
existing = {g.get("name") for g in hs_root.findall("game")}

for node in injected_nodes_for_hs:
    if node.get("name") not in existing:
        hs_root.append(create_hs_node(node))
        existing.add(node.get("name"))

for g in naomi_menu.findall("game"):
    if g.get("name") not in existing: hs_root.append(g); existing.add(g.get("name"))

for g in atomis_list:
    if g.get("name") not in existing: hs_root.append(g); existing.add(g.get("name"))

# DDP SWAP
NEW_PARENT, OLD_PARENT = "ddpdojblk", "ddp3"
for g in hs_root.findall("game"):
    name, clone_node = g.get("name"), g.find("cloneof")
    if name == NEW_PARENT and clone_node is not None: clone_node.text = ""
    elif name == OLD_PARENT and clone_node is not None: clone_node.text = NEW_PARENT
    elif clone_node is not None and clone_node.text == OLD_PARENT: clone_node.text = NEW_PARENT

# Save sorted by ROM name for the main database
sorted_games = sorted(hs_root.findall("game"), key=lambda x: x.get("name").lower())
new_hs_root = ET.Element("menu")
new_hs_root[:] = sorted_games
indent(new_hs_root)
ET.ElementTree(new_hs_root).write(HS_XML, encoding="utf-8", xml_declaration=True)

# =================================================
# 4) FILTER VERTICAL
# =================================================
print("Filtering Vertical Games...")
vertical_names = {m.get("name") for m in mame_root.findall("machine") if m.find("display") is not None and m.find("display").get("rotate") in ("90", "270")}

final_vertical_menu = ET.Element("menu")
for g in new_hs_root.findall("game"):
    name = g.get("name")
    parent = (g.findtext("cloneof") or "").strip() or name
    if (parent in vertical_names or name in vertical_names) and name not in REMOVE_GAMES:
        final_vertical_menu.append(g)

# =================================================
# 4.5) CUSTOM VERTICAL OVERRIDES & RESCUE & SORT
# =================================================
print("Applying Custom Overrides, Rescuing 'sbugger', and Sorting by Description...")

# 1. Rescue sbugger (from MAME XML)
if not any(g.get("name") == "sbugger" for g in final_vertical_menu.findall("game")):
    m_node = mame_root.find(".//machine[@name='sbugger']")
    if m_node is not None:
        final_vertical_menu.append(create_hs_node(m_node))

# 2. Overrides
FORCE_PARENTS = {"dtrvwz5v", "grdnstrmv", "headon2sl", "hexpoola", "phrcrazev", "rallyxeg", "sbugger", "statriv2v", "trvwz4v", "tictacv"}
CLONE_MAP = {"grdnstrmk": "grdnstrmv", "grdnstrmj": "grdnstrmv", "redfoxwp2": "grdnstrmv", "redfoxwp2a": "grdnstrmv", "hexpool": "hexpoola", "rallyxtd": "rallyxeg", "sbuggera": "sbugger", "trvwz4va": "trvwz4v"}

for g in final_vertical_menu.findall("game"):
    name, clone_node = g.get("name"), g.find("cloneof")
    if name in FORCE_PARENTS and clone_node is not None: clone_node.text = ""
    if name in CLONE_MAP and clone_node is not None: clone_node.text = CLONE_MAP[name]

# 3. FINAL SORT BY DESCRIPTION
vertical_sorted = sorted(final_vertical_menu.findall("game"), key=lambda g: (g.findtext("description") or "").lower())
final_vertical_menu[:] = vertical_sorted

indent(final_vertical_menu)
ET.ElementTree(final_vertical_menu).write(VERTICAL_XML, encoding="utf-8", xml_declaration=True)

# =================================================
# 5) SPLITS (ALL SUB-DATABASES WILL BE SORTED)
# =================================================
print("Creating Split Databases (Inheriting Sort Order)...")
root = final_vertical_menu
by_genre = defaultdict(list)
for g in root.findall("game"): by_genre[clean_filename(g.findtext("genre"))].append(g)
for genre, games in by_genre.items():
    m = ET.Element("menu"); m[:] = games
    ET.ElementTree(m).write(DB / "genres - vertical" / f"{genre}.xml", encoding="utf-8", xml_declaration=True)

for manu in PRIORITY:
    games = [g for g in root.findall("game") if pick_manufacturer(g.findtext("manufacturer")) == manu]
    if games:
        m = ET.Element("menu"); m[:] = games
        ET.ElementTree(m).write(DB / "manufacturer - vertical" / f"{manu}.xml", encoding="utf-8", xml_declaration=True)

shmup_file = DB / "genres - vertical" / "Shoot-'Em-Up.xml"
if shmup_file.exists():
    shmups = ET.parse(shmup_file).getroot()
    for manu in PRIORITY:
        games = [g for g in shmups.findall("game") if pick_manufacturer(g.findtext("manufacturer")) == manu]
        if games:
            m = ET.Element("menu"); m[:] = games
            ET.ElementTree(m).write(DB / "manufacturer - shmups" / f"{manu}.xml", encoding="utf-8", xml_declaration=True)

bucket = defaultdict(lambda: defaultdict(list))
for g in root.findall("game"):
    m_name = pick_manufacturer(g.findtext("manufacturer"))
    if m_name: bucket[m_name][g.findtext("genre") or "Unknown"].append(g)
for manu, genres in bucket.items():
    d = DB / "manufacturer - vertical by genres" / manu
    d.mkdir(exist_ok=True)
    for gen, games in genres.items():
        m = ET.Element("menu"); m[:] = games
        ET.ElementTree(m).write(d / f"{clean_filename(gen)}.xml", encoding="utf-8", xml_declaration=True)

# =================================================
# 6) FINAL CLEANUP & ORGANIZATION
# =================================================
replacements = {"<genre>Shoot-'Em-Up</genre>": "<genre>Shoot-&apos;Em-Up</genre>", "<genre>Beat-'Em-Up</genre>": "<genre>Beat-&apos;Em-Up</genre>"}
for xml in DB.rglob("*.xml"):
    text = xml.read_text(encoding="utf-8")
    for old, new in replacements.items(): text = text.replace(old, new)
    xml.write_text(text, encoding="utf-8")

FINAL_DIR = DB / "!Final"
FINAL_DIR.mkdir(exist_ok=True)
m_dir = FINAL_DIR / "MAME"; m_dir.mkdir(exist_ok=True)
shutil.copy2(VERTICAL_XML, m_dir / "MAME.xml")
for f in (DB / "genres - vertical").glob("*.xml"): shutil.copy2(f, m_dir / f.name)

n_dir = FINAL_DIR / "Sega Naomi"; n_dir.mkdir(exist_ok=True)
shutil.copy2(NAOMI_XML, n_dir / "Sega Naomi.xml")
for f in (DB / "genres - naomi").glob("*.xml"): shutil.copy2(f, n_dir / f.name)

s_dir = FINAL_DIR / "Shoot-'Em-Up"; s_dir.mkdir(exist_ok=True)
if shmup_file.exists(): shutil.copy2(shmup_file, s_dir / "Shoot-'Em-Up.xml")
for f in (DB / "manufacturer - shmups").glob("*.xml"): shutil.copy2(f, s_dir / f.name)

for xml_file in (DB / "manufacturer - vertical").glob("*.xml"):
    target = FINAL_DIR / xml_file.stem; target.mkdir(exist_ok=True)
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
