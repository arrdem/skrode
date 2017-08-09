"""
A quick and dirty script to crawl my Twitter friends & followers, populating the db
"""

import sys

from twitter import _FileCache

from bbdb import schema, twitter, config, make_session_factory

import arrow


factory = make_session_factory()

bbdb_config = config.BBDBConfig()

twitter_api = twitter.api_for_config(bbdb_config, sleep_on_rate_limit=True)

if __name__ == '__main__':
  session = factory()

  if len(sys.argv) == 2:
    user = twitter_api.GetUser(screen_name=sys.argv[1])

  else:
    # Get me
    user = twitter_api.VerifyCredentials()

  # Ensure the seed user is in the db
  twitter.insert_user(session, user)
  user_id = user.id

  try:
    when = arrow.utcnow()

    for user_id in twitter_api.GetFollowerIDs(user_id=user_id):
      if session.query(schema.TwitterHandle).filter_by(id=user.id).first():
        continue

      else:
        # Hydrate the one user explicitly
        user = twitter_api.GetUser(user_id=user_id)
        print(twitter.insert_user(session, user))
        schema.get_or_create(session, schema.TwitterFollows,
                             follows_id=user_id, follower_id=user.id, when=when)

    for user_id in twitter_api.GetFriendIDs(user_id=user_id):
      if session.query(schema.TwitterHandle).filter_by(id=user.id).first():
        continue

      else:
        user = twitter_api.GetUser(user_id=user_id)
        print(twitter.insert_user(session, user))
        schema.get_or_create(session, schema.TwitterFollows,
                             follower_id=user_id, follows_id=user.id, when=when)

  finally:
    session.flush()
    session.close()
