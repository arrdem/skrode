"""
A really stupid script to visualize the bbdb schema
"""

from __future__ import absolute_import, print_function

import argparse
import sys

from skrode.schema import Base
from sqlalchemy_schemadisplay import create_schema_graph


args = argparse.ArgumentParser()
args.add_argument("-o", dest="outfile")


def main(opts):
  graph = create_schema_graph(
      metadata=Base.metadata,
      rankdir="LR",               # From left to right (instead of top to bottom)
      concentrate=False           # Don't try to join the relation lines together
  )
  graph.write_png(opts.outfile)   # write out the file


if __name__ == "__main__":
  main(args.parse_args(sys.argv[1:]))
