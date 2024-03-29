NAME = counselor

.PHONY: requirements test install install-deploy-tools build deploy-test deploy-prod

requirements:
	pip install -r requirements.txt

test:
	python -m unittest discover -v -s ./tests/unit/ -p '*test*.py'

install: requirements
	pip install --user .

install-deploy-tools:
	python -m pip install --user --upgrade setuptools wheel launchpadlib keyring twine

clean-build-and-dist:
	rm -rf build/
	rm -rf *.egg-info

build: clean-build-and-dist
	python setup.py sdist bdist_wheel

upload-test: build
	python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*

upload-prod: build
	python -m twine upload dist/*

deploy-test: build upload-test clean-build-and-dist

deploy-prod: build upload-prod clean-build-and-dist