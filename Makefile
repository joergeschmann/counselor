NAME = Counselor

.PHONY: requirements install

requirements:
	pip install -r requirements.txt

install: requirements
	pip install --user .