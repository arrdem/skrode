%.py:

etc/dbschema.png: src/bbdb/schema.py
	python ./graph_bbdb_schema.py -o etc/dbschema.png
