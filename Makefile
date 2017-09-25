# The virtualenvironment

BUILDROOT=.build
VIRTUALENV=$(BUILDROOT)/venv
VIRTUALENVLIB=$(VIRTUALENV)/lib/python3.6/site-packages
PYTHON=$(VIRTUALENV)/bin/python
VENDORED=$(BUILDROOT)/vendored

.build:
	mkdir -p .build

venv: $(VIRTUALENV)/bin/activate

$(VIRTUALENV)/bin/activate: $(BUILDROOT) requirements.txt
	test -d $(VIRTUALENV) || virtualenv --python python3 $(VIRTUALENV)
	$(VIRTUALENV)/bin/pip install -Ur requirements.txt
	test -d ~/.virtualenvs && test -e $@ || ln -s $(shell realpath $(VIRTUALENV)) ~/.virtualenvs/skrode

# Vendored dependnecies
vendored: $(VENDORED)

$(VENDORED):
	test -d $(VENDORED) || mkdir $(VENDORED)

# Skrode itself
skrode: $(VIRTUALENVLIB)/skrode.egg-link

$(VIRTUALENVLIB)/skrode.egg-link: venv python-twitter
	$(PYTHON) setup.py develop

# Our vendored python-twitter dependency
python-twitter: $(VIRTUALENVLIB)/python-twitter.egg-link

$(VIRTUALENVLIB)/python-twitter.egg-link: venv vendored
	test -d $(VENDORED)/python-twitter || git clone git@github.com:arrdem/python-twitter.git $(VENDORED)/python-twitter
	$(PYTHON) $(VENDORED)/python-twitter/setup.py develop

# Dummy target for Python files
%.py:

# A target for graphing the database schema
etc/dbschema.png: venv src/bbdb/schema.py
	$(PYTHON) ./graph_bbdb_schema.py -o etc/dbschema.png
