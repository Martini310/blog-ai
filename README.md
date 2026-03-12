# README (wersja: przewodnik po kodzie, nie marketing)

Ten dokument jest napisany "dla Ciebie", żebyś mógł wejść w projekt jak junior i rozumieć:
- co robi każdy folder i plik,
- jak idzie przepływ danych przez system,
- które elementy od czego zależą,
- gdzie są miejsca niedokończone (`TODO`) i co to oznacza.

## 1. Co to za system

To backend SaaS do automatyzacji contentu SEO:
- API (FastAPI) przyjmuje żądania użytkownika.
- Serwisy (`app/services`) robią logikę biznesową.
- Taski (`app/tasks`) wykonują ciężkie operacje asynchronicznie w Celery.
- Dane są w PostgreSQL (SQLAlchemy async).
- Kolejka i broker zadań to Redis.
- Logi i monitoring: structlog (JSON), Sentry, Flower.

Najważniejsza zasada architektury w tym repo:
- route = cienka warstwa HTTP,
- service = logika biznesowa,
- task = orkiestracja tła + retry + logi.

## 2. Jak przepływa żądanie (mentalny model)

### 2.1 Żądanie HTTP (np. `POST /api/v1/projects`)
1. `app/main.py` tworzy aplikację, middleware i router.
2. `app/api/routes/projects.py` odbiera payload i woła `ProjectService`.
3. `app/services/project_service.py` robi walidacje biznesowe i operacje DB.
4. `app/models/*.py` definiują tabele i relacje ORM.
5. `app/core/database.py` zarządza sesją SQLAlchemy async.
6. Odpowiedź wraca jako schema z `app/schemas/*.py`.

### 2.2 Zadanie asynchroniczne (np. generowanie artykułu)
1. Route dispatchuje task (`.delay(...)`) z Celery.
2. `app/tasks/content_tasks.py` uruchamia async flow przez `get_db()`.
3. `timed_generation_step(...)` z `generation_log_service.py` loguje każdy krok do `generation_logs`.
4. Task może się retry'ować (ustawienia Celery + `autoretry_for`).

## 3. Szybka mapa domeny danych

Główne encje:
- `users` -> użytkownicy i role.
- `subscription_plans`, `user_subscriptions` -> limity i plan.
- `projects` -> projekt klienta.
- `project_analyses` -> snapshot analizy AI dla projektu.
- `content_schedules` -> harmonogram generacji.
- `topics` -> tematy.
- `articles` -> wygenerowane artykuły.
- `generation_logs` -> audyt kroków AI (tokeny, czas, status).

Najważniejsze relacje:
- `User 1..n Project`
- `User 1..1 UserSubscription`
- `Project 1..1 ProjectAnalysis`
- `Project 1..n Topic`
- `Topic 1..n Article`
- `Project 1..n ContentSchedule`

## 4. Struktura repo: każdy folder i plik

## 4.1 Root (`/`)

`/.dockerignore`
- Rola: wycina zbędne pliki z kontekstu builda Dockera.
- Zależności: używany przez `docker build` i `docker-compose`.
- Uwaga: ignoruje `*.md`, `tests/`, `docs/`, więc README nie trafia do obrazu.

`/.env` (lokalny)
- Rola: lokalne sekrety/konfiguracja runtime.
- Zależności: czytany przez `app/core/config.py`.
- Uwaga: nie powinien być commitowany.

`/.env.example`
- Rola: szablon zmiennych środowiskowych.
- Zależności: mapuje się 1:1 na pola `Settings` w `app/core/config.py`.

`/.gitignore`
- Rola: reguły ignorowania plików dla Git.

`/AGENTS.md`
- Rola: reguły architektury i stylu pracy dla agentów/automatyzacji.
- Zależności: dokument procesowy, nie runtime.

