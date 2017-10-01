"""
Helpers for dealing with facebook.com
"""

from __future__ import absolute_import

import re

from skrode.services import mk_insert_user, mk_service


insert_facebook = mk_service("Facebook", ["http://facebook.com", "http://messenger.com"])
_fb_user_pattern = re.compile(r"(https?://)?(facebook.com)/(?P<username>[^/?]+)(/.+)?(&.+)?")


def external_id(username):
  m = re.match(_fb_user_pattern, username)
  if m:
    username = m.group("username")

  return "facebook+user:%s" % username


insert_user = mk_insert_user(insert_facebook, external_id)
