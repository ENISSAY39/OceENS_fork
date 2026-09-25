# OcéEns II

Course-evaluation platform built for the EPF engineering school.

## Overview

**OcéEns II** lets program managers, facilitators, campus managers and
administrators create and run evaluation *sondages* (surveys) for EPF's
programs, and lets students answer them. Answers can be exported, visualised,
and summarised by an LLM (*synthèses*). The interface uses EPF's official
visual identity.

The application itself is in French. This documentation is in English and keeps
the product's French vocabulary where the application uses it; `CONTEXT.md`
says where that boundary is.

### Tech stack

| Component | Technology |
|-----------|------------|
| **Framework** | FastAPI (Python 3.12, set in `.python-version`) |
| **Packaging** | [uv](https://docs.astral.sh/uv/): `pyproject.toml`, `uv.lock`, one `oceens` package under `src/` |
| **Authentication** | Microsoft Entra ID (Azure AD) via OAuth 2.0 / MSAL and Microsoft Graph; a development sign-in for local work |
| **Database** | SQLite (SQLAlchemy + SQLModel) |
| **Templating** | Jinja2 (server-side rendering) |
| **Frontend** | HTML / CSS / JavaScript, no framework |
| **Server** | Uvicorn |
| **Logging** | Python's standard `logging` module, through Uvicorn's handlers |
| **Exports** | pandas (CSV) |
| **Summaries** | A separate daemon calling an LLM (`requests-cache`, `markdown-it-py`) |

---

## Getting started

A fresh clone runs locally in development mode with **no Entra credentials and
no LLM key**.

1. **Clone the repository and create `.env` from the example.** The
   application and `docker-compose.yaml` both read `.env`, and
   `.env.example` ships `AUTH_MODE=dev`: the [development
   sign-in](#development-sign-in) replaces Entra ID, so the `ENTRA_*`
   variables stay commented out.

   ```bash
   git clone https://github.com/EPF-MDE/OceENS.git
   cd OceENS
   cp .env.example .env            # Windows (PowerShell): Copy-Item .env.example .env
   ```

2. **Start the application**, either with Uvicorn or with Docker Compose.

   **With uv** ([install uv](https://docs.astral.sh/uv/getting-started/installation/)
   first). `uv sync` creates `.venv` from `uv.lock` with the Python version in
   `.python-version`, downloading it if needed; `uv run` runs a command in that
   environment, so there is nothing to activate. The commands are the same on
   Windows, macOS and Linux:

   ```bash
   uv sync
   uv run uvicorn oceens.main:app --port 8000
   ```

   `uv run oceens` does the same on every interface (`0.0.0.0:8000`), as in
   production. Nothing depends on the working directory: templates, static
   files and seed data are read from the package, and the database stays in
   `database/` at the repository root.

   **With Docker Compose** (needs a running Docker daemon):

   ```bash
   docker compose up --build
   ```

   Without a `.env` file, `docker compose` stops with `env file .env not
   found`: step 1 is not optional. The image runs Uvicorn without `--reload`;
   rebuild it to pick up code changes. Stop and clean up with
   `docker compose down`.

3. **Open <http://localhost:8000>** and sign in from `/dev/login`, which lists
   the seeded users by role.

On first start the application creates the SQLite database and inserts a
demonstration data set (see [Database](#database)).

Without an LLM key everything works except *synthèses*: requesting one marks it
as a configuration error instead of calling the provider. See
[LLM summaries](#llm-summaries) to enable them.

To check that a clone starts as it should, or before proposing a change, follow
the [smoke test](docs/smoke-test.md).

---

## Configuration

Every setting is an environment variable, read from `.env` at startup
(`python-dotenv` locally, `env_file` with Docker Compose). `.env.example` is the
template: copy it, then change what you need. Nothing else in this README
restates these rules.

### Authentication settings

| Variable | Meaning |
|----------|---------|
| `AUTH_MODE` | `entra` (default when unset) or `dev`, case- and whitespace-insensitive. Any other value stops the application at startup with exit code 1. `.env.example` ships `dev` so a fork starts without credentials; a deployment must leave it unset or set it to `entra`. |
| `DEV_LOGIN_KEY` | `dev` only, optional. When set, every development sign-in must provide it (`key` field) or gets `401`; when empty, the sign-in is open to anyone who reaches the server. Ignored, with a warning, under `entra`. |
| `SECRET_KEY` | Signs the session cookies. See [below](#secret_key). |
| `ALLOWED_DOMAINS` | Comma-separated e-mail domains allowed to sign in, with Entra ID or with the development sign-in (`403` otherwise). When unset: `epf.fr,epfedu.fr` under `dev`, and **no domain at all** under `entra`, so nobody can sign in. Adding a user by e-mail from the admin dashboard checks the same variable, with `epf.fr,epfedu.fr` as its default in both modes. |
| `ENTRA_CLIENT_ID`, `ENTRA_CLIENT_SECRET`, `ENTRA_TENANT_ID` | Microsoft Entra ID application. Required under `entra`: if any of the three is missing, the application stops at startup with exit code 1. Not read under `dev`. |
| `REDIRECT_URI` | Entra ID callback URL, `https://<host>/auth/callback`. Defaults to `https://localhost/auth/callback`. Not used under `dev`. |

#### `SECRET_KEY`

Anyone who knows `SECRET_KEY` can forge a session cookie, including an admin's.

- Under `entra` it is **required**: if it is missing or empty, the application
  logs a critical error and stops at startup with exit code 1.
- Under `dev` it is optional: when empty, a random key is drawn at each start
  (with a warning), so sessions do not survive a restart. A *known* key
  (shared, copied from an example) lets anyone forge a cookie and bypass
  `DEV_LOGIN_KEY`, which `dev` accepts because it is meant for local use only.

Generate one with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Database settings

| Variable | Meaning |
|----------|---------|
| `LOCAL_DATABASE_DIR` | Folder holding the SQLite file `db_oceens.db`. Defaults to `database/` at the repository root; a relative path is resolved from the repository root. The folder is created if needed. |

With Docker Compose, `LOCAL_DATABASE_DIR` selects the host folder
(`./database` when empty), mounted at `/app/database`; inside the container the
application always uses `/app/database`.

### LLM settings

| Variable | Meaning |
|----------|---------|
| `LLM_API_KEY` | API key of the default provider, Ollama EPF. When empty, the application starts normally and every requested summary is marked as a configuration error. Other providers read their key from their own variable, see [LLM providers](#llm-providers). |
| `RUN_SUMMARIES_DAEMON` | `1`, `true`, `yes` or `on`: Uvicorn starts the summaries daemon as a child process and stops it on shutdown. Leave it empty when something else runs the daemon, such as `launch.sh` in production. |

> [!CAUTION]
> Never commit `.env`. It is listed in `.gitignore`, like `*.db` files
> (`database/db_oceens.db`, `cache_llm.db`).

---

## Roles

- `student`: answers the *sondages* they are enrolled in. A user with no role
  row is a student.
- `program_manager:<code>`: manages the *sondages* of their program(s).
- `facilitator:<code>`: runs the *sondages* of their program(s).
- `campus_manager:<campus>`: campus-wide scope.
- `admin`: global administration.

A user can hold several roles, each with its own scope (program codes or
campuses separated by `;`).

---

## Pages and routes

### Pages

| Route | Description |
|-------|-------------|
| `/` | Home and sign-in hub; redirects a signed-in user to their dashboard. |
| `/login`, `/auth/callback`, `/logout` | Microsoft Entra ID sign-in flow. Under `dev`, `/login` redirects to `/dev/login` and `/auth/callback` does not exist. |
| `/dev/login` | Development sign-in: user picker on `GET`, sign-in on `POST`. Only under `AUTH_MODE=dev`. |
| `/dashboard/student` | Student dashboard. |
| `/dashboard/program-manager` | Program-manager dashboard. |
| `/dashboard/facilitator` | Facilitator dashboard. |
| `/dashboard/campus-manager` | Campus-manager dashboard. |
| `/dashboard/teachers/analytics` | Satisfaction score per teacher, filterable by school year, semester and program. `campus_manager` and `program_manager`, each within their scope. |
| `/dashboard/admin` | Admin dashboard. |
| `/dashboard/survey-create` | Create and configure a *sondage*. |
| `/api/surveys/{survey_id}` | The questionnaire (answering a *sondage*). |
| `/api/surveys/{survey_id}/visualisation` | Answers visualisation. Accepts `?teacher=<name>` to open already filtered on a teacher. |
| `/backend/prompts`, `/backend/prompts/new`, `/backend/prompts/{id}/edit` | LLM prompts: list, create, edit. Admin only. |
| `/backend/templates` | *Sondage* templates. |
| `/backend/providers` | LLM providers. Admin only. |
| `/backend/llm/prices` | Price grid. Admin only. |
| `/backend/llm/costs` | Cost of the *synthèses*. Admin only. |

Any other path that returns `404` is redirected to `/`.

### API

| Route | Description |
|-------|-------------|
| `POST /api/surveys`, `POST /api/surveys/{id}` | Create a *sondage*; submit answers. |
| `POST /api/surveys/{id}/status` | Open (`1`) or close (`0`) a *sondage*. |
| `DELETE /api/surveys/{id}`, `POST /api/surveys/{id}/delete` | Delete a *sondage*. |
| `GET`, `POST`, `DELETE /api/surveys/{id}/students` | Students enrolled in a *sondage*. |
| `GET /api/surveys/{id}/export` | CSV export of the answers. |
| `GET /api/surveys/{id}/cost` | Cost of the *synthèses* of one *sondage*. |
| `POST /api/surveys/{id}/generate-summaries` | Queue the *synthèses* of a closed *sondage*. |
| `POST /api/surveys/{id}/destroy-summaries` | Delete them and set the *sondage* back to closed. |
| `POST /api/users`, `PUT /api/users/{user_id}/role` | Add a user by e-mail; change a user's roles. |
| `POST`, `PUT`, `DELETE /api/sections…`, `/api/questions…` | Edit sections and questions. |
| `POST /api/templates`, `PUT`, `DELETE /api/templates/{id}`, `…/toggle-active`, `…/duplicate` | Edit *sondage* templates. |
| `POST /api/prompts`, `PUT`, `DELETE /api/prompts/{id}` | Create, edit and delete prompts. Editing or deleting a prompt that a *synthèse* references is refused (`409`). |

---

## Database

The database is a single SQLite file, `db_oceens.db`, in the folder set by
[`LOCAL_DATABASE_DIR`](#database-settings) (`database/` by default, ignored by Git).
Tables are created at startup if they do not exist.

At every start, the application also synchronises the program list from
`src/oceens/import/Program_list.csv`, and inserts the default LLM provider, the USD → EUR
rate and the known model prices when they are missing; values edited in the
administration are kept.

The demonstration data set (users, roles, templates, *sondages*, answers, the
default prompt) is inserted **only when the database has no user**. To start
over from the demonstration data, stop the application and delete
`db_oceens.db`.

To try each role's screens with the [development sign-in](#development-sign-in),
the data set has a user holding that role and no other:

| Role | User |
|------|------|
| `admin` | `arnaud.jousset@epf.fr` |
| `program_manager:MDAI5` | `oceens.program-manager@epf.fr` |
| `facilitator:MDAI5` | `oceens.facilitator@epf.fr` |
| `campus_manager:Montpellier` | `oceens.campus-manager@epf.fr` |
| `student` (no role row) | `bob.leponge@epfedu.fr` |

The seeded *sondages* are all open, and the campus-manager dashboard lists only
closed ones: until a Montpellier *sondage* is closed, the campus manager sees
its data in `/dashboard/teachers/analytics`.

---

## LLM summaries

*Synthèses* are produced by a daemon, `oceens-summaries-daemon`
(`summaries_generator_daemon.py`), separate from the web application. The two only communicate through the `summaries`
table, used as a queue:

1. From a closed *sondage*, a manager requests the *synthèses*
   (`generate-summaries`). The application inserts one row per open question
   that has answers (per module and teacher in module sections) with
   `http_status = 0`, and marks the *sondage* as "generation in progress".
2. The daemon processes the rows one at a time and writes back the result:
   `200` is done (the summary is stored as HTML), any other value is a failure
   kept for diagnosis, with a readable message in `metadata_text`.

The daemon loops, writes to the database and calls an external service. Run it
only when needed, either by hand:

```bash
uv run oceens-summaries-daemon
```

or alongside Uvicorn with [`RUN_SUMMARIES_DAEMON`](#llm-settings). In
production without Docker, `launch.sh` runs the application and the daemon in
separate `screen` sessions.

The daemon reads `.env` when it starts: restart it after changing a key.

### LLM providers

The provider is **configured from the interface** (`/backend/providers`, admin
only), with no code change. The default provider is **Ollama EPF**
(`https://locallm.mde.epf.fr/ollama`, model `gemma4:26b`), created
automatically at startup. Students get their own key from
<https://locallm.mde.epf.fr> with their EPF account and put it in
`LLM_API_KEY`.

| `api_type` | Covers |
|------------|--------|
| `ollama` | Ollama servers (local, EPF, third-party) |
| `openai` | OpenAI **and any OpenAI-compatible endpoint**: vLLM, Groq, Mistral, LM Studio… |
| `anthropic` | Claude API (Anthropic) |

#### No key in the database

The SQLite database is not encrypted and ends up in backups, so **no API key is
stored in it**. The `llm_providers` table only holds the *name* of the
environment variable (`api_key_env`, e.g. `OPENAI_API_KEY`); the value stays in
`.env` and is resolved at call time. The name must match `LLM_*` or
`*_API_KEY`, and system secrets (`SECRET_KEY`, `ENTRA_CLIENT_SECRET`…) are
refused explicitly.

#### Adding a provider

1. **Add the key to `.env`** under a conforming name (`LLM_*` or `*_API_KEY`):

   ```env
   OPENAI_API_KEY=sk-...
   ```

2. **Restart the daemon** so it reads the new variable.

3. **Create the provider** in `/backend/providers` → *+ Nouveau fournisseur*:
   name, API type, base URL, variable name (`OPENAI_API_KEY`) and default
   model. The **"clé présente / absente"** indicator confirms the variable is
   loaded. The **Tester** button checks that the URL and key answer, then sends
   a one-token generation to confirm the account can actually generate (see
   below).

4. **Attach a prompt** to the provider: in `/backend/prompts`, a `<select>`
   sets a prompt's provider. A prompt with no provider (`provider_id` NULL)
   falls back to Ollama EPF.

> [!NOTE]
> A provider referenced by at least one prompt cannot be deleted.

#### Exhausted credit and other provider errors

Each provider reports failures in its own format: exhausted credit is a
`429 insufficient_quota` at OpenAI but a `400 "Your credit balance is too
low"` at Anthropic. `services/llm_client.py` normalises these answers into
categories (`quota`, `rate_limit`, `auth`, `model`, `server`) and writes a
readable message to `Summary.metadata_text` instead of the raw JSON, so a
failed *synthèse* explains itself in the interface. The provider's raw answer
stays in the daemon's logs.

> [!IMPORTANT]
> Listing models is not enough to test a key: at OpenAI as at Anthropic,
> `GET /v1/models` still answers normally with a zero balance. The **Tester**
> button therefore also sends a one-token generation, the only way to detect
> exhausted credit **before** starting a batch of *synthèses*.

---

## Cost of the summaries

The cost of each *synthèse* is **measured, not estimated**. At generation time
the daemon records the token counters returned by the provider
(`Summary.input_tokens`, `output_tokens`, `model_used`): it is the only chance
to capture them, no API returns them afterwards. The amount is then computed
by crossing these counters with the price grid.

All amounts are **in euros**, and every total is a **range** (min, max).

### Price grid: `/backend/llm/prices`

Prices live in the database (`llm_model_prices`) and are editable from the
administration, so a price change or a locally added provider needs no
release. A price has two parts, which add up:

- a **flat cost per generation**, as a range, for models whose cost is not
  measured in tokens;
- a **price per million tokens**, input and output, for providers that bill by
  consumption. Providers publish it in dollars; it is converted to euros when
  saved, at the USD → EUR rate stored in the administration (0.92 by default).

Seeded at startup, without ever overwriting a price edited by hand:

| Model | Flat cost per generation | Input / output per million tokens |
| --- | ---: | ---: |
| `gemma4:26b` (Ollama EPF, self-hosted) | €0.02 – €0.05 | — |
| `claude-opus-5` | — | $5.00 / $25.00, converted |
| `claude-sonnet-5` | — | $3.00 / $15.00, converted |
| `claude-haiku-4-5` | — | $1.00 / $5.00, converted |

Self-hosted is not free: GPU, electricity and server depreciation come to 2 to 5
cents per *synthèse*. Prices for other providers (OpenAI, Mistral, Groq…) are
**entered by hand**, never guessed. A price specific to a provider wins over a
generic price for the same model name.

### Where to see costs

| Where | What |
| --- | --- |
| `/backend/llm/costs` | Global cost, per *sondage* and per model (admin) |
| 💰 button on a *sondage* row | Cost of that *sondage*'s *synthèses* |

### What is not priced

A *synthèse* cannot be priced when its counters are missing (generated before
this feature, or a provider that does not expose them) or when its model has no
price. It is then **counted separately**, never estimated or set to zero: a
made-up amount would be displayed with the authority of a real one. Screens say
explicitly when a total is partial.

> [!IMPORTANT]
> Tracking starts when the feature is deployed: *synthèses* generated before
> have no counters and cannot be priced retroactively.

---

## Authentication

### Microsoft Entra ID (OAuth 2.0)

Under `AUTH_MODE=entra`, sign-in goes through **Microsoft Entra ID** with MSAL:

```
1. The user clicks "Se connecter"
   → FastAPI generates a random state (UUID, CSRF protection)
   → Redirect to Microsoft's sign-in page

2. The user authenticates with Microsoft
   → Microsoft redirects to /auth/callback with a code and the state

3. The server exchanges the code for an access token
   → User details are read from Microsoft Graph
   → Roles and their scopes are read from the database
   → The session {name, email, roles} is created
   → Redirect to the matching dashboard

4. On sign-out (/logout)
   → The session and cookies are cleared
   → The user is signed out at Microsoft
   → Back to the home page
```

Authentication alone allows nothing: every route then checks the role and the
scope (program or campus) with `require_roles()` and its helpers.

### Development sign-in

To work on a fork without an Azure application, `AUTH_MODE=dev` enables a
**development sign-in**: you pick a user's e-mail address and are signed in as
them, with no proof of identity. It must **never** be used in production. Its
settings are `DEV_LOGIN_KEY`, `SECRET_KEY` and `ALLOWED_DOMAINS`, described in
[Configuration](#authentication-settings).

Under `dev`, the session cookie is no longer restricted to HTTPS
(`http://localhost` works), `/login` redirects to `/dev/login`,
`/auth/callback` does not exist, and `/logout` clears the session and returns
to `/`. A warning is logged at startup. A red banner that cannot be dismissed
shows on every page that includes the shared header: it recalls the signed-in
address, offers "Changer d'utilisateur" (`/dev/login`), and says "accès ouvert
à tous" when `DEV_LOGIN_KEY` is not set.

In a browser, `GET /dev/login` lists the users in the database, grouped by role
name without scope (a user with no role is listed under `student`, a user with
several roles under each). A click signs in as that user; a free field accepts
any other address, with an optional name. When `DEV_LOGIN_KEY` is set, a
single key field is shown and used for every sign-in on the page; the key is
never stored in the session. Come back to this page to switch users.

`POST /dev/login` takes a form with `email`, an optional `name`, and `key` when
`DEV_LOGIN_KEY` is set. The user is fetched or created as after an Entra
callback: an unknown address becomes a new student. Without `name`, the
display name is built from the address (`bob.leponge@epfedu.fr` → "Bob
Leponge"). A new sign-in replaces the session.

```bash
# Sign in as the seeded admin; -c stores the session cookie
curl -i -c cookies.txt \
  -d email=antoine.gademer@epf.fr -d key=my-key \
  http://localhost:8000/dev/login

# Reuse the cookie (-b) for the next requests
curl -b cookies.txt -c cookies.txt -L http://localhost:8000/
```

Drop `-d key=…` when `DEV_LOGIN_KEY` is empty.

---

## Logging

Application logs use Python's standard `logging` module and the `uvicorn`
logger, so messages from the application, `core/auth.py` and `core/seed.py`
share the server's format, colours and handlers.

| Level | Use |
|-------|-----|
| `DEBUG` | Detail useful in development and during seeding. |
| `INFO` | Startup, shutdown and normal operations. |
| `WARNING` | An expected resource is missing, or a non-blocking situation. |
| `ERROR` / `EXCEPTION` | An operation failed; `logger.exception()` keeps the traceback. |
| `CRITICAL` | Required configuration is missing and prevents startup. |

```python
import logging

logger = logging.getLogger("uvicorn")

logger.info("Operation done")

try:
    risky_operation()
except Exception:
    logger.exception("Operation failed")
```

Use the logger rather than `print()` for new diagnostics. The application level
is set to `DEBUG` in `core/dependencies.py`. Logs go through Uvicorn's handler,
usually to `stderr`; redirect it separately, e.g. `2> error.log`, to keep them.

---

## Project structure

All the code lives in one package, `oceens`, under `src/`. Paths such as
`core/auth.py` elsewhere in this README are relative to `src/oceens/`.

```
OceENS/
├── pyproject.toml                    # Package, dependencies, entry points
├── uv.lock                           # Locked dependency versions
├── .python-version                   # Python version (3.12)
├── Dockerfile, docker-compose.yaml, .dockerignore
├── launch.sh                         # Production launcher, without Docker (screen)
├── .env.example                      # Configuration template, copied to .env (not committed)
│
├── src/oceens/
│   ├── __main__.py                   # `oceens` entry point: serves the app with Uvicorn
│   ├── main.py                       # FastAPI factory, middlewares, router assembly
│   ├── summaries_generator_daemon.py # Summaries daemon; `oceens-summaries-daemon` entry point
│   ├── sondage_loader.py             # Loads a complete sondage for export
│   ├── survey_loader_from_xlsx.py    # Imports sondages from an Excel file
│   │
│   ├── core/                         # Low-level access and security
│   │   ├── auth.py                   #   Entra ID sign-in and development sign-in
│   │   ├── database.py               #   SQLite engine and the SessionDep dependency
│   │   ├── security.py               #   Roles, scopes, access control
│   │   ├── dependencies.py           #   Shared Jinja templates and logger
│   │   └── seed.py                   #   Initial data and program synchronisation
│   ├── models/                       # SQLModel schema, one file per table
│   ├── routers/                      # Routes, split by business domain
│   │   └── llm/                      #   LLM administration: providers, prices, costs
│   ├── services/                     # Business logic: aggregations, CSV export, LLM client and costs
│   │
│   ├── templates/                    # Jinja2 templates: dashboard/, backend/, template_parts/
│   ├── static/                       # css/, js/, img/
│   └── import/                       # Seed data: program list, demonstration answers
│
├── database/                         # SQLite database (not committed)
├── docs/                             # Smoke test, ADRs, agent docs
└── llm-utils/                        # LLM tools outside the application
```

---

## Notable features

### Teacher analytics

`/dashboard/teachers/analytics` (`campus_manager`, `program_manager`) aggregates
the satisfaction score per `(teacher, sondage)` from `QCU_Satisfaction` answers
that carry an `Answer.teacher` (module sections). Teachers are sorted with
`teacher_sort_key()`, case- and accent-insensitive, and the list can be filtered
by school year, semester, program and teacher.

### Teacher filter in the visualisation

A client-side selector filters the visualisation without reloading: only the
chosen teacher's modules stay visible, and the Campus and Program sections are
hidden. The page reads `?teacher=<name>` on load to start filtered; links from
the analytics pass it, so a click on a teacher's score opens their view.

### *Sondages* imported from Excel

`uv run python -m oceens.survey_loader_from_xlsx SYLLABUS_FILE FORMS_FILE
PROGRAM SEMESTER SCHOOL_YEAR` loads a *sondage* from two Excel files.
*Sondages* loaded this way have no `QCU_Attendance`
question: `services/visualisation_data.py` then uses
`satisfaction_responses_count` as the fallback denominator for the teacher
score. Teacher names are normalised with `.title()` on import and on
aggregation, to merge case variants (`"GADEMER Antoine"` and `"Gademer
Antoine"` are one entry). Questions are sorted by `question_id` in the
template, so charts come before verbatims whatever the insertion order.

### Campus-manager scope

The `campus_manager` dashboard only shows closed *sondages* with at least one
respondent. The questionnaire link and QR code are hidden there
(`can_view_survey_link=False`): this role reads results without distributing
*sondages*.

### Orphan students cleanup

When a *sondage* is deleted, students no longer attached to **any other**
*sondage* are deleted too (`services/helpers.py`, `_delete_orphan_students`).
Users with a privileged role (`admin`, `program_manager`, `facilitator`,
`campus_manager`) are never deleted this way.

### Adding a user by e-mail

The "Utilisateurs" tab of the admin dashboard has a **"+ Ajouter un
utilisateur"** button: an e-mail address is enough to create the account, as a
student (`POST /api/users`, admin only). The address is validated (format and
[allowed domain](#authentication-settings)) and duplicates are refused.

---

## Deployment checklist

- [ ] `.env` holds the real Entra ID credentials and a dedicated
      [`SECRET_KEY`](#secret_key)
- [ ] `AUTH_MODE` unset or `entra`
- [ ] `ALLOWED_DOMAINS` set: under `entra` its default allows nobody
- [ ] A valid TLS certificate (Let's Encrypt or equivalent); the session
      cookie is HTTPS-only outside `dev`
- [ ] The database is present (`database/db_oceens.db`) or its Docker volume
      mounted
- [ ] Secrets, including `LLM_API_KEY`, kept out of the repository and the image
- [ ] **Docker Compose**: `.env` loaded through `env_file`, never copied into
      the image
- [ ] The summaries daemon running if *synthèses* are used

---

## Before contributing

There is no automated test suite or CI yet. Before proposing a change that
touches startup, configuration, dependencies or the container, run the
[smoke test](docs/smoke-test.md); then test the routes your change touches by
hand, on a throwaway SQLite database (never a copy of production), with the
relevant roles and *sondage* statuses.

---

## Resources

- [FastAPI](https://fastapi.tiangolo.com/)
- [FastAPI and Uvicorn logging guide](https://apitally.io/blog/fastapi-logging-guide)
- [MSAL Python](https://github.com/AzureAD/microsoft-authentication-library-for-python)
- [Microsoft Graph](https://learn.microsoft.com/en-us/graph/)
- [Jinja2](https://jinja.palletsprojects.com/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [SQLModel](https://sqlmodel.tiangolo.com/)
- [pandas](https://pandas.pydata.org/)

---

**OcéEns team** — EPF