`/Dockerfile`
- Rola: buduje obraz aplikacji.
- Jak działa:
1. Stage `builder` instaluje zależności (`uv pip install ...`).
2. Stage `runtime` kopiuje paczki + kod `app/` + `alembic/`.
3. Uruchamia jako nie-root (`appuser`).
- Zależności: `requirements.txt`, `app/`, `alembic/`, `alembic.ini`.

`/docker-compose.yml`
- Rola: lokalny stack multi-service.
- Serwisy: `postgres`, `redis`, `api`, `celery-worker`, `celery-beat`, `flower`.
- Zależności: `.env`, `Dockerfile`, Redis/Postgres images.

`/requirements.txt`
- Rola: pin wersji bibliotek Python.
- Kluczowe grupy:
1. API: FastAPI/Uvicorn.
2. DB: SQLAlchemy + asyncpg + Alembic.
3. Auth: jose + bcrypt.
4. Async jobs: Celery + Redis + Flower.
5. Observability: structlog + sentry-sdk.

`/alembic.ini`
- Rola: konfiguracja Alembic (logowanie, template nazw plików migracji).
- Uwaga: URL DB jest ustawiany dynamicznie przez `alembic/env.py`.

`/README.md`
- Rola: ten przewodnik.

## 4.2 Folder `alembic/`

`/alembic/env.py`
- Rola: runtime Alembica (offline/online migration mode).
- Jak działa:
1. dodaje root projektu do `sys.path`,
2. importuje `app.models`, żeby `Base.metadata` miało wszystkie tabele,
3. odpala migracje async przez `create_async_engine`.
- Zależności: `app.core.config.settings`, `app.core.database.Base`, `app.models`.

`/alembic/script.py.mako`
- Rola: szablon nowo tworzonych plików migracji.

`/alembic/versions/20260305_6e530ad89a95_initial_schema.py`
- Rola: pierwsza migracja tworząca komplet tabel i indeksów.
- Zależności: stan modeli z czasu generacji migracji.

## 4.3 Folder `scripts/`

`/scripts/create_superuser.py`
- Rola: CLI do utworzenia pierwszego admina.
- Jak działa: otwiera `AsyncSessionLocal`, sprawdza email, hashuje hasło, zapisuje `User`.
- Zależności: `app.core.database`, `app.core.security.hash_password`, `app.models.user`.

`/scripts/run_migration.sh`
- Rola: helper do migracji z poziomu kontenera `api`.
- Jak działa:
1. `alembic revision --autogenerate`,
2. `alembic upgrade head`.
- Zależności: działający `docker compose` i kontener `api`.

## 4.4 Folder `app/`

`/app/__init__.py`
- Rola: oznacza `app` jako pakiet Python (plik pusty).

`/app/main.py`
- Rola: główny entrypoint FastAPI.
- Jak działa:
1. konfiguruje logging,
2. inicjalizuje Sentry,
3. dodaje middleware (`CorrelationId`, `RequestLogging`, `ErrorHandler`),
4. mapuje wyjątki (`AuthError` -> 401),
5. montuje `api_router` pod `/api/v1`.
- Zależności: `app.core.*`, `app.api.router`.

### 4.4.1 `app/core/`

`/app/core/__init__.py`
- Rola: marker pakietu (pusty).

`/app/core/config.py`
- Rola: centralna konfiguracja (`Settings`) przez `pydantic-settings`.
- Jak działa: czyta `.env`, waliduje typy, udostępnia singleton `settings`.
- Kluczowe pola: DB, Redis, JWT, Sentry, CORS, limity feature flag.
- Zależności: praktycznie cały projekt.

`/app/core/database.py`
- Rola: async engine SQLAlchemy + fabryka sesji.
- Jak działa:
1. tworzy `engine`,
2. udostępnia `AsyncSessionLocal`,
3. daje dependency `get_db_session()` (FastAPI),
4. daje context manager `get_db()` (taski/skrypty).
- Zależności: `settings.DATABASE_URL`.
- Użycie: API dependencies, taski Celery, skrypty.

