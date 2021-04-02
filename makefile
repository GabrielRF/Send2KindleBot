.PHONY: install
install: # system-wide standard python installation
	pip install -r requirements.txt

.PHONY: install.hack
install.hack: # install development requirements
	pip install -r requirements.dev.txt

.PHONY: lint
lint: # lint code
	flake8 .

.PHONY: format
format:
	isort .
	black -l 79 .

.PHONY: clean
clean: # remove temporary files and artifacts
	rm -rf site/
	rm -rf *.egg-info dist build
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '.coverage' -exec rm -f {} +
	find . -name '__pycache__' -exec rmdir {} +
