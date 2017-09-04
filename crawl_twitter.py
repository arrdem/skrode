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

if __name__ == "__main__":
  opts = args.parse_args(sys.argv[1:])

  session = factory()

  if opts.user:
    user = twitter_api.GetUser(screen_name=opts.user)
  else:
    user = twitter_api.VerifyCredentials()

  # Ensure the seed user is in the db
  crawl_user_id = user.id
  crawl_user = bt.insert_user(session, user)

  try:
    when = arrow.utcnow()

    if opts.followers:
      bt.crawl_followers(session, twitter_api, crawl_user, when=when)

    if opts.friends:
      bt.crawl_friends(session, twitter_api, crawl_user, when=when)

  finally:
    session.flush()
    session.close()
