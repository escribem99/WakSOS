# Icônes pour l'overlay Iop

## Structure des fichiers

Placez vos icônes dans ce dossier (`assets/iop/`) :

### Icônes de combos
- `combo_1.png` - Icône pour le combo "Vol de Vie"
- `combo_2.png` - Icône pour le combo "Poussée"
- `combo_3.png` - Icône pour le combo "Préparation"
- `combo_4.png` - Icône pour le combo "Dommages +"
- `combo_5.png` - Icône pour le combo "Combo PA"

### Icônes de ressources
- `pa.png` - Icône pour les Points d'Action (PA)
- `pm.png` - Icône pour les Points de Mouvement (PM)
- `pw.png` - Icône pour les Points de Wakfu (PW)

### Icônes de sorts
- `{NomDuSort}.png` - Une icône pour chaque sort utilisé dans les combos
  - Le nom du fichier doit correspondre exactement au nom du sort dans `iop_combos.json`
  - Exemple : si un sort s'appelle "Épée de Feu", le fichier doit être `Épée de Feu.png`

## Format des fichiers

- Format : PNG recommandé
- Taille : Recommandé 64x64 pixels ou similaire (sera redimensionné automatiquement par Tkinter)
- Transparence : Supportée (fond transparent recommandé)

## Configuration dans iop_combos.json

Dans le fichier `iop_combos.json`, vous devez :

1. **Ajouter les sorts** dans la section `"sorts"` :
```json
{
  "sorts": {
    "NomDuSort": {
      "cout": {
        "PA": 2,
        "PM": 1
      },
      "icone": "NomDuSort.png"
    }
  }
}
```

2. **Les combos** sont déjà définis avec leurs séquences de ressources.

## Exemple complet

Si vous avez un sort "Épée de Feu" qui coûte 2 PA :
- Placez `Épée de Feu.png` dans `assets/iop/`
- Ajoutez dans `iop_combos.json` :
```json
{
  "sorts": {
    "Épée de Feu": {
      "cout": {
        "PA": 2
      },
      "icone": "Épée de Feu.png"
    }
  }
}
```





