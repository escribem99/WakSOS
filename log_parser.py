"""
Module pour parser le fichier log de Wakfu et détecter les états
"""
import os
import re
import time
from typing import Dict, Optional
from collections import defaultdict


class WakfuLogParser:
    """Parse le fichier log de Wakfu pour extraire les états des personnages"""
    
    def __init__(self, log_path: Optional[str] = None, combo_tracker=None):
        """
        Initialise le parser de logs
        
        Args:
            log_path: Chemin vers le fichier log. Si None, utilise le chemin par défaut.
            combo_tracker: Instance de ComboTracker pour récupérer les coûts des sorts (optionnel)
        """
        self.log_path = log_path or self.find_default_log_path()
        self.file_position = 0
        self.combo_tracker = combo_tracker
        self.states = {
            "iop": {
                "Concentration": 0,
                "Courroux": 0,
                "Préparation": 0
            },
            "cra": {
                "Affûtage": 0,
                "Précision": 0
            }
        }
        self.current_class = None
        
        # État pour gérer le sort "Charge" en attente
        # Structure: {"sort_name": "Charge", "character": "XXX", "lines_since": 0}
        self.pending_charge = None
        
        # Système de déduplication pour éviter de traiter les lignes dupliquées
        # (quand deux fenêtres Wakfu sont ouvertes dans le même combat)
        # Structure: {hash_ligne: timestamp}
        self.processed_lines_cache = {}
        self.dedup_window = 0.5  # Fenêtre de déduplication : 500ms
        
        # Patterns pour détecter les états dans les logs
        # Format réel: "NomPersonnage: État (+XX Niv.)"
        # Exemple: "Nemen-Arc: Affûtage (+20 Niv.)"
        self.patterns = {
            "iop": {
                "Concentration": [
                    r"[Cc]oncentration\s*\(?\+\s*(\d+)\s*[Nn]iv\.?\)?",  # "Concentration (+20 Niv.)"
                    r"[Cc]oncentration\s*[:\-]?\s*\(?\+\s*(\d+)",  # "Concentration: +20" ou "Concentration (+20"
                    r"[Cc]oncentration\s*[:\-]?\s*(\d+)",  # "Concentration: 20"
                    r"(\d+)\s*[Cc]oncentration",  # "20 Concentration"
                ],
                "Courroux": [
                    r"[Cc]ourroux\s*\(?\+\s*(\d+)\s*[Nn]iv\.?\)?",  # "Courroux (+20 Niv.)"
                    r"[Cc]ourroux\s*[:\-]?\s*\(?\+\s*(\d+)",
                    r"[Cc]ourroux\s*[:\-]?\s*(\d+)",
                    r"(\d+)\s*[Cc]ourroux",
                ],
                "Préparation": [
                    r"[Pp]réparation\s*\(?\+\s*(\d+)\s*[Nn]iv\.?\)?",  # "Préparation (+20 Niv.)"
                    r"[Pp]reparation\s*\(?\+\s*(\d+)\s*[Nn]iv\.?\)?",  # Sans accent
                    r"[Pp]réparation\s*[:\-]?\s*\(?\+\s*(\d+)",
                    r"[Pp]reparation\s*[:\-]?\s*\(?\+\s*(\d+)",
                    r"[Pp]réparation\s*[:\-]?\s*(\d+)",
                    r"[Pp]reparation\s*[:\-]?\s*(\d+)",
                    r"(\d+)\s*[Pp]réparation",
                    r"(\d+)\s*[Pp]reparation",
                ]
            },
            "cra": {
                "Affûtage": [
                    r"[Aa]ffûtage\s*\(?\+\s*(\d+)\s*[Nn]iv\.?\)?",  # "Affûtage (+20 Niv.)" - Format principal
                    r"[Aa]ffutage\s*\(?\+\s*(\d+)\s*[Nn]iv\.?\)?",  # Sans accent
                    r"[Aa]ffûtage\s*[:\-]?\s*\(?\+\s*(\d+)",  # "Affûtage: +20"
                    r"[Aa]ffutage\s*[:\-]?\s*\(?\+\s*(\d+)",
                    r"[Aa]ffûtage\s*[:\-]?\s*(\d+)",
                    r"[Aa]ffutage\s*[:\-]?\s*(\d+)",
                    r"(\d+)\s*[Aa]ffûtage",
                    r"(\d+)\s*[Aa]ffutage",
                ],
                "Précision": [
                    r"[Pp]récision\s*\(?\+\s*(\d+)\s*[Nn]iv\.?\)?",  # "Précision (+20 Niv.)" - Format principal
                    r"[Pp]recision\s*\(?\+\s*(\d+)\s*[Nn]iv\.?\)?",  # Sans accent
                    r"[Pp]récision\s*[:\-]?\s*\(?\+\s*(\d+)",  # "Précision: +20"
                    r"[Pp]recision\s*[:\-]?\s*\(?\+\s*(\d+)",
                    r"[Pp]récision\s*[:\-]?\s*(\d+)",
                    r"[Pp]recision\s*[:\-]?\s*(\d+)",
                    r"(\d+)\s*[Pp]récision",
                    r"(\d+)\s*[Pp]recision",
                ]
            }
        }
        
        # Patterns pour détecter la classe
        self.class_patterns = {
            "iop": [r"[Ii]op", r"[Cc]lasse.*[Ii]op"],
            "cra": [r"[Cc]ra", r"[Cc]râ", r"[Cc]lasse.*[Cc]ra", r"[Cc]lasse.*[Cc]râ"]
        }
    
    def find_default_log_path(self) -> str:
        """Trouve le chemin par défaut du fichier log de Wakfu"""
        # Chemins possibles pour Windows
        possible_paths = [
            os.path.expanduser(r"~\AppData\Local\Ankama\Wakfu\logs\wakfu.log"),
            os.path.expanduser(r"~\AppData\Local\Ankama\Wakfu\logs\wakfu-debug.log"),
            os.path.expanduser(r"~\Documents\Wakfu\logs\wakfu.log"),
            r"C:\Program Files (x86)\Wakfu\logs\wakfu.log",
            r"C:\Program Files\Wakfu\logs\wakfu.log"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # Si aucun chemin trouvé, retourner le plus probable
        return possible_paths[0]
    
    def read_new_lines(self) -> list:
        """Lit les nouvelles lignes depuis la dernière position"""
        if not os.path.exists(self.log_path):
            return []
        
        try:
            with open(self.log_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Aller à la dernière position
                f.seek(self.file_position)
                
                # Lire les nouvelles lignes
                new_lines = f.readlines()
                
                # Mettre à jour la position
                self.file_position = f.tell()
                
                return new_lines
        except Exception as e:
            # Erreur lors de la lecture du log
            return []
    
    def detect_class(self, line: str) -> Optional[str]:
        """Détecte la classe mentionnée dans la ligne"""
        line_lower = line.lower()
        
        for class_name, patterns in self.class_patterns.items():
            for pattern in patterns:
                if re.search(pattern, line_lower):
                    return class_name
        
        return None
    
    def parse_state_value(self, line: str, state_name: str, class_name: str) -> Optional[int]:
        """
        Parse une ligne pour extraire la valeur d'un état
        
        Retourne la valeur absolue de l'état (pas le delta)
        """
        patterns = self.patterns.get(class_name, {}).get(state_name, [])
        
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                try:
                    value = int(match.group(1))
                    # S'assurer que la valeur est positive et raisonnable (max 1000 pour permettre des valeurs élevées)
                    if 0 <= value <= 1000:
                        return value
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def detect_state_change(self, line: str) -> Dict:
        """
        Détecte un changement d'état dans une ligne de log
        
        Returns:
            Dict avec les informations du changement d'état ou None
        """
        # D'abord, essayer de détecter la classe depuis le texte (pour compatibilité)
        detected_class = self.detect_class(line)
        if detected_class:
            self.current_class = detected_class
        
        # Chercher les états dans toutes les classes
        # Si on trouve un état, on déduit la classe depuis l'état trouvé
        for class_name in ["iop", "cra"]:
            states_to_check = self.states.get(class_name, {})
            
            for state_name in states_to_check.keys():
                value = self.parse_state_value(line, state_name, class_name)
                
                if value is not None:
                    # On a trouvé un état, donc on connaît la classe
                    self.current_class = class_name
                    
                    # Mettre à jour l'état
                    # Le format "(+XX Niv.)" indique la valeur actuelle, pas un gain
                    # Donc on remplace toujours la valeur
                    old_value = self.states[class_name][state_name]
                    new_value = value  # Toujours remplacer, jamais accumuler
                    
                    self.states[class_name][state_name] = new_value
                    
                    return {
                        "class": class_name,
                        "state": state_name,
                        "old_value": old_value,
                        "new_value": new_value,
                        "line": line.strip()
                    }
        
        return None
    
    def detect_combat_end(self, line: str) -> bool:
        """
        Détecte si la ligne indique la fin d'un combat
        
        Args:
            line: Ligne de log à analyser
            
        Returns:
            True si la fin de combat est détectée
        """
        # Pattern flexible pour détecter la fin de combat
        # Format: "[Information (combat)] Combat terminé, cliquez ici pour rouvrir l'écran de fin de combat."
        combat_end_patterns = [
            r"\[Information \(combat\)\].*[Cc]ombat terminé.*cliquez ici pour rouvrir",
            r"\[Information \(combat\)\].*[Cc]ombat terminé.*fin de combat",
            r"[Cc]ombat terminé.*cliquez ici pour rouvrir l'écran de fin de combat"
        ]
        
        for pattern in combat_end_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return True
        
        return False
    
    def detect_partipris(self, line: str) -> bool:
        """
        Détecte si la ligne contient "-2 PA max (Parti pris)"
        Cela indique qu'il faut retirer 100 d'Affûtage si > 100
        
        Args:
            line: Ligne de log à analyser
            
        Returns:
            True si le message Parti pris est détecté
        """
        partipris_patterns = [
            r"-2\s*PA\s*max\s*\([Pp]arti\s*[Pp]ris\)",
            r"-2\s*PA\s*max.*[Pp]arti\s*[Pp]ris",
            r"[Pp]arti\s*[Pp]ris.*-2\s*PA"
        ]
        
        for pattern in partipris_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return True
        
        return False
    
    def detect_pointe_affutee(self, line: str) -> bool:
        """
        Détecte si la ligne contient "La Pointe affûtée est prête !"
        
        Args:
            line: Ligne de log à analyser
            
        Returns:
            True si le message Pointe affûtée est détecté
        """
        pointe_patterns = [
            r"[Ll]a\s+[Pp]ointe\s+affûtée\s+est\s+prête",
            r"[Ll]a\s+[Pp]ointe\s+affutee\s+est\s+prete",  # Sans accents
            r"[Pp]ointe\s+affûtée\s+est\s+prête",
            r"[Pp]ointe\s+affutee\s+est\s+prete",
            r"[Pp]ointe\s+affûtée.*prête",  # Plus flexible
            r"[Pp]ointe\s+affutee.*prete",
            r"[Pp]ointe.*affûtée.*prête",
            r"[Pp]ointe.*affutee.*prete"
        ]
        
        for pattern in pointe_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                # Message Pointe affûtée détecté
                return True
        
        return False
    
    def detect_consomme_pointe_affutee(self, line: str) -> bool:
        """
        Détecte si la ligne contient "Consomme Pointe affûtée"
        
        Args:
            line: Ligne de log à analyser
            
        Returns:
            True si le message "Consomme Pointe affûtée" est détecté
        """
        consomme_patterns = [
            r"[Cc]onsomme\s+[Pp]ointe\s+affûtée",
            r"[Cc]onsomme\s+[Pp]ointe\s+affutee",  # Sans accents
            r"[Cc]onsomme.*[Pp]ointe\s+affûtée",
            r"[Cc]onsomme.*[Pp]ointe\s+affutee"
        ]
        
        for pattern in consomme_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                # Message 'Consomme Pointe affûtée' détecté
                return True
        
        return False
    
    def detect_balise_affutee(self, line: str) -> Optional[int]:
        """
        Détecte si la ligne contient "Balise affûtée (+X Niv.)" et extrait la valeur X
        
        Args:
            line: Ligne de log à analyser
            
        Returns:
            La valeur X si détectée, None sinon
        """
        balise_patterns = [
            r"[Bb]alise\s+affûtée\s+\(\+(\d+)\s*[Nn]iv\.?\)",
            r"[Bb]alise\s+affutee\s+\(\+(\d+)\s*[Nn]iv\.?\)",  # Sans accents
            r"[Bb]alise.*affûtée.*\(\+(\d+)\s*[Nn]iv\.?\)",
            r"[Bb]alise.*affutee.*\(\+(\d+)\s*[Nn]iv\.?\)"
        ]
        
        for pattern in balise_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                try:
                    value = int(match.group(1))
                    if 0 <= value <= 1000:
                        # Message 'Balise affûtée' détecté
                        return value
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def detect_lance_sort_balise(self, line: str) -> bool:
        """
        Détecte si la ligne contient "lance le sort Balise"
        
        Args:
            line: Ligne de log à analyser
            
        Returns:
            True si le message est détecté
        """
        lance_sort_patterns = [
            r"lance\s+le\s+sort\s+Balise",
            r"lance\s+le\s+sort\s+balise",  # Minuscule aussi
            r"Lance\s+le\s+sort\s+Balise",  # Majuscule au début
            r"lançe\s+le\s+sort\s+Balise",  # Avec accent
            r"lançe\s+le\s+sort\s+balise"   # Avec accent et minuscule
        ]
        
        for pattern in lance_sort_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                # Message 'lance le sort Balise' détecté
                return True
        
        return False
    
    def detect_se_rapproche(self, line: str) -> Optional[int]:
        """
        Détecte si la ligne contient "X se rapproche de Y case(s)" et extrait le nombre de cases
        
        Format attendu: "XXX se rapproche de Y case(s)" où Y est 1, 2 ou 3
        
        Args:
            line: Ligne de log à analyser
            
        Returns:
            Nombre de cases (1, 2 ou 3) si détecté, None sinon
        """
        # Pattern pour "X se rapproche de Y case(s)"
        pattern = r"se\s+rapproche\s+de\s+(\d+)\s+case(?:\(s\)|s)?"
        match = re.search(pattern, line, re.IGNORECASE)
        if match:
            try:
                cases = int(match.group(1))
                if 1 <= cases <= 3:
                    return cases
            except (ValueError, IndexError):
                pass
        return None
    
    def detect_tour_suivant(self, line: str) -> bool:
        """
        Détecte si la ligne contient "X seconde(s) reportée(s) pour le tour suivant"
        
        Format attendu: "X seconde(s) reportée(s) pour le tour suivant"
        où X est un nombre et (s) est optionnel
        
        Args:
            line: Ligne de log à analyser
            
        Returns:
            True si le message est détecté
        """
        # Pattern principal qui gère toutes les variantes :
        # - "X seconde(s) reportée(s) pour le tour suivant" (avec (s) optionnel)
        # - "X seconde reportée pour le tour suivant" (sans (s))
        # - "X secondes reportées pour le tour suivant" (avec s)
        # Le pattern capture le nombre et gère les variantes avec/sans (s)
        tour_suivant_pattern = r"\d+\s+seconde(?:\(s\)|s)?\s+reportée(?:\(s\)|s)?\s+pour\s+le\s+tour\s+suivant"
        
        if re.search(tour_suivant_pattern, line, re.IGNORECASE):
            return True
        
        return False
    
    def detect_lance_sort(self, line: str) -> Optional[str]:
        """
        Détecte si le message contient 'lance le sort' et extrait le nom du sort
        
        Format attendu: "[Information (combat)] XXX lance le sort Épée de Iop"
        
        Args:
            line: Ligne du log à analyser
            
        Returns:
            Nom du sort si détecté, None sinon
        """
        # On évite "lance le sort Balise" qui est déjà géré séparément
        if "lance le sort Balise" in line.lower():
            return None
        
        # Pattern pour "XXX lance le sort ZZZZ" où ZZZZ peut contenir plusieurs mots
        # On capture tout ce qui suit "lance le sort" jusqu'à la fin de la ligne
        pattern = r"lance\s+le\s+sort\s+(.+?)(?:\s*$|\s*\[|$)"
        match = re.search(pattern, line, re.IGNORECASE)
        if match:
            sort_name = match.group(1).strip()
            # Nettoyer le nom (enlever les caractères de fin de ligne, espaces, etc.)
            sort_name = sort_name.rstrip('.,;:!?\n\r\t ')
            # Supprimer tout ce qui est entre parenthèses (ex: "Super Iop Punch (Critiques)" -> "Super Iop Punch")
            sort_name = re.sub(r'\s*\([^)]*\)\s*', '', sort_name)
            # Nettoyer à nouveau les espaces en trop
            sort_name = sort_name.strip()
            # Si le nom est vide après nettoyage, retourner None
            if not sort_name:
                return None
            return sort_name
        return None
    
    def _is_duplicate_line(self, line: str) -> bool:
        """
        Vérifie si une ligne a déjà été traitée récemment (déduplication)
        
        Args:
            line: Ligne de log à vérifier
            
        Returns:
            True si la ligne est un doublon récent, False sinon
        """
        # Nettoyer le cache des entrées trop anciennes
        current_time = time.time()
        self.processed_lines_cache = {
            line_hash: timestamp 
            for line_hash, timestamp in self.processed_lines_cache.items()
            if current_time - timestamp < self.dedup_window
        }
        
        # Créer un hash de la ligne (sans le timestamp qui peut varier)
        # On enlève le timestamp au début de la ligne pour comparer uniquement le contenu
        # Format typique: "HH:MM:SS,mmm - [Type] Contenu"
        # On garde seulement la partie après le timestamp
        line_content = line.strip()
        # Extraire la partie après le timestamp (après le premier " - ")
        if " - " in line_content:
            line_content = " - ".join(line_content.split(" - ")[1:])
        
        # Créer un hash simple de la ligne
        line_hash = hash(line_content)
        
        # Vérifier si cette ligne a déjà été traitée récemment
        if line_hash in self.processed_lines_cache:
            return True
        
        # Ajouter la ligne au cache
        self.processed_lines_cache[line_hash] = current_time
        return False
    
    def process_logs(self):
        """Traite les nouvelles lignes du log"""
        new_lines = self.read_new_lines()
        
        # Filtrer les lignes dupliquées
        filtered_lines = []
        for line in new_lines:
            if not self._is_duplicate_line(line):
                filtered_lines.append(line)
        
        new_lines = filtered_lines
        
        changes = []
        combat_ended = False
        
        # Si on a un Charge en attente, chercher le message de rapprochement dans les nouvelles lignes
        if self.pending_charge:
            self.pending_charge["lines_since"] += len(new_lines)
            charge_detected = False
            
            for line in new_lines:
                cases = self.detect_se_rapproche(line)
                if cases is not None:
                    # On a trouvé le message de rapprochement
                    # Déterminer le coût : cases + 1 PA
                    # 1 case = 2 PA, 2 cases = 3 PA, 3 cases = 4 PA
                    pa_cost = cases + 1
                    sort_cost = {"PA": pa_cost}
                    
                    changes.append({
                        "type": "lance_sort",
                        "class": "iop",
                        "sort_name": self.pending_charge["sort_name"],
                        "sort_cost": sort_cost,
                        "message": f"Sort lancé: {self.pending_charge['sort_name']} (coût: {sort_cost})"
                    })
                    
                    # Réinitialiser l'état en attente
                    self.pending_charge = None
                    charge_detected = True
                    break
            
            # Si on n'a pas trouvé le message après 3 lignes, traiter comme 1 PA
            if not charge_detected and self.pending_charge and self.pending_charge["lines_since"] >= 3:
                sort_cost = {"PA": 1}
                changes.append({
                    "type": "lance_sort",
                    "class": "iop",
                    "sort_name": self.pending_charge["sort_name"],
                    "sort_cost": sort_cost,
                    "message": f"Sort lancé: {self.pending_charge['sort_name']} (coût: {sort_cost}, pas de rapprochement détecté)"
                })
                self.pending_charge = None
        
        # Index pour suivre où on en est dans les nouvelles lignes (pour chercher le message après Charge)
        line_index = 0
        for line in new_lines:
            line_index += 1
            # Vérifier si c'est la fin d'un combat
            if self.detect_combat_end(line):
                combat_ended = True
                # Réinitialiser tous les états
                self.reset_states()
                # Combat terminé - Réinitialisation des compteurs
            
            # Vérifier si c'est le message "X seconde(s) reportée(s) pour le tour suivant"
            if self.detect_tour_suivant(line):
                changes.append({
                    "type": "tour_suivant",
                    "message": "Tour suivant détecté - Réinitialisation des combos"
                })
                # Tour suivant détecté
            
            # Vérifier si c'est le message Parti pris (réduire Affûtage de 100 si > 100)
            if self.detect_partipris(line):
                if "cra" in self.states and "Affûtage" in self.states["cra"]:
                    current_affutage = self.states["cra"]["Affûtage"]
                    if current_affutage > 100:
                        old_value = current_affutage
                        new_value = current_affutage - 100
                        self.states["cra"]["Affûtage"] = new_value
                        changes.append({
                            "type": "partipris",
                            "class": "cra",
                            "state": "Affûtage",
                            "old_value": old_value,
                            "new_value": new_value,
                            "message": "Parti pris activé - Affûtage réduit de 100"
                        })
                        # Parti pris activé - Affûtage réduit
            
            # Vérifier si c'est le message "La Pointe affûtée est prête !"
            if self.detect_pointe_affutee(line):
                changes.append({
                    "type": "pointe_affutee",
                    "class": "cra",
                    "message": "La Pointe affûtée est prête !"
                })
                # La Pointe affûtée est prête
            
            # Vérifier si c'est le message "Consomme Pointe affûtée"
            if self.detect_consomme_pointe_affutee(line):
                changes.append({
                    "type": "consomme_pointe_affutee",
                    "class": "cra",
                    "message": "Consomme Pointe affûtée"
                })
                # Consomme Pointe affûtée détecté
            
            # Vérifier si c'est le message "Balise affûtée (+X Niv.)"
            balise_value = self.detect_balise_affutee(line)
            if balise_value is not None:
                changes.append({
                    "type": "balise_affutee",
                    "class": "cra",
                    "value": balise_value,
                    "message": f"Balise affûtée: {balise_value}"
                })
                # Balise affûtée détectée
            
            # Vérifier si c'est le message "lance le sort Balise ..."
            if self.detect_lance_sort_balise(line):
                changes.append({
                    "type": "lance_sort_balise",
                    "class": "cra",
                    "message": "Lance le sort Balise"
                })
                # Lance le sort Balise détecté
            
            # Détecter les sorts lancés (pour les combos Iop)
            sort_name = self.detect_lance_sort(line)
            if sort_name:
                # Cas spécial : le sort "Charge" nécessite d'attendre le message de rapprochement
                if sort_name.lower() == "charge":
                    # Extraire le nom du personnage qui lance le sort
                    character_match = re.search(r"(\S+)\s+lance\s+le\s+sort\s+Charge", line, re.IGNORECASE)
                    character = character_match.group(1) if character_match else "Unknown"
                    
                    # Mettre en attente le sort Charge
                    self.pending_charge = {
                        "sort_name": sort_name,
                        "character": character,
                        "lines_since": 0
                    }
                    
                    # Chercher immédiatement le message de rapprochement dans les lignes suivantes du même batch
                    charge_detected = False
                    remaining_lines = new_lines[line_index:]  # Lignes après la ligne actuelle
                    for remaining_line in remaining_lines:
                        cases = self.detect_se_rapproche(remaining_line)
                        if cases is not None:
                            # On a trouvé le message de rapprochement
                            # Déterminer le coût : cases + 1 PA
                            pa_cost = cases + 1
                            sort_cost = {"PA": pa_cost}
                            
                            changes.append({
                                "type": "lance_sort",
                                "class": "iop",
                                "sort_name": sort_name,
                                "sort_cost": sort_cost,
                                "message": f"Sort lancé: {sort_name} (coût: {sort_cost})"
                            })
                            
                            # Réinitialiser l'état en attente
                            self.pending_charge = None
                            charge_detected = True
                            break
                    
                    # Si on n'a pas trouvé dans les lignes suivantes, on attendra le prochain batch
                    if not charge_detected:
                        # Ne pas traiter immédiatement, attendre le message de rapprochement
                        continue
                    else:
                        # On a trouvé le message, continuer avec les autres lignes
                        continue
                
                # Vérifier si c'est un sort Iop de deux façons :
                # 1. Le nom du sort contient "Iop" (ex: "Épée de Iop")
                # 2. Le sort est dans la base de données des sorts Iop
                is_iop_sort = False
                
                # Vérifier si le nom contient "Iop"
                if "iop" in sort_name.lower():
                    is_iop_sort = True
                # Sinon, vérifier si le sort est dans la base de données Iop
                elif self.combo_tracker:
                    sort_cost = self.combo_tracker.get_sort_cost(sort_name)
                    if sort_cost is not None:
                        is_iop_sort = True
                
                if is_iop_sort:
                    # Récupérer le coût du sort depuis combo_tracker si disponible
                    sort_cost = None
                    if self.combo_tracker:
                        sort_cost = self.combo_tracker.get_sort_cost(sort_name)
                    
                    changes.append({
                        "type": "lance_sort",
                        "class": "iop",
                        "sort_name": sort_name,
                        "sort_cost": sort_cost,  # Coût en PA/PM/PW
                        "message": f"Sort lancé: {sort_name}" + (f" (coût: {sort_cost})" if sort_cost else "")
                    })
                    # Sort Iop détecté avec coût
            
            # Détecter les changements d'états
            change = self.detect_state_change(line)
            if change:
                changes.append(change)
        
        # Si le combat s'est terminé, ajouter un changement spécial
        if combat_ended:
            changes.append({
                "type": "combat_end",
                "message": "Combat terminé"
            })
        
        return changes
    
    def get_states(self, class_name: Optional[str] = None) -> Dict:
        """
        Retourne les états actuels
        
        Args:
            class_name: Nom de la classe ('iop' ou 'cra'). Si None, retourne tous les états.
        """
        if class_name:
            return self.states.get(class_name, {}).copy()
        return {k: v.copy() for k, v in self.states.items()}
    
    def reset_states(self, class_name: Optional[str] = None, state_name: Optional[str] = None):
        """
        Réinitialise les états
        
        Args:
            class_name: Nom de la classe ('iop' ou 'cra'). Si None, réinitialise toutes les classes.
            state_name: Nom de l'état spécifique à réinitialiser. Si None, réinitialise tous les états de la classe.
        """
        if class_name:
            if class_name in self.states:
                if state_name:
                    # Réinitialiser un état spécifique
                    if state_name in self.states[class_name]:
                        self.states[class_name][state_name] = 0
                else:
                    # Réinitialiser tous les états de la classe
                    for state in self.states[class_name]:
                        self.states[class_name][state] = 0
        else:
            # Réinitialiser tous les états de toutes les classes
            for class_states in self.states.values():
                for state in class_states:
                    class_states[state] = 0
        # Réinitialiser aussi le sort Charge en attente
        self.pending_charge = None
    
    def set_log_path(self, path: str):
        """Définit un nouveau chemin de log et réinitialise la position"""
        if os.path.exists(path):
            self.log_path = path
            self.file_position = 0
            return True
        return False

