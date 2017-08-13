"""
A quick and dirty script to crawl my Twitter friends & followers, populating the db
"""

import sys

from bbdb import schema, twitter as bt, config, make_session_factory

import arrow
from twitter import _FileCache
import twitter.error


factory = make_session_factory()

bbdb_config = config.BBDBConfig()

twitter_api = bt.api_for_config(bbdb_config, sleep_on_rate_limit=True)

if __name__ == '__main__':
  session = factory()

  if len(sys.argv) == 2:
    user = twitter_api.GetUser(screen_name=sys.argv[1])

  else:
    # Get me
    user = twitter_api.VerifyCredentials()

  # Ensure the seed user is in the db
  bt.insert_user(session, user)
  user_id = user.id

  try:
    when = arrow.utcnow()

    for user_id in twitter_api.GetFollowerIDs(user_id=user_id):
      try:
        handle = session.query(schema.TwitterHandle).filter_by(id=user.id).first()
        screen_name = session.query(schema.TwitterHandle)\
                        .join(schema.TwitterScreenName)\
                        .filter(schema.TwitterHandle.id == user_id)\
                        .first()

        if handle and screen_name:
          print("Already know of user", user_id, "AKA", screen_name)
          continue

        else:
          # Hydrate the one user explicitly
          user = twitter_api.GetUser(user_id=user_id)
          print(bt.insert_user(session, user))
          schema.get_or_create(session, schema.TwitterFollows,
                               follows_id=user_id, follower_id=user.id, when=when)

      except twitter.error.TwitterError as e:
        print(user_id, e)
        continue

    print("Trying to get followings for user...")

    for user_id in twitter_api.GetFriendIDs(user_id=user_id):
      try:
        if session.query(schema.TwitterHandle).filter_by(id=user.id).first():
          continue

        else:
          user = twitter_api.GetUser(user_id=user_id)
          print(bt.insert_user(session, user))
          schema.get_or_create(session, schema.TwitterFollows,
                               follower_id=user_id, follows_id=user.id, when=when)

      except twitter.error.TwitterError as e:
        print(user_id, e)
        continue

  finally:
    session.flush()
    session.close()
