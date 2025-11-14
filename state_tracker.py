"""
Module pour suivre les états en temps réel depuis les logs
"""
import time
import threading
from log_parser import WakfuLogParser
from typing import Dict, Callable, Optional


class StateTracker:
    """Suivi des états en temps réel"""
    
    def __init__(self, log_path: Optional[str] = None, update_callback: Optional[Callable] = None, combo_tracker=None):
        """
        Initialise le tracker d'états
        
        Args:
            log_path: Chemin vers le fichier log
            update_callback: Fonction appelée à chaque mise à jour des états
            combo_tracker: Instance de ComboTracker pour récupérer les coûts des sorts (optionnel)
        """
        self.parser = WakfuLogParser(log_path, combo_tracker=combo_tracker)
        self.update_callback = update_callback
        self.running = False
        self.tracking_thread = None
        self.update_interval = 0.1  # Vérifier le log toutes les 100ms
    
    def start(self):
        """Démarre le suivi des états"""
        if self.running:
            return
        
        self.running = True
        self.tracking_thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self.tracking_thread.start()
    
    def stop(self):
        """Arrête le suivi des états"""
        self.running = False
        if self.tracking_thread:
            self.tracking_thread.join(timeout=1.0)
    
    def _tracking_loop(self):
        """Boucle principale de suivi"""
        while self.running:
            try:
                # Traiter les nouvelles lignes du log
                changes = self.parser.process_logs()
                
                # Si des changements ont été détectés, appeler le callback
                if changes and self.update_callback:
                    states = self.parser.get_states()
                    current_class = self.parser.current_class
                    self.update_callback(states, current_class, changes)
                
                time.sleep(self.update_interval)
            except Exception as e:
                # Erreur dans la boucle de suivi
                time.sleep(self.update_interval)
    
    def get_current_states(self) -> Dict:
        """Retourne les états actuels"""
        return self.parser.get_states()
    
    def get_current_class(self) -> Optional[str]:
        """Retourne la classe actuellement détectée"""
        return self.parser.current_class
    
    def set_log_path(self, path: str) -> bool:
        """Définit un nouveau chemin de log"""
        return self.parser.set_log_path(path)
    
    def reset_states(self, class_name: Optional[str] = None):
        """
        Réinitialise les états manuellement
        
        Args:
            class_name: Si spécifié, réinitialise uniquement cette classe. Sinon, réinitialise toutes les classes.
        """
        self.parser.reset_states(class_name)
        # Notifier le callback pour mettre à jour l'affichage
        if self.update_callback:
            states = self.parser.get_states()
            current_class = self.parser.current_class
            message = f"Réinitialisation manuelle ({class_name})" if class_name else "Réinitialisation manuelle"
            self.update_callback(states, current_class, [{"type": "manual_reset", "message": message, "class": class_name}])

