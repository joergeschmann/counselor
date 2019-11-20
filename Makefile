NAME = counselor

.PHONY: requirements install install-deploy-tools build upload-test upload-prod

requirements:
	pip install -r requirements.txt

install: requirements
	pip install --user .

install-deploy-tools:
	python -m pip install --user --upgrade setuptools wheel launchpadlib keyring twine

build:
	rm -rf ./build/*
	rm -rf ./dist/*
	python setup.py sdist bdist_wheel

upload-test:
	python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*

upload-prod:
	python -m twine upload dist/*