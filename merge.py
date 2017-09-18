#!/usr/bin/env python3
"""
MERGE. A quick script for merging personas together.
"""

import argparse
import sys

from bbdb import personas, schema
from bbdb.config import BBDBConfig

args = argparse.ArgumentParser()
args.add_argument("-c", "--config",
                  dest="config",
                  default="config.yml")

args.add_argument("l")
args.add_argument("r")


def main(opts):
  config = BBDBConfig(config=opts.config)
  session = config.get("sql")

  l = session.query(schema.Persona).filter_by(id=opts.l).one()
  r = session.query(schema.Persona).filter_by(id=opts.r).one()

  personas.merge_left(session, l, r)
  session.commit()


if __name__ == "__main__":
  main(args.parse_args(sys.argv[1:]))
