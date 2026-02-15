# MAME → HyperSpin Dynamic Database Pipeline

Fully automated Python pipeline that builds a complete **MAME →
HyperSpin** database ecosystem with dynamic XML injection, vertical
filtering, Naomi support, manufacturer splits, and clrmamepro export.

Designed for advanced arcade cabinet setups, vertical builds, and
curated shmup collections.

------------------------------------------------------------------------

## What This Project Does

This script automatically:

-   Generates fresh XML from MAME
-   Injects custom machine XMLs before processing
-   Merges everything into a clean HyperSpin database
-   Builds Vertical-only databases (rotate 90 / 270)
-   Extracts vertical titles from Sega Naomi & Atomiswave
-   Splits databases by Genre
-   Splits databases by Manufacturer (priority-based detection)
-   Builds Shmup-only manufacturer folders
-   Exports a filtered XML for clrmamepro
-   Organizes everything into a final ready-to-use folder structure

This is a complete end-to-end arcade XML automation pipeline.

------------------------------------------------------------------------

# Features

## Automatic MAME XML Generation

Runs:

    mame.exe -listxml

Then parses and rebuilds everything dynamically.

------------------------------------------------------------------------

## Dynamic Game Injection

Supports custom XML injection before database processing.

Example: - ddpsdoj.xml - ketmatsuri.xml

Injected games automatically: - Gain vertical detection - Merge into
HyperSpin - Appear in manufacturer/genre splits - Get included in
clrmamepro export

------------------------------------------------------------------------

## Vertical Filtering Engine

Filters games based on:

    <display rotate="90">
    <display rotate="270">

Removes unwanted titles via blacklist.

Outputs: - MAME Vertical.xml - Vertical Genre splits - Vertical
Manufacturer splits

------------------------------------------------------------------------

## Naomi & Atomiswave Auto Builder

Automatically extracts vertical games from: - naomi.cpp -
dc_atomiswave.cpp

Outputs: - Sega Naomi vertical database - Genre splits for Naomi -
Integrated into main HyperSpin DB

------------------------------------------------------------------------

## Manufacturer Intelligence

Priority manufacturers:

Capcom\
Cave\
Data East\
Gaelco\
Irem\
Kaneko\
Konami\
Namco\
Nichibutsu\
Nintendo\
Sega\
Seibu Kaihatsu\
SNK\
Taito

Smart detection handles: - Company A / Company B - Company A & Company
B - (license) cleanup

------------------------------------------------------------------------

## Shoot-'Em-Up Smart Splits

Automatically generates: - Vertical shmups - Shmups by manufacturer -
Manufacturer → Genre subfolders

------------------------------------------------------------------------

## Final Clean Folder Structure

!Final/ ├── MAME/ ├── Sega Naomi/ ├── Shoot-'Em-Up/ ├── Capcom/ ├──
Cave/ ├── SNK/ └── etc...

Fully organized for HyperSpin wheels.

------------------------------------------------------------------------

## Special Logic

### DDP Parent/Clone Restructure

-   ddpdojblk becomes parent
-   ddp3 becomes clone
-   All sub-clones re-linked automatically

Fully dynamic inside HyperSpin XML.

------------------------------------------------------------------------

## Requirements

-   Python 3.10+
-   MAME executable
-   HyperSpin base XML database
-   All Games master XML (for genre lookup)

------------------------------------------------------------------------

## Configuration

Inside script:

    BASE = Path(r"C:\YourPath")

You can configure: - Injected XML list - Manufacturer priority -
Blacklisted games - Blacklisted Naomi titles

------------------------------------------------------------------------

## Use Case

Perfect for: - Vertical-only arcade cabinets - Shmup-focused builds -
Curated manufacturer wheels - Clean HyperSpin setups - Advanced ROM
management workflows

------------------------------------------------------------------------
