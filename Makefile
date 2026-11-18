UV ?= uv
PY = .venv/bin/python

# `make evaluate <system> ...`: the system names after the target are passed on
ARGS = $(filter-out evaluate,$(MAKECMDGOALS))

install:
	$(UV) venv --allow-existing
	$(UV) pip install -r requirements/deps.compiled -e .
	$(PY) -m klara_benchmark.datasets

install-local:  # extra deps for the locally-run systems (whisper, cohere, nemotron)
	$(UV) venv --allow-existing
	$(UV) pip install -r requirements/local.compiled -e .

evaluate:
	$(PY) -m klara_benchmark.evaluate $(ARGS)

score:
	$(PY) -m klara_benchmark.score

compile:
	$(UV) pip compile -q --universal --python-version 3.11 requirements/deps.in -o requirements/deps.compiled
	$(UV) pip compile -q --universal --python-version 3.11 requirements/deps.in requirements/local.in -o requirements/local.compiled

ruff:
	uvx ruff check .

# The system names are make goals too and need a no-op rule.
ifneq (,$(filter evaluate,$(MAKECMDGOALS)))
ifneq (,$(ARGS))
$(ARGS):
	@:
endif
endif

.PHONY: install install-local evaluate score compile ruff
