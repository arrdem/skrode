"""
A hackernews backend.
"""

from __future__ import absolute_import

from skrode.services import mk_service, mk_insert_user


insert_hn = mk_service("Hackernews", ["http://news.ycombinator.com"])


def hn_external_id(id):
  return "hackernews+user:%s" % id


insert_user = mk_insert_user(insert_hn, hn_external_id)
