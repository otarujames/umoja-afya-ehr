# Production Deployment and Clinical Audio Corrections — 10.7.0

## Database connection failure corrected

The failed server deployment placed a password containing `@` and `#` directly inside a PostgreSQL URI. URI parsing treated the text after the first `@` as the host, so psycopg attempted to resolve a host containing part of the password.

Release 10.1 does not use an inline `DATABASE_URL` in Docker production. It supplies:

- `UMOJA_DB_HOST`
- `UMOJA_DB_PORT`
- `UMOJA_DB_NAME`
- `UMOJA_DB_USER`
- `UMOJA_DB_PASSWORD_FILE`

The application constructs the SQLAlchemy URL with `URL.create()`, which correctly escapes reserved characters. A malformed raw URL is rejected with an actionable startup error instead of entering a restart loop.

## Startup model

- PostgreSQL must pass `pg_isready`.
- `scripts/prestart.py` validates runtime configuration.
- The application waits for the database.
- Alembic migrations run under a PostgreSQL advisory lock.
- Reference data is bootstrapped idempotently. Release 10.2 replaces automatic administrator creation with token-protected first-run setup.
- Uvicorn starts without `--reload`.
- Liveness and readiness use separate endpoints.
- Nginx starts only after application readiness.

## Clinical Note correction

`+ New Note` routes into Clinical Documentation with the currently selected patient and encounter. The composer supports template selection, smart phrases, draft save, create-and-sign, subsequent signing, cosign workflow, locked signed notes, addenda and immutable event history.

## Clinical audio annotation

1. Select a patient and encounter.
2. Open **Audio / Dictation**.
3. Confirm the facility's consent/recording requirement.
4. Record through the browser or upload an approved audio type.
5. Play back the recording.
6. Send it to the private transcription service.
7. Review language, confidence, duration, engine/model and low-confidence warning.
8. Correct the transcript against the recording.
9. Generate an unsigned structured draft.
10. Insert the draft into a new note and complete clinician review/signature.

The service uses VAD, beam search, word timestamps and deterministic temperature. Review uses a smaller CPU model for accessibility; production defaults to `large-v3`. Accuracy remains dependent on microphone quality, accent, language, background noise, model and clinical terminology, so the system never signs or attests to a transcript automatically.

By default, the raw audio byte stream is deleted after transcription. The database retains the transcript, SHA-256 digest, MIME type, original filename, size, duration, confidence, engine/model, segments and audit trail. Deployments that legally require audio retention must implement an approved encrypted object-storage connector and update retention policy; setting a flag alone does not store audio.


Audio upload transport: the application and TLS proxy use a 60 MB request ceiling for the 50 MB clinical-audio limit, with a 360-second transcription proxy timeout.
