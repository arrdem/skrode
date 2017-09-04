#!/usr/bin/env python3
"""
WHOIS. A quick user lookup script.
"""

import argparse
import sys

from bbdb import session, personas


args = argparse.ArgumentParser()
args.add_argument("name")

if __name__ == "__main__":
  opts = args.parse_args(sys.argv[1:])

  for persona in personas.personas_by_name(session(), opts.name):
    print("- persona: %r" % persona.id)
    print("    names:")
    for name in persona.linked_names:
      print("     - %r" % name.name)

    print("    accounts:")
    for account in persona.accounts:
      print("      - service: %r" % account.service)
      print("        foreign key: %r" % account.external_id)
      print("        names:")
      for name in account.names:
        print("        - %r" % name.name)
