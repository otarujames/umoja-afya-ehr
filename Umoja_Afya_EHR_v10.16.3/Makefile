.PHONY: run test check validate migrate review review-down production clean

run:
	python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

test:
	pytest -q

check:
	python -m compileall -q backend scripts
	node --check frontend/app.js

validate:
	python scripts/validate_release.py

migrate:
	alembic upgrade head

review:
	docker compose -f docker-compose.review.yml up --build

review-down:
	docker compose -f docker-compose.review.yml down

production:
	docker compose -f docker-compose.production.yml up --build -d

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache .release_validation.db .migration_validation.db umoja_afya.db
