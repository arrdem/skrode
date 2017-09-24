"""
A quick and dirty script to crawl my Twitter friends & followers, populating the db
"""

import sys

from skrode import schema, twitter, config, make_session_factory

import arrow


if __name__ == "__main__":
  factory = make_session_factory()

  bbdb_config = config.Config()

  twitter_api = twitter.api_for_config(bbdb_config, sleep_on_rate_limit=True)

  session = factory()

  if len(sys.argv) == 2:
    user_id = twitter_api.GetUser(screen_name=sys.argv[1]).id

  else:
    user_id = twitter_api.VerifyCredentials().id

  try:
    when = arrow.utcnow()

    for user in twitter_api.GetFollowers(user_id=user_id):
      print(twitter.insert_user(session, user))
      schema.get_or_create(session, schema.TwitterFollows,
                           follows_id=user_id, follower_id=user.id, when=when)

    for user in twitter_api.GetFriends(user_id=user_id):
      print(twitter.insert_user(session, user))
      schema.get_or_create(session, schema.TwitterFollows,
                           follower_id=user_id, follows_id=user.id, when=when)

  finally:
    session.flush()
    session.close()
