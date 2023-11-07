.PHONY: pip_install
pip_install:
	pipenv install --dev


.PHONY: test
test:
	pytest -v --cov --cov-report=term --cov-report=html


.PHONY: build
build: clean
	python setup.py sdist
	python setup.py bdist_wheel
	twine check dist/*


.PHONY: clean
clean:
	rm -rf ./build/*
	rm -rf ./dist/*
	rm -rf ./htmlcov


.PHONY: install_local
install_local:
	pip install -e .


.PHONY: publish
publish: build
	twine upload dist/*


.PHONY: uninstall
uninstall:
	pip uninstall -y synapse-downloader
