# Makefile for caps
#

PYTHON ?= python
NOSETESTS ?= nosetests
CTAGS ?= ctags

clean-pyc:
	find . -name "*.pyc" | xargs rm -f

clean-so:
	find . -name "*.so" | xargs rm -f
	find . -name "*.pyd" | xargs rm -f

clean-doc-build:
	rm -rf doc/build

clean: clean-doc-build clean-pyc clean-so

upload-pypi:
	python setup.py sdist register upload -r pypi

register-pypi:
	python setup.py register -r pypi
