"""
FULL MAME / HYPERSPIN DATABASE PIPELINE
OPTIMIZED + REFACTORED VERSION

- Python 3.9+ requis (ET.indent natif)
- lxml optionnel (pip install lxml) : parsing nettement plus rapide
- Configuration optionnelle : pipeline_config.json à côté du script
  (mêmes noms que les champs de la classe Config, voir plus bas)
"""
from __future__ import annotations

import copy
import json
import logging
import re
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field, fields
from pathlib import Path

try:
    from lxml import etree as ET
    USE_LXML = True
except ImportError:
    import xml.etree.ElementTree as ET
    USE_LXML = False

log = logging.getLogger("pipeline")

DEFAULT_GENRE = "Shoot-'Em-Up"
VERTICAL_ROTATIONS = ("90", "270")


# =================================================
# CONFIG
# =================================================
@dataclass
class Config:
    base: Path = Path(r"D:/!delete/test")
    mame_version: str = "0.289"

    # XML (une <machine>) à injecter dans la base MAME
    inject_xmls: list = field(default_factory=lambda: ["ddpsdoj.xml", "ketmatsuri.xml"])
    # Jeux à ajouter depuis "Mame <version> All games.xml"
    games_to_add: list = field(default_factory=lambda: ["sbugger"])

    priority: list = field(default_factory=lambda: [
        "Capcom", "Cave", "Data East", "Gaelco",
        "Irem", "Kaneko", "Konami", "Namco",
        "Nichibutsu", "Nintendo", "Sega",
        "Seibu Kaihatsu", "SNK", "Taito",
    ])

    remove_naomi: set = field(default_factory=lambda: {
        "quizqgd", "shors2k1", "shorse", "shorsep", "shorsepr",
    })

    remove_games: set = field(default_factory=lambda: {
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
        "setaroula", "atetrisc", "atetrisc2", "bronx",
        "chamburger", "csweetht", "25pacman", "cyclshtg",
    })

    # Swap parent/clone DDP (un seul endroit, réutilisé pour l'exclusion des orphelins)
    ddp_new_parent: str = "ddpdojblk"
    ddp_old_parent: str = "ddp3"

    write_mame_xml: bool = True          # écrire mame.xml (sinon tout reste en mémoire)
    use_hs_backup: bool = True           # source = copie d'origine .orig.xml (relance idempotente)
    strict_manufacturer_match: bool = True  # mot entier (\b) au lieu d'une simple sous-chaîne

    # ---------- chemins dérivés ----------
    @property
    def mame_exe(self): return self.base / "mame.exe"
    @property
    def mame_xml(self): return self.base / "mame.xml"
    @property
    def hs_xml(self): return self.base / f"Mame {self.mame_version}.xml"
    @property
    def hs_backup(self): return self.base / f"Mame {self.mame_version}.orig.xml"
    @property
    def all_games_xml(self): return self.base / f"Mame {self.mame_version} All games.xml"
    @property
    def clrmame_xml(self): return self.base / "MAMEclrmame.xml"
    @property
    def inject_paths(self): return [self.base / n for n in self.inject_xmls]
    @property
    def db(self): return self.base / "databases"
    @property
    def vertical_xml(self): return self.db / f"Mame {self.mame_version} Vertical.xml"
    @property
    def naomi_xml(self): return self.db / "Naomi_Vertical.xml"
    @property
    def dir_genres_vertical(self): return self.db / "genres - vertical"
    @property
    def dir_manufacturer_vertical(self): return self.db / "manufacturer - vertical"
    @property
    def dir_manufacturer_shmups(self): return self.db / "manufacturer - shmups"
    @property
    def dir_manufacturer_by_genres(self): return self.db / "manufacturer - vertical by genres"
    @property
    def dir_genres_naomi(self): return self.db / "genres - naomi"
    @property
    def dir_final(self): return self.db / "!Final"
    @property
    def orphan_fix_ignore(self): return {self.ddp_new_parent, self.ddp_old_parent}

    def ensure_dirs(self):
        for d in (self.db, self.dir_genres_vertical, self.dir_manufacturer_vertical,
                  self.dir_manufacturer_shmups, self.dir_manufacturer_by_genres,
                  self.dir_genres_naomi):
            d.mkdir(parents=True, exist_ok=True)


