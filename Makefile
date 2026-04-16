SHELL := /bin/sh

dev:
	docker compose up --build

test:
	python -m pytest -q

bootstrap:
	python scripts/bootstrap.py

ingest-demo:
	python scripts/seed_demo.py
