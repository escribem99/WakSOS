# Dossier Assets

Ce dossier contient les ressources graphiques (icônes, images) utilisées par WakSOS.

## Icône de Précision

Pour afficher une icône quand la Précision dépasse 200, placez votre fichier ici avec le nom exact :

**`precision_icon.png`**

### Spécifications recommandées :
- Format : PNG (avec transparence si possible)
- Taille recommandée : 32x32 pixels à 64x64 pixels
- Le fichier sera automatiquement chargé et affiché dans l'overlay Cra quand Précision > 200

## Icône de Pointe affûtée

Pour afficher une icône quand "La Pointe affûtée est prête !", placez votre fichier ici avec le nom exact :

**`pointe_affutee_icon.png`**

### Spécifications recommandées :
- Format : PNG (avec transparence si possible)
- Taille recommandée : 32x32 pixels à 64x64 pixels
- Le fichier sera automatiquement chargé et affiché dans l'overlay Cra quand le message est détecté

### Emplacement des fichiers :
```
WakSOS/
└── assets/
    ├── precision_icon.png        ← Icône Précision > 200
    └── pointe_affutee_icon.png   ← Icône Pointe affûtée
```

Les icônes seront affichées automatiquement dans l'overlay Cra selon les conditions :
- **precision_icon.png** : Affichée quand Précision > 200
- **pointe_affutee_icon.png** : Affichée quand "La Pointe affûtée est prête !" est détecté dans les logs