def load_config() -> Config:
    cfg = Config()
    path = Path(__file__).with_name("pipeline_config.json")
    if not path.exists():
        return cfg
    data = json.loads(path.read_text(encoding="utf-8"))
    valid = {f.name for f in fields(Config)}
    for key, value in data.items():
        if key not in valid:
            log.warning("Config: clé inconnue ignorée : %s", key)
            continue
        if key == "base":
            value = Path(value)
        elif key in ("remove_naomi", "remove_games"):
            value = set(value)
        setattr(cfg, key, value)
    log.info("Config chargée depuis %s", path.name)
    return cfg


# =================================================
# HELPERS
# =================================================
def clean_filename(text):
    return re.sub(r'[\\/:*?"<>|]', "", (text or "").strip()) or "Unknown"


def compile_priority(priority, strict=True):
    """Pré-compile les motifs constructeurs (l'ordre de PRIORITY reste prioritaire)."""
    patterns = []
    for p in priority:
        body = re.escape(p)
        patterns.append((p, re.compile(rf"\b{body}\b" if strict else body, re.IGNORECASE)))
    return patterns


def pick_manufacturer(raw, patterns):
    if not raw:
        return None
    for name, pat in patterns:
        if pat.search(raw):
            return name
    return None


def parse_file(path):
    if USE_LXML:
        return ET.parse(str(path), ET.XMLParser(huge_tree=True)).getroot()
    return ET.parse(path).getroot()


def parse_bytes(data):
    if USE_LXML:
        return ET.fromstring(data, ET.XMLParser(huge_tree=True))
    return ET.fromstring(data)


def load_xml(path):
    """Parse un fichier XML UNE seule fois. Retourne la racine ou None (avec warning)."""
    if not path.exists():
        log.warning("%s introuvable, ignoré.", path.name)
        return None
    try:
        return parse_file(path)
    except ET.ParseError as e:
        log.warning("%s est mal formé : %s, ignoré.", path.name, e)
        return None


def write_xml(path, root):
    ET.indent(root, space="    ")
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(str(path), encoding="utf-8", xml_declaration=True)


def write_menu(path, games):
    """Écrit un <menu> à partir de copies des nœuds (évite le partage de nœuds entre fichiers)."""
    menu = ET.Element("menu")
    menu.extend(copy.deepcopy(g) for g in games)
    write_xml(path, menu)


def resolve_genre(machine, all_games):
    genre = (machine.findtext("genre") or "").strip()
    if not genre and all_games is not None:
        ref = all_games.get(machine.get("name"))
        if ref is not None:
            genre = (ref.findtext("genre") or "").strip()
    return genre or DEFAULT_GENRE


def create_game_node(machine, all_games=None):
    """
    Convertit une <machine> MAME ou un <game> HyperSpin en nœud <game> HyperSpin.
    cloneof est lu en attribut (MAME) OU en sous-élément (HyperSpin).
    """
    name = machine.get("name")
    g = ET.Element("game", name=name, index="", image="")
    for tag in ("description", "manufacturer", "year"):
        ET.SubElement(g, tag).text = machine.findtext(tag) or ""
    ET.SubElement(g, "genre").text = resolve_genre(machine, all_games)
    cloneof = machine.get("cloneof") or (machine.findtext("cloneof") or "").strip()
    ET.SubElement(g, "cloneof").text = cloneof
    ET.SubElement(g, "crc").text = ""
    ET.SubElement(g, "rating").text = ""
    ET.SubElement(g, "enabled").text = "Yes"
    return g