`/app/core/security.py`
- Rola: hashowanie haseł + JWT + `AuthError`.
- Jak działa:
1. `hash_password`/`verify_password` na bcrypt,
2. `create_access_token` i `create_refresh_token`,
3. `decode_token` zwraca `TokenData`.
- Zależności: `python-jose`, `bcrypt`, `settings`.

`/app/core/logging.py`
- Rola: strukturalne logowanie JSON (structlog).
- Jak działa:
1. trzyma context vars (`request_id`, `project_id`, `topic_id`, `task_name`),
2. processor `_inject_context_vars` dokleja je do każdego loga,
3. `configure_logging()` podpina renderer JSON/console.
- Zależności: `structlog`, `settings.LOG_JSON`.

`/app/core/middleware.py`
- Rola: middleware HTTP.
- Klasy:
1. `CorrelationIdMiddleware` (X-Request-ID),
2. `RequestLoggingMiddleware` (czas + status),
3. `ErrorHandlerMiddleware` (spójny JSON 500).
- Zależności: `app.core.logging`.

### 4.4.2 `app/api/`

`/app/api/__init__.py`
- Rola: marker pakietu (pusty).

`/app/api/router.py`
- Rola: centralny router API.
- Jak działa: podpina moduły tras (`health`, `auth`, `projects`, `topics`).
- Zależności: `app.api.routes.*`.

`/app/api/dependencies.py`
- Rola: dependency injection dla auth i DB.
- Jak działa:
1. `get_current_token` parsuje Bearer JWT,
2. `get_current_user` ładuje użytkownika z DB,
3. `require_admin` wymusza rolę admin.
- Aliasy: `CurrentUser`, `AdminUser`, `DBSession`.
- Zależności: `app.core.security`, `app.core.database`, `app.models.user`.

#### `app/api/routes/`

`/app/api/routes/__init__.py`
- Rola: marker pakietu (pusty).

`/app/api/routes/health.py`
- Rola: endpointy zdrowia.
- Endpointy:
1. `GET /health` (liveness),
2. `GET /health/ready` (DB + Redis).
- Zależności: `engine` (SQL), `redis.asyncio`.

`/app/api/routes/auth.py`
- Rola: rejestracja, login, refresh tokenów, profil `me`.
- Zależności: `AuthService`, schemy auth/user.

`/app/api/routes/projects.py`
- Rola: CRUD projektów + trigger analizy AI.
- Endpointy:
1. list/create/get/update/delete projektu,
2. `POST /projects/{id}/analyse` -> dispatch task Celery.
- Zależności: `ProjectService`, `analyse_project` task.

`/app/api/routes/topics.py`
- Rola: tematy wewnątrz projektu + trigger generacji artykułu.
- Endpointy:
1. list/create topic,
2. `POST /topics/{id}/generate` -> dispatch task Celery.
- Zależności: `ProjectService`, `TopicService`, `generate_article` task.

### 4.4.3 `app/models/`

`/app/models/__init__.py`
- Rola: eksportuje wszystkie modele, żeby Alembic mógł je łatwo załadować.

`/app/models/base.py`
- Rola: mixiny wspólne dla modeli.
- Klasy:
1. `TimestampMixin` (`created_at`, `updated_at`),
2. `UUIDMixin` (`id` UUID).

`/app/models/user.py`
- Rola: tabela `users`.
- Zależności relacyjne: `projects`, `subscription`.
- Bezpieczeństwo: przechowuje tylko `hashed_password`.

`/app/models/subscription.py`
- Rola: `subscription_plans` i `user_subscriptions`.
- Zależności: relacja user<->plan przez `UserSubscription`.

`/app/models/project.py`
- Rola: `projects` + `project_analyses`.
- Domena: główny obiekt klienta + snapshot analizy AI.

