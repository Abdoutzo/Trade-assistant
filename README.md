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

Tous ces paramètres (enveloppe, montants, part ETF/actions, horizon) se changent à tout moment
sur le site, dans *Réglages > Mon profil d'investissement*.

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

## Données (brique 1)

| Source | Ce qu'on en tire | Fiabilité |
|---|---|---|
| [filings.xbrl.org](https://filings.xbrl.org) | Comptes annuels officiels des sociétés cotées dans l'UE (format ESEF, depuis 2020) | Référence : chiffres audités |
| Yahoo Finance | Cours quotidiens sur 10 ans, comptes standardisés des 4 derniers exercices, ISIN vers ticker | API non officielle, recoupée avec les rapports |
| [GLEIF](https://www.gleif.org) | Entité légale derrière un ISIN, pays du siège social (règle du PEA) | Registre officiel |
| Euronext | ISIN vers ticker quand Yahoo ne connaît pas l'ISIN | Officiel |

Pour chaque année, l'outil prend le chiffre du rapport officiel quand il existe, sinon celui de
Yahoo, et signale un écart de plus de 3 % entre les deux (souvent un retraitement). Le bénéfice
par action vient d'une seule source par entreprise, pour éviter les faux sauts dus aux actions
gratuites ou aux divisions d'actions.

**Univers de départ** : 8 ETF éligibles PEA (MSCI World, S&P 500, Nasdaq-100, Europe, émergents)
et 35 grandes entreprises européennes, chaque ISIN vérifié. Sur le site : *Univers et analyses >
Charger l'univers de départ*. N'importe quel autre ISIN s'ajoute depuis la même page.

**Sans terminal** : onglet *Actions > Tester les données > Run workflow*, saisis un ISIN.

En ligne de commande : `uv run python -m trade_assistant.data seed | add ISIN | refresh | show ISIN`.

## Analyse (brique 2)

Chaque entreprise reçoit une note sur 100, décomposée en cinq piliers :

| Pilier | Poids | Mesures |
|---|---|---|
| Qualité | 30 % | ROIC, ROE, marge opérationnelle, marge de cash, conversion du bénéfice en cash (moyennes sur 3 ans) |
| Solidité | 20 % | dette nette / EBITDA, couverture des intérêts, liquidité, fonds propres / bilan |
| Croissance | 20 % | ventes sur 5 ans et sur 2 ans, bénéfice par action, régularité |
| Valorisation | 20 % | PER, PER face à son historique, rendement du cash, VE / résultat d'exploitation, dividende |
| Risque | 10 % | volatilité, pire baisse sur 5 ans, bêta face au MSCI Europe |

Chaque mesure vaut 0 à un seuil « mauvais » et 100 à un seuil « bon » : les seuils et leur
justification sont écrits dans [`analysis/scoring.py`](trade_assistant/analysis/scoring.py) et
affichés sur le site. Règles de rigueur : un ratio ne mélange jamais deux sources (donc jamais IFRS
et US GAAP) ; une série dans le temps n'est prolongée par l'autre source que si les deux
concordent ; pas de note sans au moins trois piliers mesurés ; banques et assurances jugées sans
les ratios industriels qui n'ont pas de sens pour elles.

Sur le site : *Classement* (tri par note ou par pilier, filtre par secteur) et la carte *Analyse*
de chaque fiche. En ligne de commande : `uv run python -m trade_assistant.data rank`.

## Portefeuille (brique 3)

- **Positions** calculées à partir de tes transactions Trade Republic (saisies sur le site), au
  coût moyen, valorisées en euros au dernier cours.
- **Plans du mois** : Trade Republic ne facture pas les plans d'investissement programmés (un
  ordre manuel coûte 1 €). L'outil propose donc un montant fixe par ligne : le cœur ETF, puis
  autant d'actions que le budget le permet (10 € minimum par plan), les plus en retard sur leur
  cible d'abord. Une action au-delà de 10 % du portefeuille n'est plus renforcée. Le
  rééquilibrage se fait par les nouveaux versements, sans vendre.
- **Sélection** : tes actions, celles que tu épingles, puis les meilleures notes (60/100 minimum,
  2 par secteur au plus). Tu peux exclure n'importe quelle action.
- **Simulation** : les mêmes règles rejouées mois par mois sur 5 à 15 ans, comparées à 100 % ETF
  monde, puis une fourchette de résultats à ton horizon (tirage de blocs de 12 mois du passé), en
  version historique et en version prudente ramenée à 7 %/an. Biais rétrospectif signalé : les
  actions sont choisies avec ce que l'on sait aujourd'hui.

## Veille (brique 4)

- **Collecte** gratuite : Google Actualités (français et anglais) et flux Yahoo Finance, pour
  chaque action de l'univers, chaque soir de semaine (workflow *Actualiser les données*) ou à la
  demande sur le site.
- **Tri par l'IA** (modèle rapide) : catégorie, ton, importance pour un actionnaire de long terme,
  résumé d'une ligne en français. Réponse JSON validée ; si aucun modèle ne répond, des règles par
  mots-clés prennent le relais (signalé « tri par mots-clés »).
- **Alertes** : nouvelle majeure, nouvelle notable et négative (prévisions, justice, dirigeants...),
  variation de cours de 5 % ou plus sur tes valeurs. Bandeau sur le tableau de bord.
- **Synthèse par entreprise** (modèle de raisonnement) : faits marquants et points à surveiller,
  chaque phrase liée aux articles numérotés qui l'appuient ; une phrase sans source valide est
  supprimée avant affichage.
- **Sans terminal** : onglet *Actions > Tester la veille > Run workflow*.

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
4. *Univers et analyses > Charger l'univers de départ*.
5. Pour que les cours se mettent à jour chaque soir même quand le site dort : ajoute la même
   chaîne Neon en secret GitHub `DATABASE_URL` (*Settings > Secrets and variables > Actions*).
   Le workflow *Actualiser les données* tourne alors les soirs de semaine à 18h17 UTC.

Sur l'offre gratuite, le site s'endort après 15 minutes sans visite et se réveille en environ une
minute. Les traitements lourds (collecte, analyse, e-mail mensuel) tournent dans GitHub Actions,
pas sur le site. L'image Docker fonctionne aussi chez n'importe quel autre hébergeur.

## Feuille de route

| # | Brique | État |
|---|---|---|
| 0 | Socle : API, site, connexion, routeur de LLM, base de données, CI, déploiement | fait |
| 1 | Données : cours sur 10 ans, comptes annuels (rapports officiels ESEF + Yahoo), univers PEA | fait |
| 2 | Analyse fondamentale : ratios, risque, score /100 expliqué, classement | fait |
| 3 | Portefeuille : positions, plans programmés du mois, simulation sur 10 ans et projection | fait |
| 4 | Veille : actualités triées par l'IA, alertes, synthèse sourcée par entreprise | fait |
| 5 | Agent : analyste, avocat du diable, gérant, plan mensuel validé par toi | à venir |
| 6 | Guide de l'investisseur : parcours, glossaire, leçon liée à chaque décision | à venir |
| 7 | Rapport mensuel par e-mail, lancé par GitHub Actions | à venir |
| 8 | Journal : chaque recommandation comparée à l'ETF monde dans la durée | à venir |
