"""
Helpers for dealing with github.com and gist.github.io
"""

from __future__ import absolute_import

import re

from bbdb.schema import (Persona, Human, Account, Name, AccountRelationship, Service,
                         get_or_create)
from bbdb.services import mk_service, mk_insert_user
from bbdb.personas import merge_left

from arrow import utcnow as now


insert_github = mk_service("Github", ["http://github.com",
                                      "http://gist.github.io",
                                      "http://github.io"])

_gh_user_pattern = re.compile(r"(https?://)?((gist\.)?github\.(io|com))/(?P<username>[^/?]+)(/.+)?(&.+)?")


def external_id(username):
  m = re.match(_gh_user_pattern, username)
  if m:
    username = m.group("username")

  return "github+user:%s" % username


insert_user = mk_insert_user(insert_github, external_id)
