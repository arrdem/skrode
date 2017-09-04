"""
A really stupid script to visualize the bbdb schema
"""

from bbdb.schema import Base

from sqlalchemy_schemadisplay import create_schema_graph

graph = create_schema_graph(
  metadata=Base.metadata,
  rankdir="LR", # From left to right (instead of top to bottom)
  concentrate=False # Don't try to join the relation lines together
)
graph.write_png("dbschema.png") # write out the file
