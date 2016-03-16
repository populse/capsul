# Makefile for capsul
#

PYTHON       ?= python2
NOSETESTS    ?= nosetests
CTAGS        ?= ctags
DOCSRC_DIR    = doc
CAPS          = $(shell $(PYTHON) -c "import caps; print caps.__path__[0]" 2>&1)
UPLAOD        = $(CAPS)/sphinx_resources/upload/

# Remove temporary files.
clean-pyc:
	find . -name "*.pyc" | xargs rm -f

clean-tmp:
	find . -name "*.py~" | xargs rm -f

clean-so:
	find . -name "*.so" | xargs rm -f
	find . -name "*.pyd" | xargs rm -f

# Remove the build documentation folder.
clean-doc-build:
	rm -rf doc/build

# Clean the project.
clean: clean-doc-build clean-pyc clean-so clean-tmp

# Upload source tarball on pypi server.
upload-pypi:
	$(PYTHON) setup.py sdist register upload -r pypi

# Register project on pypi server.
register-pypi:
	$(PYTHON) setup.py register -r pypi

# Build dependencies inplace.
build-inplace:
	$(PYTHON) setup.py build_ext --inplace

# Build and upload doc on pypi server.
# Requires "pip install sphinx-pypi-upload".
upload-pypidoc:
	cd doc; make html
	$(PYTHON) setup.py upload_sphinx --upload-dir=doc/_build/html -r pypi

# Build and upload doc on cea server.
upload-ceadoc:
	cd doc; make html
	$(PYTHON) $(UPLAOD)/webdav_upload.py -i capsul
