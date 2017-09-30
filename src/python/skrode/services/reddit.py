"""
Helpers for dealing with github.com and gist.github.io
"""

from __future__ import absolute_import

import re

from skrode.personas import merge_left
from skrode.schema import Account, AccountRelationship, Human, Name, Persona, Service, get_or_create
from skrode.services import mk_insert_user, mk_service

from arrow import utcnow as now


insert_reddit = mk_service("Reddit", ["http://reddit.com"])

_reddit_user_pattern = re.compile(r"(https?://)?(reddit.com)/u/(?P<username>[^/?]+)(/.+)?(&.+)?")


def external_id(username):
  m = re.match(_reddit_user_pattern, username)
  if m:
    username = m.group("username")

  return "reddit+user:%s" % username


insert_user = mk_insert_user(insert_reddit, external_id)
