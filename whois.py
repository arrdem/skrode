#!/usr/bin/env python3
"""
WHOIS. A quick user lookup script.
"""

import argparse
import sys

from bbdb import session, personas

import jinja2

PERSONA_TEMPLATE = jinja2.Template("""\
 - persona: {{persona.id}}
   names:
{% for name in persona.names %}\
     - {{name}}
{% endfor %}\
   accounts:
{% for account in persona.accounts %}\
     - service: {{account.service}}
       foreign key: {{account.external_id}}
       names:
{% for name in account.names %}\
         - {{name}}
{% endfor %}\
{% endfor %}\
""")

args = argparse.ArgumentParser()
args.add_argument("name")

if __name__ == "__main__":
  opts = args.parse_args(sys.argv[1:])

  for persona in personas.personas_by_name(session(), opts.name):
    print(PERSONA_TEMPLATE.render(persona=persona))
