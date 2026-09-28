PY ?= .venv/bin/python
ifeq ($(wildcard .venv/bin/python),)
PY = python3
endif

.PHONY: all clean pipeline test screenshots venv

all: clean pipeline test

venv:
	python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt

clean:
	rm -rf build
	rm -f web/*.html

pipeline:
	$(PY) pipeline/01_validate_graph.py
	$(PY) pipeline/02_compute_layers.py
	$(PY) pipeline/03_closures.py
	$(PY) pipeline/04_static_test.py
	$(PY) pipeline/05_simulate.py
	$(PY) pipeline/06_build_web.py
	$(PY) pipeline/07_guided_questions.py

test:
	$(PY) -m pytest -q

screenshots:
	docs/screenshots/capture.sh
