"""
Utilitaires pour gérer les versions
"""
from pathlib import Path


def increment_version(version_file="VERSION", increment_type="patch"):
    """
    Incrémente le numéro de version dans le fichier VERSION
    
    Args:
        version_file: Chemin vers le fichier VERSION
        increment_type: Type d'incrémentation ("patch", "minor", "major")
    
    Returns:
        str: Nouvelle version
    """
    version_path = Path(version_file)
    
    # Lire la version actuelle
    try:
        if version_path.exists():
            with open(version_path, 'r', encoding='utf-8') as f:
                current_version = f.read().strip()
        else:
            current_version = "1.0.0"
    except:
        current_version = "1.0.0"
    
    # Parser la version
    try:
        parts = current_version.split('.')
        major = int(parts[0]) if len(parts) > 0 else 1
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
    except:
        major, minor, patch = 1, 0, 0
    
    # Incrémenter selon le type
    if increment_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif increment_type == "minor":
        minor += 1
        patch = 0
    else:  # patch (par défaut)
        patch += 1
    
    # Nouvelle version
    new_version = f"{major}.{minor}.{patch}"
    
    # Écrire la nouvelle version
    try:
        with open(version_path, 'w', encoding='utf-8') as f:
            f.write(new_version + '\n')
    except Exception as e:
        raise Exception(f"Impossible d'écrire la nouvelle version: {e}")
    
    return new_version


def get_current_version(version_file="VERSION"):
    """
    Lit la version actuelle depuis le fichier VERSION
    
    Args:
        version_file: Chemin vers le fichier VERSION
    
    Returns:
        str: Version actuelle ou "1.0.0" si le fichier n'existe pas
    """
    version_path = Path(version_file)
    
    try:
        if version_path.exists():
            with open(version_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        else:
            return "1.0.0"
    except:
        return "1.0.0"

