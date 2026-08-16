# Audit du projet

## Vue d'ensemble

Un script Python unique (`galaxy_library_export.py`, 647 lignes) qui lit directement la base SQLite locale de GOG Galaxy 2.0 (`galaxy-2.0.db`) et exporte la bibliothèque (jeux + métadonnées) en CSV. Un petit script utilitaire (`print_gameDB.py`) transforme ensuite ce CSV en liste numérotée texte.

## Points forts

- **Architecture requête dynamique bien pensée** : la fonction `prepare()` construit dynamiquement une vue SQL (`CREATE TEMP VIEW`) en n'assemblant que les jointures correspondant aux options demandées — évite de charger des données inutiles.
- **Modèle GOG bien compris** : GOG Galaxy stocke tout sous forme de paires clé/valeur JSON (`GamePieces`/`GamePieceTypes`), un modèle EAV assez opaque. Le script maîtrise bien ce schéma (titres, ratings, métadonnées, DLC, tags, compat OS...).
- **Gestion des cas limites du monde réel** : `titleExclusion` filtre des entrées parasites connues (`dlc_123a`, objets cosmétiques Witcher 3 mal classés...), et `settings.json` permet de corriger manuellement les erreurs de classification jeu/DLC de GOG lui-même — signe d'un projet mûri par l'usage réel, pas juste théorique.
- **Portabilité Windows/macOS** via détection de `platform`.
- **CLI cohérente** générée automatiquement (wrapper `Arguments` autour d'`argparse`).

## Points faibles / dette technique

1. **`except:` nus multiples** (lignes 82, 159, 433, 443, 451) — avalent silencieusement *toute* exception, y compris des bugs réels (`KeyError`, `TypeError`...), pas seulement les cas attendus (absence de champ). Rend le débogage difficile.
2. **Requêtes SQL par concaténation de chaînes** (`.format()` un peu partout, ex. lignes 94, 200-202, 214...). Ici le risque d'injection est faible car les valeurs viennent d'un dictionnaire interne fixe (`platforms`) et non d'une entrée utilisateur — mais ce n'est pas une habitude à reproduire si le code évolue vers des entrées externes.
3. **`includeField()` a un vrai bug latent** ligne 158 : `objectFieldName` est référencé mais n'existe nulle part dans le scope — si `Type.LIST` est utilisé sur un champ avec une seule valeur (`len(s) == 1`), ça lève un `NameError`... immédiatement masqué par le `except:` de la ligne 159, qui retombe sur `object[fieldName]` (probablement le comportement voulu, mais accidentel).
4. **Complexité algorithmique dans la boucle DLC** (lignes 509-516) : pour chaque DLC de chaque jeu, on fait un scan linéaire (`next(x[1] for x in results ...)`) sur la liste complète des résultats → O(n×m). Sur une bibliothèque de plusieurs milliers d'entrées, ça peut ralentir sensiblement avec `--dlcs`.
5. **Style non idiomatique** : indentation par tabulations mélangée à des conventions de nommage Java-esque (`__bAll`, `ba()` cryptique), pas de type hints, pas de tests unitaires, tout dans un seul fichier de 647 lignes avec des fonctions imbriquées profondément (jusqu'à 4 niveaux).
6. **`print_gameDB.py`** est fragile : il suppose un chemin relatif `../gameDB.csv` (ne fonctionne que si on l'exécute depuis `helper_scripts/`) et parse le CSV en splittant manuellement par tabulation plutôt que d'utiliser le délimiteur que `csv.reader` a déjà géré.

## En résumé

Un script utilitaire solide et fonctionnel, clairement écrit par quelqu'un qui a itéré sur des cas réels de la base GOG (d'où les correctifs `settings.json` et `titleExclusion`), mais avec une hygiène de code perfectible : gestion d'erreurs trop permissive, un bug latent masqué, et une architecture monofichier qui rendrait toute évolution significative difficile à maintenir.
