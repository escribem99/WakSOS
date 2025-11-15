"""
Module pour vérifier et effectuer les mises à jour depuis Git
"""
import os
import sys
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
    
    # Vérifier si on est dans un dépôt Git valide
    # Utiliser git rev-parse pour vérifier que c'est un vrai dépôt
    check_repo = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        capture_output=True,
        text=True,
        check=False
    )
    
    if check_repo.returncode != 0:
        # Pas un dépôt Git valide, essayer d'initialiser le dépôt
        try:
            # Initialiser le dépôt Git
            init_result = subprocess.run(
                ["git", "init"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if init_result.returncode != 0:
                # Impossible d'initialiser, retourner False sans erreur (le bouton restera grisé)
                return False, None
            
            # Faire un commit initial si nécessaire (pour avoir un HEAD)
            # Vérifier s'il y a des fichiers à commiter
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if status_result.stdout.strip():
                # Il y a des fichiers non suivis, les ajouter et faire un commit initial
                subprocess.run(
                    ["git", "add", "."],
                    capture_output=True,
                    text=True,
                    check=False
                )
                subprocess.run(
                    ["git", "commit", "-m", "Initial commit"],
                    capture_output=True,
                    text=True,
                    check=False
                )
        except:
            # Si l'initialisation échoue, retourner False sans erreur
            return False, None
    
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
            except subprocess.CalledProcessError:
                # Le remote n'existe pas, essayer de le créer avec l'URL par défaut
                # URL par défaut du dépôt GitHub
                default_repo_url = "https://github.com/escribem99/WakSOS"
                try:
                    # Vérifier d'abord si on est dans un dépôt Git valide
                    check_repo = subprocess.run(
                        ["git", "rev-parse", "--git-dir"],
                        capture_output=True,
                        text=True,
                        check=False
                    )
                    
                    if check_repo.returncode != 0:
                        # Pas un dépôt Git valide, retourner False sans erreur
                        return False, None
                    
                    add_result = subprocess.run(
                        ["git", "remote", "add", "origin", default_repo_url],
                        capture_output=True,
                        text=True,
                        check=False
                    )
                    
                    if add_result.returncode != 0:
                        # Le remote existe peut-être déjà, récupérer son URL
                        error_msg = add_result.stderr or add_result.stdout or ""
                        if "already exists" in error_msg.lower():
                            try:
                                result = subprocess.run(
                                    ["git", "remote", "get-url", "origin"],
                                    capture_output=True,
                                    text=True,
                                    check=True
                                )
                                repo_url = result.stdout.strip()
                            except:
                                return False, None
                        else:
                            return False, None
                    else:
                        repo_url = default_repo_url
                except:
                    return False, None
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
        fetch_result = subprocess.run(
            ["git", "fetch", "origin"],
            capture_output=True,
            text=True,
            check=False
        )
        
        # Obtenir la branche actuelle
        try:
            current_branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                check=True
            )
            current_branch = current_branch_result.stdout.strip()
        except:
            # Par défaut, utiliser "main"
            current_branch = "main"
        
        # Vérifier quelle branche existe sur le remote
        # Si la branche locale n'existe pas sur le remote, utiliser "main"
        try:
            check_remote_branch = subprocess.run(
                ["git", "ls-remote", "--heads", "origin", current_branch],
                capture_output=True,
                text=True,
                check=False
            )
            if not check_remote_branch.stdout.strip():
                # La branche locale n'existe pas sur le remote, utiliser "main"
                current_branch = "main"
        except:
            # En cas d'erreur, utiliser "main"
            current_branch = "main"
        
        # Obtenir le commit local
        try:
            local_commit_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True
            )
            local_commit = local_commit_result.stdout.strip()
        except:
            return False, "Impossible de récupérer le commit local"
        
        # Obtenir le commit distant
        try:
            remote_commit_result = subprocess.run(
                ["git", "rev-parse", f"origin/{current_branch}"],
                capture_output=True,
                text=True,
                check=True
            )
            remote_commit = remote_commit_result.stdout.strip()
        except:
            # Si on ne peut pas récupérer le commit distant, essayer de fetch à nouveau
            try:
                subprocess.run(
                    ["git", "fetch", "origin", current_branch],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=15
                )
                remote_commit_result = subprocess.run(
                    ["git", "rev-parse", f"origin/{current_branch}"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                remote_commit = remote_commit_result.stdout.strip()
            except:
                # Si ça échoue encore, retourner False sans erreur (peut-être pas de connexion)
                return False, None
        
        # Comparer les commits
        has_update = local_commit != remote_commit
        return has_update, None
        
    except subprocess.CalledProcessError as e:
        return False, f"Erreur Git: {e}"
    except Exception as e:
        return False, f"Erreur: {e}"


def perform_update(repo_url=None, preserve_config=True):
    """
    Effectue la mise à jour en supprimant le dossier et en le re-clonant depuis GitHub
    Cela évite complètement les problèmes de conflits Git
    
    Args:
        repo_url: URL du dépôt Git (optionnel)
        preserve_config: Si True, préserve le log_path dans config.json
    
    Returns:
        tuple: (success: bool, message: str)
    """
    if not check_git_available():
        return False, "Git n'est pas installé"
    
    try:
        # Sauvegarder le log_path AVANT toute opération
        saved_log_path = None
        saved_config = None
        if preserve_config and Path("config.json").exists():
            try:
                with open("config.json", 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    saved_log_path = saved_config.get("log_path")
            except:
                pass  # Si on ne peut pas lire, on continue quand même
        
        # Récupérer l'URL du dépôt
        if not repo_url:
            # Essayer depuis update_config.json
            config_file = Path("update_config.json")
            if config_file.exists():
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        repo_url = config.get("repo_url")
                except:
                    pass
            
            # Si toujours pas d'URL, essayer depuis Git
            if not repo_url and Path(".git").exists():
                try:
                    result = subprocess.run(
                        ["git", "remote", "get-url", "origin"],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    repo_url = result.stdout.strip()
                except:
                    pass
        
        if not repo_url:
            return False, "Aucun dépôt configuré. Veuillez configurer l'URL du dépôt."
        
        # Obtenir le chemin du dossier actuel et du parent
        current_dir = Path.cwd().resolve()
        parent_dir = current_dir.parent
        folder_name = current_dir.name
        
        # Créer un nom temporaire pour le nouveau clone
        temp_folder_name = f"{folder_name}_temp_clone"
        temp_path = parent_dir / temp_folder_name
        
        # Cloner le dépôt dans un dossier temporaire
        clone_result = subprocess.run(
            ["git", "clone", repo_url, str(temp_path)],
            capture_output=True,
            text=True,
            check=False
        )
        
        if clone_result.returncode != 0:
            error_msg = clone_result.stderr or clone_result.stdout or "Erreur inconnue"
            return False, f"Erreur lors du clonage du dépôt:\n{error_msg}"
        
        # Vérifier que main.py existe dans le clone
        if not (temp_path / "main.py").exists():
            # Nettoyer le dossier temporaire
            try:
                shutil.rmtree(temp_path)
            except:
                pass
            return False, "Erreur: main.py introuvable dans le dépôt cloné"
        
        # Vérifier la syntaxe de main.py
        syntax_check = subprocess.run(
            [sys.executable, "-m", "py_compile", str(temp_path / "main.py")],
            capture_output=True,
            text=True
        )
        
        if syntax_check.returncode != 0:
            error_msg = syntax_check.stderr or "Erreur de syntaxe inconnue"
            # Nettoyer le dossier temporaire
            try:
                shutil.rmtree(temp_path)
            except:
                pass
            return False, f"Erreur de syntaxe dans main.py du dépôt:\n{error_msg}"
        
        # Au lieu de renommer/supprimer le dossier actuel (qui peut être verrouillé),
        # copier les fichiers du nouveau clone vers l'ancien dossier
        # Cela évite les problèmes d'accès refusé
        
        # Créer un backup des fichiers importants avant de les remplacer
        old_path_backup = parent_dir / f"{folder_name}_old_backup"
        
        # Supprimer le backup précédent s'il existe
        if old_path_backup.exists():
            try:
                shutil.rmtree(old_path_backup)
            except:
                pass  # Pas grave si on ne peut pas supprimer
        
        # Copier les fichiers importants dans le backup (sauf .git et dossiers temporaires)
        try:
            if current_dir.exists():
                old_path_backup.mkdir(exist_ok=True)
                # Sauvegarder config.json et autres fichiers de config
                for config_file in ["config.json", "update_config.json"]:
                    src = current_dir / config_file
                    if src.exists():
                        try:
                            shutil.copy2(src, old_path_backup / config_file)
                        except:
                            pass
        except:
            pass  # Pas grave si le backup échoue
        
        # Copier tous les fichiers du nouveau clone vers le dossier actuel
        # (en excluant .git pour garder l'historique local si nécessaire)
        try:
            for item in temp_path.iterdir():
                # Ignorer le dossier .git du nouveau clone (on garde celui du dossier actuel)
                if item.name == ".git":
                    continue
                
                dest = current_dir / item.name
                
                # Supprimer l'ancien fichier/dossier s'il existe
                if dest.exists():
                    try:
                        if dest.is_dir():
                            shutil.rmtree(dest)
                        else:
                            dest.unlink()
                    except Exception as e:
                        # Si on ne peut pas supprimer, essayer de continuer quand même
                        # (certains fichiers peuvent être verrouillés)
                        pass
                
                # Copier le nouveau fichier/dossier
                try:
                    if item.is_dir():
                        shutil.copytree(item, dest)
                    else:
                        shutil.copy2(item, dest)
                except Exception as e:
                    # Si on ne peut pas copier un fichier, continuer avec les autres
                    pass
        except Exception as e:
            # Nettoyer le dossier temporaire
            try:
                shutil.rmtree(temp_path)
            except:
                pass
            return False, f"Erreur lors de la copie des fichiers: {e}"
        
        # Supprimer le dossier temporaire après la mise à jour réussie
        try:
            if temp_path.exists():
                shutil.rmtree(temp_path)
        except:
            pass  # Pas grave si on ne peut pas supprimer le dossier temporaire
        
        # Supprimer le backup après succès
        try:
            if old_path_backup.exists():
                shutil.rmtree(old_path_backup)
        except:
            pass  # Pas grave si on ne peut pas supprimer le backup
        
        # Restaurer config.json avec le log_path sauvegardé
        if preserve_config and saved_log_path:
            config_path = current_dir / "config.json"
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    config["log_path"] = saved_log_path
                    with open(config_path, 'w', encoding='utf-8') as f:
                        json.dump(config, f, indent=2, ensure_ascii=False)
                except:
                    # Si on ne peut pas lire/écrire, créer un nouveau config.json avec juste le log_path
                    if saved_config:
                        saved_config["log_path"] = saved_log_path
                        with open(config_path, 'w', encoding='utf-8') as f:
                            json.dump(saved_config, f, indent=2, ensure_ascii=False)
                    else:
                        new_config = {"log_path": saved_log_path}
                        with open(config_path, 'w', encoding='utf-8') as f:
                            json.dump(new_config, f, indent=2, ensure_ascii=False)
            else:
                # Si config.json n'existe pas, le créer avec le log_path
                if saved_config:
                    saved_config["log_path"] = saved_log_path
                    with open(config_path, 'w', encoding='utf-8') as f:
                        json.dump(saved_config, f, indent=2, ensure_ascii=False)
                else:
                    new_config = {"log_path": saved_log_path}
                    with open(config_path, 'w', encoding='utf-8') as f:
                        json.dump(new_config, f, indent=2, ensure_ascii=False)
        
        return True, "Mise à jour réussie"
        
    except Exception as e:
        return False, f"Erreur: {e}"

