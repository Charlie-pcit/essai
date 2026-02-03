# Veille IA & Automatisation

Cette application réalise une veille quotidienne sur l'IA et l'automatisation, du lundi au vendredi. Elle collecte les articles pertinents depuis des sources (RSS), sélectionne 4 à 5 sujets, puis génère un résumé et le lien source.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Modifiez `config.json` pour ajuster les sources et les mots-clés.

## Exécution

```bash
python app.py
```

## Planification (exemple cron)

Exécuter tous les jours ouvrés à 8h00 :

```cron
0 8 * * 1-5 /path/to/venv/bin/python /path/to/essai/app.py >> /path/to/essai/veille.log 2>&1
```

## Sortie

Un fichier `veille-YYYY-MM-DD.md` est généré avec les 4-5 sujets les plus pertinents, un résumé et les liens sources.
