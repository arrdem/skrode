"""
A really stupid script to visualize the bbdb schema
"""

import argparse
import sys

from sqlalchemy_schemadisplay import create_schema_graph

from bbdb.schema import Base

parser = argparse.ArgumentParser()
parser.add_argument("-o", dest="outfile")

def main(opts):
  graph = create_schema_graph(
    metadata=Base.metadata,
    rankdir="LR", # From left to right (instead of top to bottom)
    concentrate=False # Don't try to join the relation lines together
  )
  graph.write_png(opts.outfile) # write out the file

if __name__ == "__main__" or 1:
  main(parser.parse_args(sys.argv[1:]))
