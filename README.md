# 🏛️ HATVP Explorer

Interface web pour explorer le répertoire des représentants d'intérêts (lobbyistes) de la HATVP.

## Fonctionnalités

- **Recherche par objet d'activité** : full-text dans ~95 000 descriptions libres d'actions de lobbying
- **Recherche par secteur** : dans les 31 catégories prédéfinies (Energie, Santé, Numérique…)
- Affichage interactif des résultats + export CSV
- Smart matching : gestion des accents, casse, variantes

---

## 🚀 Déploiement sur Render (gratuit)

### Étape 1 — Préparer GitHub

1. Créez un compte sur [github.com](https://github.com) si ce n'est pas fait
2. Créez un **nouveau repository** (ex: `hatvp-explorer`)
3. Uploadez ces 3 fichiers dans le repo :
   - `app.py`
   - `requirements.txt`
   - `render.yaml`

```
# Si vous avez Git installé :
git init
git add app.py requirements.txt render.yaml
git commit -m "Initial commit"
git remote add origin https://github.com/VOTRE_NOM/hatvp-explorer.git
git push -u origin main
```

### Étape 2 — Déployer sur Render

1. Créez un compte sur [render.com](https://render.com)
2. Cliquez **"New +"** → **"Web Service"**
3. Connectez votre compte GitHub et sélectionnez le repo `hatvp-explorer`
4. Render détecte automatiquement le `render.yaml` — cliquez **"Deploy"**
5. Attendez 2-3 minutes ⏳
6. Votre app est disponible sur `https://hatvp-explorer.onrender.com` (URL personnalisable)

### Étape 3 — Partager l'URL

Envoyez simplement l'URL à vos collègues. Pas d'installation nécessaire de leur côté.

---

## ⚠️ Plan gratuit Render

- L'app **s'endort après 15 min** d'inactivité
- Au réveil, la première personne attend **~30-60 secondes**
- Les données HATVP sont **mises en cache 12h** (pas de re-téléchargement à chaque visite)

Pour supprimer le délai de réveil : plan **Starter à 7$/mois** sur Render.

---

## 💻 Lancer en local (Windows)

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Lancer l'app
streamlit run app.py

# L'app s'ouvre automatiquement sur http://localhost:8501
```

---

## 📁 Structure du projet

```
hatvp-explorer/
├── app.py              # Application Streamlit
├── requirements.txt    # Dépendances Python
├── render.yaml         # Config déploiement Render
└── README.md           # Ce fichier
```

---

## 🔗 Sources des données

- Données : [data.gouv.fr — HATVP vues séparées](https://www.data.gouv.fr/datasets/repertoire-des-representants-dinterets-fichiers-en-vues-separees)
- Répertoire officiel : [hatvp.fr/le-repertoire](https://www.hatvp.fr/le-repertoire/)
- Licence : Licence Ouverte Etalab 2.0
