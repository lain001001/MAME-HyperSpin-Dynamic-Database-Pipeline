import xml.etree.ElementTree as ET
from pathlib import Path

# =================================================
# TARGET PATH
# =================================================
TARGET_XML = Path(r"C:\Users\PC\OneDrive\Perso\buy\HS2026\files\databases\Mame 0.284 Vertical.xml")

PRIORITY = [
    "Atari", "Bally", "BFM", "Capcom", "Cave", "Data East", "Gaelco",
    "IGS", "IGT", "Irem", "Jaleco", "Kaneko", "Konami", "Midway", "Namco",
    "Nichibutsu", "Nintendo", "Novotech", "Psikyo", "Sammy", "Sega",
    "Seibu Kaihatsu", "SNK", "Taito"
]

# =================================================
# PROCESSING
# =================================================
if not TARGET_XML.exists():
    print(f"ERROR: {TARGET_XML} not found.")
else:
    try:
        root = ET.parse(TARGET_XML).getroot()
        
        parents = 0
        clones = 0
        # This will now only store Parent counts
        mfg_counts = {m: 0 for m in PRIORITY}

        for game in root.findall("game"):
            cloneof = game.find("cloneof")
            
            # Check if Clone
            if cloneof is not None and (cloneof.text or "").strip():
                clones += 1
            else:
                # It is a PARENT
                parents += 1
                
                # Handle Manufacturer logic ONLY for parents
                mfg_element = game.find("manufacturer")
                if mfg_element is not None and mfg_element.text:
                    mfg_text = mfg_element.text.strip()
                    for p in PRIORITY:
                        if mfg_text.startswith(p):
                            mfg_counts[p] += 1
                            break 

        # =================================================
        # OUTPUT
        # =================================================
        print(f"\nSTATS FOR: {TARGET_XML.name}")
        print("-" * 30)
        print(f"{'Parents':<13}: {parents}")
        print(f"{'Clones':<13}: {clones}")
        print(f"{'Total':<13}: {parents + clones}")

        print(f"\n{'='*30}")
        print("Shoot-'Em-Up.xml")
        print(f"  Parents    : 518")
        print(f"  Clones     : 1172")
        print(f"  Total      : 1690")
        print(f"{'='*30}")

        print("\nPRIORITY MANUFACTURERS (PARENTS ONLY)")
        print("-" * 30)
        for mfg in PRIORITY:
            if mfg_counts[mfg] > 0:
                print(f"{mfg:<15}: {mfg_counts[mfg]}")

    except ET.ParseError as e:
        print(f"XML PARSE ERROR: {e}")
        
"""
STATS FOR: Mame 0.284 Vertical.xml
------------------------------
Parents      : 1006
Clones       : 2023
Total        : 3029

==============================
Shoot-'Em-Up.xml
  Parents    : 518
  Clones     : 1172
  Total      : 1690
==============================

PRIORITY MANUFACTURERS (PARENTS ONLY)
------------------------------
Atari          : 15
Bally          : 10
Capcom         : 19
Cave           : 20
Data East      : 65
IGS            : 2
Irem           : 17
Jaleco         : 15
Kaneko         : 21
Konami         : 52
Midway         : 6
Namco          : 45
Nichibutsu     : 18
Nintendo       : 12
Psikyo         : 9
Sammy          : 1
Sega           : 58
Seibu Kaihatsu : 13
SNK            : 30
Taito          : 75
"""
