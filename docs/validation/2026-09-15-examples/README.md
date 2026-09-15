# Preuves de l'étape 2 — 15 septembre 2026

**Jeu actuel : 200 patients synthétiques ; IDs 1, 2 et 3 conservés et noms
chiffrés. Six contrôles structurés réussis. Cinq requêtes texte/PDF et neuf
contrôles réussis.** Les deux runners retournent 0.

Runtime : MaskQL 1.6.0, commit
`b58bdb7818592334eed93f38553ece8fd372cdc4`. Le patch des exemples exécutés
porte l'empreinte SHA-256
`6ac2a694de6ce73523140a41e402bccb1baa2961b7e120ae941d7dc8c5561c4f`.

| Fichier | Contenu |
| --- | --- |
| `summary.json` | Bilan des exemples, provenance et nettoyage. |
| `structured-result.json` | Règles, requête, attendu, chiffrés obtenus, aperçu, déchiffrement et contrôles. |
| `text-report.json` | Requêtes, graine, attendus, empreintes et neuf contrôles texte/PDF. |
| `commands.json` | Commandes exactes, variables de test, horaires et codes de sortie. |
| `environment.json` | Versions exécutées, images et empreintes du plugin chargé. |
| `source.patch` | Adaptations des exemples et de leur documentation sur le commit de base. |
| `source-sha256.json` | Empreintes des 178 fichiers de la copie exécutée. |
| `evidence.zip` | 52 fichiers de preuves et un manifeste SHA-256 interne. |
| `SHA256SUMS` | Empreintes des fichiers ci-dessus. |

Dans l'archive :

- `source/` contient les données fictives, les requêtes, les règles, les
  attendus, les deux runners et leurs instructions ;
- `results/structured/` contient les 200 entrées, les attendus et le résultat ;
- `results/unstructured/` contient les cinq sorties textuelles et le rapport ;
- `logs/` contient les journaux complets des commandes et des conteneurs ;
- `provenance/` et `recording/` conservent l'environnement et l'enregistrement ;
- `image/` contient la recette de l'image Trino locale et son chargeur Python.

Les entrées sont synthétiques. Les mots de passe présents dans les commandes
sont ceux explicitement définis pour la pile de démonstration. Aucun jeton
Hugging Face, clé privée TLS, environnement virtuel ou modèle n'est archivé.
Les sorties texte illustrent ces fonctions, sans établir une précision
clinique ni un retrait exhaustif des identifiants.

## Vérifier et reproduire

```bash
shasum -a 256 -c SHA256SUMS
unzip -t evidence.zip
```

Pour retrouver les sources exactes, extraire le commit de base dans un
répertoire neuf puis y appliquer `source.patch` avec `git apply`.
Après extraction de l'archive, la recette `image/` permet de recréer le tag
local consigné dans [commands.json](commands.json) :

```bash
docker build --pull=false -t rudymerieux/maskql-trino:publication-fixes-20260915 image
docker tag \
  rudymerieux/maskql@sha256:f9bfe155961514e5386f01d71ab3ffa768bdc2a79524f69580b80eaa345a6c4e \
  rudymerieux/maskql:publication-fixes-20260915
```

L'image backend de ce digest doit être disponible localement, au besoin avec
`docker pull`. Le script de pile compile et monte les JAR du commit évalué.
Suivre ensuite les commandes de [commands.json](commands.json), en adaptant
les chemins de Python et de Java à l'installation. Les durées observées ne
sont pas un benchmark.

Les résultats des exemples sont distincts du
[run de l'étape 1](../2026-09-15-tests/README.md), conservé séparément.
