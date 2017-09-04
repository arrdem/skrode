"""
Join Twitter handles against the Keybase API.
"""

import argparse
import sys

from bbdb import schema, config, keybase, make_session_factory

from keybase import Api

args = argparse.ArgumentParser()
args.add_argument("-f", "--fast", dest="fast",
                  action="store_true",
                  default=True)
args.add_argument("-r", "--refresh",
                  dest="fast",
                  action="store_false")

factory = make_session_factory()

bbdb_config = config.BBDBConfig()

if __name__ == "__main__":
  opts = args.parse_args(sys.argv[1:])

  session = factory()
  kb_api = Api()

  try:
    keybase.link_keybases(session, kb=kb_api, fast=opts.fast)

  finally:
    session.flush()
    session.close()
