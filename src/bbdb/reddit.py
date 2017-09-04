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


insert_reddit = mk_service("Reddit", ["http://reddit.com"])

_reddit_user_pattern = re.compile(r"(https?://)?(reddit.com)/u/(?P<username>[^/?]+)(/.+)?(&.+)?")


def external_id(username):
  m = re.match(_reddit_user_pattern, username)
  if m:
    username = m.group("username")

  return "reddit:%s" % username


def insert_user(session, username, persona=None, when=None):
  when = when or now()
  persona = persona or Persona()

  r_user = get_or_create(session, Account,
                         service=insert_reddit(session),
                         external_id=external_id(username))
  r_user.when = when
  if persona and r_user.persona:
    merge_left(session, persona, r_user.persona)
  else:
    r_user.persona = persona = persona or Persona()

  session.add(r_user)

  get_or_create(session, Name,
                name=username,
                account=r_user,
                persona=persona)

  session.commit()
  session.refresh(r_user)
  return r_user 
