CONFIG ?= config.yml

.venv/touchfile: requirements.txt
 	ifeq (, $(shell which virtualenv))
 		$(error "Could not find virtualenv, consider doing `pip install virtualenv`")
 	endif	
	test -d .venv || virtualenv .venv
	. .venv/bin/activate ; pip install -Ur requirements.txt
	touch .venv/touchfile

init: .venv/touchfile

freeze: .venv/touchfile
	set -e ; . .venv/bin/activate ; pip freeze
	
export: .venv/touchfile
	set -e ; . .venv/bin/activate ; python exporter.py -c ${CONFIG}

import: .venv/touchfile
	set -e ; . .venv/bin/activate ; python importer.py -c ${CONFIG}

status: .venv/touchfile
	set -e ; . .venv/bin/activate ; python status.py -c ${CONFIG}

clean:
	rm -rf .venv build dist *.egg-info .pytest-cache
	find -iname "*.pyc" -delete
	find -iname "__pycache__" -delete

.PHONY: clean freeze export import

