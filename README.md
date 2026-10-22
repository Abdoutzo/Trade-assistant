# Trade Assistant

**Un assistant d'investissement personnel pour un PEA Trade Republic.** Il analyse les
entreprises à partir de leurs rapports financiers officiels et de l'actualité, propose chaque mois
quoi acheter et combien, explique pourquoi, et t'apprend à décider seul.

> Outil personnel d'aide à la décision, pas un conseil en investissement. Tout investissement en
> actions comporte un risque de perte en capital. L'outil ne passe jamais d'ordre : c'est toi qui
> exécutes dans l'application Trade Republic.

## Stratégie

| | |
|---|---|
| **Enveloppe** | PEA Trade Republic : 0 € de frais sur les plans programmés, fiscalité réduite après 5 ans (17,2 % au lieu de 30 %) |
| **Versements** | 500 € au départ, puis 100 € par mois (DCA) |
| **Cœur (70 %)** | un ETF monde éligible PEA, en plan programmé |
| **Satellites (30 %)** | 3 à 8 entreprises européennes choisies par l'agent, au maximum 10 % du portefeuille chacune |
| **Rééquilibrage** | par les nouveaux versements, sans vendre (donc sans impôt ni frais) |

## Architecture

```
GitHub Actions (cron mensuel)          Render (gratuit)                    Neon (Postgres gratuit)
  collecte données + news      ---->   FastAPI  /api/*            <---->   portefeuille, analyses,
  analyse + agent              ---->   site React (web/dist)               recommandations, journal
  e-mail du plan (Brevo)               connexion par mot de passe
```

- **`trade_assistant/`** : le serveur Python (FastAPI). Calculs financiers testés, agent, API.
- **`web/`** : le site (React, Vite, Tailwind), servi par le même serveur une fois construit.
- **Données** : SQLite sur ta machine, Postgres Neon une fois déployé (même code).

### Modèles d'IA : le meilleur du gratuit, avec relais automatique

Chaque tâche demande un **rôle** ; chaque rôle est une chaîne de modèles essayés dans l'ordre. Si
un fournisseur refuse (quota, modèle retiré du catalogue gratuit), le suivant prend le relais.

| Rôle | Usage | Chaîne par défaut |
|---|---|---|
| `reasoning` | analyse approfondie, avocat du diable, plan mensuel | NVIDIA Nemotron 3 Ultra (550B), NVIDIA GLM-5.3, Gemini Flash, Groq gpt-oss-120b |
| `long_context` | lire un rapport annuel entier (1M tokens) | Gemini Flash, NVIDIA Nemotron 3 Ultra |
| `fast` | trier les actualités, résumés courts | Groq gpt-oss-120b, NVIDIA Nemotron 3.5 Lightning, Gemini Flash-Lite |

Une seule clé suffit pour démarrer (NVIDIA). Chaque clé en plus ajoute un relais. Les chaînes se
changent dans `.env` sans toucher au code. Chaque appel est journalisé (fournisseur, latence,
tokens) pour suivre la consommation des offres gratuites.

## Mettre ses clés d'API sans terminal

Dans le dépôt GitHub : *Settings > Secrets and variables > Actions > New repository secret*, nom
`NVIDIA_API_KEY` (puis `GOOGLE_API_KEY`, `GROQ_API_KEY` si tu en as). Pour vérifier qu'elles
marchent : onglet *Actions > Vérifier les clés LLM > Run workflow*. Le résultat indique quel
modèle a répondu pour chaque rôle, sans jamais afficher de clé.

Ces secrets servent aux traitements lancés par GitHub (analyse et e-mail du mois). Pour le site
en ligne, la même clé se met aussi dans Render (voir « Déployer gratuitement »).

## Lancer en local

Prérequis : [uv](https://docs.astral.sh/uv/) et Node 22.

```bash
cp .env.example .env          # puis renseigne au moins NVIDIA_API_KEY
uv sync
uv run uvicorn trade_assistant.api:app --reload          # API sur :8000

cd web && npm install && npm run dev                      # site sur http://localhost:5173
```

Sans `APP_PASSWORD` en local, il n'y a pas de page de connexion. Pour servir le site construit
depuis Python seul : `cd web && npm run build`, puis ouvre http://localhost:8000.

Tests : `uv run pytest` et `uv run ruff check .`

## Déployer gratuitement

1. **Base de données** : crée un projet sur [Neon](https://neon.tech) (région Frankfurt) et
   copie la chaîne de connexion `postgresql://...`.
2. **Site** : sur [Render](https://render.com), *New > Blueprint*, choisis ce dépôt (le fichier
   `render.yaml` décrit tout). Renseigne `APP_PASSWORD` (long !), `DATABASE_URL` et tes clés
   d'API. `SECRET_KEY` est généré automatiquement.
3. Ouvre l'adresse `https://trade-assistant-xxxx.onrender.com` et connecte-toi.

Sur l'offre gratuite, le site s'endort après 15 minutes sans visite et se réveille en environ une
minute. Les traitements lourds (collecte, analyse, e-mail mensuel) tournent dans GitHub Actions,
pas sur le site. L'image Docker fonctionne aussi chez n'importe quel autre hébergeur.

## Feuille de route

| # | Brique | État |
|---|---|---|
| 0 | Socle : API, site, connexion, routeur de LLM, base de données, CI, déploiement | fait |
| 1 | Données : cours, fondamentaux sur 10 ans (rapports ESEF et SEC), univers PEA | à venir |
| 2 | Analyse fondamentale : qualité, valorisation, risque, score expliqué | à venir |
| 3 | Portefeuille et backtest : allocation cœur/satellites, simulation historique | à venir |
| 4 | Veille : actualités et publications, résumés sourcés, alertes | à venir |
| 5 | Agent : analyste, avocat du diable, gérant, plan mensuel validé par toi | à venir |
| 6 | Guide de l'investisseur : parcours, glossaire, leçon liée à chaque décision | à venir |
| 7 | Rapport mensuel par e-mail, lancé par GitHub Actions | à venir |
| 8 | Journal : chaque recommandation comparée à l'ETF monde dans la durée | à venir |