`/app/models/content.py`
- Rola: `content_schedules`, `topics`, `articles`.
- Domena: planowanie i produkcja contentu.

`/app/models/generation_log.py`
- Rola: append-only audit log kroków AI.
- Użycie: billing/debug/monitoring, szczególnie w taskach.

### 4.4.4 `app/schemas/`

`/app/schemas/__init__.py`
- Rola: marker pakietu (pusty).

`/app/schemas/common.py`
- Rola: wspólne schemy (`APIResponse`, `PaginatedResponse`, `ORMBase`).

`/app/schemas/user.py`
- Rola: bezpieczny output użytkownika (`UserOut`).

`/app/schemas/auth.py`
- Rola: request/response auth (`RegisterRequest`, `LoginRequest`, `TokenResponse`, `RefreshRequest`).

`/app/schemas/project.py`
- Rola: DTO dla projektów i analizy (`ProjectCreate`, `ProjectUpdate`, `ProjectOut`, `ProjectAnalysisOut`).

`/app/schemas/content.py`
- Rola: DTO dla topic/article/schedule.

`/app/schemas/generation_log.py`
- Rola: DTO do tworzenia i odczytu logów generacji.

### 4.4.5 `app/services/`

`/app/services/__init__.py`
- Rola: marker pakietu (pusty).

`/app/services/auth_service.py`
- Rola: logika biznesowa auth.
- Metody:
1. `register`,
2. `login`,
3. `refresh`.
- Zależności: `User` model, `security.py`, schemy auth.

`/app/services/project_service.py`
- Rola: logika projektów (CRUD + limity planu free tier).
- Zależności: `Project` model, `settings.MAX_PROJECTS_FREE_TIER`, Sentry.
- Uwaga: limit planu jest na razie hardcoded (TODO).

`/app/services/topic_service.py`
- Rola: logika tematów w projekcie.
- Zależności: `Topic` model.

`/app/services/generation_log_service.py`
- Rola: zapis wpisów `GenerationLog` + helper `timed_generation_step`.
- Jak działa `timed_generation_step`:
1. mierzy czas kroku,
2. zapisuje sukces lub błąd,
3. dokłada token usage i kontekst.
- Zależności: `GenerationLog`, `GenerationLogCreate`, `get_request_id`.

### 4.4.6 `app/tasks/`

`/app/tasks/__init__.py`
- Rola: marker pakietu (pusty).

`/app/tasks/celery_app.py`
- Rola: konfiguracja aplikacji Celery.
- Jak działa:
1. ustawia broker/backend Redis,
2. rejestruje moduły tasków,
3. ustawia beat schedule,
4. przy starcie workera konfiguruje logowanie + Sentry.

`/app/tasks/content_tasks.py`
- Rola: taski generacyjne:
1. `generate_article`,
2. `analyse_project`.
- Ważne: obecnie kroki LLM są stubami (`TODO`) i mają przykładowe dane.
- Dobre praktyki już są: retry, backoff, context logowania, zapisy do `generation_logs`.

`/app/tasks/scheduler_tasks.py`
- Rola: taski periodyczne od Beat:
1. `run_due_content_schedules`,
2. `cleanup_stale_logs`.
- Uwaga: aktualnie logika dispatchu tematów jest zaznaczona jako `TODO`.

### 4.4.7 `app/scheduler/`

`/app/scheduler/__init__.py`
- Rola: placeholder pod przyszłe zarządzanie harmonogramami (CRUD + sync z Beat).

### 4.4.8 `app/admin/`

`/app/admin/__init__.py`
- Rola: placeholder pod panel admina (`sqladmin`/custom panel).

## 5. Najważniejsze zależności między modułami

Praktyczna mapa "kto kogo używa":

