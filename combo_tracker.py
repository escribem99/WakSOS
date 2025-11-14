"""
Module pour tracker les combos Iop
"""
import json
import os
from typing import Dict, List, Optional, Tuple


class ComboTracker:
    """Tracker pour suivre les combos Iop en cours"""
    
    def __init__(self, combos_file: str = "iop_combos.json"):
        """
        Initialise le tracker de combos
        
        Args:
            combos_file: Chemin vers le fichier JSON contenant les sorts et combos
        """
        self.combos_file = combos_file
        self.sorts = {}  # {nom_sort: {cout: {PA: X, PM: Y, PW: Z}, icone: "..."}}
        self.combos = {}  # {combo_id: {nom: "...", sequence: [...]}}
        self.load_combos()
        
        # État des combos en cours (peut y avoir plusieurs combos actifs simultanément)
        self.active_combo_ids = []  # Liste des IDs de combos actifs (ex: ["combo_1", "combo_3"])
        self.combo_progress = {}  # {combo_id: [liste des sorts utilisés]} pour chaque combo actif
        self.used_sorts = []  # Liste de tous les sorts utilisés depuis le début du combo
        
        # Dernier sort d'un combo terminé (pour servir de base au prochain combo)
        self.last_completed_sort_cost = None  # Coût du dernier sort d'un combo terminé
        self.last_completed_sort_name = None  # Nom du dernier sort d'un combo terminé
    
    def load_combos(self):
        """Charge les combos depuis le fichier JSON"""
        if not os.path.exists(self.combos_file):
            # Fichier introuvable, utilisation des valeurs par défaut
            self._create_default_combos()
            return
        
        try:
            with open(self.combos_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.sorts = data.get("sorts", {})
                self.combos = data.get("combos", {})
                # Sorts et combos chargés
        except Exception as e:
            # Erreur lors du chargement du fichier
            self._create_default_combos()
    
    def _create_default_combos(self):
        """Crée les combos par défaut si le fichier n'existe pas"""
        self.combos = {
            "combo_1": {
                "nom": "Vol de Vie",
                "sequence": [
                    {"PM": 1},
                    {"PA": 3},
                    {"PA": 3}
                ]
            },
            "combo_2": {
                "nom": "Poussée",
                "sequence": [
                    {"PA": 1},
                    {"PA": 1},
                    {"PA": 2}
                ]
            },
            "combo_3": {
                "nom": "Préparation",
                "sequence": [
                    {"PM": 1},
                    {"PM": 1},
                    {"PW": 1}
                ]
            },
            "combo_4": {
                "nom": "Dommages +",
                "sequence": [
                    {"PA": 2},
                    {"PA": 1},
                    {"PM": 1}
                ]
            },
            "combo_5": {
                "nom": "Combo PA",
                "sequence": [
                    {"PW": 1},
                    {"PA": 3},
                    {"PW": 1},
                    {"PA": 1}
                ]
            }
        }
    
    def get_sort_cost(self, sort_name: str) -> Optional[Dict[str, int]]:
        """
        Récupère le coût d'un sort depuis la base de données
        
        Args:
            sort_name: Nom du sort
            
        Returns:
            Dictionnaire avec les coûts (ex: {"PA": 2, "PM": 1}) ou None si non trouvé
        """
        sort_info = self.sorts.get(sort_name)
        if sort_info:
            return sort_info.get("cout", {})
        return None
    
    def get_sort_icon(self, sort_name: str) -> Optional[str]:
        """
        Récupère l'icône d'un sort depuis la base de données
        
        Args:
            sort_name: Nom du sort
            
        Returns:
            Nom du fichier icône ou None si non trouvé
        """
        sort_info = self.sorts.get(sort_name)
        if sort_info:
            return sort_info.get("icone")
        return None
    
    def _costs_match(self, cost1: Dict[str, int], cost2: Dict[str, int]) -> bool:
        """
        Vérifie si deux coûts correspondent
        
        Args:
            cost1: Premier coût (ex: {"PA": 2})
            cost2: Deuxième coût (ex: {"PA": 2})
            
        Returns:
            True si les coûts correspondent
        """
        return cost1 == cost2
    
    def _get_possible_combos(self, first_cost: Dict[str, int]) -> List[str]:
        """
        Retourne la liste des IDs de combos qui commencent par ce coût
        
        Args:
            first_cost: Coût du premier sort
            
        Returns:
            Liste des IDs de combos possibles
        """
        possible = []
        for combo_id, combo_data in self.combos.items():
            sequence = combo_data.get("sequence", [])
            if sequence and self._costs_match(sequence[0], first_cost):
                possible.append(combo_id)
        return possible
    
    def process_sort(self, sort_name: str, sort_cost: Optional[Dict[str, int]] = None) -> Dict:
        """
        Traite un sort lancé et met à jour l'état des combos
        
        Args:
            sort_name: Nom du sort lancé
            sort_cost: Coût du sort (optionnel, utilisé si fourni, sinon cherché dans la base de données)
            
        Returns:
            Dictionnaire avec les informations de mise à jour du combo
        """
        # Utiliser le coût fourni en paramètre, sinon chercher dans la base de données
        if sort_cost is None:
            sort_cost = self.get_sort_cost(sort_name)
        
        if not sort_cost:
            # Sort non trouvé dans la base de données
            return {
                "type": "sort_unknown",
                "message": f"Sort '{sort_name}' non trouvé dans la base de données"
            }
        
        # Si aucun combo n'est actif, vérifier d'abord si on peut continuer avec le dernier sort terminé
        if not self.active_combo_ids:
            # Si on a un dernier sort d'un combo terminé, traiter le nouveau sort comme la deuxième étape
            if self.last_completed_sort_cost:
                # Chercher les combos qui commencent par le coût du dernier sort terminé
                possible_combos_from_last = self._get_possible_combos(self.last_completed_sort_cost)
                
                if possible_combos_from_last:
                    # Le nouveau sort correspond à un combo qui commence par le dernier sort terminé
                    # On démarre le nouveau combo avec le dernier sort comme première étape
                    self.active_combo_ids = possible_combos_from_last.copy()
                    self.combo_progress = {combo_id: [self.last_completed_sort_name] for combo_id in possible_combos_from_last}
                    self.used_sorts = [self.last_completed_sort_name]
                    
                    # Maintenant, traiter le nouveau sort comme la deuxième étape du combo
                    valid_combos = []
                    completed_combos = []
                    
                    for combo_id in self.active_combo_ids.copy():
                        combo_data = self.combos[combo_id]
                        sequence = combo_data.get("sequence", [])
                        
                        # On est déjà à l'étape 1 (le dernier sort terminé), donc on cherche l'étape 2
                        current_step = 1  # On est à l'étape 1 (index 1 dans la séquence)
                        
                        if current_step >= len(sequence):
                            # Ce combo est terminé (cas improbable mais possible)
                            completed_combos.append(combo_id)
                            continue
                        
                        # Vérifier si le sort correspond à l'étape suivante (étape 2)
                        expected_cost = sequence[current_step]
                        if self._costs_match(sort_cost, expected_cost):
                            # Le sort correspond, mettre à jour la progression
                            self.combo_progress[combo_id].append(sort_name)
                            
                            # Vérifier si le combo est terminé après ce sort
                            if current_step + 1 >= len(sequence):
                                completed_combos.append(combo_id)
                            else:
                                valid_combos.append(combo_id)
                        else:
                            # Le sort ne correspond pas, ce combo est invalide
                            pass
                    
                    # Mettre à jour la liste des combos actifs
                    self.active_combo_ids = valid_combos
                    self.used_sorts.append(sort_name)
                    
                    # Réinitialiser le dernier sort terminé puisqu'on a commencé un nouveau combo
                    self.last_completed_sort_cost = None
                    self.last_completed_sort_name = None
                    
                    # Si un combo est terminé
                    if completed_combos:
                        primary_combo_id = completed_combos[0]
                        combo_data = self.combos[primary_combo_id]
                        self.last_completed_sort_cost = sort_cost
                        self.last_completed_sort_name = sort_name
                        
                        # Trouver les combos possibles pour le prochain combo
                        possible_next_combos = self._get_possible_combos(sort_cost)
                        all_combo_ids = list(self.combos.keys())
                        hidden_combos = [cid for cid in all_combo_ids if cid not in possible_next_combos]
                        
                        return {
                            "type": "combo_completed",
                            "combo_id": primary_combo_id,
                            "combo_name": combo_data["nom"],
                            "sort_name": sort_name,
                            "sort_cost": sort_cost,
                            "next_combo_base": sort_cost,
                            "possible_next_combos": possible_next_combos,
                            "hidden_combos": hidden_combos
                        }
                    
                    # Si aucun combo n'est valide, vérifier si le nouveau sort peut démarrer un nouveau combo
                    if not valid_combos:
                        # Réinitialiser le dernier sort terminé puisqu'on ne peut pas continuer
                        self.last_completed_sort_cost = None
                        self.last_completed_sort_name = None
                        
                        # Vérifier si le nouveau sort peut démarrer un nouveau combo
                        possible_combos = self._get_possible_combos(sort_cost)
                        if possible_combos:
                            # Le nouveau sort peut démarrer un nouveau combo
                            self.active_combo_ids = possible_combos.copy()
                            self.combo_progress = {combo_id: [sort_name] for combo_id in possible_combos}
                            self.used_sorts = [sort_name]
                            
                            primary_combo_id = possible_combos[0]
                            return {
                                "type": "combo_started",
                                "combo_id": primary_combo_id,
                                "combo_name": self.combos[primary_combo_id]["nom"],
                                "sort_name": sort_name,
                                "sort_cost": sort_cost,
                                "possible_combos": possible_combos,
                                "active_combos": possible_combos,
                                "hidden_combos": [cid for cid in self.combos.keys() if cid not in possible_combos]
                            }
                        else:
                            # Aucun combo possible, reset complet et réafficher tous les combos
                            self.reset_combo()
                            return {
                                "type": "combo_broken",
                                "message": f"Combo cassé: le sort '{sort_name}' (coût: {sort_cost}) ne correspond à aucune étape attendue"
                            }
                    
                    # Sinon, le combo progresse normalement
                    primary_combo_id = valid_combos[0]
                    combo_data = self.combos[primary_combo_id]
                    sequence = combo_data.get("sequence", [])
                    primary_current_step = len(self.combo_progress.get(primary_combo_id, []))
                    
                    return {
                        "type": "combo_progress",
                        "combo_id": primary_combo_id,
                        "combo_name": combo_data["nom"],
                        "sort_name": sort_name,
                        "sort_cost": sort_cost,
                        "step": primary_current_step,
                        "total_steps": len(sequence),
                        "active_combos": valid_combos
                    }
            
            # Si pas de dernier sort terminé, ou si le nouveau sort ne correspond pas,
            # chercher les combos possibles qui commencent par ce nouveau sort
            possible_combos = self._get_possible_combos(sort_cost)
            if possible_combos:
                # Initialiser tous les combos possibles
                self.active_combo_ids = possible_combos.copy()
                self.combo_progress = {combo_id: [sort_name] for combo_id in possible_combos}
                self.used_sorts = [sort_name]
                
                # Réinitialiser le dernier sort terminé puisqu'on démarre un nouveau combo
                self.last_completed_sort_cost = None
                self.last_completed_sort_name = None
                
                # Retourner le premier combo pour l'affichage (mais tous sont actifs)
                primary_combo_id = possible_combos[0]
                return {
                    "type": "combo_started",
                    "combo_id": primary_combo_id,
                    "combo_name": self.combos[primary_combo_id]["nom"],
                    "sort_name": sort_name,
                    "sort_cost": sort_cost,
                    "possible_combos": possible_combos,
                    "active_combos": possible_combos,  # Tous les combos actifs
                    "hidden_combos": [cid for cid in self.combos.keys() if cid not in possible_combos]
                }
            else:
                # Aucun combo ne commence par ce coût
                # Réinitialiser le dernier sort terminé aussi
                self.reset_combo()
                return {
                    "type": "no_combo",
                    "message": f"Aucun combo ne commence par ce coût: {sort_cost}"
                }
        
        # Des combos sont actifs, vérifier si le sort correspond à l'étape suivante de chacun
        valid_combos = []  # Combos qui correspondent encore
        completed_combos = []  # Combos qui sont terminés
        
        for combo_id in self.active_combo_ids.copy():
            combo_data = self.combos[combo_id]
            sequence = combo_data.get("sequence", [])
            
            # Obtenir l'étape actuelle pour ce combo spécifique
            current_step = len(self.combo_progress.get(combo_id, []))
            
            # Vérifier si on a dépassé la séquence
            if current_step >= len(sequence):
                # Ce combo est terminé
                completed_combos.append(combo_id)
                continue
            
            # Vérifier si le sort correspond à l'étape suivante
            expected_cost = sequence[current_step]
            if self._costs_match(sort_cost, expected_cost):
                # Le sort correspond, mettre à jour la progression
                if combo_id not in self.combo_progress:
                    self.combo_progress[combo_id] = []
                self.combo_progress[combo_id].append(sort_name)
                
                # Vérifier si le combo est terminé après ce sort
                if current_step + 1 >= len(sequence):
                    completed_combos.append(combo_id)
                else:
                    valid_combos.append(combo_id)
            else:
                # Le sort ne correspond pas, ce combo est invalide
                # On le retire silencieusement (pas d'erreur, juste on ne le suit plus)
                pass
        
        # Mettre à jour la liste des combos actifs
        self.active_combo_ids = valid_combos
        self.used_sorts.append(sort_name)
        
        # Si un combo est terminé, garder le dernier sort en mémoire et afficher les combos possibles
        if completed_combos:
            primary_combo_id = completed_combos[0]
            combo_data = self.combos[primary_combo_id]
            
            # Trouver tous les combos qui commencent par ce dernier sort
            possible_next_combos = self._get_possible_combos(sort_cost)
            
            # Si aucun combo ne commence par ce dernier sort, réafficher tous les combos possibles
            if not possible_next_combos:
                # Réinitialiser le dernier sort puisqu'il ne sert à rien
                self.last_completed_sort_cost = None
                self.last_completed_sort_name = None
                
                # Retourner un reset pour réafficher tous les combos
                return {
                    "type": "combo_completed_no_next",
                    "combo_id": primary_combo_id,
                    "combo_name": combo_data["nom"],
                    "sort_name": sort_name,
                    "sort_cost": sort_cost,
                    "message": "Aucun combo ne commence par ce sort, réaffichage de tous les combos"
                }
            
            # Sinon, garder en mémoire le dernier sort pour servir de base au prochain combo
            self.last_completed_sort_cost = sort_cost
            self.last_completed_sort_name = sort_name
            
            all_combo_ids = list(self.combos.keys())
            hidden_combos = [cid for cid in all_combo_ids if cid not in possible_next_combos]
            
            # Ne pas reset, mais préparer l'affichage des combos possibles
            # Les combos actifs restent vides pour l'instant, mais on garde le dernier sort
            return {
                "type": "combo_completed",
                "combo_id": primary_combo_id,
                "combo_name": combo_data["nom"],
                "sort_name": sort_name,
                "sort_cost": sort_cost,
                "next_combo_base": sort_cost,  # Indique que ce sort peut servir de base au prochain combo
                "possible_next_combos": possible_next_combos,  # Combos qui commencent par ce sort
                "hidden_combos": hidden_combos  # Combos à cacher
            }
        
        # Si aucun combo n'est valide, c'est une erreur
        if not valid_combos:
            self.reset_combo()
            return {
                "type": "combo_broken",
                "message": f"Combo cassé: le sort '{sort_name}' (coût: {sort_cost}) ne correspond à aucune étape attendue"
            }
        
        # Sinon, le combo progresse (on retourne le premier combo actif pour l'affichage)
        primary_combo_id = valid_combos[0]
        combo_data = self.combos[primary_combo_id]
        sequence = combo_data.get("sequence", [])
        # Obtenir l'étape actuelle du combo primaire après l'ajout du sort
        primary_current_step = len(self.combo_progress.get(primary_combo_id, []))
        
        return {
            "type": "combo_progress",
            "combo_id": primary_combo_id,
            "combo_name": combo_data["nom"],
            "sort_name": sort_name,
            "sort_cost": sort_cost,
            "step": primary_current_step,  # Étape actuelle (1-indexed pour l'affichage)
            "total_steps": len(sequence),
            "active_combos": valid_combos  # Tous les combos encore actifs
        }
    
    def reset_combo(self):
        """Réinitialise les combos en cours"""
        self.active_combo_ids = []
        self.combo_progress = {}
        self.used_sorts = []
        self.last_completed_sort_cost = None
        self.last_completed_sort_name = None
    
    def get_combo_state(self) -> Dict:
        """
        Retourne l'état actuel des combos
        
        Returns:
            Dictionnaire avec l'état des combos
        """
        return {
            "active_combo_ids": self.active_combo_ids.copy(),
            "combo_progress": {k: v.copy() for k, v in self.combo_progress.items()},
            "used_sorts": self.used_sorts.copy(),
            "all_combos": {k: v.copy() for k, v in self.combos.items()}
        }

