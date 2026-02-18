import os
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont

# --- CONFIGURATION ---
XML_PATH = r'C:\HyperSpin\Databases\MAME\MAME.xml'

# Tailles maximales (en pixels)
MAX_WIDTH_NAME = 600   # Largeur max pour le nom du jeu
MAX_HEIGHT_NAME = 47   # Hauteur max pour le nom du jeu

MAX_WIDTH_INFO = 400   # Largeur max pour Manufacturer - Year
MAX_HEIGHT_INFO = 47   # Hauteur max pour Manufacturer - Year

# Paramètres visuels
FONT_PATH = "C:/Windows/Fonts/impact.ttf"
FONT_SIZE = 38
TEXT_COLOR = "white"
SHADOW_COLOR = "black"

# --- INITIALISATION ---
BASE_DIR = os.path.dirname(XML_PATH)
OUTPUT_NAME_DIR = os.path.join(BASE_DIR, 'name')
OUTPUT_INFO_DIR = os.path.join(BASE_DIR, 'info')

os.makedirs(OUTPUT_NAME_DIR, exist_ok=True)
os.makedirs(OUTPUT_INFO_DIR, exist_ok=True)

def create_text_image(text, output_path, max_w, max_h):
    """Génère une image PNG avec redimensionnement automatique si dépassement."""
    if not text:
        text = "Unknown"

    try:
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    except:
        font = ImageFont.load_default()

    # 1. Calcul initial de la taille du texte
    dummy_img = Image.new('RGBA', (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    bbox = draw.textbbox((0, 0), text, font=font)
    
    tw = int(bbox[2] - bbox[0]) + 20 
    th = int(bbox[3] - bbox[1]) + 10

    # 2. Création de l'image de travail à la taille du texte
    temp_img = Image.new('RGBA', (tw, th + 10), (0, 0, 0, 0))
    temp_draw = ImageDraw.Draw(temp_img)
    y_pos = 2

    # Dessin des effets (Ombre + Contour)
    temp_draw.text((4, y_pos + 3), text, font=font, fill=SHADOW_COLOR)
    for offset in [(1,1), (-1,1), (1,-1), (-1,-1), (2,0), (-2,0), (0,2), (0,-2)]:
        temp_draw.text((2 + offset[0], y_pos + offset[1]), text, font=font, fill=SHADOW_COLOR)
    temp_draw.text((2, y_pos), text, font=font, fill=TEXT_COLOR)

    # 3. Recadrage au plus près du texte
    cropped_bbox = temp_img.getbbox()
    if cropped_bbox:
        temp_img = temp_img.crop(cropped_bbox)

    # 4. Ajustement aux dimensions MAX
    # Si l'image est plus grande que le max autorisé, on réduit
    ratio = min(max_w / temp_img.width, max_h / temp_img.height)
    
    if ratio < 1.0:
        new_w = int(temp_img.width * ratio)
        new_h = int(temp_img.height * ratio)
        temp_img = temp_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # 5. Création de l'image finale (centrée verticalement dans max_h)
    final_img = Image.new('RGBA', (temp_img.width + 5, max_h), (0, 0, 0, 0))
    y_centered = (max_h - temp_img.height) // 2
    final_img.paste(temp_img, (0, y_centered), temp_img)
    
    final_img.save(output_path)

# --- TRAITEMENT DU XML ---
print(f"Ouverture : {XML_PATH}")

try:
    tree = ET.parse(XML_PATH)
    root = tree.getroot()

    for game in root.findall('game'):
        game_id = game.get('name')
        desc = game.find('description').text if game.find('description') is not None else ""
        manu = game.find('manufacturer').text if game.find('manufacturer') is not None else "Unknown"
        year = game.find('year').text if game.find('year') is not None else ""
        
        info_text = f"{manu} - {year}"

        if game_id:
            print(f"Génération : {game_id}")
            # On passe les limites de taille spécifiques
            create_text_image(desc, os.path.join(OUTPUT_NAME_DIR, f"{game_id}.png"), MAX_WIDTH_NAME, MAX_HEIGHT_NAME)
            create_text_image(info_text, os.path.join(OUTPUT_INFO_DIR, f"{game_id}.png"), MAX_WIDTH_INFO, MAX_HEIGHT_INFO)

    print("\nTerminé !")

except Exception as e:
    print(f"Erreur : {e}")
