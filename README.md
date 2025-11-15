# WakSOS - Wakfu State Overlay System

Un overlay pour suivre vos états dans Wakfu pour les classes **Iop** et **Cra**.

## Fonctionnalités

- Overlay transparent qui s'affiche par-dessus le jeu
- Suivi des états en temps réel via lecture du fichier log
- **Iop** : Concentration, Courroux, Préparation
- **Cra** : Affûtage, Précision
- Interface claire et personnalisable
- Détection automatique depuis les logs du jeu

## Installation

1. Installer Python 3.8 ou supérieur
2. Installer les dépendances (aucune dépendance externe requise, juste Python standard)
3. Trouver le fichier log de Wakfu :
```bash
python find_log.py
```

4. Si le fichier log est trouvé automatiquement, vous pouvez l'ajouter dans `config.json` :
```json
{
  "log_path": "C:\\Users\\VotreNom\\AppData\\Local\\Ankama\\Wakfu\\logs\\wakfu.log"
}
```

## Utilisation

### Lancement de l'overlay

```bash
python main.py
```

Au premier lancement (ou si le fichier log n'est pas trouvé), une fenêtre de sélection s'ouvrira automatiquement vous permettant de :

- **Parcourir** : Sélectionner manuellement le fichier log via un explorateur de fichiers
- **Détection auto** : Essayer de trouver automatiquement le fichier log
- **Valider** : Sauvegarder votre sélection
- **Annuler** : Utiliser la détection automatique par défaut

Le chemin sélectionné sera sauvegardé dans `config.json` pour les prochains lancements.

### Trouver le fichier log manuellement

Si vous préférez trouver le chemin vous-même :

```bash
python find_log.py
```

Copiez le chemin affiché et ajoutez-le dans `config.json` sous la clé `"log_path"`.

## Classes supportées

### Iop
- **Concentration** : Jauge augmentant avec l'utilisation de sorts
- **Courroux** : Augmente les dégâts du prochain sort de 4 PA
- **Préparation** : Augmente les dégâts du prochain sort

### Cra
- **Affûtage** : Augmente les dégâts des sorts de zone
- **Précision** : Augmente les chances de coups critiques

## Configuration

Les paramètres peuvent être ajustés dans `config.json` :

- `log_path` : Chemin vers le fichier log (null pour auto-détection)
- `overlay.transparency` : Transparence de l'overlay (0.0 à 1.0)
- `overlay.position` : Position initiale de l'overlay
- `overlay.always_on_top` : Garder l'overlay au-dessus des autres fenêtres

### Test du parser

Pour tester si le parser détecte correctement les états :

```bash
python test_parser.py
```

## Structure du projet

```
WakSOS/
├── main.py              # Point d'entrée principal
├── overlay.py            # Gestion de l'overlay transparent
├── log_parser.py         # Parser pour lire et analyser les logs
├── state_tracker.py      # Suivi des états en temps réel
├── log_selector.py       # Interface de sélection du fichier log
├── find_log.py           # Utilitaire pour trouver le fichier log
├── test_parser.py        # Script de test du parser
├── classes/              # Modules spécifiques par classe
│   ├── __init__.py
│   ├── iop.py
│   └── cra.py
├── config.json           # Configuration
└── requirements.txt      # Dépendances Python
```

## Notes importantes

- Le système lit directement le fichier log de Wakfu (pas besoin d'OCR)
- L'overlay est déplaçable en cliquant-glissant dessus
- Les états sont détectés automatiquement depuis les messages du chat dans les logs
- Si le fichier log n'est pas trouvé automatiquement, spécifiez le chemin dans `config.json`

## Contribution

Ce projet est open source. N'hésitez pas à contribuer ou à signaler des bugs !

