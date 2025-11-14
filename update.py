"""
Script de mise à jour automatique pour WakSOS
Permet de mettre à jour le programme depuis un dépôt Git (GitHub, GitLab, etc.)
"""
import os
import sys
import subprocess
import shutil
import json
from pathlib import Path


def check_git_available():
    """Vérifie si Git est installé et disponible"""
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_update_config():
    """Récupère la configuration de mise à jour depuis un fichier"""
    config_file = Path("update_config.json")
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_update_config(config):
    """Sauvegarde la configuration de mise à jour"""
    config_file = Path("update_config.json")
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_current_version():
    """Récupère la version actuelle depuis un fichier VERSION ou Git"""
    version_file = Path("VERSION")
    if version_file.exists():
        return version_file.read_text(encoding='utf-8').strip()
    
    # Sinon, essayer de récupérer depuis Git
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--always"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except:
        return "unknown"


def update_from_git(repo_url=None, branch="main"):
    """
    Met à jour le programme depuis un dépôt Git
    
    Args:
        repo_url: URL du dépôt Git (optionnel, utilise l'origine si déjà un repo Git)
        branch: Branche à utiliser (défaut: main)
    """
    print("🔄 Vérification des mises à jour...")
    
    # Vérifier si Git est disponible
    if not check_git_available():
        print("❌ Git n'est pas installé sur votre système.")
        print("   Installez Git depuis: https://git-scm.com/downloads")
        return False
    
    # Récupérer la configuration
    config = get_update_config()
    if not repo_url:
        repo_url = config.get("repo_url")
    if not branch:
        branch = config.get("branch", "main")
    
    # Vérifier si on est déjà dans un dépôt Git
    is_git_repo = Path(".git").exists()
    
    if not is_git_repo:
        if not repo_url:
            print("❌ Ce dossier n'est pas un dépôt Git et aucune URL n'a été configurée.")
            print("\n📝 Configuration requise:")
            repo_url = input("   Entrez l'URL du dépôt Git (ex: https://github.com/USERNAME/WakSOS.git): ").strip()
            if not repo_url:
                print("❌ Aucune URL fournie. Configuration annulée.")
                return False
            
            # Sauvegarder la configuration
            config["repo_url"] = repo_url
            config["branch"] = branch
            save_update_config(config)
            print(f"✅ Configuration sauvegardée: {repo_url}")
        
        # Demander si on veut cloner ou initialiser
        print(f"\n📦 Dépôt Git détecté: {repo_url}")
        print("   Options:")
        print("   1. Cloner le dépôt (recommandé si c'est la première fois)")
        print("   2. Initialiser un dépôt Git ici")
        choice = input("   Votre choix (1/2): ").strip()
        
        if choice == "1":
            # Cloner le dépôt dans un dossier parent
            parent_dir = Path.cwd().parent
            repo_name = repo_url.split("/")[-1].replace(".git", "")
            clone_path = parent_dir / repo_name
            
            if clone_path.exists():
                print(f"❌ Le dossier {clone_path} existe déjà.")
                return False
            
            try:
                print(f"📥 Clonage du dépôt dans {clone_path}...")
                subprocess.run(["git", "clone", repo_url, str(clone_path)], check=True)
                print(f"✅ Dépôt cloné avec succès dans {clone_path}")
                print(f"💡 Pour utiliser WakSOS, déplacez-vous dans ce dossier.")
                return True
            except subprocess.CalledProcessError as e:
                print(f"❌ Erreur lors du clonage: {e}")
                return False
        else:
            # Initialiser un nouveau dépôt Git
            print(f"📦 Initialisation du dépôt Git depuis {repo_url}...")
            try:
                subprocess.run(["git", "init"], check=True)
                subprocess.run(["git", "remote", "add", "origin", repo_url], check=True)
                subprocess.run(["git", "fetch", "origin"], check=True)
                subprocess.run(["git", "checkout", "-b", branch, f"origin/{branch}"], check=True)
                print("✅ Dépôt Git initialisé avec succès!")
                return True
            except subprocess.CalledProcessError as e:
                print(f"❌ Erreur lors de l'initialisation: {e}")
                return False
    
    # Récupérer les dernières modifications
    print("📥 Récupération des dernières modifications...")
    try:
        # Vérifier le remote origin
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                check=True
            )
            current_remote = result.stdout.strip()
            
            # Si l'URL du remote est différente de celle configurée, la mettre à jour
            if repo_url and current_remote != repo_url:
                print(f"🔄 Mise à jour du remote origin: {repo_url}")
                subprocess.run(["git", "remote", "set-url", "origin", repo_url], check=True)
        except:
            # Pas de remote origin, l'ajouter
            if repo_url:
                print(f"➕ Ajout du remote origin: {repo_url}")
                subprocess.run(["git", "remote", "add", "origin", repo_url], check=True)
        
        # Sauvegarder les modifications locales non commitées
        subprocess.run(["git", "stash"], capture_output=True)
        
        # Récupérer les dernières modifications
        subprocess.run(["git", "fetch", "origin"], check=True)
        
        # Vérifier s'il y a des mises à jour
        current_branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        ).stdout.strip()
        
        local_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        ).stdout.strip()
        
        remote_commit = subprocess.run(
            ["git", "rev-parse", f"origin/{current_branch}"],
            capture_output=True,
            text=True,
            check=True
        ).stdout.strip()
        
        if local_commit == remote_commit:
            print("✅ Vous avez déjà la dernière version!")
            # Restaurer les modifications locales
            subprocess.run(["git", "stash", "pop"], capture_output=True)
            return True
        
        # Afficher les changements
        print(f"📋 Nouvelles modifications disponibles:")
        commits = subprocess.run(
            ["git", "log", f"{local_commit}..{remote_commit}", "--oneline"],
            capture_output=True,
            text=True,
            check=True
        ).stdout.strip()
        
        if commits:
            print(commits)
        
        # Demander confirmation
        response = input("\n❓ Voulez-vous mettre à jour maintenant? (o/N): ").strip().lower()
        if response not in ['o', 'oui', 'y', 'yes']:
            print("❌ Mise à jour annulée.")
            subprocess.run(["git", "stash", "pop"], capture_output=True)
            return False
        
        # Mettre à jour
        print("🔄 Mise à jour en cours...")
        subprocess.run(["git", "pull", "origin", current_branch], check=True)
        
        # Restaurer les modifications locales si possible
        subprocess.run(["git", "stash", "pop"], capture_output=True)
        
        print("✅ Mise à jour terminée avec succès!")
        
        # Afficher la nouvelle version
        new_version = get_current_version()
        print(f"📌 Version actuelle: {new_version}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors de la mise à jour: {e}")
        # Restaurer les modifications locales en cas d'erreur
        subprocess.run(["git", "stash", "pop"], capture_output=True)
        return False


