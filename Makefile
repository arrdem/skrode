# The virtualenvironment
venv: venv/bin/activate

venv/bin/activate: requirements.txt
	test -d venv || virtualenv --python python3 venv
	venv/bin/pip install -Ur requirements.txt

# Vendored dependnecies
vendored:
	test -d vendored || mkdir vendored

python-twitter: venv/lib/python3.6/site-packages/python-twitter.egg-link

venv/lib/python3.6/site-packages/python-twitter.egg-link: venv vendored
	git clone git@github.com:arrdem/python-twitter.git clone vendored/python-twitter
	venv/bin/python vendored/python-twitter/setup.py develop

# Skrode itself
skrode: venv/lib/python3.6/site-packages/skrode.egg-link

venv/lib/python3.6/site-packages/skrode.egg-link: venv python-twitter
	venv/bin/python setup.py develop

# Dummy target for Python files
%.py:

# A target for graphing the database schema
etc/dbschema.png: venv src/bbdb/schema.py
	venv/bin/python ./graph_bbdb_schema.py -o etc/dbschema.png

# A target for running (or restarting) the service
.PHONY: run
run: venv skrode
	venv/bin/python ./run.py -c service-config.yml
