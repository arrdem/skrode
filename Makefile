# A target for graphing the database schema

PANTS=./pants

etc/dbschema.png: 
	$(PANTS) -q run scripts/graph_schema -- -o etc/dbschema.png
