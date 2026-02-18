"""
pip install Pillow
"""
import os
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont

# --- CONFIGURATION ---
# Chemin vers ton fichier XML
XML_PATH = r'C:\HyperSpin\Databases\MAME\MAME.xml'

# Définition des dossiers basées sur l'emplacement du XML
BASE_DIR = os.path.dirname(XML_PATH)
OUTPUT_NAME_DIR = os.path.join(BASE_DIR, 'name')
OUTPUT_INFO_DIR = os.path.join(BASE_DIR, 'info')

# Paramètres visuels
FONT_PATH = "C:/Windows/Fonts/impact.ttf"  # Police condensée proche de ton exemple
FONT_SIZE = 38
HEIGHT = 47
TEXT_COLOR = "white"
SHADOW_COLOR = "black"

# --- INITIALISATION ---
# Création physique des dossiers s'ils n'existent pas
os.makedirs(OUTPUT_NAME_DIR, exist_ok=True)
os.makedirs(OUTPUT_INFO_DIR, exist_ok=True)

def create_text_image(text, output_path):
    """Génère une image PNG avec texte, contour et ombre portée."""
    if not text:
        text = "Unknown"

    # Charger la police
    try:
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    except:
        font = ImageFont.load_default()

    # Simulation d'une image pour calculer la taille du texte
    dummy_img = Image.new('RGBA', (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    bbox = draw.textbbox((0, 0), text, font=font)
    
    # Largeur dynamique + marge pour les effets
    width = int(bbox[2] - bbox[0]) + 20 

    # Création de l'image de travail
    img = Image.new('RGBA', (width, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Calcul du centrage vertical (ajustement manuel -5 pour l'équilibre visuel)
    text_height = bbox[3] - bbox[1]
    y_pos = (HEIGHT - text_height) // 2 - 5

    # 1. Dessiner l'ombre portée (décalée en bas à droite)
    draw.text((4, y_pos + 3), text, font=font, fill=SHADOW_COLOR)
    
    # 2. Dessiner le contour noir (épais)
    for offset in [(1,1), (-1,1), (1,-1), (-1,-1), (2,0), (-2,0), (0,2), (0,-2)]:
        draw.text((2 + offset[0], y_pos + offset[1]), text, font=font, fill=SHADOW_COLOR)

    # 3. Dessiner le texte principal par-dessus
    draw.text((2, y_pos), text, font=font, fill=TEXT_COLOR)

    # Recadrage automatique pour enlever le vide à droite
    final_bbox = img.getbbox()
    if final_bbox:
        img = img.crop(final_bbox)
        # On replace dans une image de hauteur fixe (47px) avec une petite marge
        final_img = Image.new('RGBA', (img.width + 10, HEIGHT), (0, 0, 0, 0))
        final_img.paste(img, (0, 0), img)
        final_img.save(output_path)

# --- TRAITEMENT DU XML ---
print(f"Ouverture du fichier : {XML_PATH}")

try:
    tree = ET.parse(XML_PATH)
    root = tree.getroot()

    # On boucle sur chaque balise <game>
    for game in root.findall('game'):
        game_id = game.get('name')
        
        # Extraction des données avec sécurité si la balise est absente
        desc = game.find('description').text if game.find('description') is not None else ""
        manu = game.find('manufacturer').text if game.find('manufacturer') is not None else "Unknown"
        year = game.find('year').text if game.find('year') is not None else ""
        
        info_text = f"{manu} - {year}"

        if game_id:
            print(f"Traitement de : {game_id}")
            
            # Image 1 : Nom du jeu (Description)
            name_file = os.path.join(OUTPUT_NAME_DIR, f"{game_id}.png")
            create_text_image(desc, name_file)
            
            # Image 2 : Manufacturer - Year
            info_file = os.path.join(OUTPUT_INFO_DIR, f"{game_id}.png")
            create_text_image(info_text, info_file)

    print("\nOpération terminée avec succès !")
    print(f"Images disponibles dans : {BASE_DIR}")

except FileNotFoundError:
    print(f"Erreur : Le fichier {XML_PATH} est introuvable.")
except Exception as e:
    print(f"Une erreur est survenue : {e}")
