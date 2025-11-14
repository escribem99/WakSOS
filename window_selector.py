"""
Module pour sélectionner les fenêtres Wakfu et détecter la fenêtre active
"""
import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import threading
from pathlib import Path
from debug_logger import debug, info, error, warning
try:
    from update_checker import check_update_available, perform_update
except ImportError:
    check_update_available = None
    perform_update = None

try:
    import win32gui
    import win32con
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    print("⚠ pywin32 non installé. Installation nécessaire pour la sélection de fenêtres.")
    print("   Installez avec: pip install pywin32")


class WindowSelector:
    """Fenêtre pour sélectionner les fenêtres Wakfu"""
    
    def __init__(self, config_path="config.json", parent=None):
        """Initialise le sélecteur de fenêtres"""
        if not WIN32_AVAILABLE:
            raise ImportError("pywin32 est requis pour la sélection de fenêtres")
        
        self.config_path = config_path
        self.selected_windows = {
            "iop": None,
            "cra": None
        }
        self.window_handles = {}  # {hwnd: window_info}
        self.selection_done = False
        self.update_available = False
        self.update_button = None
        self.update_blink_state = False
        self.update_blink_job = None
        
        # Créer la fenêtre principale ou une Toplevel si parent fourni
        if parent is None:
            self.root = tk.Tk()
        else:
            self.root = tk.Toplevel(parent)
        
        # Charger la version
        self.version = self.load_version()
        self.root.title(f"WakSOS v{self.version} - Sélection des fenêtres Wakfu")
        self.root.geometry("700x500")
        self.root.resizable(False, False)
        
        # Empêcher la fermeture accidentelle
        self.root.protocol("WM_DELETE_WINDOW", self.skip)
        
        # Centrer la fenêtre
        self.center_window()
        
        self.create_ui()
    
    def center_window(self):
        """Centre la fenêtre sur l'écran"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def get_wakfu_windows(self):
        """Récupère toutes les fenêtres Wakfu ouvertes"""
        windows = []
        
        def enum_handler(hwnd, ctx):
            if win32gui.IsWindowVisible(hwnd):
                window_text = win32gui.GetWindowText(hwnd)
                class_name = win32gui.GetClassName(hwnd)
                
                # Chercher les fenêtres Wakfu (généralement contiennent "Wakfu" dans le titre)
                if "wakfu" in window_text.lower() or "wakfu" in class_name.lower():
                    rect = win32gui.GetWindowRect(hwnd)
                    width = rect[2] - rect[0]
                    height = rect[3] - rect[1]
                    
                    window_info = {
                        "hwnd": hwnd,
                        "title": window_text,
                        "class": class_name,
                        "width": width,
                        "height": height
                    }
                    windows.append(window_info)
                    self.window_handles[hwnd] = window_info
        
        win32gui.EnumWindows(enum_handler, None)
        return windows
    
    def refresh_windows(self):
        """Rafraîchit la liste des fenêtres Wakfu"""
        self.window_handles = {}
        windows = self.get_wakfu_windows()
        
        # Mettre à jour les listes déroulantes
        for class_name in ["iop", "cra"]:
            combo = getattr(self, f"{class_name}_combo", None)
            if combo:
                combo['values'] = [f"{w['title']} ({w['width']}x{w['height']})" for w in windows]
                if len(windows) == 0:
                    combo.set("Aucune fenêtre Wakfu détectée")
                else:
                    combo.set("Sélectionner une fenêtre...")
        
        return len(windows) > 0
    
    def select_window(self, class_name):
        """Sélectionne une fenêtre pour une classe"""
        combo = getattr(self, f"{class_name}_combo", None)
        if not combo:
            return
        
        selection = combo.get()
        if not selection or selection == "Aucune fenêtre Wakfu détectée" or selection == "Sélectionner une fenêtre...":
            self.selected_windows[class_name] = None
            return
        
        # Trouver la fenêtre correspondante
        for hwnd, window_info in self.window_handles.items():
            window_str = f"{window_info['title']} ({window_info['width']}x{window_info['height']})"
            if window_str == selection:
                self.selected_windows[class_name] = hwnd
                # Fenêtre sélectionnée
                return
        
        self.selected_windows[class_name] = None
    
    def clear_selection(self, class_name):
        """Désélectionne une fenêtre pour une classe"""
        combo = getattr(self, f"{class_name}_combo", None)
        if combo:
            combo.set("Sélectionner une fenêtre...")
        self.selected_windows[class_name] = None
        # Sélection effacée
    
    def load_version(self):
        """Charge le numéro de version depuis le fichier VERSION"""
        try:
            version_file = Path("VERSION")
            if version_file.exists():
                return version_file.read_text(encoding='utf-8').strip()
        except:
            pass
        return "1.0.0"  # Version par défaut
    
    def create_ui(self):
        """Crée l'interface utilisateur"""
        # Titre
        title_label = tk.Label(
            self.root,
            text=f"Sélectionnez les fenêtres Wakfu pour chaque classe",
            font=('Arial', 12, 'bold'),
            pady=10
        )
        title_label.pack()
        
        # Version
        version_label = tk.Label(
            self.root,
            text=f"Version {self.version}",
            font=('Arial', 8),
            fg='gray',
            pady=2
        )
        version_label.pack()
        
        # Instructions
        instructions = tk.Label(
            self.root,
            text="Sélectionnez la fenêtre Wakfu correspondant à chaque classe (optionnel).\n"
                 "L'overlay s'affichera uniquement lorsque la fenêtre sélectionnée est active.\n"
                 "Vous pouvez sélectionner seulement Iop, seulement Cra, les deux, ou aucun.",
            font=('Arial', 9),
            fg='gray',
            pady=5,
            justify='left'
        )
        instructions.pack()
        
        # Frame pour les sélections
        selection_frame = tk.Frame(self.root, pady=20)
        selection_frame.pack(fill=tk.BOTH, expand=True, padx=20)
        
        # Sélection pour Iop
        iop_frame = tk.Frame(selection_frame)
        iop_frame.pack(fill=tk.X, pady=10)
        
        iop_label = tk.Label(iop_frame, text="Fenêtre Iop:", font=('Arial', 10, 'bold'), width=15, anchor='w')
        iop_label.pack(side=tk.LEFT, padx=5)
        
        self.iop_combo = ttk.Combobox(iop_frame, state="readonly", width=50)
        self.iop_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.iop_combo.bind('<<ComboboxSelected>>', lambda e: self.select_window("iop"))
        
        # Sélection pour Cra
        cra_frame = tk.Frame(selection_frame)
        cra_frame.pack(fill=tk.X, pady=10)
        
        cra_label = tk.Label(cra_frame, text="Fenêtre Cra:", font=('Arial', 10, 'bold'), width=15, anchor='w')
        cra_label.pack(side=tk.LEFT, padx=5)
        
        self.cra_combo = ttk.Combobox(cra_frame, state="readonly", width=50)
        self.cra_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.cra_combo.bind('<<ComboboxSelected>>', lambda e: self.select_window("cra"))
        
        # Bouton pour désélectionner Cra
        cra_clear_btn = tk.Button(cra_frame, text="✕", command=lambda: self.clear_selection("cra"), 
                                  font=('Arial', 8), width=2, height=1)
        cra_clear_btn.pack(side=tk.LEFT, padx=2)
        
        # Bouton de rafraîchissement
        refresh_btn = tk.Button(
            self.root,
            text="🔄 Rafraîchir la liste",
            command=self.refresh_windows,
            font=('Arial', 9),
            pady=5
        )
        refresh_btn.pack(pady=10)
        
        # Boutons
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=20)
        
        ok_btn = tk.Button(
            button_frame,
            text="Valider",
            command=self.validate,
            font=('Arial', 10, 'bold'),
            bg='#4CAF50',
            fg='white',
            width=15,
            height=2
        )
        ok_btn.pack(side=tk.LEFT, padx=10)
        
        # Bouton Mettre à jour
        self.update_button = tk.Button(
            button_frame,
            text="Mettre à jour",
            command=self.handle_update,
            font=('Arial', 10),
            width=15,
            height=2,
            state=tk.DISABLED,
            bg='#808080',  # Gris par défaut
            fg='white'
        )
        self.update_button.pack(side=tk.LEFT, padx=10)
        
        skip_btn = tk.Button(
            button_frame,
            text="Ignorer",
            command=self.skip,
            font=('Arial', 10),
            width=15,
            height=2
        )
        skip_btn.pack(side=tk.LEFT, padx=10)
        
        # Vérifier les mises à jour en arrière-plan
        self.check_for_updates()
        
        # Rafraîchir la liste au démarrage
        self.refresh_windows()
    
    def validate(self):
        """Valide les sélections et sauvegarde"""
        # WindowSelector.validate() appelé
        # Sélectionner les fenêtres choisies (peut être None si non sélectionné)
        # Sélection des fenêtres
        self.select_window("iop")
        self.select_window("cra")
        # Fenêtres sélectionnées
        
        # Sauvegarder dans la config
        # Chargement de la config
        config = {}
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        
        # Sauvegarder les handles de fenêtres (même si None, pour indiquer qu'on a fait une sélection)
        window_config = {}
        for class_name in ["iop", "cra"]:
            hwnd = self.selected_windows.get(class_name)
            if hwnd:
                window_info = self.window_handles.get(hwnd)
                if window_info:
                    window_config[class_name] = {
                        "hwnd": hwnd,
                        "title": window_info['title']
                    }
            # Si hwnd est None, on ne l'ajoute pas (pas de fenêtre associée)
        
        config["window_mapping"] = window_config
        
            # Sauvegarde de la config
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        info(f"✓ Configuration sauvegardée: {window_config}")
        # Marquer que la sélection est terminée
        self.selection_done = True
        # Fermer la fenêtre
        # Destruction de la fenêtre
        try:
            # Juste détruire la fenêtre
            # check_window() dans main.py détectera la fermeture et quittera le mainloop
            # Appel de self.root.destroy()
            self.root.destroy()
            # self.root.destroy() terminé
        except Exception as e:
            error(f"Erreur lors de la fermeture: {e}")
            import traceback
            traceback.print_exc()
            try:
                self.root.destroy()
            except:
                pass
        # WindowSelector.validate() terminé
    
    def check_for_updates(self):
        """Vérifie s'il y a des mises à jour disponibles en arrière-plan"""
        def check_thread():
            try:
                has_update, error_msg = check_update_available()
                if has_update:
                    self.update_available = True
                    # Activer le bouton et démarrer le clignotement
                    self.root.after(0, self.enable_update_button)
                else:
                    self.update_available = False
                    # Désactiver le bouton
                    self.root.after(0, self.disable_update_button)
            except Exception as e:
                error(f"Erreur lors de la vérification des mises à jour: {e}")
                self.root.after(0, self.disable_update_button)
        
        # Lancer la vérification dans un thread séparé
        thread = threading.Thread(target=check_thread, daemon=True)
        thread.start()
    
    def enable_update_button(self):
        """Active le bouton de mise à jour et démarre le clignotement"""
        if self.update_button:
            self.update_button.config(state=tk.NORMAL, bg='#ff0000', fg='white')
            self.start_update_blink()
    
    def disable_update_button(self):
        """Désactive le bouton de mise à jour"""
        if self.update_button:
            self.stop_update_blink()
            self.update_button.config(state=tk.DISABLED, bg='#808080', fg='white')
    
    def start_update_blink(self):
        """Démarre l'animation de clignotement du bouton"""
        if self.update_blink_job:
            return  # Déjà en cours
        
        def blink():
            if not self.update_available or not self.update_button:
                self.stop_update_blink()
                return
            
            self.update_blink_state = not self.update_blink_state
            if self.update_blink_state:
                self.update_button.config(bg='#ff0000')  # Rouge
            else:
                self.update_button.config(bg='#cc0000')  # Rouge foncé
            
            self.update_blink_job = self.root.after(500, blink)
        
        blink()
    
    def stop_update_blink(self):
        """Arrête l'animation de clignotement"""
        if self.update_blink_job:
            self.root.after_cancel(self.update_blink_job)
            self.update_blink_job = None
        self.update_blink_state = False
    
    def handle_update(self):
        """Gère le clic sur le bouton de mise à jour"""
        if not self.update_available:
            return
        
        # Demander confirmation
        response = messagebox.askyesno(
            "Mise à jour disponible",
            "Une mise à jour est disponible.\n\n"
            "Voulez-vous mettre à jour maintenant ?\n\n"
            "Note: Le chemin des logs sera préservé.",
            icon='question'
        )
        
        if not response:
            return
        
        # Désactiver le bouton pendant la mise à jour
        self.update_button.config(state=tk.DISABLED, text="Mise à jour...")
        self.stop_update_blink()
        
        def update_thread():
            try:
                success, message = perform_update(preserve_config=True)
                if success:
                    self.root.after(0, lambda: messagebox.showinfo(
                        "Mise à jour réussie",
                        "La mise à jour a été effectuée avec succès !\n\n"
                        "Le programme va se redémarrer.",
                        icon='info'
                    ))
                    # Redémarrer le programme
                    self.root.after(1000, self.restart_program)
                else:
                    self.root.after(0, lambda: messagebox.showerror(
                        "Erreur de mise à jour",
                        f"Erreur lors de la mise à jour:\n{message}",
                        icon='error'
                    ))
                    # Réactiver le bouton
                    self.root.after(0, self.enable_update_button)
            except Exception as e:
                error(f"Erreur lors de la mise à jour: {e}")
                self.root.after(0, lambda: messagebox.showerror(
                    "Erreur",
                    f"Erreur inattendue: {e}",
                    icon='error'
                ))
                self.root.after(0, self.enable_update_button)
        
        thread = threading.Thread(target=update_thread, daemon=True)
        thread.start()
    
    def restart_program(self):
        """Redémarre le programme après une mise à jour"""
        import sys
        import subprocess
        python = sys.executable
        script = os.path.abspath("main.py")
        subprocess.Popen([python, script])
        self.root.quit()
        sys.exit(0)
    
    def skip(self):
        """Ignore la sélection (ne change pas la config)"""
        # WindowSelector.skip() appelé
        self.selected_windows = {"iop": None, "cra": None}
        self.selection_done = True
        # Arrêter le clignotement si actif
        self.stop_update_blink()
        # Fermer la fenêtre
        # Destruction de la fenêtre
        try:
            # Juste détruire la fenêtre
            # check_window() dans main.py détectera la fermeture et quittera le mainloop
            # Appel de self.root.destroy()
            self.root.destroy()
            # self.root.destroy() terminé
        except Exception as e:
            error(f"Erreur lors de la fermeture: {e}")
            import traceback
            traceback.print_exc()
            try:
                self.root.destroy()
            except:
                pass
        # WindowSelector.skip() terminé
    
    def run(self):
        """Lance la fenêtre de sélection (ne fait rien si c'est une Toplevel, le parent gère mainloop)"""
        self.selection_done = False
        # Si c'est une Toplevel, le parent (temp_root) gérera mainloop()
        # Si c'est un Tk(), utiliser mainloop()
        if not isinstance(self.root, tk.Toplevel):
            try:
                self.root.mainloop()
            except Exception as e:
                print(f"Erreur dans run(): {e}")
                import traceback
                traceback.print_exc()
        return self.selected_windows


def get_active_window():
    """Retourne le handle de la fenêtre active"""
    if not WIN32_AVAILABLE:
        return None
    try:
        return win32gui.GetForegroundWindow()
    except:
        return None


def is_window_active(hwnd):
    """Vérifie si une fenêtre est active (a le focus)"""
    if not WIN32_AVAILABLE or hwnd is None:
        return False
    try:
        active_hwnd = win32gui.GetForegroundWindow()
        return active_hwnd == hwnd
    except:
        return False


def is_window_valid(hwnd):
    """Vérifie si un handle de fenêtre est toujours valide"""
    if not WIN32_AVAILABLE or hwnd is None:
        return False
    try:
        return win32gui.IsWindow(hwnd) and win32gui.IsWindowVisible(hwnd)
    except:
        return False

