#!/usr/bin/env python3
"""
WHOIS. A quick user lookup script.
"""

import argparse
import sys

from bbdb.config import BBDBConfig
from bbdb import personas

import jinja2

def indent(str, width=2):
  return "\n".join(["%s%s" % (" " * width, line) for line in str.splitlines()])


PERSONA_RAW = """\
persona: {{persona.id}}
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
"""

PERSONA_TEMPLATE = jinja2.Template("---\n" + PERSONA_RAW)

HUMAN_RAW = """\
human: {{human.id}}
personas:
{%% for persona in human.personas %%}\
  - %s
{%% endfor %%}\
""" % (indent(PERSONA_RAW, width=4).lstrip(),)

HUMAN_TEMPLATE = jinja2.Template("---\n" + HUMAN_RAW)

args = argparse.ArgumentParser()
args.add_argument("-c", "--config",
                  dest="config",
                  default="config.yml")
args.add_argument("name")

if __name__ == "__main__":
  opts = args.parse_args(sys.argv[1:])
  config = BBDBConfig(config=opts.config)

  for persona in personas.personas_by_name(config.get("sql"), opts.name):
    if persona.owner:
      print(HUMAN_TEMPLATE.render(human=persona.owner))
    else:
      print(PERSONA_TEMPLATE.render(persona=persona))
