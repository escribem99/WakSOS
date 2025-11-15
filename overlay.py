"""
Module pour créer et gérer l'overlay transparent
"""
import tkinter as tk
from tkinter import PhotoImage
import json
import os
import time
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    # PIL/Pillow non disponible, redimensionnement des images limité


class ComboOverlay:
    def __init__(self, class_name, config_path="config.json", reset_callback=None):
        """
        Initialise l'overlay avec la configuration
        
        Args:
            class_name: Nom de la classe ('iop' ou 'cra')
            config_path: Chemin vers le fichier de configuration
            reset_callback: Fonction à appeler pour réinitialiser les états
        """
        self.class_name = class_name
        self.config = self.load_config(config_path)
        self.reset_callback = reset_callback
        self.root = None
        # Pour le clignotement de la barre de Préparation
        self.preparation_blink_state = False
        self.preparation_blink_job = None
        self.state_labels = {}
        self.precision_icon_label = None  # Label pour l'icône de Précision
        self.precision_icon = None  # Image de l'icône
        self.pointe_affutee_icon_label = None  # Label pour l'icône Pointe affûtée
        self.pointe_affutee_icon = None  # Image de l'icône Pointe affûtée
        self.pointe_affutee_active = False  # État de la Pointe affûtée
        self.balise_affutee_icon = None  # Image de la balise affûtée
        self.balise_affutee_frame = None  # Frame contenant l'image et le compteur
        self.balise_affutee_label = None  # Label pour l'image de la balise
        self.balise_affutee_counter_label = None  # Label pour le compteur (texte sur l'image)
        self.balise_affutee_value = 0  # Valeur actuelle de la balise affûtée
        self._icon_refs = []  # Références aux images pour éviter le garbage collection
        self.is_visible = True  # État de visibilité de l'overlay
        self.last_click_time = 0  # Timestamp du dernier clic sur l'overlay
        self.wakfu_window_hwnd = None  # HWND de la fenêtre Wakfu associée (pour remettre le focus)
        
        # Pour l'Iop : structure pour les combos
        if self.class_name == "iop":
            self.combo_tracker = None  # Sera initialisé depuis l'extérieur
            self.combo_frames = {}  # {combo_id: frame}
            self.combo_icons = {}  # {combo_id: icon_image}
            self.combo_step_labels = {}  # {combo_id: [label1, label2, ...]} pour chaque étape
            self.resource_icons = {}  # {PA: icon, PM: icon, PW: icon}
            self.active_combo_id = None
            self.used_sorts = []  # Liste des sorts utilisés dans le combo actif
        
        self.create_overlay()
    
    def load_config(self, config_path):
        """Charge la configuration depuis le fichier JSON"""
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return self.get_default_config()
    
    def get_default_config(self):
        """Retourne la configuration par défaut"""
        return {
            "overlay": {
                "position": {"x": 100, "y": 100},
                "transparency": 0.85,
                "always_on_top": True
            }
        }
    
    def create_overlay(self):
        """Crée la fenêtre overlay transparente"""
        self.root = tk.Tk()
        self.root.title(f"WakSOS - {self.class_name.upper()}")
        
        # Supprimer la barre de titre (nom de fenêtre et boutons)
        self.root.overrideredirect(True)
        
        # Configuration de la transparence
        alpha = self.config.get("overlay", {}).get("transparency", 0.85)
        self.root.attributes('-alpha', alpha)
        self.root.attributes('-topmost', self.config.get("overlay", {}).get("always_on_top", True))
        
        # Fond transparent - utiliser une couleur spécifique pour la transparence
        # Utiliser une couleur très rare (presque noire mais différente) pour la transparence
        transparent_color = '#000001'  # Presque noir mais pas exactement noir - sera transparent
        self.root.configure(bg=transparent_color)
        self.root.attributes('-transparentcolor', transparent_color)
        
        # Stocker la couleur transparente pour l'utiliser partout
        self.transparent_color = transparent_color
        
        # Position initiale selon la classe
        overlay_positions = self.config.get("overlay", {}).get("positions", {})
        class_pos = overlay_positions.get(self.class_name, {})
        
        # Valeurs par défaut si pas de position spécifique
        if not class_pos:
            # Position par défaut : Iop à gauche, Cra à droite
            if self.class_name == "iop":
                x, y = 100, 100
            else:  # cra
                x, y = 400, 100
        else:
            x = class_pos.get("x", 100)
            y = class_pos.get("y", 100)
        
        self.root.geometry(f"280x180+{x}+{y}")
        
        # Frame principal avec fond transparent
        main_frame = tk.Frame(self.root, bg=self.transparent_color)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Frame pour l'icône de déplacement (zone cliquable très grande)
        drag_frame = tk.Frame(main_frame, bg=self.transparent_color, width=280, height=40)
        drag_frame.pack(pady=5, fill=tk.X)
        drag_frame.pack_propagate(False)  # Empêcher le frame de rétrécir
        
        # Icône de déplacement (remplace le label "Classe")
        self.drag_handle = tk.Label(
            drag_frame,
            text="☰",  # Symbole hamburger pour indiquer le déplacement
            font=('Arial', 18),
            fg='#666666',
            bg=self.transparent_color,
            cursor='hand2'
        )
        self.drag_handle.pack(expand=True)
        
        # Permettre le déplacement via le frame entier (zone très grande)
        drag_frame.bind('<Button-1>', self.start_move)
        drag_frame.bind('<B1-Motion>', self.on_move)
        self.drag_handle.bind('<Button-1>', self.start_move)
        self.drag_handle.bind('<B1-Motion>', self.on_move)
        
        # Frame pour les états - avec fond transparent
        self.states_frame = tk.Frame(main_frame, bg=self.transparent_color)
        self.states_frame.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        
        # Frame séparé pour les icônes (en bas, après les états) - avec fond transparent
        self.icons_frame = tk.Frame(main_frame, bg=self.transparent_color)
        self.icons_frame.pack(pady=5, fill=tk.X)
        
        # Initialiser les labels d'états (seront créés dynamiquement)
        self.state_labels = {}
        
        # Sauvegarder la référence à main_frame pour l'icône
        self.main_frame = main_frame
        
        # Pour l'Iop : créer l'affichage des combos
        if self.class_name == "iop":
            # Ajuster la taille de la fenêtre pour les combos (plus large pour 5 colonnes)
            # Largeur divisée par deux : 700px -> 350px
            self.root.geometry(f"350x500+{x}+{y}")
            # Créer un frame pour le dernier sort utilisé (entre les états et les combos)
            self.last_sort_frame = tk.Frame(main_frame, bg=self.transparent_color)
            self.last_sort_frame.pack(pady=2, fill=tk.X)
            self.last_sort_label = None
            self.last_sort_text_label = None  # Label pour le texte "Dernier sort : "
            self.last_sort_name = None
            # Créer le frame pour les combos
            self.combos_frame = tk.Frame(main_frame, bg=self.transparent_color)
            self.combos_frame.pack(pady=5, fill=tk.BOTH, expand=True)
            # Ne pas charger les combos ici - sera fait après l'assignation du combo_tracker dans main.py
        else:
            # Charger les icônes après la création complète de la fenêtre
            # (nécessaire pour que PhotoImage fonctionne correctement)
            # Charger les icônes immédiatement (pas de délai pour éviter les problèmes)
            self.load_icons()
        
        # Permettre aussi le déplacement via tous les widgets enfants
        def bind_drag_to_widget(widget):
            """Lie les événements de déplacement à un widget"""
            widget.bind('<Button-1>', self.start_move)
            widget.bind('<B1-Motion>', self.on_move)
        
        # Lier le déplacement aux frames principaux (mais PAS à main_frame car les boutons sont dedans)
        # Ne lier qu'aux frames enfants spécifiques pour éviter les conflits avec les boutons
        bind_drag_to_widget(self.states_frame)
        bind_drag_to_widget(self.icons_frame)
        bind_drag_to_widget(drag_frame)
        
        # Bouton pour réinitialiser (bouton Reset)
        def reset_with_focus():
            """Réinitialise les états et garde le focus sur l'overlay"""
            import time
            self.last_click_time = time.time()
            self.root.lift()  # Remettre l'overlay au premier plan
            self.root.attributes('-topmost', True)  # S'assurer qu'il reste au premier plan
            self.reset_states()
            # Pour l'overlay Iop, remettre le focus sur la fenêtre Wakfu après le clic
            if self.class_name == "iop" and self.wakfu_window_hwnd is not None:
                try:
                    import win32gui
                    import win32con
                    # Remettre le focus sur la fenêtre Wakfu
                    win32gui.SetForegroundWindow(self.wakfu_window_hwnd)
                except:
                    pass  # Ignorer les erreurs
        
        reset_btn = tk.Button(
            main_frame,
            text="Reset",
            font=('Arial', 9),
            fg='white',
            bg='#ff8800',
            activebackground='#ffaa00',
            activeforeground='white',
            command=reset_with_focus,
            width=5,
            height=1,
            cursor='hand2',
            relief='flat',
            bd=0
        )
        reset_btn.place(x=5, y=5)
        # Mettre à jour last_click_time aussi sur le clic du bouton
        reset_btn.bind('<Button-1>', lambda e: setattr(self, 'last_click_time', time.time()))
        # Les boutons ne sont pas liés au déplacement grâce à la vérification dans start_move
        
        # Bouton pour fermer (petit X en haut à droite)
        # Ajuster la position X selon la taille de la fenêtre
        if self.class_name == "iop":
            close_x = 330  # Pour la fenêtre Iop (350px de large, bouton à droite, laisser de la marge)
        else:
            close_x = 250  # Pour la fenêtre Cra
        
        def close_with_focus():
            """Ferme l'overlay et garde le focus"""
            import time
            self.last_click_time = time.time()
            # Pour l'overlay Iop, remettre le focus sur la fenêtre Wakfu avant de fermer
            if self.class_name == "iop" and self.wakfu_window_hwnd is not None:
                try:
                    import win32gui
                    import win32con
                    # Remettre le focus sur la fenêtre Wakfu
                    win32gui.SetForegroundWindow(self.wakfu_window_hwnd)
                except:
                    pass  # Ignorer les erreurs
            self.close_overlay()
        
        close_btn = tk.Button(
            main_frame,
            text="×",
            font=('Arial', 12),
            fg='white',
            bg='#ff0000',
            activebackground='#ff3333',
            activeforeground='white',
            command=close_with_focus,
            width=2,
            height=1,
            cursor='hand2',
            relief='flat',
            bd=0
        )
        close_btn.place(x=close_x, y=5)
        # Mettre à jour last_click_time aussi sur le clic du bouton
        close_btn.bind('<Button-1>', lambda e: setattr(self, 'last_click_time', time.time()))
        # Les boutons ne sont pas liés au déplacement grâce à la vérification dans start_move
        
        # S'assurer que l'overlay garde le focus quand on clique dessus
        def on_click(event):
            """Garde le focus sur l'overlay quand on clique dessus"""
            import time
            self.last_click_time = time.time()
            self.root.lift()
            self.root.attributes('-topmost', True)
            # Pour l'overlay Iop, remettre le focus sur la fenêtre Wakfu après le clic
            if self.class_name == "iop" and self.wakfu_window_hwnd is not None:
                try:
                    import win32gui
                    import win32con
                    # Remettre le focus sur la fenêtre Wakfu
                    win32gui.SetForegroundWindow(self.wakfu_window_hwnd)
                except:
                    pass  # Ignorer les erreurs
        
        # Lier les clics sur main_frame ET tous les frames enfants pour garder le focus
        main_frame.bind('<Button-1>', on_click, add='+')
        if hasattr(self, 'states_frame') and self.states_frame:
            self.states_frame.bind('<Button-1>', on_click, add='+')
        if hasattr(self, 'icons_frame') and self.icons_frame:
            self.icons_frame.bind('<Button-1>', on_click, add='+')
        if hasattr(self, 'combos_frame') and self.combos_frame:
            self.combos_frame.bind('<Button-1>', on_click, add='+')
        
        # S'assurer que la fenêtre est visible dès sa création
        # (nécessaire car overrideredirect peut parfois cacher la fenêtre)
        self.root.update()
        self.root.deiconify()
        self.root.lift()
        self.root.attributes('-topmost', True)
        # Fenêtre créée et rendue visible
    
    def load_icons(self):
        """Charge toutes les icônes après l'initialisation complète de la fenêtre"""
        try:
            # S'assurer que la fenêtre root existe
            if not self.root or not self.root.winfo_exists():
                # Fenêtre root non disponible pour charger les icônes
                return
            
            # Vérifier que icons_frame existe
            if not hasattr(self, 'icons_frame') or self.icons_frame is None:
                # icons_frame n'existe pas encore lors du chargement des icônes
                return
            
            
            # Initialiser la liste de références pour éviter le garbage collection
            if not hasattr(self, '_icon_refs'):
                self._icon_refs = []
            
            # Charger l'icône de Précision
            icon_path = os.path.join("assets", "precision_icon.png")
            if os.path.exists(icon_path):
                try:
                    # Vérifier que le fichier n'est pas vide
                    if os.path.getsize(icon_path) > 0:
                        # Créer l'image dans le contexte de la fenêtre root
                        self.precision_icon = PhotoImage(master=self.root, file=icon_path)
                        # Garder une référence pour éviter le garbage collection
                        self._icon_refs.append(self.precision_icon)
                        # Icône Précision chargée
                    else:
                        # Fichier icône Précision vide
                        self.precision_icon = None
                except tk.TclError as e:
                    # Erreur TclError lors du chargement de l'icône Précision
                    self.precision_icon = None
                except Exception as e:
                    # Erreur lors du chargement de l'icône Précision
                    self.precision_icon = None
            else:
                self.precision_icon = None
            
            # Charger l'icône de Pointe affûtée
            icon_path = os.path.join("assets", "pointe_affutee_icon.png")
            if os.path.exists(icon_path):
                try:
                    # Vérifier que le fichier n'est pas vide
                    file_size = os.path.getsize(icon_path)
                    if file_size > 0:
                        # Créer l'image dans le contexte de la fenêtre root
                        self.pointe_affutee_icon = PhotoImage(master=self.root, file=icon_path)
                        # Garder une référence pour éviter le garbage collection
                        self._icon_refs.append(self.pointe_affutee_icon)
                        # Icône Pointe affûtée chargée
                    else:
                        # Fichier icône Pointe affûtée vide
                        self.pointe_affutee_icon = None
                except tk.TclError as e:
                    # Erreur TclError lors du chargement de l'icône Pointe affûtée
                    self.pointe_affutee_icon = None
                except Exception as e:
                    # Erreur lors du chargement de l'icône Pointe affûtée
                    import traceback
                    traceback.print_exc()
                    self.pointe_affutee_icon = None
            else:
                # Fichier icône Pointe affûtée introuvable
                self.pointe_affutee_icon = None
            
            # Charger l'icône de Balise affûtée
            icon_path = os.path.join("assets", "balise_affutee.png")
            if os.path.exists(icon_path):
                try:
                    file_size = os.path.getsize(icon_path)
                    if file_size > 0:
                        self.balise_affutee_icon = PhotoImage(master=self.root, file=icon_path)
                        self._icon_refs.append(self.balise_affutee_icon)
                        # Icône Balise affûtée chargée
                    else:
                        # Fichier icône Balise affûtée vide
                        self.balise_affutee_icon = None
                except tk.TclError as e:
                    # Erreur TclError lors du chargement de l'icône Balise affûtée
                    self.balise_affutee_icon = None
                except Exception as e:
                    # Erreur lors du chargement de l'icône Balise affûtée
                    self.balise_affutee_icon = None
            else:
                # Fichier icône Balise affûtée introuvable
                self.balise_affutee_icon = None
        except Exception as e:
            # Erreur lors du chargement des icônes
            import traceback
            traceback.print_exc()
    
    def create_progress_bar(self, state_name: str, value: int, color: str):
        """
        Crée une barre de progression personnalisée pour un état
        
        Args:
            state_name: Nom de l'état
            value: Valeur actuelle
            color: Couleur de la barre
            
        Returns:
            Frame contenant la barre de progression
        """
        # Frame pour contenir la barre et le label - avec fond transparent
        progress_frame = tk.Frame(self.states_frame, bg=self.transparent_color)
        
        # Permettre le déplacement via la barre de progression
        progress_frame.bind('<Button-1>', self.start_move)
        progress_frame.bind('<B1-Motion>', self.on_move)
        
        # Label avec le nom de l'état - avec fond transparent et largeur fixe pour alignement
        # Utiliser une largeur fixe pour éviter les décalages
        name_label = tk.Label(
            progress_frame,
            text=state_name,
            font=('Arial', 10, 'bold'),
            fg=color,
            bg=self.transparent_color,
            anchor='w',
            width=12  # Largeur fixe pour aligner toutes les barres
        )
        name_label.pack(side=tk.LEFT, padx=(0, 5))
        # Permettre le déplacement via le label
        name_label.bind('<Button-1>', self.start_move)
        name_label.bind('<B1-Motion>', self.on_move)
        
        # Canvas pour la barre de progression
        bar_width = 180
        bar_height = 20
        # Pour la Préparation, utiliser une bordure plus épaisse pour le clignotement
        # Sinon, bordure normale
        if state_name == "Préparation":
            highlight_thickness = 2
        else:
            highlight_thickness = 1
        
        canvas = tk.Canvas(
            progress_frame,
            width=bar_width,
            height=bar_height,
            bg='#2a2a2a',
            highlightthickness=highlight_thickness,
            highlightbackground='#444444',
            relief='flat',
            takefocus=0  # Empêcher le canvas de prendre le focus
        )
        # Stocker la référence au canvas pour le clignotement
        canvas.original_highlight = '#444444'
        canvas.pack(side=tk.LEFT, padx=5)
        # Permettre le déplacement via le canvas
        canvas.bind('<Button-1>', self.start_move)
        canvas.bind('<B1-Motion>', self.on_move)
        
        # Calculer le pourcentage avec les valeurs max appropriées
        max_values = {
            "Précision": 250,
            "Affûtage": 200,
            "Concentration": 100,
            "Courroux": 5,
            "Préparation": 40
        }
        max_value = max_values.get(state_name, 100)
        percentage = min(100, (value / max_value) * 100) if max_value > 0 else 0
        fill_width = int((percentage / 100) * bar_width)
        
        # Dessiner la barre de progression
        canvas.create_rectangle(
            0, 0, fill_width, bar_height,
            fill=color,
            outline='',
            tags='progress'
        )
        
        # Afficher la valeur sur la barre de progression (texte centré)
        # Choisir la couleur du texte selon la position (blanc si barre remplie, couleur si vide)
        text_color = '#ffffff' if fill_width > bar_width / 2 else color
        canvas.create_text(
            bar_width / 2, bar_height / 2,
            text=str(value),
            fill=text_color,
            font=('Arial', 10, 'bold'),
            tags='value_text'
        )
        
        # Label pour la valeur à côté (optionnel, pour référence)
        value_label = tk.Label(
            progress_frame,
            text="",  # Vide car la valeur est sur la barre
            font=('Arial', 10, 'bold'),
            fg='#ffffff',
            bg=self.transparent_color,
            width=0
        )
        value_label.pack(side=tk.LEFT, padx=0)
        
        # Stocker les références pour la mise à jour
        progress_frame.canvas = canvas
        progress_frame.value_label = value_label
        progress_frame.name_label = name_label
        progress_frame.max_value = max_value
        progress_frame.state_color = color
        
        return progress_frame
    
    def update_progress_bar(self, state_name: str, value: int, color: str):
        """
        Met à jour une barre de progression existante
        
        Args:
            state_name: Nom de l'état
            value: Nouvelle valeur
            color: Couleur de la barre
        """
        if state_name not in self.state_labels:
            return
        
        progress_frame = self.state_labels[state_name]
        canvas = progress_frame.canvas
        value_label = progress_frame.value_label
        max_value = progress_frame.max_value
        
        # Calculer le pourcentage
        percentage = min(100, (value / max_value) * 100) if max_value > 0 else 0
        bar_width = 180
        fill_width = int((percentage / 100) * bar_width)
        
        # Pour la Préparation, gérer le clignotement si >= 40
        if state_name == "Préparation":
            if value >= 40:
                # Si le clignotement n'est pas déjà actif, le démarrer
                if not self.preparation_blink_job:
                    # Démarrer le clignotement
                    self._start_preparation_blink(canvas, fill_width, color, value)
                else:
                    # Le clignotement est déjà actif, juste mettre à jour les valeurs
                    # On stocke les nouvelles valeurs dans progress_frame pour que le clignotement les utilise
                    progress_frame.current_value = value
                    progress_frame.current_fill_width = fill_width
                    # Ne pas redessiner ici, laisser le clignotement gérer
                    return
            else:
                # Arrêter le clignotement si la valeur est < 40
                if self.preparation_blink_job:
                    try:
                        # Vérifier que la fenêtre existe encore avant d'annuler
                        if self.root.winfo_exists():
                            self.root.after_cancel(self.preparation_blink_job)
                    except:
                        pass  # Fenêtre déjà détruite, ignorer
                    self.preparation_blink_job = None
                    self.preparation_blink_state = False
                    # Remettre la bordure normale
                    try:
                        original_border = getattr(canvas, 'original_highlight', '#444444')
                        canvas.config(highlightbackground=original_border)
                    except:
                        pass
                # Continuer pour redessiner la barre normalement (pas de clignotement)
        
        # Mettre à jour la barre (seulement si pas de clignotement actif)
        canvas.delete('progress')
        canvas.delete('value_text')
        
        canvas.create_rectangle(
            0, 0, fill_width, 20,
            fill=color,
            outline='',
            tags='progress'
        )
        
        # Mettre à jour le texte de la valeur sur la barre
        bar_width = 180
        text_color = '#ffffff' if fill_width > bar_width / 2 else color
        canvas.create_text(
            bar_width / 2, 10,
            text=str(value),
            fill=text_color,
            font=('Arial', 10, 'bold'),
            tags='value_text'
        )
    
    def _start_preparation_blink(self, canvas, fill_width, base_color, value):
        """
        Démarre l'animation de clignotement pour la barre de Préparation
        Fait clignoter les bordures du canvas
        
        Args:
            canvas: Canvas de la barre de progression
            fill_width: Largeur de remplissage
            base_color: Couleur de base
            value: Valeur actuelle
        """
        # Stocker la référence au progress_frame pour récupérer les valeurs actuelles
        progress_frame = None
        for state_name, frame in self.state_labels.items():
            if state_name == "Préparation" and hasattr(frame, 'canvas') and frame.canvas == canvas:
                progress_frame = frame
                break
        
        # Stocker les valeurs dans progress_frame pour que le clignotement puisse les utiliser
        if progress_frame:
            progress_frame.current_value = value
            progress_frame.current_fill_width = fill_width
            progress_frame.base_color = base_color
        
        # Récupérer la couleur de bordure originale
        original_border = getattr(canvas, 'original_highlight', '#444444')
        blink_border = "#ffff00"  # Jaune vif pour le clignotement
        
        def blink():
            # Vérifier que la fenêtre et le canvas existent encore
            try:
                if not self.root.winfo_exists() or not canvas.winfo_exists():
                    self.preparation_blink_job = None
                    return
            except:
                self.preparation_blink_job = None
                return
            
            # Vérifier que la barre existe toujours
            if "Préparation" not in self.state_labels:
                self.preparation_blink_job = None
                # Remettre la bordure normale
                try:
                    if canvas.winfo_exists():
                        canvas.config(highlightbackground=original_border)
                except:
                    pass
                return
            
            current_frame = self.state_labels["Préparation"]
            if not hasattr(current_frame, 'canvas') or current_frame.canvas != canvas:
                self.preparation_blink_job = None
                # Remettre la bordure normale
                try:
                    if canvas.winfo_exists():
                        canvas.config(highlightbackground=original_border)
                except:
                    pass
                return
            
            # Récupérer les valeurs actuelles depuis progress_frame
            if hasattr(current_frame, 'current_value'):
                current_value = current_frame.current_value
            else:
                current_value = value
            
            # Vérifier que la valeur est toujours >= 40
            if current_value < 40:
                self.preparation_blink_job = None
                self.preparation_blink_state = False
                # Remettre la bordure normale
                try:
                    canvas.config(highlightbackground=original_border)
                except:
                    pass
                return
            
            # Alterner l'état du clignotement
            self.preparation_blink_state = not self.preparation_blink_state
            
            # Changer la couleur de la bordure
            try:
                if self.preparation_blink_state:
                    # État clignotant : bordure jaune vif
                    canvas.config(highlightbackground=blink_border)
                else:
                    # État normal : bordure originale
                    canvas.config(highlightbackground=original_border)
            except Exception as e:
                # Ignorer les erreurs si le canvas n'existe plus
                self.preparation_blink_job = None
                return
            
            # Programmer le prochain clignotement (500ms)
            if self.root and self.root.winfo_exists():
                try:
                    self.preparation_blink_job = self.root.after(500, blink)
                except:
                    self.preparation_blink_job = None
            else:
                self.preparation_blink_job = None
        
        # Vérifier que la valeur est bien >= 40 avant de démarrer le clignotement
        if value < 40:
            # Ne pas démarrer le clignotement si la valeur est < 40
            return
        
        # Démarrer le clignotement (commencer avec l'état normal, puis clignoter)
        self.preparation_blink_state = False  # Commencer avec l'état normal
        # S'assurer que la bordure est normale au départ
        try:
            canvas.config(highlightbackground=original_border)
        except:
            pass
        if self.root and self.root.winfo_exists():
            # Programmer le premier clignotement après 500ms
            self.preparation_blink_job = self.root.after(500, blink)
    
    def start_move(self, event):
        """Démarre le déplacement de la fenêtre"""
        # Ignorer si le clic vient d'un bouton ou d'un de ses enfants
        widget = event.widget
        # Vérifier si le widget est un bouton ou un enfant d'un bouton
        while widget:
            if isinstance(widget, tk.Button):
                return  # Ne pas déplacer si on clique sur un bouton
            try:
                widget = widget.master
            except:
                break
        
        # Obtenir la position de la souris par rapport à l'écran
        self.start_x = event.x_root
        self.start_y = event.y_root
        # Obtenir la position actuelle de la fenêtre
        self.window_x = self.root.winfo_x()
        self.window_y = self.root.winfo_y()
    
    def on_move(self, event):
        """Gère le déplacement de la fenêtre"""
        # Calculer le déplacement depuis le point de départ
        deltax = event.x_root - self.start_x
        deltay = event.y_root - self.start_y
        # Nouvelle position de la fenêtre
        new_x = self.window_x + deltax
        new_y = self.window_y + deltay
        self.root.geometry(f"+{new_x}+{new_y}")
    
    def update_states(self, states_dict, class_name=""):
        """
        Met à jour l'affichage des états pour cette classe spécifique
        
        Args:
            states_dict: Dict avec les états {class_name: {state_name: value}}
            class_name: Nom de la classe (ignoré, on utilise self.class_name)
        """
        # Obtenir les états de cette classe spécifique
        if self.class_name in states_dict:
            class_states = states_dict[self.class_name]
        else:
            class_states = {}
        
        # Couleurs pour chaque état (couleurs sobres et ternes)
        state_colors = {
            "Concentration": "#4a9e9e",  # Cyan terne
            "Courroux": "#9e6a4a",  # Orange terne
            "Préparation": "#9e9e4a",  # Jaune terne
            "Affûtage": "#5a8a5a",  # Vert terne
            "Précision": "#7a6a9a"  # Violet terne
        }
        
        # Créer ou mettre à jour les labels d'états
        for i, (state_name, value) in enumerate(class_states.items()):
            # Pour Cra, utiliser des barres de progression pour Affûtage et Précision
            # Pour Iop, utiliser des barres de progression pour Concentration, Courroux et Préparation
            use_progress_bar = False
            if self.class_name == "cra" and state_name in ["Affûtage", "Précision"]:
                use_progress_bar = True
            elif self.class_name == "iop" and state_name in ["Concentration", "Courroux", "Préparation"]:
                use_progress_bar = True
            
            if use_progress_bar:
                if state_name not in self.state_labels:
                    # Créer une barre de progression personnalisée
                    progress_frame = self.create_progress_bar(state_name, value, state_colors.get(state_name, "#ffffff"))
                    progress_frame.pack(pady=5, padx=10, fill=tk.X)
                    self.state_labels[state_name] = progress_frame
                else:
                    # Mettre à jour la barre de progression
                    self.update_progress_bar(state_name, value, state_colors.get(state_name, "#ffffff"))
            else:
                # Pour les autres états, utiliser des labels normaux
                if state_name not in self.state_labels:
                    # Créer un nouveau label
                    label = tk.Label(
                        self.states_frame,
                        text=f"{state_name}: {value}",
                        font=('Arial', 11, 'bold'),
                        fg=state_colors.get(state_name, "#ffffff"),
                        bg=self.transparent_color,
                        anchor='w'
                    )
                    label.pack(pady=2, padx=10, fill=tk.X)
                    # Permettre le déplacement via le label
                    label.bind('<Button-1>', self.start_move)
                    label.bind('<B1-Motion>', self.on_move)
                    self.state_labels[state_name] = label
                else:
                    # Mettre à jour le label existant
                    self.state_labels[state_name].config(
                        text=f"{state_name}: {value}",
                        fg=state_colors.get(state_name, "#ffffff")
                    )
                    # S'assurer que le déplacement est toujours lié
                    if not hasattr(self.state_labels[state_name], '_drag_bound'):
                        self.state_labels[state_name].bind('<Button-1>', self.start_move)
                        self.state_labels[state_name].bind('<B1-Motion>', self.on_move)
                        self.state_labels[state_name]._drag_bound = True
        
        # Gérer l'icône de Précision pour le Cra (afficher si Précision > 200)
        try:
            if self.class_name == "cra" and "Précision" in class_states:
                precision_value = class_states["Précision"]
                if precision_value > 200:
                    # Afficher l'icône
                    if self.precision_icon and self.precision_icon_label is None:
                        # Vérifier que l'image existe toujours
                        try:
                            # Tester si l'image est valide
                            _ = self.precision_icon.width()
                            # Créer le label avec l'icône dans le frame des icônes
                            self.precision_icon_label = tk.Label(
                                self.icons_frame,
                                image=self.precision_icon,
                                bg=self.transparent_color
                            )
                            # Garder une référence à l'image dans le label
                            self.precision_icon_label.image = self.precision_icon
                            self.precision_icon_label.pack(side=tk.LEFT, padx=5)
                            # Icône Précision affichée
                        except (tk.TclError, AttributeError) as e:
                            # Image Précision invalide, rechargement nécessaire
                            self.precision_icon = None
                            self.precision_icon_label = None
                    elif self.precision_icon_label:
                        # Vérifier si le widget existe toujours et n'est pas déjà packé
                        try:
                            if self.precision_icon_label.winfo_exists():
                                if not self.precision_icon_label.winfo_viewable():
                                    self.precision_icon_label.pack(side=tk.LEFT, padx=5)
                            else:
                                # Widget détruit, recréer
                                self.precision_icon_label = None
                        except tk.TclError:
                            # Widget détruit, recréer
                            self.precision_icon_label = None
                else:
                    # Masquer l'icône si Précision <= 200
                    if self.precision_icon_label:
                        try:
                            if self.precision_icon_label.winfo_exists():
                                self.precision_icon_label.pack_forget()
                        except tk.TclError:
                            self.precision_icon_label = None
            else:
                # Masquer l'icône si ce n'est pas le Cra ou si Précision n'est pas dans les états
                if self.precision_icon_label:
                    try:
                        if self.precision_icon_label.winfo_exists():
                            self.precision_icon_label.pack_forget()
                    except tk.TclError:
                        self.precision_icon_label = None
        except Exception as e:
            # Erreur lors de la gestion de l'icône Précision
            import traceback
            traceback.print_exc()
        
        # Gérer l'icône de Balise affûtée pour le Cra (affichée en permanence)
        try:
            if self.class_name == "cra" and self.balise_affutee_icon:
                if self.balise_affutee_frame is None:
                    # Créer un frame pour contenir l'image et le compteur
                    self.balise_affutee_frame = tk.Frame(self.icons_frame, bg=self.transparent_color)
                    # Label pour l'image
                    self.balise_affutee_label = tk.Label(
                        self.balise_affutee_frame,
                        image=self.balise_affutee_icon,
                        bg=self.transparent_color
                    )
                    self.balise_affutee_label.image = self.balise_affutee_icon
                    self.balise_affutee_label.pack()
                    
                    # Label pour le compteur (texte centré sur l'image)
                    self.balise_affutee_counter_label = tk.Label(
                        self.balise_affutee_frame,
                        text=str(self.balise_affutee_value) if self.balise_affutee_value > 0 else "",
                        font=('Arial', 14, 'bold'),
                        fg='#ffffff',
                        bg=self.transparent_color,
                        relief='flat'
                    )
                    # Positionner le compteur au centre de l'image
                    # Utiliser place() pour positionner par rapport au frame
                    self.balise_affutee_counter_label.place(relx=0.5, rely=0.5, anchor='center')
                    
                    # Pack le frame dans icons_frame (à droite de Pointe affûtée)
                    self.balise_affutee_frame.pack(side=tk.LEFT, padx=5)
                    # Icône Balise affûtée affichée
                else:
                    # Mettre à jour le compteur
                    if self.balise_affutee_counter_label:
                        if self.balise_affutee_value > 0:
                            self.balise_affutee_counter_label.config(text=str(self.balise_affutee_value))
                        else:
                            self.balise_affutee_counter_label.config(text="")
        except Exception as e:
            # Erreur lors de la gestion de l'icône Balise affûtée
            import traceback
            traceback.print_exc()
        
        # Gérer l'icône de Pointe affûtée pour le Cra
        try:
            if self.class_name == "cra":
                if self.pointe_affutee_active:
                    # Vérifier que icons_frame existe
                    if not hasattr(self, 'icons_frame') or self.icons_frame is None:
                        # icons_frame n'existe pas, impossible d'afficher l'icône
                        return
                    
                    # Afficher l'icône
                    if self.pointe_affutee_icon and self.pointe_affutee_icon_label is None:
                        # Vérifier que l'image existe toujours
                        try:
                            # Tester si l'image est valide
                            _ = self.pointe_affutee_icon.width()
                            # Créer le label avec l'icône dans le frame des icônes
                            self.pointe_affutee_icon_label = tk.Label(
                                self.icons_frame,
                                image=self.pointe_affutee_icon,
                                bg=self.transparent_color
                            )
                            # Garder une référence à l'image dans le label
                            self.pointe_affutee_icon_label.image = self.pointe_affutee_icon
                            self.pointe_affutee_icon_label.pack(side=tk.LEFT, padx=5)
                        except (tk.TclError, AttributeError) as e:
                            # Image Pointe affûtée invalide
                            self.pointe_affutee_icon = None
                            self.pointe_affutee_icon_label = None
                    elif self.pointe_affutee_icon_label:
                        # Vérifier si le widget existe toujours et n'est pas déjà packé
                        try:
                            if self.pointe_affutee_icon_label.winfo_exists():
                                if not self.pointe_affutee_icon_label.winfo_viewable():
                                    self.pointe_affutee_icon_label.pack(side=tk.LEFT, padx=5)
                            else:
                                # Widget détruit, recréer
                                self.pointe_affutee_icon_label = None
                        except tk.TclError:
                            # Widget détruit, recréer
                            self.pointe_affutee_icon_label = None
                else:
                    # Masquer l'icône si Pointe affûtée n'est pas active
                    if self.pointe_affutee_icon_label:
                        try:
                            if self.pointe_affutee_icon_label.winfo_exists():
                                self.pointe_affutee_icon_label.pack_forget()
                        except tk.TclError:
                            self.pointe_affutee_icon_label = None
        except Exception as e:
            # Erreur lors de la gestion de l'icône Pointe affûtée
            import traceback
            traceback.print_exc()
        
        # Supprimer les labels d'états qui ne sont plus pertinents
        states_to_remove = [name for name in self.state_labels.keys() if name not in class_states]
        for state_name in states_to_remove:
            self.state_labels[state_name].destroy()
            del self.state_labels[state_name]
    
    def update_combo(self, combo_count, class_name="", timer=0.0):
        """Méthode de compatibilité (dépréciée, utiliser update_states)"""
        # Gardée pour compatibilité, mais redirige vers update_states
        pass
    
    def set_pointe_affutee_active(self, active: bool):
        """Active ou désactive l'affichage de l'icône Pointe affûtée"""
        # Juste mettre à jour le flag, l'affichage sera géré dans update_states()
        self.pointe_affutee_active = active
    
    def set_balise_affutee_value(self, value: int):
        """Met à jour la valeur de la balise affûtée"""
        self.balise_affutee_value = value
        # Mettre à jour l'affichage si le label existe
        if self.balise_affutee_counter_label:
            if value > 0:
                self.balise_affutee_counter_label.config(text=str(value))
            else:
                self.balise_affutee_counter_label.config(text="")
    
    def reset_states(self):
        """Réinitialise les états de cet overlay uniquement via le callback"""
        # Désactiver aussi la Pointe affûtée lors du reset
        self.set_pointe_affutee_active(False)
        # Réinitialiser la balise affûtée
        self.set_balise_affutee_value(0)
        if self.reset_callback:
            # Passer le nom de la classe pour ne réinitialiser que cette classe
            self.reset_callback(self.class_name)
    
    def close_overlay(self):
        """Ferme cet overlay uniquement"""
        if self.root:
            try:
                # Vérifier que la fenêtre existe encore avant de la détruire
                if self.root.winfo_exists():
                    self.root.destroy()  # Détruire la fenêtre au lieu de quitter
            except tk.TclError:
                pass  # Fenêtre déjà fermée ou détruite
    
    def run(self):
        """Lance la boucle principale de l'overlay"""
        self.root.mainloop()
    
    def update(self):
        """Met à jour l'interface (à appeler périodiquement)"""
        try:
            self.root.update_idletasks()
            self.root.update()
        except tk.TclError:
            # Fenêtre fermée
            pass
    
    def show(self):
        """Affiche l'overlay"""
        if self.root and self.root.winfo_exists():
            try:
                if not self.is_visible:
                    # Forcer l'affichage de la fenêtre
                    self.root.deiconify()
                    self.root.lift()
                    self.root.attributes('-topmost', True)
                    self.is_visible = True
                    # Overlay affiché
            except tk.TclError as e:
                # Erreur lors de l'affichage de l'overlay
                pass
    
    def hide(self):
        """Masque l'overlay"""
        if self.root:
            try:
                if self.is_visible:
                    self.root.withdraw()  # Cacher la fenêtre
                    self.is_visible = False
                    # Overlay masqué
            except tk.TclError as e:
                # Erreur lors du masquage de l'overlay
                pass
    
    def load_combo_display(self):
        """Charge et affiche les combos pour l'Iop"""
        if self.class_name != "iop":
            return
        
        try:
            # Le combo_tracker devrait être passé depuis l'extérieur (main.py)
            # Si ce n'est pas le cas, en créer un
            if not self.combo_tracker:
                from combo_tracker import ComboTracker
                self.combo_tracker = ComboTracker("iop_combos.json")
            
            # Charger les icônes de ressources
            self._load_resource_icons()
            
            # Créer l'affichage des combos
            self._create_combo_grid()
        except Exception as e:
            # Erreur lors du chargement de l'affichage des combos
            import traceback
            traceback.print_exc()
    
    def _load_resource_icons(self, target_size=None):
        """
        Charge les icônes de ressources (PA, PM, PW)
        
        Args:
            target_size: Taille cible pour redimensionner les icônes (None = taille originale)
        """
        resource_names = ["PA", "PM", "PW"]
        for resource in resource_names:
            # Essayer plusieurs variantes de noms de fichiers
            possible_paths = [
                os.path.join("assets", "iop", f"{resource.lower()}.png"),
                os.path.join("assets", "iop", f"{resource.upper()}.png"),
                os.path.join("assets", "iop", f"{resource}.png"),
            ]
            
            icon_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    icon_path = path
                    break
            
            if icon_path:
                try:
                    if PIL_AVAILABLE and target_size:
                        # Utiliser PIL pour redimensionner
                        pil_image = Image.open(icon_path)
                        # Redimensionner en gardant les proportions
                        pil_image = pil_image.resize((target_size, target_size), Image.Resampling.LANCZOS)
                        icon = ImageTk.PhotoImage(master=self.root, image=pil_image)
                        # Icône chargée et redimensionnée
                    else:
                        # Charger sans redimensionnement
                        icon = PhotoImage(master=self.root, file=icon_path)
                        if target_size and not PIL_AVAILABLE:
                            # PIL non disponible, icône non redimensionnée
                            pass
                        else:
                            # Icône chargée
                            pass
                    self.resource_icons[resource] = icon
                    self._icon_refs.append(icon)
                except Exception as e:
                    # Erreur lors du chargement de l'icône
                    import traceback
                    traceback.print_exc()
                    self.resource_icons[resource] = None
            else:
                # Icône introuvable
                self.resource_icons[resource] = None
    
    def _create_combo_grid(self):
        """Crée la grille d'affichage des combos"""
        if not self.combo_tracker:
            return
        
        # Frame pour la ligne des icônes de combos
        self.combo_icons_frame = tk.Frame(self.combos_frame, bg=self.transparent_color)
        self.combo_icons_frame.pack(pady=5, fill=tk.X)
        
        # Frame pour les séquences de ressources (sous les icônes de combos)
        self.sequences_frame = tk.Frame(self.combos_frame, bg=self.transparent_color)
        self.sequences_frame.pack(pady=2, fill=tk.BOTH, expand=True)
        
        combos = self.combo_tracker.combos
        combo_ids = sorted(combos.keys())  # combo_1, combo_2, etc.
        
        # Déterminer d'abord la taille de référence en chargeant temporairement les icônes de combos
        reference_icon_size = 48  # Taille par défaut
        combo_icons_loaded = {}  # Stocker les icônes de combos chargées
        for combo_id in combo_ids:
            combo_icon_path = os.path.join("assets", "iop", f"{combo_id}.png")
            if os.path.exists(combo_icon_path):
                try:
                    test_icon = PhotoImage(master=self.root, file=combo_icon_path)
                    icon_size = max(test_icon.width(), test_icon.height())
                    if icon_size > reference_icon_size:
                        reference_icon_size = icon_size
                    combo_icons_loaded[combo_id] = test_icon
                    self._icon_refs.append(test_icon)
                except:
                    pass
        
        # Recharger les icônes de ressources avec la taille de référence
        self._load_resource_icons(target_size=reference_icon_size)
        
        # Déterminer la largeur maximale des icônes de combos pour uniformiser les colonnes
        max_combo_icon_width = reference_icon_size
        for combo_id in combo_ids:
            combo_icon = combo_icons_loaded.get(combo_id)
            if combo_icon:
                try:
                    icon_width = combo_icon.width()
                    if icon_width > max_combo_icon_width:
                        max_combo_icon_width = icon_width
                except:
                    pass
        
        # Calculer la largeur uniforme pour toutes les colonnes
        uniform_column_width = max_combo_icon_width + 4  # +4 pour padding (2px de chaque côté)
        
        # Configurer toutes les colonnes des deux frames avec la même largeur
        for idx in range(len(combo_ids)):
            self.combo_icons_frame.columnconfigure(idx, weight=0, minsize=uniform_column_width)
            self.sequences_frame.columnconfigure(idx, weight=0, minsize=uniform_column_width)
        
        # Stocker les colonnes pour l'alignement
        combo_columns = []
        combo_icon_labels = []
        
        # Créer une colonne pour chaque combo
        for idx, combo_id in enumerate(combo_ids):
            combo_data = combos[combo_id]
            combo_name = combo_data["nom"]
            sequence = combo_data["sequence"]
            
            # Utiliser l'icône déjà chargée ou la charger
            combo_icon = combo_icons_loaded.get(combo_id)
            if not combo_icon:
                # Si pas chargée, essayer de la charger
                combo_icon_path = os.path.join("assets", "iop", f"{combo_id}.png")
                if os.path.exists(combo_icon_path):
                    try:
                        combo_icon = PhotoImage(master=self.root, file=combo_icon_path)
                        self._icon_refs.append(combo_icon)
                        combo_icons_loaded[combo_id] = combo_icon
                        # Icône combo chargée
                    except Exception as e:
                        # Erreur lors du chargement de l'icône combo
                        pass
            
            # Frame pour l'icône du combo (pour l'aligner avec la colonne)
            combo_icon_container = tk.Frame(self.combo_icons_frame, bg=self.transparent_color)
            combo_icon_container.grid(row=0, column=idx, padx=1, sticky='n')  # Aligné en haut
            # Lier les clics pour mettre à jour last_click_time et remettre le focus sur Wakfu
            def on_combo_click(event):
                self.last_click_time = time.time()
                if self.wakfu_window_hwnd is not None:
                    try:
                        import win32gui
                        win32gui.SetForegroundWindow(self.wakfu_window_hwnd)
                    except:
                        pass
            combo_icon_container.bind('<Button-1>', on_combo_click)
            
            # Colonne pour ce combo (même largeur que l'icône de combo)
            combo_column = tk.Frame(self.sequences_frame, bg=self.transparent_color)
            combo_column.grid(row=0, column=idx, padx=1, sticky='n')  # Aligné en haut
            combo_columns.append(combo_column)
            # Lier les clics pour mettre à jour last_click_time et remettre le focus sur Wakfu
            combo_column.bind('<Button-1>', on_combo_click)
            
            # Label pour l'icône du combo (dans la ligne du haut) - aligné en haut
            if combo_icon:
                combo_icon_label = tk.Label(
                    combo_icon_container,
                    image=combo_icon,
                    bg=self.transparent_color
                )
                combo_icon_label.pack(anchor='n')  # Aligné en haut
            else:
                # Placeholder si l'icône n'existe pas
                combo_icon_label = tk.Label(
                    combo_icon_container,
                    text=combo_name[:3],  # Afficher les 3 premières lettres
                    font=('Arial', 10),
                    fg='white',
                    bg=self.transparent_color,
                    width=8
                )
                combo_icon_label.pack(anchor='n')  # Aligné en haut
            
            # Lier les clics sur le label pour mettre à jour last_click_time et remettre le focus sur Wakfu
            def on_combo_label_click(event):
                self.last_click_time = time.time()
                if self.wakfu_window_hwnd is not None:
                    try:
                        import win32gui
                        win32gui.SetForegroundWindow(self.wakfu_window_hwnd)
                    except:
                        pass
            combo_icon_label.bind('<Button-1>', on_combo_label_click)
            combo_icon_labels.append(combo_icon_label)
            
            # Ajouter un tooltip avec le nom du combo au survol
            self._create_tooltip(combo_icon_label, combo_name)
            self._create_tooltip(combo_icon_container, combo_name)
            
            # Stocker les labels des étapes pour ce combo
            step_labels = []
            
            # Créer un label pour chaque étape de la séquence
            for step_idx, step_cost in enumerate(sequence):
                # Déterminer quelle ressource et quelle quantité
                resource_type = None
                resource_amount = 0
                for res, amount in step_cost.items():
                    resource_type = res
                    resource_amount = amount
                    break
                
                # Charger l'icône de la ressource
                resource_icon = self.resource_icons.get(resource_type)
                
                # Utiliser la taille de référence pour toutes les icônes de ressources
                icon_size = reference_icon_size
                
                step_canvas = tk.Canvas(
                    combo_column,
                    width=icon_size,
                    height=icon_size,
                    bg=self.transparent_color,
                    highlightthickness=0,
                    relief='flat',
                    takefocus=0  # Empêcher le canvas de prendre le focus
                )
                step_canvas.pack(pady=0, anchor='center')
                # Lier les clics pour mettre à jour last_click_time et remettre le focus sur Wakfu
                def on_step_canvas_click(event):
                    self.last_click_time = time.time()
                    if self.wakfu_window_hwnd is not None:
                        try:
                            import win32gui
                            win32gui.SetForegroundWindow(self.wakfu_window_hwnd)
                        except:
                            pass
                step_canvas.bind('<Button-1>', on_step_canvas_click)
                
                # Forcer la mise à jour pour obtenir les dimensions réelles
                step_canvas.update_idletasks()
                
                # Utiliser la taille du canvas (qui devrait être icon_size)
                canvas_width = icon_size
                canvas_height = icon_size
                
                x = canvas_width // 2
                y = canvas_height // 2
                
                # Afficher l'icône de ressource sur le canvas
                if resource_icon:
                    try:
                        # Centrer l'icône sur le canvas
                        image_id = step_canvas.create_image(x, y, image=resource_icon, anchor='center')
                        # Garder une référence à l'image pour éviter le garbage collection
                        step_canvas.image = resource_icon
                        step_canvas.image_id = image_id
                        
                        # Afficher le chiffre superposé sur l'icône (centré)
                        # Créer d'abord le contour noir (légèrement décalé)
                        step_canvas.create_text(
                            x+1, y+1,  # Légèrement décalé pour l'ombre
                            text=str(resource_amount),
                            fill='black',
                            font=('Arial', 14, 'bold'),
                            anchor='center'
                        )
                        step_canvas.create_text(
                            x-1, y-1,  # Légèrement décalé pour l'ombre
                            text=str(resource_amount),
                            fill='black',
                            font=('Arial', 14, 'bold'),
                            anchor='center'
                        )
                        step_canvas.create_text(
                            x+1, y-1,  # Légèrement décalé pour l'ombre
                            text=str(resource_amount),
                            fill='black',
                            font=('Arial', 14, 'bold'),
                            anchor='center'
                        )
                        step_canvas.create_text(
                            x-1, y+1,  # Légèrement décalé pour l'ombre
                            text=str(resource_amount),
                            fill='black',
                            font=('Arial', 14, 'bold'),
                            anchor='center'
                        )
                        # Puis le texte blanc par-dessus
                        amount_text_id = step_canvas.create_text(
                            x, y,  # Centré sur l'icône
                            text=str(resource_amount),
                            fill='white',
                            font=('Arial', 14, 'bold'),
                            anchor='center'
                        )
                    except Exception as e:
                        # Erreur lors de l'affichage de l'icône
                        import traceback
                        traceback.print_exc()
                        # Afficher un placeholder texte
                        step_canvas.create_text(
                            x, y,
                            text=f"{resource_type}\n{resource_amount}",
                            fill='white',
                            font=('Arial', 10),
                            anchor='center'
                        )
                        amount_text_id = None
                else:
                    # Placeholder avec texte si pas d'icône
                    step_canvas.create_text(
                        x, y,
                        text=f"{resource_type}\n{resource_amount}",
                        fill='white',
                        font=('Arial', 10),
                        anchor='center'
                    )
                    amount_text_id = None
                
                # Stocker les références
                step_labels.append({
                    "canvas": step_canvas,
                    "resource_icon": resource_icon,
                    "amount_text_id": amount_text_id,
                    "resource_type": resource_type,
                    "resource_amount": resource_amount,
                    "sort_icon": None,  # Sera remplacé par l'icône du sort quand utilisé
                    "sort_image_id": None  # ID de l'image du sort sur le canvas
                })
            
            # Stocker les informations du combo
            self.combo_frames[combo_id] = combo_column
            self.combo_icons[combo_id] = combo_icon
            self.combo_step_labels[combo_id] = step_labels
            # Stocker aussi la référence au container de l'icône pour pouvoir le réafficher
            if not hasattr(self, 'combo_icon_containers'):
                self.combo_icon_containers = {}
            self.combo_icon_containers[combo_id] = combo_icon_container
    
    def handle_combo_update(self, combo_update: dict):
        """
        Gère les mises à jour des combos depuis le combo tracker
        
        Args:
            combo_update: Dictionnaire avec les informations de mise à jour
        """
        if self.class_name != "iop":
            return
        
        update_type = combo_update.get("type")
        
        if update_type == "combo_started":
            # Un ou plusieurs combos ont commencé
            primary_combo_id = combo_update.get("combo_id")
            possible_combos = combo_update.get("possible_combos", [])
            active_combos = combo_update.get("active_combos", possible_combos)  # Tous les combos actifs
            hidden_combos = combo_update.get("hidden_combos", [])
            
            # Stocker les combos actifs
            self.active_combo_id = primary_combo_id  # Pour compatibilité
            if not hasattr(self, 'active_combo_ids'):
                self.active_combo_ids = []
            self.active_combo_ids = active_combos.copy()
            
            # Masquer les combos impossibles
            for combo_id in hidden_combos:
                if combo_id in self.combo_frames:
                    self.combo_frames[combo_id].grid_remove()
            
            # Réinitialiser toutes les étapes des combos actifs (pour enlever les sorts des combos précédents)
            for combo_id in active_combos:
                if combo_id in self.combo_step_labels:
                    step_labels = self.combo_step_labels[combo_id]
                    for step_idx, step_info in enumerate(step_labels):
                        canvas = step_info["canvas"]
                        
                        # Réinitialiser la bordure
                        canvas.config(highlightbackground='black', highlightthickness=0)
                        
                        # Si ce n'est pas la première étape, remettre l'icône de ressource
                        if step_idx > 0 and step_info.get("sort_icon"):
                            resource_icon = step_info.get("resource_icon")
                            if resource_icon:
                                # Effacer le canvas et redessiner avec l'icône de ressource
                                canvas.delete("all")
                                
                                # Retirer le tooltip du sort s'il existe
                                if hasattr(canvas, 'tooltip'):
                                    try:
                                        canvas.tooltip.destroy()
                                    except:
                                        pass
                                    canvas.tooltip = None
                                # Retirer les bindings du tooltip
                                try:
                                    canvas.unbind('<Enter>')
                                    canvas.unbind('<Leave>')
                                except:
                                    pass
                                
                                # Afficher l'icône de ressource
                                icon_size = max(canvas.winfo_width(), canvas.winfo_height())
                                if icon_size < 10:
                                    try:
                                        icon_size = max(resource_icon.width(), resource_icon.height())
                                    except:
                                        icon_size = 48
                                
                                x = icon_size // 2
                                y = icon_size // 2
                                canvas.create_image(x, y, image=resource_icon, anchor='center')
                                canvas.image = resource_icon  # Garder la référence
                                
                                # Réafficher le chiffre (avec contour noir)
                                # Créer d'abord le contour noir
                                canvas.create_text(x+1, y+1, text=str(step_info["resource_amount"]), fill='black', font=('Arial', 14, 'bold'), anchor='center')
                                canvas.create_text(x-1, y-1, text=str(step_info["resource_amount"]), fill='black', font=('Arial', 14, 'bold'), anchor='center')
                                canvas.create_text(x+1, y-1, text=str(step_info["resource_amount"]), fill='black', font=('Arial', 14, 'bold'), anchor='center')
                                canvas.create_text(x-1, y+1, text=str(step_info["resource_amount"]), fill='black', font=('Arial', 14, 'bold'), anchor='center')
                                # Puis le texte blanc
                                amount_text_id = canvas.create_text(
                                    x, y,
                                    text=str(step_info["resource_amount"]),
                                    fill='white',
                                    font=('Arial', 14, 'bold'),
                                    anchor='center'
                                )
                                step_info["amount_text_id"] = amount_text_id
                            
                            step_info["sort_icon"] = None
                            step_info["sort_image_id"] = None
            
            # Mettre à jour le premier sort utilisé pour tous les combos actifs
            sort_name = combo_update.get("sort_name")
            if sort_name:
                for combo_id in active_combos:
                    self._update_combo_step(combo_id, 0, sort_name)
            
            # Si on a un deuxième sort (nouveau combo basé sur le dernier sort terminé)
            second_sort = combo_update.get("second_sort")
            if second_sort:
                # Mettre à jour la deuxième étape pour tous les combos actifs
                for combo_id in active_combos:
                    self._update_combo_step(combo_id, 1, second_sort)
        
        elif update_type == "combo_progress":
            # Le combo progresse
            primary_combo_id = combo_update.get("combo_id")
            sort_name = combo_update.get("sort_name")
            step = combo_update.get("step", 0)
            active_combos = combo_update.get("active_combos", [primary_combo_id] if primary_combo_id else [])
            
            # Mettre à jour tous les combos actifs
            if sort_name:
                # Masquer les combos qui ne sont plus actifs
                all_combo_ids = sorted(self.combo_tracker.combos.keys())
                for combo_id in all_combo_ids:
                    if combo_id not in active_combos and combo_id in self.combo_frames:
                        # Ce combo n'est plus actif, le masquer
                        self.combo_frames[combo_id].grid_remove()
                    elif combo_id in active_combos and combo_id in self.combo_frames:
                        # Ce combo est actif, s'assurer qu'il est visible
                        combo_frame = self.combo_frames[combo_id]
                        # Trouver l'index du combo
                        idx = all_combo_ids.index(combo_id)
                        combo_frame.grid(row=0, column=idx, padx=1, sticky='n')
                        # Réafficher aussi l'icône
                        if hasattr(self, 'combo_icon_containers') and combo_id in self.combo_icon_containers:
                            icon_container = self.combo_icon_containers[combo_id]
                            icon_container.grid(row=0, column=idx, padx=1, sticky='n')
                
                # Mettre à jour l'étape pour tous les combos actifs
                # Chaque combo a sa propre progression, donc on utilise step - 1 pour tous
                # (le step retourné correspond au combo primaire, mais tous les combos actifs sont à la même étape globale)
                for combo_id in active_combos:
                    # Obtenir la progression actuelle de ce combo depuis le tracker
                    if self.combo_tracker and hasattr(self.combo_tracker, 'combo_progress'):
                        combo_progress = self.combo_tracker.combo_progress.get(combo_id, [])
                        # L'étape est la longueur de la progression (0-based)
                        combo_step = len(combo_progress) - 1  # -1 car on vient d'ajouter le sort
                        if combo_step >= 0:
                            self._update_combo_step(combo_id, combo_step, sort_name)
                    else:
                        # Fallback si le tracker n'est pas disponible
                        self._update_combo_step(combo_id, step - 1, sort_name)
        
        elif update_type == "combo_completed":
            # Le combo est terminé, on garde le dernier sort et on affiche les combos possibles
            combo_id = combo_update.get("combo_id")
            sort_name = combo_update.get("sort_name")
            possible_next_combos = combo_update.get("possible_next_combos", [])
            hidden_combos = combo_update.get("hidden_combos", [])
            
            if combo_id and sort_name:
                # Mettre à jour la dernière étape
                step_labels = self.combo_step_labels.get(combo_id, [])
                if step_labels:
                    self._update_combo_step(combo_id, len(step_labels) - 1, sort_name)
            
            # Afficher les combos possibles basés sur le dernier sort terminé
            # Cacher les combos qui ne commencent pas par ce dernier sort
            for combo_id_to_hide in hidden_combos:
                if combo_id_to_hide in self.combo_frames:
                    self.combo_frames[combo_id_to_hide].grid_remove()
            
            # Afficher les combos possibles avec le dernier sort comme première étape
            all_combo_ids = sorted(self.combo_tracker.combos.keys())
            for combo_id_to_show in possible_next_combos:
                if combo_id_to_show in self.combo_frames:
                    # Réafficher le combo
                    idx = all_combo_ids.index(combo_id_to_show)
                    self.combo_frames[combo_id_to_show].grid(row=0, column=idx, padx=1, sticky='n')
                    if hasattr(self, 'combo_icon_containers') and combo_id_to_show in self.combo_icon_containers:
                        icon_container = self.combo_icon_containers[combo_id_to_show]
                        icon_container.grid(row=0, column=idx, padx=1, sticky='n')
                    
                    # Réinitialiser toutes les étapes de ce combo (pour enlever les sorts des combos précédents)
                    if combo_id_to_show in self.combo_step_labels:
                        step_labels = self.combo_step_labels[combo_id_to_show]
                        for step_idx, step_info in enumerate(step_labels):
                            canvas = step_info["canvas"]
                            
                            # Réinitialiser la bordure
                            canvas.config(highlightbackground='black', highlightthickness=0)
                            
                            # Si c'est la première étape, mettre le dernier sort terminé
                            if step_idx == 0:
                                self._update_combo_step(combo_id_to_show, 0, sort_name)
                            else:
                                # Pour les autres étapes, remettre l'icône de ressource
                                if step_info.get("sort_icon"):
                                    resource_icon = step_info.get("resource_icon")
                                    if resource_icon:
                                        # Effacer le canvas et redessiner avec l'icône de ressource
                                        canvas.delete("all")
                                        
                                        # Retirer le tooltip du sort s'il existe
                                        if hasattr(canvas, 'tooltip'):
                                            try:
                                                canvas.tooltip.destroy()
                                            except:
                                                pass
                                            canvas.tooltip = None
                                        # Retirer les bindings du tooltip
                                        try:
                                            canvas.unbind('<Enter>')
                                            canvas.unbind('<Leave>')
                                        except:
                                            pass
                                        
                                        # Afficher l'icône de ressource
                                        icon_size = max(canvas.winfo_width(), canvas.winfo_height())
                                        if icon_size < 10:
                                            try:
                                                icon_size = max(resource_icon.width(), resource_icon.height())
                                            except:
                                                icon_size = 48
                                        
                                        x = icon_size // 2
                                        y = icon_size // 2
                                        canvas.create_image(x, y, image=resource_icon, anchor='center')
                                        canvas.image = resource_icon  # Garder la référence
                                        
                                        # Réafficher le chiffre (avec contour noir)
                                        # Créer d'abord le contour noir
                                        canvas.create_text(x+1, y+1, text=str(step_info["resource_amount"]), fill='black', font=('Arial', 14, 'bold'), anchor='center')
                                        canvas.create_text(x-1, y-1, text=str(step_info["resource_amount"]), fill='black', font=('Arial', 14, 'bold'), anchor='center')
                                        canvas.create_text(x+1, y-1, text=str(step_info["resource_amount"]), fill='black', font=('Arial', 14, 'bold'), anchor='center')
                                        canvas.create_text(x-1, y+1, text=str(step_info["resource_amount"]), fill='black', font=('Arial', 14, 'bold'), anchor='center')
                                        # Puis le texte blanc
                                        amount_text_id = canvas.create_text(
                                            x, y,
                                            text=str(step_info["resource_amount"]),
                                            fill='white',
                                            font=('Arial', 14, 'bold'),
                                            anchor='center'
                                        )
                                        step_info["amount_text_id"] = amount_text_id
                                    
                                    step_info["sort_icon"] = None
                                    step_info["sort_image_id"] = None
        
        elif update_type == "combo_completed_no_next":
            # Le combo est terminé mais aucun nouveau combo ne commence par ce sort
            # On réaffiche tous les combos possibles (comme un reset)
            combo_id = combo_update.get("combo_id")
            sort_name = combo_update.get("sort_name")
            
            if combo_id and sort_name:
                # Mettre à jour la dernière étape
                step_labels = self.combo_step_labels.get(combo_id, [])
                if step_labels:
                    self._update_combo_step(combo_id, len(step_labels) - 1, sort_name)
            
            # Réafficher tous les combos (comme un reset)
            self._reset_combo_display()
        
        elif update_type == "combo_broken" or update_type == "combo_reset":
            # Le combo est cassé ou réinitialisé
            self._reset_combo_display()
    
    def _update_combo_step(self, combo_id: str, step_index: int, sort_name: str):
        """
        Met à jour une étape d'un combo avec l'icône du sort utilisé
        
        Args:
            combo_id: ID du combo
            step_index: Index de l'étape (0-based)
            sort_name: Nom du sort utilisé
        """
        if combo_id not in self.combo_step_labels:
            return
        
        step_labels = self.combo_step_labels[combo_id]
        if step_index >= len(step_labels):
            return
        
        step_info = step_labels[step_index]
        canvas = step_info["canvas"]
        
        # Charger l'icône du sort
        sort_icon_path = os.path.join("assets", "iop", f"{sort_name}.png")
        if os.path.exists(sort_icon_path):
            try:
                sort_icon = PhotoImage(master=self.root, file=sort_icon_path)
                self._icon_refs.append(sort_icon)
                step_info["sort_icon"] = sort_icon
                
                # Effacer le canvas et redessiner avec l'icône du sort
                canvas.delete("all")
                
                # Afficher l'icône du sort
                icon_size = max(canvas.winfo_width(), canvas.winfo_height())
                if icon_size < 10:  # Si pas encore dimensionné, utiliser la taille de l'image
                    try:
                        icon_size = max(sort_icon.width(), sort_icon.height())
                    except:
                        icon_size = 48
                
                x = icon_size // 2
                y = icon_size // 2
                image_id = canvas.create_image(x, y, image=sort_icon, anchor='center')
                step_info["sort_image_id"] = image_id
                canvas.image = sort_icon  # Garder la référence
                
                # Ajouter un tooltip avec le nom du sort au survol
                self._create_tooltip(canvas, sort_name)
                
                # Réafficher le chiffre par-dessus (avec contour noir)
                # Créer d'abord le contour noir
                canvas.create_text(x+1, y+1, text=str(step_info["resource_amount"]), fill='black', font=('Arial', 14, 'bold'), anchor='center')
                canvas.create_text(x-1, y-1, text=str(step_info["resource_amount"]), fill='black', font=('Arial', 14, 'bold'), anchor='center')
                canvas.create_text(x+1, y-1, text=str(step_info["resource_amount"]), fill='black', font=('Arial', 14, 'bold'), anchor='center')
                canvas.create_text(x-1, y+1, text=str(step_info["resource_amount"]), fill='black', font=('Arial', 14, 'bold'), anchor='center')
                # Puis le texte blanc
                amount_text_id = canvas.create_text(
                    x, y,
                    text=str(step_info["resource_amount"]),
                    fill='white',
                    font=('Arial', 14, 'bold'),
                    anchor='center'
                )
                step_info["amount_text_id"] = amount_text_id
                
                # Icône sort chargée et affichée
            except Exception as e:
                # Erreur lors du chargement de l'icône sort
                import traceback
                traceback.print_exc()
        
        # Mettre en surbrillance (bordure colorée)
        canvas.config(highlightbackground='#00ff00', highlightthickness=2)
    
    def _reset_combo_display(self):
        """Réinitialise l'affichage des combos"""
        if not self.combo_tracker:
            return
        
        # Réafficher tous les combos (y compris ceux qui étaient masqués)
        combos = self.combo_tracker.combos
        combo_ids = sorted(combos.keys())
        
        # Réafficher tous les combos (y compris ceux qui étaient masqués)
        for idx, combo_id in enumerate(combo_ids):
            if combo_id in self.combo_frames:
                combo_frame = self.combo_frames[combo_id]
                # Réafficher le frame (grid au lieu de grid_remove)
                combo_frame.grid(row=0, column=idx, padx=1, sticky='n')
            
            # Réafficher aussi l'icône du combo si elle existe
            if hasattr(self, 'combo_icon_containers') and combo_id in self.combo_icon_containers:
                icon_container = self.combo_icon_containers[combo_id]
                icon_container.grid(row=0, column=idx, padx=1, sticky='n')
        
        # Réinitialiser les surbrillances et remettre les icônes de ressources
        for combo_id, step_labels in self.combo_step_labels.items():
            for step_info in step_labels:
                canvas = step_info["canvas"]
                
                # Réinitialiser la bordure
                canvas.config(highlightbackground='black', highlightthickness=0)
                
                # Remettre l'icône de ressource si elle a été remplacée
                if step_info["sort_icon"]:
                    resource_icon = step_info.get("resource_icon")
                    if resource_icon:
                        # Effacer le canvas et redessiner avec l'icône de ressource
                        canvas.delete("all")
                        
                        # Retirer le tooltip du sort s'il existe
                        if hasattr(canvas, 'tooltip'):
                            try:
                                canvas.tooltip.destroy()
                            except:
                                pass
                            canvas.tooltip = None
                        # Retirer les bindings du tooltip
                        try:
                            canvas.unbind('<Enter>')
                            canvas.unbind('<Leave>')
                        except:
                            pass
                        
                        # Afficher l'icône de ressource
                        icon_size = max(canvas.winfo_width(), canvas.winfo_height())
                        if icon_size < 10:
                            try:
                                icon_size = max(resource_icon.width(), resource_icon.height())
                            except:
                                icon_size = 48
                        
                        x = icon_size // 2
                        y = icon_size // 2
                        canvas.create_image(x, y, image=resource_icon, anchor='center')
                        canvas.image = resource_icon  # Garder la référence
                        
                        # Réafficher le chiffre (avec contour noir)
                        # Créer d'abord le contour noir
                        canvas.create_text(x+1, y+1, text=str(step_info["resource_amount"]), fill='black', font=('Arial', 14, 'bold'), anchor='center')
                        canvas.create_text(x-1, y-1, text=str(step_info["resource_amount"]), fill='black', font=('Arial', 14, 'bold'), anchor='center')
                        canvas.create_text(x+1, y-1, text=str(step_info["resource_amount"]), fill='black', font=('Arial', 14, 'bold'), anchor='center')
                        canvas.create_text(x-1, y+1, text=str(step_info["resource_amount"]), fill='black', font=('Arial', 14, 'bold'), anchor='center')
                        # Puis le texte blanc
                        amount_text_id = canvas.create_text(
                            x, y,
                            text=str(step_info["resource_amount"]),
                            fill='white',
                            font=('Arial', 14, 'bold'),
                            anchor='center'
                        )
                        step_info["amount_text_id"] = amount_text_id
                    
                    step_info["sort_icon"] = None
                    step_info["sort_image_id"] = None
        
        self.active_combo_id = None
        self.used_sorts = []
        # Ne pas réinitialiser l'affichage du dernier sort utilisé (il reste affiché)
    
    def _update_last_sort(self, sort_name: str):
        """
        Met à jour l'affichage du dernier sort utilisé
        
        Args:
            sort_name: Nom du sort utilisé
        """
        if self.class_name != "iop":
            return
        
        if not hasattr(self, 'last_sort_frame') or self.last_sort_frame is None:
            return
        
        # Charger l'icône du sort
        sort_icon_path = os.path.join("assets", "iop", f"{sort_name}.png")
        if os.path.exists(sort_icon_path):
            try:
                # Charger l'icône et la redimensionner en plus petit
                if PIL_AVAILABLE:
                    pil_image = Image.open(sort_icon_path)
                    # Redimensionner à 40x40 (plus petit que les icônes de combo)
                    target_size = 40
                    pil_image = pil_image.resize((target_size, target_size), Image.Resampling.LANCZOS)
                    sort_icon = ImageTk.PhotoImage(master=self.root, image=pil_image)
                else:
                    # Sans PIL, charger l'image normale
                    sort_icon = PhotoImage(master=self.root, file=sort_icon_path)
                
                self._icon_refs.append(sort_icon)
                
                # Supprimer les anciens labels s'ils existent
                if self.last_sort_label:
                    try:
                        self.last_sort_label.destroy()
                    except:
                        pass
                    self.last_sort_label = None
                
                if self.last_sort_text_label:
                    try:
                        self.last_sort_text_label.destroy()
                    except:
                        pass
                    self.last_sort_text_label = None
                
                # Créer un label avec le texte "Dernier sort : "
                self.last_sort_text_label = tk.Label(
                    self.last_sort_frame,
                    text="Dernier sort : ",
                    bg=self.transparent_color,
                    fg='white',
                    font=('Arial', 10)
                )
                self.last_sort_text_label.pack(side=tk.LEFT, padx=(0, 5))
                
                # Créer un nouveau label avec l'icône du sort (plus petite)
                self.last_sort_label = tk.Label(
                    self.last_sort_frame,
                    image=sort_icon,
                    bg=self.transparent_color
                )
                self.last_sort_label.image = sort_icon  # Garder la référence
                self.last_sort_label.pack(side=tk.LEFT, pady=5)
                
                # Ajouter un tooltip avec le nom du sort
                self._create_tooltip(self.last_sort_label, sort_name)
                
                # Stocker le nom du sort
                self.last_sort_name = sort_name
            except Exception as e:
                # Erreur lors du chargement de l'icône
                import traceback
                traceback.print_exc()
    
    def _create_tooltip(self, widget, text):
        """
        Crée un tooltip qui s'affiche au survol du widget
        
        Args:
            widget: Widget Tkinter sur lequel ajouter le tooltip
            text: Texte à afficher dans le tooltip
        """
        # Retirer les anciens bindings et tooltip s'ils existent
        if hasattr(widget, 'tooltip'):
            try:
                widget.tooltip.destroy()
            except:
                pass
            widget.tooltip = None
        
        try:
            widget.unbind('<Enter>')
            widget.unbind('<Leave>')
        except:
            pass
        
        def on_enter(event):
            # Créer une fenêtre tooltip
            tooltip = tk.Toplevel(self.root)
            tooltip.wm_overrideredirect(True)  # Pas de barre de titre
            tooltip.wm_attributes('-topmost', True)
            try:
                tooltip.wm_attributes('-alpha', 0.9)  # Légèrement transparent
            except:
                pass  # L'attribut alpha n'est pas supporté sur tous les systèmes
            
            # Obtenir la position de la souris
            x = event.x_root + 10
            y = event.y_root + 10
            
            # Créer un label avec le texte
            label = tk.Label(
                tooltip,
                text=text,
                font=('Arial', 10),
                bg='#2a2a2a',
                fg='white',
                relief='solid',
                borderwidth=1,
                padx=8,
                pady=4
            )
            label.pack()
            
            # Positionner la fenêtre
            tooltip.geometry(f"+{x}+{y}")
            
            # Stocker la référence au tooltip dans le widget
            widget.tooltip = tooltip
        
        def on_leave(event):
            # Détruire le tooltip quand on quitte le widget
            if hasattr(widget, 'tooltip'):
                try:
                    widget.tooltip.destroy()
                except:
                    pass
                widget.tooltip = None
        
        # Lier les événements de survol
        widget.bind('<Enter>', on_enter)
        widget.bind('<Leave>', on_leave)