# =================================================
# 0) PRÉ-VÉRIFICATIONS
# =================================================
def check_inputs(cfg):
    ok = True
    if not cfg.mame_exe.exists():
        log.error("mame.exe introuvable : %s", cfg.mame_exe)
        ok = False
    if not cfg.all_games_xml.exists():
        log.error("Fichier requis introuvable : %s", cfg.all_games_xml)
        ok = False
    if not (cfg.hs_xml.exists() or (cfg.use_hs_backup and cfg.hs_backup.exists())):
        log.error("Base HyperSpin introuvable : %s", cfg.hs_xml)
        ok = False
    if not ok:
        sys.exit(1)


# =================================================
# 1) MAME.XML : GÉNÉRATION EN MÉMOIRE + INDEX EN UNE PASSE
# =================================================
def generate_mame_root(cfg):
    log.info("Génération de la base MAME (-listxml, en mémoire)...")
    try:
        proc = subprocess.run(
            [str(cfg.mame_exe), "-listxml"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            check=True, cwd=str(cfg.base),
        )
    except (OSError, subprocess.CalledProcessError) as e:
        log.error("Échec de mame -listxml : %s", e)
        sys.exit(1)
    return parse_bytes(proc.stdout)


class MameIndex:
    """Toutes les structures dérivées de la base MAME, remplies en UNE seule passe."""

    def __init__(self, remove_naomi):
        self.remove_naomi = remove_naomi
        self.machines = {}                      # nom -> <machine>
        self.vertical = set()                   # noms des machines verticales
        self.clone_groups = defaultdict(list)   # parent -> clones (ordre MAME)
        self.naomi = []                         # <machine> Naomi verticales
        self.atomiswave = []                    # <machine> Atomiswave verticales

    def add(self, m):
        name = m.get("name")
        self.machines[name] = m

        parent = m.get("cloneof")
        if parent:
            self.clone_groups[parent].append(name)

        disp = m.find("display")
        if disp is None or disp.get("rotate") not in VERTICAL_ROTATIONS:
            return
        self.vertical.add(name)

        source = (m.get("sourcefile") or "").lower()
        if source.endswith("naomi.cpp") and name not in self.remove_naomi:
            self.naomi.append(m)
        if source == "sega/dc_atomiswave.cpp":
            self.atomiswave.append(m)


def inject_machines(cfg, mame_root, index):
    """Injecte les XML custom dans la base MAME. Les nœuds sont ajoutés puis indexés."""
    injected = []
    for xml_path in cfg.inject_paths:
        root = load_xml(xml_path)
        if root is None:
            continue
        candidates = [root] if root.tag == "machine" else root.findall("machine")
        if not candidates:
            log.warning("%s ne contient aucune <machine>, ignoré.", xml_path.name)
            continue
        log.info("Patch de %s dans la base MAME...", xml_path.name)
        for m in candidates:
            name = m.get("name")
            if name in index.machines:
                log.warning("  %s existe déjà dans la base MAME, ignoré.", name)
                continue
            mame_root.append(m)
            index.add(m)
            injected.append(m)
            log.info("  %s injecté.", name)
    return injected


# =================================================
# 2) BASE HYPERSPIN : FUSION, PARENTS MANQUANTS, SWAP DDP, TRI
# =================================================
def prepare_hs_source(cfg):
    """
    La base d'origine est sauvegardée une fois (.orig.xml) et sert de source à chaque
    exécution : relancer le script repart toujours de l'original (idempotent).
    Pour partir d'une nouvelle base d'origine, supprimer le fichier .orig.xml.
    """
    if not cfg.use_hs_backup:
        return cfg.hs_xml
    if not cfg.hs_backup.exists():
        shutil.copy2(cfg.hs_xml, cfg.hs_backup)
        log.info("Sauvegarde de la base d'origine : %s", cfg.hs_backup.name)
    return cfg.hs_backup


def fix_missing_parents(hs_root, games, all_games):
    """Ajoute les parents manquants, de façon itérative (parents de parents), sans doublon."""
    added = []
    pending = list(games.values())
    while pending:
        node = pending.pop()
        parent = (node.findtext("cloneof") or "").strip()
        if not parent or parent in games:
            continue
        src = all_games.get(parent)
        if src is None:
            log.warning("  Parent '%s' (requis par '%s') absent de %s",
                        parent, node.get("name"), "All games")
            continue
        new = create_game_node(src, all_games)
        hs_root.append(new)
        games[parent] = new          # le nœud créé, pas l'élément source
        added.append((node.get("name"), parent))
        pending.append(new)          # son propre parent sera vérifié à son tour
    return added


def apply_ddp_swap(games, new_parent, old_parent):
    for name, g in games.items():
        node = g.find("cloneof")
        if node is None:
            continue
        if name == new_parent:
            node.text = ""
        elif name == old_parent:
            node.text = new_parent
        elif (node.text or "").strip() == old_parent:
            node.text = new_parent


def build_hs_db(cfg, index, injected, all_games):
    log.info("Fusion de toutes les sources dans la base HyperSpin...")
    hs_root = parse_file(prepare_hs_source(cfg))
    games = {g.get("name"): g for g in hs_root.iterfind("game")}

    def add(node):
        name = node.get("name")
        if name in games:
            return False
        hs_root.append(node)
        games[name] = node
        return True

    # A) jeux injectés
    for m in injected:
        add(create_game_node(m, all_games))
    # B) Naomi  C) Atomiswave
    for m in index.naomi:
        add(create_game_node(m, all_games))
    for m in index.atomiswave:
        add(create_game_node(m, all_games))

    # D) jeux personnalisés
    log.info("Ajout des jeux de games_to_add...")
    for rom in cfg.games_to_add:
        src = all_games.get(rom)
        if src is None:
            log.error("  '%s' INTROUVABLE dans %s", rom, cfg.all_games_xml.name)
        elif add(create_game_node(src, all_games)):
            log.info("  '%s' ajouté.", rom)
        else:
            log.warning("  '%s' existe déjà, ignoré.", rom)

    # E) parents manquants
    log.info("Vérification des parents manquants...")
    added = fix_missing_parents(hs_root, games, all_games)
    for child, parent in added:
        log.info("  parent '%s' ajouté (requis par '%s')", parent, child)
    if not added:
        log.info("  aucun parent manquant")

    # F) swap DDP
    log.info("Swap parent/clone DDP (%s <-> %s)...", cfg.ddp_old_parent, cfg.ddp_new_parent)
    apply_ddp_swap(games, cfg.ddp_new_parent, cfg.ddp_old_parent)

    # G) tri alphabétique
    sorted_games = sorted(games.values(), key=lambda g: g.get("name").lower())
    new_root = ET.Element("menu")
    new_root.extend(sorted_games)
    write_xml(cfg.hs_xml, new_root)
    return new_root


# =================================================
# 3) VERTICAL + CORRECTION DES ORPHELINS
# =================================================
def build_vertical(cfg, hs_root, vertical_names):
    log.info("Création de la base Vertical...")
    menu = ET.Element("menu")
    for g in hs_root.iterfind("game"):
        name = g.get("name")
        parent = (g.findtext("cloneof") or "").strip() or name
        if (parent in vertical_names or name in vertical_names) and name not in cfg.remove_games:
            menu.append(copy.deepcopy(g))   # copie : la base HS n'est pas modifiée
    return menu


def fix_orphan_clones(vertical_menu, clone_groups, ignore):
    log.info("Correction des clones orphelins (Vertical)...")
    vertical = {g.get("name"): g for g in vertical_menu.iterfind("game")}

    def set_parent(name, parent):
        node = vertical[name].find("cloneof")
        if node is not None:
            node.text = parent

    unique_promoted, multi_groups = [], {}
    for parent, clones in clone_groups.items():
        if parent in ignore or parent in vertical:
            continue
        present = [c for c in clones if c in vertical]
        if not present:
            continue
        if len(present) == 1:
            set_parent(present[0], "")
            unique_promoted.append(present[0])
        else:
            new_parent = present[0]
            set_parent(new_parent, "")
            for c in present[1:]:
                set_parent(c, new_parent)
            multi_groups[new_parent] = present[1:]

    log.info("--- ORPHELINS UNIQUES PROMUS ---")
    for name in sorted(unique_promoted) or ["(aucun)"]:
        log.info("   %s", name)
    log.info("--- GROUPES MULTI-ORPHELINS RECONSTRUITS ---")
    if multi_groups:
        for parent, children in multi_groups.items():
            log.info("  Nouveau parent : %s", parent)
            for c in children:
                log.info("     - %s", c)
    else:
        log.info("   (aucun)")
    log.info("Total promus : %d | groupes reconstruits : %d",
             len(unique_promoted), len(multi_groups))


# =================================================
# 4) DÉCOUPAGES GENRE / CONSTRUCTEUR (UNE PASSE)
# =================================================
def export_splits(cfg, vertical_menu, naomi_nodes, patterns):
    log.info("Création des bases découpées (une passe)...")
    by_genre = defaultdict(list)
    by_manu = defaultdict(list)
    shmup_by_manu = defaultdict(list)
    manu_by_genre = defaultdict(lambda: defaultdict(list))

    for g in vertical_menu.iterfind("game"):
        genre = g.findtext("genre") or "Unknown"
        genre_file = clean_filename(genre)
        manu = pick_manufacturer(g.findtext("manufacturer"), patterns)

        by_genre[genre_file].append(g)
        if manu:
            by_manu[manu].append(g)
            manu_by_genre[manu][genre_file].append(g)
            if "Shoot-'Em-Up" in genre:
                shmup_by_manu[manu].append(g)

    for genre, games in by_genre.items():
        write_menu(cfg.dir_genres_vertical / f"{genre}.xml", games)
    for manu, games in by_manu.items():
        write_menu(cfg.dir_manufacturer_vertical / f"{manu}.xml", games)
    for manu, games in shmup_by_manu.items():
        write_menu(cfg.dir_manufacturer_shmups / f"{manu}.xml", games)
    for manu, genres in manu_by_genre.items():
        for genre, games in genres.items():
            write_menu(cfg.dir_manufacturer_by_genres / manu / f"{genre}.xml", games)

    by_genre_naomi = defaultdict(list)
    for g in naomi_nodes:
        by_genre_naomi[clean_filename(g.findtext("genre"))].append(g)
    for genre, games in by_genre_naomi.items():
        write_menu(cfg.dir_genres_naomi / f"{genre}.xml", games)


# =================================================
# 5) ORGANISATION FINALE
# =================================================
def organize_final(cfg):
    log.info("Organisation de la structure finale...")
    final = cfg.dir_final
    final.mkdir(parents=True, exist_ok=True)

    m_dir = final / "MAME"
    m_dir.mkdir(exist_ok=True)
    shutil.copy2(cfg.vertical_xml, m_dir / "MAME.xml")
    for f in cfg.dir_genres_vertical.glob("*.xml"):
        shutil.copy2(f, m_dir / f.name)

    n_dir = final / "Sega Naomi"
    n_dir.mkdir(exist_ok=True)
    shutil.copy2(cfg.naomi_xml, n_dir / "Sega Naomi.xml")
    for f in cfg.dir_genres_naomi.glob("*.xml"):
        shutil.copy2(f, n_dir / f.name)

    s_dir = final / "Shoot-'Em-Up"
    s_dir.mkdir(exist_ok=True)
    shmup_file = cfg.dir_genres_vertical / "Shoot-'Em-Up.xml"
    if shmup_file.exists():
        shutil.copy2(shmup_file, s_dir / shmup_file.name)
    for f in cfg.dir_manufacturer_shmups.glob("*.xml"):
        shutil.copy2(f, s_dir / f.name)

    for xml_file in cfg.dir_manufacturer_vertical.glob("*.xml"):
        target = final / xml_file.stem
        target.mkdir(exist_ok=True)
        shutil.copy2(xml_file, target / xml_file.name)

    if cfg.dir_manufacturer_by_genres.exists():
        shutil.copytree(cfg.dir_manufacturer_by_genres, final, dirs_exist_ok=True)


# =================================================
# 6) DAT CLRMAMEPRO (INTÉGRITÉ DES PARENTS)
# =================================================
def build_clrmame(cfg, mame_root, index, vertical_menu, naomi_nodes, atomis_nodes):
    log.info("Génération de MAMEclrmame.xml avec intégrité des parents...")
    # Vertical + Naomi + Atomiswave
    allowed = {g.get("name") for g in vertical_menu.iterfind("game")}
    allowed.update(g.get("name") for g in naomi_nodes)
    allowed.update(g.get("name") for g in atomis_nodes)

    required_parents = set()
    for name in allowed:
        m = index.machines.get(name)
        if m is not None and m.get("cloneof"):
            required_parents.add(m.get("cloneof"))

    total = allowed | required_parents

    # liste d'abord (les nœuds sont déplacés avec lxml) ; dernière étape du script
    selected = [m for m in mame_root.iterfind("machine") if m.get("name") in total]
    new_root = ET.Element("mame", dict(mame_root.attrib))
    new_root.extend(selected)
    write_xml(cfg.clrmame_xml, new_root)

    log.info("DAT généré : %d entrées au total.", len(total))
    log.info("(%d parents cachés ajoutés pour que les sets merged fonctionnent.)",
             len(required_parents - allowed))


# =================================================
# MAIN
# =================================================
def main():
    if sys.version_info < (3, 9):
        sys.exit("Python 3.9+ requis.")
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    t0 = time.perf_counter()
    log.info("Parseur XML : %s", "lxml" if USE_LXML else "xml.etree (installer lxml pour accélérer)")

    cfg = load_config()
    check_inputs(cfg)
    cfg.ensure_dirs()
    patterns = compile_priority(cfg.priority, cfg.strict_manufacturer_match)

    # --- base "All games" (une seule fois, validée + parsée en une passe) ---
    log.info("Chargement de la base complète pour les lookups...")
    all_games_root = load_xml(cfg.all_games_xml)
    if all_games_root is None:
        log.error("Impossible de charger %s, arrêt.", cfg.all_games_xml.name)
        sys.exit(1)
    all_games = {g.get("name"): g for g in all_games_root.iterfind("game")}

    # --- base MAME en mémoire + index en une passe + injection ---
    mame_root = generate_mame_root(cfg)
    index = MameIndex(cfg.remove_naomi)
    for m in mame_root.iterfind("machine"):
        index.add(m)
    injected = inject_machines(cfg, mame_root, index)
    if cfg.write_mame_xml:
        write_xml(cfg.mame_xml, mame_root)
        log.info("mame.xml écrit (une seule fois).")

    # --- Naomi / Atomiswave ---
    naomi_nodes = [create_game_node(m, all_games) for m in index.naomi]
    atomis_nodes = [create_game_node(m, all_games) for m in index.atomiswave]
    write_menu(cfg.naomi_xml, naomi_nodes)

    # --- base HyperSpin ---
    hs_root = build_hs_db(cfg, index, injected, all_games)

    # --- Vertical (écrit une seule fois, après correction des orphelins) ---
    vertical_menu = build_vertical(cfg, hs_root, index.vertical)
    fix_orphan_clones(vertical_menu, index.clone_groups, cfg.orphan_fix_ignore)
    write_xml(cfg.vertical_xml, vertical_menu)

    # --- découpages, organisation finale, DAT ---
    export_splits(cfg, vertical_menu, naomi_nodes, patterns)
    organize_final(cfg)
    build_clrmame(cfg, mame_root, index, vertical_menu, naomi_nodes, atomis_nodes)

    log.info("TOUTES LES ÉTAPES TERMINÉES en %.1f s", time.perf_counter() - t0)


if __name__ == "__main__":
    main()
