# Preuves de validation — 15 septembre 2026

**71 tests Python réussis, zéro échec, zéro erreur, zéro ignoré.**
`uv run tox` retourne 0. La compilation Maven utilise `-DskipTests` et
n'exécute pas de suite Java.

Le code évalué a ensuite été publié dans **MaskQL 1.6.1** : le commit
`b58bdb7818592334eed93f38553ece8fd372cdc4` est inclus dans cette release.
Les preuves conservent l'état consigné lors de l'exécution, avant cette
publication. Le patch reconstitue la copie testée depuis MaskQL 1.6.0,
commit `f7dd60ece3926378d99b90b7c02fcb6d6dde2d48`.
Empreinte SHA-256 du patch exact :
`a01c1fb7a6700786e4d49e622e74669cc9684505f799b99ea760fb058684e837`.

| Fichier | Contenu |
| --- | --- |
| `summary.json` | Résultats des 71 tests, étapes tox, chargement NLP et nettoyage. |
| `environment.json` | Versions et dépendances observées, images et empreintes du plugin chargé. |
| `commands.json` | Commandes, horaires UTC, durées, statuts et environnement explicite. |
| `source.patch` | Différence entre le commit de base et la copie exacte évaluée. |
| `source-sha256.json` | Empreintes des 176 fichiers suivis de la copie source. |
| `source-integrity.json` | Vérification d'intégrité et précision documentaire ajoutée ensuite. |
| `evidence.zip` | Journaux du run réussi, scripts, provenance et manifeste SHA-256 interne. |
| `SHA256SUMS` | Empreintes des fichiers structurés, du patch et de l'archive. |

L'archive contient les journaux complets de cette exécution de tox et de
ses conteneurs, le Dockerfile de l'image locale de validation, les scripts
d'enregistrement, la capture des threads de la pile testée, le rapport
et les éléments de provenance. Les journaux du run sont conservés tels
qu'exécutés, avec leurs avertissements. Les données et clés de test sont
synthétiques. Aucun environnement virtuel, modèle, image Docker ou clé
privée TLS n'est inclus.

Le dossier a été renommé de `2026-09-15-fixes` en `2026-09-15-tests` pour
désigner clairement la validation réussie. Les résultats, journaux,
archives et manifestes d'intégrité sont inchangés. Les chemins conservés
dans l'archive reflètent l'organisation au moment de l'exécution.
Les scripts d'enregistrement conservent également les chemins locaux
utilisés ; [commands.json](commands.json) donne les commandes à reproduire
avec les chemins adaptés à l'installation.

Pour vérifier l'intégrité depuis ce répertoire :

```bash
shasum -a 256 -c SHA256SUMS
unzip -t evidence.zip
```

Pour reconstituer la copie source, extraire le commit de base dans un
répertoire neuf, puis appliquer `source.patch` avec `git apply`. Les
empreintes permettent de vérifier cette copie. Les JAR sont recompilés
par tox et montés dans Trino ; le Dockerfile de validation réutilise
l'image de base figée avec le chargeur Python corrigé.
