# Software Bill of Materials — Release 10.7.0

The authoritative direct Python dependency list is `requirements.txt`. Container base images are:

- `python:3.12-slim`
- `postgres:16-alpine`
- `nginx:1.27-alpine` in the production reverse-proxy profile

Direct application packages:

| Package | Version | Purpose |
|---|---:|---|
| FastAPI | 0.128.2 | REST application framework |
| Uvicorn | 0.48.0 | ASGI server |
| SQLAlchemy | 2.0.50 | ORM and database transactions |
| Pydantic | 2.13.4 | Request/configuration validation |
| PyYAML | 6.0.3 | Configuration parsing |
| psycopg | 3.3.2 | PostgreSQL driver |
| Alembic | 1.18.4 | Database migrations |
| argon2-cffi | 23.1.0 | Argon2id password hashing |
| httpx | 0.28.1 | API testing/client support |
| pytest | 9.0.2 | Automated tests |

Production release engineering must generate a complete transitive CycloneDX or SPDX SBOM, scan it against current vulnerability sources, document exceptions and repeat the scan for every build.
