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
	
tts_export: .venv/touchfile
	set -e ; . .venv/bin/activate ; python tts_exporter.py -c ${CONFIG}

cs_export: .venv/touchfile
	set -e ; . .venv/bin/activate ; python cs_exporter.py -c ${CONFIG}

cs_import: .venv/touchfile
	set -e ; . .venv/bin/activate ; python cs_importer.py -c ${CONFIG}

status: .venv/touchfile
	set -e ; . .venv/bin/activate ; python status.py -c ${CONFIG}

clean:
	rm -rf .venv build dist *.egg-info .pytest-cache
	find -iname "*.pyc" -delete
	find -iname "__pycache__" -delete

.PHONY: clean freeze tts_export cs_export cs_import

