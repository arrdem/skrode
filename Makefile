# A target for graphing the database schema

PANTS=./pants

*.py:

etc/dbschema.png: src/python/skrode/schema.py
	$(PANTS) -q run scripts/graph_schema -- -o etc/dbschema.png
