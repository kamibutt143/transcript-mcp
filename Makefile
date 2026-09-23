.PHONY: test build run

test:
	python -m unittest discover -s tests -v
	python -m compileall app

build:
	docker build -t softnest-transcript-mcp:local .

run:
	docker compose up -d --build
