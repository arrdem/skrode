"""
Helpers for dealing with lobste.rs
"""

from __future__ import absolute_import

from lobsters import User
from skrode import schema
from skrode.github import insert_user as gh_insert_user
from skrode.personas import merge_left
from skrode.reddit import insert_user as reddit_insert_user
from skrode.services import mk_insert_user, mk_service
from skrode.twitter import insert_twitter
from skrode.twitter import insert_user as twitter_insert_user

from arrow import utcnow as now
from twitter.error import TwitterError


_lobsters_user_pattern = re.compile("(https?://)lobste.rs/(u|user)/(?P<username>[^/?]+)")


insert_lobsters = mk_service("Lobsters", ["http://lobste.rs"])


def lobsters_external_id(user_or_id):
  if isinstance(user_or_id, User):
    return lobsters_external_id(user_or_id.name)
  else:
    return "lobsters+user:%s" % user_or_id


_insert_user = mk_insert_user(insert_lobsters, lobsters_external_id)


def insert_user(session, twitter_api, user, persona=None, when=None):
  when = when or now()

  dbuser = _insert_user(session, user.name, persona=persona, when=when)

  if user.github:
    gh = gh_insert_user(session, user.github,
                        persona=dbuser.persona,
                        when=when)
    print("[DEBUG]", gh)

  if user.twitter:
    # If there isn't already a persona with this twitter account...
    tw = session.query(schema.Account)\
                .filter(schema.Account.service == insert_twitter(session))\
                .join(schema.Name)\
                .filter(schema.Name.name == ("@" + user.twitter))\
                .first()

    if tw and tw.persona:
      merge_left(session, dbuser.persona, tw.persona)

    elif tw and not tw.persona:
      # This is a schema violation but you never know
      tw.persona = dbuser.persona
      session.add(tw)

    else:
      try:
        print("[DEBUG] Hitting Twitter API for user", user.twitter)
        tw = twitter_insert_user(session, twitter_api.GetUser(screen_name=user.twitter),
                                 persona=dbuser.persona, when=when)
        print(tw)
      except TwitterError as e:
        print(e)
        pass

  if user.reddit:
    rdt = reddit_insert_user(session, user.reddit,
                             persona=dbuser.persona, when=when)
    print("[DEBUG]", rdt)

  return dbuser
