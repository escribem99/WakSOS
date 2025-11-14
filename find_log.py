"""
Utilitaire pour trouver le fichier log de Wakfu
"""
import os


def find_wakfu_log():
    """Trouve le fichier log de Wakfu"""
    possible_paths = [
        os.path.expanduser(r"~\AppData\Local\Ankama\Wakfu\logs\wakfu.log"),
        os.path.expanduser(r"~\AppData\Local\Ankama\Wakfu\logs\wakfu-debug.log"),
        os.path.expanduser(r"~\Documents\Wakfu\logs\wakfu.log"),
        r"C:\Program Files (x86)\Wakfu\logs\wakfu.log",
        r"C:\Program Files\Wakfu\logs\wakfu.log"
    ]
    
    found_paths = []
    for path in possible_paths:
        if os.path.exists(path):
            found_paths.append(path)
            print(f"✓ Trouvé: {path}")
        else:
            print(f"✗ Non trouvé: {path}")
    
    if found_paths:
        print(f"\nFichier log recommandé: {found_paths[0]}")
        return found_paths[0]
    else:
        print("\n⚠ Aucun fichier log trouvé automatiquement.")
        print("Vous devrez spécifier le chemin manuellement dans config.json")
        return None


if __name__ == "__main__":
    find_wakfu_log()





