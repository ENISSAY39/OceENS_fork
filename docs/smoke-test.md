# Smoke test manuel

Le dépôt ne contient pas de suite de tests automatisés ni de CI (les premiers
tests sont #85, la CI #78). Cette procédure se passe entièrement **à
l'extérieur du processus** : on part d'un clone neuf, on lance l'application
et on observe ce qu'elle répond et avec quel code de sortie.

À dérouler avant de proposer un changement qui touche au démarrage, à la
configuration, aux dépendances ou au conteneur.

## Vérifications statiques

```bash
python -m compileall -q main.py \
  sondage_loader.py survey_loader_from_xlsx.py summaries_generator_daemon.py \
  core models routers services
git diff --check
```

## 1. Démarrage local, sans credentials

Dans un clone neuf de la branche, avec un environnement virtuel vide :

```bash
cp .env.example .env
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn main:app --port 8000
```

Attendu, sans aucun credential Entra ni clé LLM :

| Route | Réponse |
|---|---|
| `GET /` | 200 |
| `GET /dev/login` | 200 |
| `GET /nope` | 303 vers `/` (middleware 404 → `/`) |

Les logs de démarrage créent les tables, insèrent le jeu de démonstration et
ne contiennent ni erreur ni trace d'exception.

## 2. Démarrage avec Docker

Avec le même `.env`, sur une machine Linux :

```bash
docker compose up --build
```

Attendu : l'image se construit et `/` répond. Sans `.env`, `docker compose`
échoue avec `env file .env not found` — c'est voulu, la première commande
d'un fork est `cp .env.example .env`.

## 3. Codes de sortie sur configuration invalide

Une configuration de démarrage invalide doit sortir en **code 1**, pour qu'un
superviseur ou une CI voie l'échec :

```bash
AUTH_MODE=bogus .venv/bin/python -c "import main"; echo $?   # 1
```

```bash
# Le .env doit être écarté : load_dotenv() y relirait AUTH_MODE=dev et
# l'application démarrerait normalement (code 0).
mv .env .env.bak
env -u AUTH_MODE -u ENTRA_CLIENT_ID -u ENTRA_CLIENT_SECRET -u ENTRA_TENANT_ID \
  .venv/bin/python -c "import main"; echo $?   # 1
mv .env.bak .env
```

Attendu : la ligne de log `INVALID AUTH_MODE 'bogus'` pour la première,
`MISSING ENTRA INFO. Please check .env` pour la seconde. En témoin,
`AUTH_MODE=dev` sort en 0.

## 4. Absence de clé LLM

`.env.example` livre `LLM_API_KEY` **vide** : l'application démarre
normalement, seules les synthèses sont indisponibles. Avec le daemon
`summaries_generator_daemon.py` lancé, une demande de synthèse est marquée en
erreur de configuration (`http_status` 500, « variable d'environnement
absente ou vide ») et aucun appel n'est fait au fournisseur.

## Ensuite

Tester manuellement les routes concernées par le changement, sur une base
SQLite jetable (jamais une copie de production), avec les rôles et les
statuts de sondage pertinents.
