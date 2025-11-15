"""
Module de logging pour le debug
"""
import logging
import os
from datetime import datetime

# Créer le dossier logs s'il n'existe pas
if not os.path.exists("logs"):
    os.makedirs("logs")

# Créer un nom de fichier avec timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"logs/debug_{timestamp}.log"

# Configurer le logging (niveau INFO pour éviter les messages DEBUG)
# Ne pas afficher dans la console pour éviter le flood, uniquement dans le fichier log
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8')
        # StreamHandler retiré pour éviter le flood dans la console
    ]
)

logger = logging.getLogger(__name__)

# Désactiver les messages DEBUG de PIL/Pillow
logging.getLogger('PIL').setLevel(logging.WARNING)

def debug(msg):
    """Affiche un message de debug (désactivé pour réduire le bruit)"""
    # Désactivé pour réduire le bruit dans la console
    pass

def info(msg):
    """Affiche un message d'information (uniquement dans le fichier log, pas dans la console)"""
    logger.info(msg)
    # Ne plus afficher dans la console pour éviter le flood

def error(msg):
    """Affiche un message d'erreur"""
    logger.error(msg)
    print(f"[ERROR] {msg}")

def warning(msg):
    """Affiche un message d'avertissement"""
    logger.warning(msg)
    print(f"[WARNING] {msg}")

