PYTHON ?= python3

.PHONY: run test check

run:
	PYTHONPATH=src $(PYTHON) -m depviz $(ARGS)

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

check:
	$(PYTHON) tools/check_style.py src tests
