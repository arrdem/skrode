"""
Helpers for dealing with github.com and gist.github.io
"""

from __future__ import absolute_import

import re

from bbdb.schema import (Persona, Human, Account, Name, AccountRelationship, Service,
                         get_or_create)
from bbdb.services import mk_service
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

  return "github:%s" % username


def insert_user(session, username, persona=None, when=None):
  when = when or now()

  gh_user = session.query(Account)\
                   .filter_by(service=insert_github(session),
                              external_id=external_id(username))\
                   .first()
  if not gh_user:
    gh_user = Account(service=insert_github(session),
                      external_id=external_id(username),
                      persona=Persona())
    session.add(gh_user)

  gh_user.when = when
  if gh_user.persona and persona:
    merge_left(session, persona, gh_user.persona)
  else:
    gh_user.persona = persona = persona or Persona()

  get_or_create(session, Name,
                name=username,
                account=gh_user,
                persona=persona)

  session.commit()
  session.refresh(gh_user)
  return gh_user
