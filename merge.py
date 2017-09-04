#!/usr/bin/env python3
"""
MERGE. A quick script for merging users.
"""

import argparse
import sys

from bbdb import session, personas, schema


args = argparse.ArgumentParser()
args.add_argument("l")
args.add_argument("r")

if __name__ == "__main__":
  opts = args.parse_args(sys.argv[1:])
  session = session()

  l = session.query(schema.Persona).filter_by(id=opts.l).one()
  r = session.query(schema.Persona).filter_by(id=opts.r).one()

  personas.merge_left(session, l, r)
  session.delete(r)
  session.commit()
