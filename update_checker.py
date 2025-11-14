"""
Module pour vérifier et effectuer les mises à jour depuis Git
"""
import os
import subprocess
import json
import shutil
from pathlib import Path


def check_git_available():
    """Vérifie si Git est installé et disponible"""
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def check_update_available(repo_url=None):
    """
    Vérifie s'il y a des mises à jour disponibles
    
    Returns:
        tuple: (has_update: bool, error_message: str or None)
    """
    if not check_git_available():
        return False, "Git n'est pas installé"
    
    # Vérifier si on est dans un dépôt Git
    if not Path(".git").exists():
        return False, "Pas un dépôt Git"
    
    try:
        # Récupérer la configuration si pas d'URL fournie
        if not repo_url:
            config_file = Path("update_config.json")
            if config_file.exists():
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        repo_url = config.get("repo_url")
                except:
                    pass
        
        if not repo_url:
            # Essayer de récupérer depuis le remote existant
            try:
                result = subprocess.run(
                    ["git", "remote", "get-url", "origin"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                repo_url = result.stdout.strip()
            except:
                return False, "Aucun dépôt configuré"
        
        # Vérifier le remote origin
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                check=True
            )
            current_remote = result.stdout.strip()
            
            if repo_url and current_remote != repo_url:
                subprocess.run(["git", "remote", "set-url", "origin", repo_url], check=True, capture_output=True)
        except:
            if repo_url:
                subprocess.run(["git", "remote", "add", "origin", repo_url], check=True, capture_output=True)
        
        # Récupérer les dernières modifications
        subprocess.run(["git", "fetch", "origin"], check=True, capture_output=True)
        
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
        
        return local_commit != remote_commit, None
        
    except subprocess.CalledProcessError as e:
        return False, f"Erreur Git: {e}"
    except Exception as e:
        return False, f"Erreur: {e}"


def perform_update(repo_url=None, preserve_config=True):
    """
    Effectue la mise à jour depuis Git en préservant config.json
    
    Args:
        repo_url: URL du dépôt Git (optionnel)
        preserve_config: Si True, préserve le log_path dans config.json
    
    Returns:
        tuple: (success: bool, message: str)
    """
    if not check_git_available():
        return False, "Git n'est pas installé"
    
    if not Path(".git").exists():
        return False, "Pas un dépôt Git"
    
    try:
        # Sauvegarder le log_path AVANT toute opération Git
        saved_log_path = None
        saved_config = None
        if preserve_config and Path("config.json").exists():
            try:
                with open("config.json", 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    saved_log_path = saved_config.get("log_path")
            except:
                pass  # Si on ne peut pas lire, on continue quand même
        
        # Sauvegarder les modifications locales
        subprocess.run(["git", "stash"], capture_output=True, check=False)
        
        # Récupérer la configuration si pas d'URL fournie
        if not repo_url:
            config_file = Path("update_config.json")
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    repo_url = config.get("repo_url")
        
        if not repo_url:
            try:
                result = subprocess.run(
                    ["git", "remote", "get-url", "origin"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                repo_url = result.stdout.strip()
            except:
                return False, "Aucun dépôt configuré"
        
        # Vérifier le remote origin
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                check=True
            )
            current_remote = result.stdout.strip()
            
            if repo_url and current_remote != repo_url:
                subprocess.run(["git", "remote", "set-url", "origin", repo_url], check=True, capture_output=True)
        except:
            if repo_url:
                subprocess.run(["git", "remote", "add", "origin", repo_url], check=True, capture_output=True)
        
        # Récupérer les dernières modifications
        subprocess.run(["git", "fetch", "origin"], check=True, capture_output=True)
        
        # Obtenir la branche actuelle
        current_branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        ).stdout.strip()
        
        # Mettre à jour
        subprocess.run(["git", "pull", "origin", current_branch], check=True, capture_output=True)
        
        # Restaurer config.json avec le log_path sauvegardé
        if preserve_config and saved_log_path:
            if Path("config.json").exists():
                try:
                    with open("config.json", 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    config["log_path"] = saved_log_path
                    with open("config.json", 'w', encoding='utf-8') as f:
                        json.dump(config, f, indent=2, ensure_ascii=False)
                except:
                    # Si on ne peut pas lire/écrire, créer un nouveau config.json avec juste le log_path
                    if saved_config:
                        saved_config["log_path"] = saved_log_path
                        with open("config.json", 'w', encoding='utf-8') as f:
                            json.dump(saved_config, f, indent=2, ensure_ascii=False)
                    else:
                        new_config = {"log_path": saved_log_path}
                        with open("config.json", 'w', encoding='utf-8') as f:
                            json.dump(new_config, f, indent=2, ensure_ascii=False)
            else:
                # Si config.json n'existe pas après la mise à jour, le recréer avec le log_path
                if saved_config:
                    saved_config["log_path"] = saved_log_path
                    with open("config.json", 'w', encoding='utf-8') as f:
                        json.dump(saved_config, f, indent=2, ensure_ascii=False)
                else:
                    new_config = {"log_path": saved_log_path}
                    with open("config.json", 'w', encoding='utf-8') as f:
                        json.dump(new_config, f, indent=2, ensure_ascii=False)
        
        # Restaurer les modifications locales si possible
        subprocess.run(["git", "stash", "pop"], capture_output=True)
        
        return True, "Mise à jour réussie"
        
    except subprocess.CalledProcessError as e:
        # Restaurer les modifications locales en cas d'erreur
        subprocess.run(["git", "stash", "pop"], capture_output=True)
        return False, f"Erreur lors de la mise à jour: {e}"
    except Exception as e:
        return False, f"Erreur: {e}"

