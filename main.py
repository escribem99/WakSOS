"""
Point d'entrée principal de WakSOS - Version simplifiée et fonctionnelle
"""
import json
import time
import os
import queue
import threading
import tkinter as tk
from overlay import ComboOverlay
from state_tracker import StateTracker
from log_selector import LogSelector
from window_selector import WindowSelector, is_window_active, is_window_valid
from combo_tracker import ComboTracker
from debug_logger import debug, info, error, warning

# Essayer d'importer keyboard pour les raccourcis globaux
try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False
    warning("⚠ Module 'keyboard' non disponible. Installez-le avec: pip install keyboard")
    warning("   Les raccourcis clavier globaux ne fonctionneront pas.")


class WakSOS:
    def __init__(self, skip_selection=False):
        """Initialise l'application principale"""
        self.running = False
        self.config = self.load_config()
        
        # Sélectionner le fichier log
        log_path = self.config.get("log_path")
        if not skip_selection:
            if not log_path or not os.path.exists(log_path):
                selector = LogSelector("config.json")
                selector.run()
                self.config = self.load_config()
                log_path = self.config.get("log_path")
                if not log_path or not os.path.exists(log_path):
                    from log_parser import WakfuLogParser
                    parser = WakfuLogParser()
                    if os.path.exists(parser.log_path):
                        log_path = parser.log_path
        
        # Initialiser le combo tracker d'abord
        self.combo_tracker = ComboTracker("iop_combos.json")
        
        # Initialiser le tracker d'états avec le combo_tracker pour détecter les coûts
        self.tracker = StateTracker(log_path=log_path, update_callback=self.on_states_update, combo_tracker=self.combo_tracker)
        
        # Réinitialiser les états dans le parser AVANT de créer les overlays
        # Cela évite que les anciennes valeurs du log soient rechargées
        self.tracker.parser.reset_states()
        # Réinitialiser aussi la position du fichier pour ne lire que les nouvelles lignes
        if hasattr(self.tracker.parser, 'file_position'):
            try:
                # Se positionner à la fin du fichier pour ignorer les anciennes lignes
                if os.path.exists(log_path):
                    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                        f.seek(0, 2)  # Se positionner à la fin
                        self.tracker.parser.file_position = f.tell()
            except:
                pass  # En cas d'erreur, continuer quand même
        
        # Callback pour réinitialiser les états
        def reset_states_callback(class_name):
            self.tracker.reset_states(class_name)
            if class_name == "iop":
                self.combo_tracker.reset_combo()
        
        # Sélectionner les fenêtres Wakfu
        self.window_mapping = self.config.get("window_mapping", {})
        if not skip_selection:
            try:
                temp_root = tk.Tk()
                temp_root.withdraw()
                selector = WindowSelector("config.json", parent=temp_root)
                
                def check_window():
                    try:
                        if not selector.root.winfo_exists():
                            temp_root.quit()
                        else:
                            temp_root.after(50, check_window)
                    except:
                        temp_root.quit()
                
                temp_root.after(50, check_window)
                temp_root.mainloop()
                
                try:
                    if temp_root.winfo_exists():
                        temp_root.destroy()
                except:
                    pass
                
                tk._default_root = None
                time.sleep(0.2)
                
                self.config = self.load_config()
                self.window_mapping = self.config.get("window_mapping", {})
            except Exception as e:
                error(f"Erreur lors de la sélection de fenêtres: {e}")
                self.window_mapping = {}
        
        # Récupérer les handles de fenêtres
        self.iop_window_hwnd = None
        self.cra_window_hwnd = None
        self.overlay_iop = None
        self.overlay_cra = None
        
        if self.window_mapping:
            iop_config = self.window_mapping.get("iop", {})
            cra_config = self.window_mapping.get("cra", {})
            self.iop_window_hwnd = iop_config.get("hwnd") if iop_config else None
            self.cra_window_hwnd = cra_config.get("hwnd") if cra_config else None
        
        time.sleep(0.1)
        
        # Créer les overlays
        if self.iop_window_hwnd is not None:
            try:
                self.overlay_iop = ComboOverlay("iop", "config.json", reset_callback=reset_states_callback)
                self.overlay_iop.combo_tracker = self.combo_tracker
                # Stocker le HWND de la fenêtre Wakfu pour remettre le focus après les clics
                self.overlay_iop.wakfu_window_hwnd = self.iop_window_hwnd
                # Charger immédiatement (pas de délai pour éviter les problèmes)
                self.overlay_iop.load_combo_display()
                # Forcer l'affichage immédiat de l'overlay
                self.overlay_iop.show()
                # Attendre un peu pour que l'overlay soit complètement initialisé
                time.sleep(0.1)
                # Réinitialiser automatiquement l'overlay au lancement
                # Réinitialiser d'abord les combos
                self.combo_tracker.reset_combo()
                self.overlay_iop.handle_combo_update({"type": "combo_reset"})
                # Réinitialiser les états (cela va aussi mettre à jour l'affichage via le callback)
                self.overlay_iop.reset_states()
                # Réinitialiser explicitement l'affichage des états à 0
                if self.overlay_iop.class_name == "iop":
                    self.overlay_iop.update_states({"iop": {"Concentration": 0, "Courroux": 0, "Préparation": 0}}, "iop")
                info("✓ Overlay Iop créé et affiché (reset automatique)")
            except Exception as e:
                error(f"Erreur lors de la création de l'overlay Iop: {e}")
                import traceback
                traceback.print_exc()
        
        if self.cra_window_hwnd is not None:
            try:
                self.overlay_cra = ComboOverlay("cra", "config.json", reset_callback=reset_states_callback)
                # Forcer l'affichage immédiat de l'overlay
                self.overlay_cra.show()
                # Attendre un peu pour que l'overlay soit complètement initialisé
                time.sleep(0.1)
                # Réinitialiser automatiquement l'overlay au lancement
                self.overlay_cra.reset_states()
                # Réinitialiser explicitement l'affichage des états à 0
                if self.overlay_cra.class_name == "cra":
                    self.overlay_cra.update_states({"cra": {"Affûtage": 0, "Précision": 0}}, "cra")
                info("✓ Overlay Cra créé et affiché (reset automatique)")
            except Exception as e:
                error(f"Erreur lors de la création de l'overlay Cra: {e}")
                import traceback
                traceback.print_exc()
        
        if self.overlay_iop is None and self.overlay_cra is None:
            warning("⚠ Aucun overlay créé ! Veuillez sélectionner au moins une fenêtre (Iop ou Cra)")
        
        # File d'attente pour les changements depuis le thread du tracker
        self.pending_changes = []
        self.changes_queue = queue.Queue()
        
        # File d'attente pour les commandes depuis les raccourcis clavier
        self.hotkey_queue = queue.Queue()
        
        # Variables pour suivre l'état des touches (initialisées avant setup_global_hotkeys)
        self.alt_i_pressed = False
        self.alt_c_pressed = False
        
        # Initialiser les raccourcis clavier globaux
        self.setup_global_hotkeys()
    
    def load_config(self):
        """Charge la configuration"""
        try:
            with open("config.json", 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def setup_global_hotkeys(self):
        """Configure les raccourcis clavier globaux pour forcer l'affichage des overlays"""
        if not KEYBOARD_AVAILABLE:
            return
        
        def on_alt_i_press(event):
            """Quand Alt+I est pressé (appelé depuis un thread)"""
            if event.name == 'i' and keyboard.is_pressed('alt'):
                try:
                    self.hotkey_queue.put(('press_iop',), block=False)
                except:
                    pass
        
        def on_alt_i_release(event):
            """Quand Alt+I est relâché (appelé depuis un thread)"""
            if event.name == 'i':
                try:
                    self.hotkey_queue.put(('release_iop',), block=False)
                except:
                    pass
        
        def on_alt_c_press(event):
            """Quand Alt+C est pressé (appelé depuis un thread)"""
            if event.name == 'c' and keyboard.is_pressed('alt'):
                try:
                    self.hotkey_queue.put(('press_cra',), block=False)
                except:
                    pass
        
        def on_alt_c_release(event):
            """Quand Alt+C est relâché (appelé depuis un thread)"""
            if event.name == 'c':
                try:
                    self.hotkey_queue.put(('release_cra',), block=False)
                except:
                    pass
        
        try:
            # Surveiller Alt+I pour maintenir l'overlay Iop visible
            keyboard.on_press_key('i', on_alt_i_press, suppress=False)
            keyboard.on_release_key('i', on_alt_i_release, suppress=False)
            # Surveiller Alt+C pour maintenir l'overlay Cra visible
            keyboard.on_press_key('c', on_alt_c_press, suppress=False)
            keyboard.on_release_key('c', on_alt_c_release, suppress=False)
            # Afficher un message stylisé pour les raccourcis clavier
            print("\n" + "="*60)
            print("╔" + "═"*58 + "╗")
            print("║" + " "*58 + "║")
            print("║" + " "*18 + "WakSOS".center(22) + " "*18 + "║")
            print("║" + " "*58 + "║")
            print("╠" + "═"*58 + "╣")
            print("║" + " "*58 + "║")
            print("║" + " "*18 + "RACCOURCIS CLAVIER".center(22) + " "*18 + "║")
            print("║" + " "*58 + "║")
            print("║" + " "*12 + "Maintenir Alt+I  →  Focus Iop".ljust(34) + " "*12 + "║")
            print("║" + " "*12 + "Maintenir Alt+C  →  Focus Cra".ljust(34) + " "*12 + "║")
            print("║" + " "*58 + "║")
            print("╚" + "═"*58 + "╝")
            print("="*60 + "\n")
        except Exception as e:
            error(f"Erreur lors de la configuration des raccourcis clavier: {e}")
    
    def process_hotkey_commands(self):
        """Traite les commandes depuis les raccourcis clavier (appelé depuis le thread principal)"""
        try:
            while True:
                command = self.hotkey_queue.get_nowait()
                if command[0] == 'press_iop':
                    self.alt_i_pressed = True
                    if self.overlay_iop and self.overlay_iop.root.winfo_exists():
                        try:
                            self.overlay_iop.show()
                            # Alt+I pressé: Overlay Iop forcé à s'afficher
                        except Exception as e:
                            # Erreur lors de l'affichage de l'overlay Iop
                            pass
                elif command[0] == 'release_iop':
                    self.alt_i_pressed = False
                    # Alt+I relâché
                elif command[0] == 'press_cra':
                    self.alt_c_pressed = True
                    if self.overlay_cra and self.overlay_cra.root.winfo_exists():
                        try:
                            self.overlay_cra.show()
                            # Alt+C pressé: Overlay Cra forcé à s'afficher
                        except Exception as e:
                            # Erreur lors de l'affichage de l'overlay Cra
                            pass
                elif command[0] == 'release_cra':
                    self.alt_c_pressed = False
                    # Alt+C relâché
        except:
            pass  # Queue vide, continuer
    
    def on_states_update(self, states_dict, current_class, changes):
        """Callback appelé quand les états sont mis à jour (depuis le thread du tracker)"""
        # Ne pas accéder aux widgets Tkinter depuis ce thread !
        # Mettre les changements dans une queue pour traitement dans le thread principal
        if changes:
            try:
                self.changes_queue.put((states_dict, current_class, changes), block=False)
            except:
                pass  # Queue pleine, ignorer
    
    def process_pending_changes(self):
        """Traite les changements en attente depuis le thread principal"""
        try:
            while True:
                states_dict, current_class, changes = self.changes_queue.get_nowait()
                for change in changes:
                    if change.get("type") == "pointe_affutee" and self.overlay_cra:
                        self.overlay_cra.pointe_affutee_active = True
                    elif change.get("type") == "consomme_pointe_affutee" and self.overlay_cra:
                        self.overlay_cra.pointe_affutee_active = False
                    elif change.get("type") == "balise_affutee" and self.overlay_cra:
                        value = change.get("value", 0)
                        self.overlay_cra.set_balise_affutee_value(value)
                    elif change.get("type") == "lance_sort_balise" and self.overlay_cra:
                        current_value = self.overlay_cra.balise_affutee_value
                        new_value = max(0, current_value - 1)
                        self.overlay_cra.set_balise_affutee_value(new_value)
                    elif change.get("type") == "combat_end" and self.overlay_cra:
                        self.overlay_cra.pointe_affutee_active = False
                        self.overlay_cra.set_balise_affutee_value(0)
                    elif change.get("type") == "manual_reset" and self.overlay_cra:
                        self.overlay_cra.pointe_affutee_active = False
                    elif change.get("type") == "lance_sort" and change.get("class") == "iop":
                        sort_name = change.get("sort_name")
                        sort_cost = change.get("sort_cost")
                        if sort_name:
                            # Sort détecté (pas de message console pour éviter le flood)
                            
                            # Mettre à jour l'affichage du dernier sort utilisé (pour tous les sorts Iop)
                            if self.overlay_iop:
                                self.overlay_iop._update_last_sort(sort_name)
                            
                            # Vérifier si le sort est un sort combo avant de le traiter
                            if self.combo_tracker.is_sort_combo(sort_name):
                                # Passer le coût au combo_tracker si disponible (pour le sort Charge notamment)
                                combo_update = self.combo_tracker.process_sort(sort_name, sort_cost=sort_cost)
                                if self.overlay_iop:
                                    self.overlay_iop.handle_combo_update(combo_update)
                            # Si le sort n'est pas un combo, on ne fait rien (juste l'affichage du dernier sort)
                            
                            # Réinitialiser la Préparation après chaque sort utilisé
                            if self.tracker:
                                self.tracker.parser.reset_states("iop", "Préparation")
                                # Mettre à jour l'overlay Iop pour afficher la Préparation à 0
                                if self.overlay_iop:
                                    states = self.tracker.get_current_states()
                                    self.overlay_iop.update_states(states, "iop")
                    elif change.get("type") == "combat_end":
                        self.combo_tracker.reset_combo()
                        if self.overlay_iop:
                            self.overlay_iop.handle_combo_update({"type": "combo_reset"})
                    elif change.get("type") == "tour_suivant":
                        # Réinitialiser les combos quand un nouveau tour commence
                        self.combo_tracker.reset_combo()
                        if self.overlay_iop:
                            self.overlay_iop.handle_combo_update({"type": "combo_reset"})
        except:
            pass  # Queue vide, continuer
    
    def start(self):
        """Démarre l'application"""
        info("Démarrage de WakSOS...")
        log_path = self.tracker.parser.log_path
        if log_path and os.path.exists(log_path):
            info(f"✓ Lecture du log: {log_path}")
        else:
            warning(f"⚠ Fichier log introuvable: {log_path}")
        info("Appuyez sur Ctrl+C pour arrêter")
        
        self.running = True
        self.tracker.start()
        
        # Lier la fermeture des fenêtres
        if self.overlay_iop:
            self.overlay_iop.root.protocol("WM_DELETE_WINDOW", lambda: self.overlay_iop.close_overlay())
        if self.overlay_cra:
            self.overlay_cra.root.protocol("WM_DELETE_WINDOW", lambda: self.overlay_cra.close_overlay())
        
        # Boucle principale
        last_update = 0
        update_interval = 0.5
        
        if self.overlay_iop is None and self.overlay_cra is None:
            warning("⚠ Aucun overlay créé ! Impossible de continuer.")
            return
        
        info("Boucle principale démarrée - le programme restera ouvert indéfiniment")
        iteration_count = 0
        
        # BOUCLE INFINIE - NE JAMAIS SORTIR SAUF CTRL+C
        while True:
            try:
                iteration_count += 1
                
                try:
                    current_time = time.time()
                    
                    # Traiter les changements en attente depuis le thread du tracker
                    self.process_pending_changes()
                    
                    # Traiter les commandes depuis les raccourcis clavier
                    self.process_hotkey_commands()
                    
                    # Mettre à jour les états périodiquement
                    if current_time - last_update >= update_interval:
                        try:
                            states = self.tracker.get_current_states()
                            
                            if self.overlay_iop:
                                try:
                                    if self.overlay_iop.root.winfo_exists():
                                        self.overlay_iop.update_states(states, "iop")
                                except tk.TclError:
                                    pass
                            
                            if self.overlay_cra:
                                try:
                                    if self.overlay_cra.root.winfo_exists():
                                        self.overlay_cra.update_states(states, "cra")
                                except tk.TclError:
                                    pass
                            
                            last_update = current_time
                        except Exception as e:
                            error(f"Erreur lors de la mise à jour des états: {e}")
                            import traceback
                            traceback.print_exc()
                    
                    # Afficher/masquer les overlays selon la fenêtre active OU si Alt+I/C est maintenu
                    if self.overlay_iop:
                        try:
                            if self.overlay_iop.root.winfo_exists():
                                if self.iop_window_hwnd is not None:
                                    is_valid = is_window_valid(self.iop_window_hwnd)
                                    wakfu_is_active = is_window_active(self.iop_window_hwnd)
                                    
                                    # Afficher si la fenêtre Wakfu est active OU si Alt+I est maintenu
                                    if is_valid and (wakfu_is_active or getattr(self, 'alt_i_pressed', False)):
                                        if not self.overlay_iop.is_visible:
                                            self.overlay_iop.show()
                                    else:
                                        # Masquer si la fenêtre Wakfu n'est pas active ET Alt+I n'est pas maintenu
                                        if self.overlay_iop.is_visible:
                                            self.overlay_iop.hide()
                                
                                self.overlay_iop.root.update()
                        except:
                            pass
                    
                    if self.overlay_cra:
                        try:
                            if self.overlay_cra.root.winfo_exists():
                                if self.cra_window_hwnd is not None:
                                    is_valid = is_window_valid(self.cra_window_hwnd)
                                    wakfu_is_active = is_window_active(self.cra_window_hwnd)
                                    
                                    # Afficher si la fenêtre Wakfu est active OU si Alt+C est maintenu
                                    if is_valid and (wakfu_is_active or getattr(self, 'alt_c_pressed', False)):
                                        if not self.overlay_cra.is_visible:
                                            self.overlay_cra.show()
                                    else:
                                        # Masquer si la fenêtre Wakfu n'est pas active ET Alt+C n'est pas maintenu
                                        if self.overlay_cra.is_visible:
                                            self.overlay_cra.hide()
                                
                                self.overlay_cra.root.update()
                        except:
                            pass
                    
                    # Le programme reste ouvert indéfiniment
                    time.sleep(0.01)
                except tk.TclError as e:
                    # Ignorer les erreurs TclError (fenêtre fermée, etc.)
                    error_msg = str(e)
                    # Ignorer les erreurs TclError
                    # Sinon, ignorer silencieusement l'erreur Tcl_AsyncDelete
                    time.sleep(0.01)
                except RuntimeError as e:
                    # Ignorer RuntimeError liés à Tcl_AsyncDelete
                    error_msg = str(e)
                    if "Tcl_AsyncDelete" in error_msg or "wrong thread" in error_msg.lower():
                        # Ignorer silencieusement
                        pass
                    else:
                        error(f"RuntimeError dans la boucle (itération {iteration_count}): {e}")
                    time.sleep(0.01)
                except Exception as e:
                    error(f"Exception dans la boucle principale (itération {iteration_count}): {e}")
                    import traceback
                    traceback.print_exc()
                    # CONTINUER MÊME EN CAS D'ERREUR
                    time.sleep(0.1)
            except KeyboardInterrupt:
                info("\nArrêt de WakSOS (Ctrl+C)...")
                break
            except RuntimeError as e:
                # Ignorer RuntimeError liés à Tcl_AsyncDelete
                error_msg = str(e)
                if "Tcl_AsyncDelete" in error_msg or "wrong thread" in error_msg.lower():
                    # Ignorer silencieusement et continuer
                    # Erreur Tcl_AsyncDelete ignorée, continuation
                    time.sleep(0.1)
                else:
                    error(f"RuntimeError FATALE dans la boucle (itération {iteration_count}): {e}")
                    import traceback
                    traceback.print_exc()
                    time.sleep(0.5)
            except Exception as e:
                error(f"Exception FATALE dans la boucle (itération {iteration_count}): {e}")
                import traceback
                traceback.print_exc()
                # CONTINUER MÊME EN CAS D'ERREUR FATALE
                time.sleep(0.5)
        
        # Nettoyage seulement si on sort de la boucle
        info("Arrêt de WakSOS...")
        self.running = False
        self.tracker.stop()
        
        # Nettoyer les raccourcis clavier
        if KEYBOARD_AVAILABLE:
            try:
                keyboard.unhook_all()
                # Raccourcis clavier désactivés
            except:
                pass
        
        if self.overlay_iop:
            try:
                self.overlay_iop.close_overlay()
            except:
                pass
        if self.overlay_cra:
            try:
                self.overlay_cra.close_overlay()
            except:
                pass
        info("Fonction start() terminée")


if __name__ == "__main__":
    from debug_logger import debug, info, error, warning
    
    # FORCER LE PROGRAMME À RESTER OUVERT
    import sys
    import atexit
    
    def keep_alive():
        """Fonction pour maintenir le processus ouvert"""
        while True:
            try:
                time.sleep(1)
            except:
                pass
    
    # Enregistrer une fonction pour maintenir le processus ouvert
    atexit.register(lambda: time.sleep(999999))
    
    try:
        info("=== DÉMARRAGE DE WAKSOS ===")
        app = WakSOS()
        # Appeler start() directement (pas dans un thread - Tkinter doit être dans le thread principal)
        try:
            app.start()
        except:
            # Même si start() se termine, on reste ouvert
            pass
        
        # BOUCLE INFINIE ABSOLUE
        info("Boucle de maintien du processus démarrée")
        while True:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                info("\nArrêt demandé (Ctrl+C)...")
                break
            except:
                # Continuer même en cas d'erreur
                time.sleep(1)
    except KeyboardInterrupt:
        info("\nArrêt demandé (Ctrl+C)...")
    except Exception as e:
        error(f"ERREUR FATALE: {e}")
        import traceback
        traceback.print_exc()
        # Même en cas d'erreur fatale, on reste ouvert
        info("Le programme reste ouvert malgré l'erreur. Appuyez sur Ctrl+C pour fermer.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