1. `main.py` -> `api/router.py`, `core/*`.
2. `api/routes/*.py` -> `api/dependencies.py`, `services/*.py`, czasem `tasks/*.py`.
3. `services/*.py` -> `models/*.py`, `schemas/*.py`, `core/*`.
4. `tasks/*.py` -> `services/*.py`, `core/database.py`, `core/logging.py`.
5. `alembic/env.py` -> `models/__init__.py` -> wszystkie modele.

## 6. Endpointy i ich odpowiedzialność

Auth:
1. `POST /api/v1/auth/register`
2. `POST /api/v1/auth/login`
3. `POST /api/v1/auth/refresh`
4. `GET /api/v1/auth/me`

Projects:
1. `GET /api/v1/projects`
2. `POST /api/v1/projects`
3. `GET /api/v1/projects/{project_id}`
4. `PATCH /api/v1/projects/{project_id}`
5. `DELETE /api/v1/projects/{project_id}`
6. `POST /api/v1/projects/{project_id}/analyse`

Topics:
1. `GET /api/v1/projects/{project_id}/topics`
2. `POST /api/v1/projects/{project_id}/topics`
3. `POST /api/v1/projects/{project_id}/topics/{topic_id}/generate`

Health:
1. `GET /api/v1/health`
2. `GET /api/v1/health/ready`

## 7. Co jest już produkcyjnie zrobione, a co jeszcze szkieletem

Gotowe fundamenty:
1. separacja warstw (route/service/task/model),
2. auth JWT + hashowanie haseł,
3. migracja bazowa i modele domenowe,
4. Celery + Beat + Flower + Redis,
5. strukturalne logowanie i integracja z Sentry,
6. logi generacji do tabeli `generation_logs`.

Miejsca `TODO` / szkielety:
1. realne wywołania LLM w `content_tasks.py` (teraz stuby),
2. zaawansowane strategie schedulera (obecny dobór topików i dispatch działa, ale bez np. retry policy per project),
3. polityka retencji logów (`cleanup_stale_logs`),
4. panel admina (`app/admin`),
5. moduł scheduler management (`app/scheduler`),
6. billing oparty o realne koszty modeli (token usage jest logowane, ale bez wyceny finansowej).

## 8. Jak czytać kod krok po kroku (dla juniora)

Najlepsza kolejność:
1. `app/main.py` - zobacz jak startuje aplikacja.
2. `app/core/config.py` - zrozum zmienne środowiskowe.
3. `app/api/routes/projects.py` - zobacz cienki route.
4. `app/services/project_service.py` - zobacz gdzie siedzi logika.
5. `app/models/project.py` + migracja Alembic - jak to mapuje się do DB.
6. `app/tasks/content_tasks.py` + `generation_log_service.py` - jak działa backend async.

## 9. Uruchomienie lokalne (krótko)

1. Uzupełnij `.env` (na bazie `.env.example`).
2. Uruchom stack:
```bash
docker compose up --build
```
3. API:
`http://localhost:8000/api/v1/health`
4. Docs:
`http://localhost:8000/docs`
5. Flower:
`http://localhost:5555`

## 10. Testy

Aktualny pakiet testów (`tests/`) obejmuje:
1. limity subskrypcji i usage miesięczne,
2. cooldown + markery w schedulerze,
3. dispatch schedulera z blokadą limitów,
4. ścieżkę `blocked_limit` w `generate_article`.

Uruchomienie:
```bash
python -m pytest tests -q
```

W kontenerze (z podmontowanym katalogiem `tests`):
```bash
docker compose run --rm -T \
  -v /ABS/PATH/TO/blog-ai/tests:/app/tests:ro \
  -v /ABS/PATH/TO/blog-ai/pytest.ini:/app/pytest.ini:ro \
  api python -m pytest tests -q
```

## 11. Jedno zdanie podsumowania

Ten kod to dobrze rozdzielony szkielet produkcyjnego systemu AI content automation: warstwy i observability są poprawnie przygotowane, a główna rzecz do dokończenia to właściwa logika generacji AI i schedulera.
