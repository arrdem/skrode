#!/usr/bin/env python3
"""
A quick and dirty script to crawl my Twitter friends & followers, populating the db
"""

import argparse
import sys

from bbdb import schema, twitter as bt, config, make_session_factory

import arrow
from twitter import _FileCache
import twitter.error


args = argparse.ArgumentParser()
args.add_argument("-u", "--username", dest="user")
args.add_argument("-F", "--no-follows",
                  dest="friends",
                  default=True)
args.add_argument("-R", "--no-followers",
                  dest="followers",
                  default=True)

factory = make_session_factory()

bbdb_config = config.BBDBConfig()

twitter_api = bt.api_for_config(bbdb_config, sleep_on_rate_limit=True)

if __name__ == '__main__':
  opts = args.parse_args(sys.argv[1:])

  session = factory()

  user = twitter_api.GetUser(screen_name=opts.user)

  # Ensure the seed user is in the db
  crawl_user_id = user.id
  crawl_user = bt.insert_user(session, user)

  try:
    when = arrow.utcnow()

    if opts.followers:
      for user_id in twitter_api.GetFollowerIDs(user_id=crawl_user_id):
        try:
          extid = bt.twitter_external_id(user_id)
          handle = session.query(schema.Account)\
                          .filter_by(external_id=extid)\
                          .first()
          screen_names = session.query(schema.AccountName)\
                                .join(schema.Account)\
                                .filter(schema.Account.external_id == extid)\
                                .all()

          if handle and screen_name:
            print("Already know of user", user_id, "AKA", ", ".join(screen_name))
            continue

          else:
            # Hydrate the one user explicitly
            user = twitter_api.GetUser(user_id=user_id)
            new_account = bt.insert_user(session, user)
            print(new_account)
            schema.get_or_create(session, schema.AccountRelationship,
                                 left=new_account, right=crawl_user,
                                 rel=schema.ACCOUNTRELATIONSHIP.follows,
                                 when=when)

        except twitter.error.TwitterError as e:
          print(user_id, e)
          continue

    if opts.friends:
      for user_id in twitter_api.GetFriendIDs(user_id=crawl_user_id):
        try:
          if session.query(schema.Account)\
                    .filter_by(external_id=bt.twitter_external_id(user_id))\
                    .first():
            continue

          else:
            user = twitter_api.GetUser(user_id=user_id)
            new_user = bt.insert_user(session, user)
            print(new_user)
            schema.get_or_create(session, schema.AccountRelationship,
                                 left=crawl_user, right=new_user,
                                 rel=schema.ACCOUNTRELATIONSHIP.follows,
                                 when=when)

        except twitter.error.TwitterError as e:
          print(user_id, e)
          continue

  finally:
    session.flush()
    session.close()
