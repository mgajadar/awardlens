.PHONY: install demo dashboard test lint check docker

install:
	python -m pip install -e ".[dev]"

demo:
	awardlens demo

dashboard:
	streamlit run app.py

test:
	pytest --cov=awardlens --cov-report=term-missing

lint:
	ruff check .

check: lint test

docker:
	docker compose up --build