def update_from_http(version_url, files_url_base):
    """
    Met à jour le programme depuis un serveur HTTP
    
    Args:
        version_url: URL pour récupérer la version actuelle (fichier texte)
        files_url_base: URL de base pour télécharger les fichiers
    """
    try:
        import urllib.request
        import json
        
        print("🔄 Vérification des mises à jour...")
        
        # Récupérer la version distante
        with urllib.request.urlopen(version_url) as response:
            remote_version = response.read().decode('utf-8').strip()
        
        current_version = get_current_version()
        
        if remote_version == current_version:
            print("✅ Vous avez déjà la dernière version!")
            return True
        
        print(f"📌 Version actuelle: {current_version}")
        print(f"📌 Version disponible: {remote_version}")
        
        # Récupérer la liste des fichiers à mettre à jour
        files_url = f"{files_url_base}/files.json"
        with urllib.request.urlopen(files_url) as response:
            files_data = json.loads(response.read().decode('utf-8'))
        
        # Demander confirmation
        response = input("\n❓ Voulez-vous mettre à jour maintenant? (o/N): ").strip().lower()
        if response not in ['o', 'oui', 'y', 'yes']:
            print("❌ Mise à jour annulée.")
            return False
        
        # Télécharger et mettre à jour les fichiers
        print("🔄 Mise à jour en cours...")
        for file_info in files_data.get("files", []):
            file_path = file_info["path"]
            file_url = f"{files_url_base}/{file_path}"
            
            print(f"  📥 Téléchargement: {file_path}")
            
            # Créer le dossier si nécessaire
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Télécharger le fichier
            with urllib.request.urlopen(file_url) as response:
                with open(file_path, 'wb') as f:
                    f.write(response.read())
        
        # Mettre à jour le fichier VERSION
        with open("VERSION", 'w', encoding='utf-8') as f:
            f.write(remote_version)
        
        print("✅ Mise à jour terminée avec succès!")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la mise à jour: {e}")
        return False


def main():
    """Fonction principale"""
    print("=" * 60)
    print("🚀 WakSOS - Système de mise à jour")
    print("=" * 60)
    print()
    
    # Afficher la version actuelle
    current_version = get_current_version()
    print(f"📌 Version actuelle: {current_version}")
    
    # Récupérer la configuration
    config = get_update_config()
    if config.get("repo_url"):
        print(f"📦 Dépôt configuré: {config.get('repo_url')}")
    print()
    
    # Mise à jour via Git
    success = update_from_git()
    
    if success:
        print()
        print("💡 Astuce: Vous pouvez relancer ce script à tout moment pour vérifier les mises à jour.")
    else:
        print()
        print("💡 Pour configurer la mise à jour:")
        print("   1. Créez un dépôt sur GitHub/GitLab")
        print("   2. Relancez ce script et entrez l'URL du dépôt")
    
    input("\nAppuyez sur Entrée pour fermer...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Mise à jour interrompue par l'utilisateur.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
        input("\nAppuyez sur Entrée pour fermer...")
        sys.exit(1)

