"""
Module pour sélectionner le fichier log de Wakfu
"""
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import json
from log_parser import WakfuLogParser


class LogSelector:
    """Fenêtre pour sélectionner le fichier log"""
    
    def __init__(self, config_path="config.json"):
        """Initialise le sélecteur de log"""
        self.config_path = config_path
        self.selected_path = None
        self.root = tk.Tk()
        self.root.title("WakSOS - Sélection du fichier log")
        self.root.geometry("600x300")
        self.root.resizable(False, False)
        
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
    
    def create_ui(self):
        """Crée l'interface utilisateur"""
        # Frame principal
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Titre
        title_label = tk.Label(
            main_frame,
            text="Sélectionnez le fichier log de Wakfu",
            font=('Arial', 14, 'bold')
        )
        title_label.pack(pady=(0, 20))
        
        # Chemin actuel
        current_path_frame = tk.Frame(main_frame)
        current_path_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(
            current_path_frame,
            text="Fichier log actuel:",
            font=('Arial', 10)
        ).pack(anchor='w')
        
        self.path_label = tk.Label(
            current_path_frame,
            text="Aucun fichier sélectionné",
            font=('Arial', 9),
            fg='gray',
            wraplength=550,
            justify='left'
        )
        self.path_label.pack(anchor='w', pady=(5, 0))
        
        # Charger le chemin depuis la config
        self.load_current_path()
        
        # Boutons
        button_frame = tk.Frame(main_frame)
        button_frame.pack(pady=20)
        
        browse_btn = tk.Button(
            button_frame,
            text="Parcourir...",
            font=('Arial', 11),
            width=15,
            height=2,
            command=self.browse_file,
            bg='#4CAF50',
            fg='white',
            cursor='hand2'
        )
        browse_btn.pack(side=tk.LEFT, padx=5)
        
        auto_detect_btn = tk.Button(
            button_frame,
            text="Détection auto",
            font=('Arial', 11),
            width=15,
            height=2,
            command=self.auto_detect,
            bg='#2196F3',
            fg='white',
            cursor='hand2'
        )
        auto_detect_btn.pack(side=tk.LEFT, padx=5)
        
        # Boutons de validation
        validation_frame = tk.Frame(main_frame)
        validation_frame.pack(pady=20)
        
        cancel_btn = tk.Button(
            validation_frame,
            text="Annuler",
            font=('Arial', 10),
            width=12,
            command=self.cancel,
            bg='#f44336',
            fg='white',
            cursor='hand2'
        )
        cancel_btn.pack(side=tk.LEFT, padx=5)
        
        ok_btn = tk.Button(
            validation_frame,
            text="Valider",
            font=('Arial', 10),
            width=12,
            command=self.validate,
            bg='#4CAF50',
            fg='white',
            cursor='hand2'
        )
        ok_btn.pack(side=tk.LEFT, padx=5)
        
        # Instructions
        instructions = tk.Label(
            main_frame,
            text="Le fichier log se trouve généralement dans:\n"
                 "AppData\\Local\\Ankama\\Wakfu\\logs\\wakfu.log",
            font=('Arial', 9),
            fg='gray',
            justify='left'
        )
        instructions.pack(pady=(10, 0))
    
    def load_current_path(self):
        """Charge le chemin actuel depuis la config"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    log_path = config.get("log_path")
                    if log_path and os.path.exists(log_path):
                        self.selected_path = log_path
                        self.path_label.config(
                            text=log_path,
                            fg='green'
                        )
                        return
        except Exception:
            pass
        
        # Essayer la détection automatique
        parser = WakfuLogParser()
        if os.path.exists(parser.log_path):
            self.selected_path = parser.log_path
            self.path_label.config(
                text=parser.log_path,
                fg='blue'
            )
    
    def browse_file(self):
        """Ouvre le dialogue de sélection de fichier"""
        initial_dir = os.path.expanduser("~")
        
        # Essayer de trouver le dossier Wakfu par défaut
        possible_dirs = [
            os.path.expanduser(r"~\AppData\Local\Ankama\Wakfu\logs"),
            os.path.expanduser(r"~\Documents\Wakfu\logs"),
            os.path.expanduser("~")
        ]
        
        for dir_path in possible_dirs:
            if os.path.exists(dir_path):
                initial_dir = dir_path
                break
        
        file_path = filedialog.askopenfilename(
            title="Sélectionner le fichier log de Wakfu",
            initialdir=initial_dir,
            filetypes=[
                ("Fichiers log", "*.log"),
                ("Tous les fichiers", "*.*")
            ]
        )
        
        if file_path:
            if os.path.exists(file_path):
                self.selected_path = file_path
                self.path_label.config(
                    text=file_path,
                    fg='green'
                )
            else:
                messagebox.showerror(
                    "Erreur",
                    "Le fichier sélectionné n'existe pas."
                )
    
    def auto_detect(self):
        """Détecte automatiquement le fichier log"""
        parser = WakfuLogParser()
        
        if os.path.exists(parser.log_path):
            self.selected_path = parser.log_path
            self.path_label.config(
                text=f"✓ Détecté: {parser.log_path}",
                fg='blue'
            )
            messagebox.showinfo(
                "Détection réussie",
                f"Fichier log trouvé:\n{parser.log_path}"
            )
        else:
            messagebox.showwarning(
                "Fichier non trouvé",
                "Impossible de trouver automatiquement le fichier log.\n"
                "Veuillez le sélectionner manuellement."
            )
    
    def validate(self):
        """Valide la sélection et sauvegarde"""
        if not self.selected_path:
            messagebox.showwarning(
                "Aucun fichier sélectionné",
                "Veuillez sélectionner un fichier log avant de continuer."
            )
            return
        
        if not os.path.exists(self.selected_path):
            messagebox.showerror(
                "Fichier introuvable",
                "Le fichier sélectionné n'existe pas."
            )
            return
        
        # Sauvegarder dans la config
        try:
            config = {}
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            config["log_path"] = self.selected_path
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            self.root.quit()
        except Exception as e:
            messagebox.showerror(
                "Erreur",
                f"Impossible de sauvegarder la configuration:\n{e}"
            )
    
    def cancel(self):
        """Annule la sélection"""
        # Toujours fermer, même sans sélection
        # L'application utilisera la détection automatique
        self.root.quit()
    
    def get_selected_path(self):
        """Retourne le chemin sélectionné"""
        return self.selected_path
    
    def run(self):
        """Lance la fenêtre de sélection"""
        self.root.mainloop()
        self.root.destroy()
        return self.selected_path

