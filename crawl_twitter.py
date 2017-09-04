#!/usr/bin/env python3
"""
A quick and dirty script to crawl my Twitter friends & followers, populating the db
"""

import argparse
import sys

from bbdb import schema, twitter as bt, config, make_session_factory, personas

import arrow
from twitter.models import User
from twitter.error import TwitterError


args = argparse.ArgumentParser()
args.add_argument("-u", "--username", dest="user")
args.add_argument("-F", "--no-follows",
                  dest="friends",
                  default=True)
args.add_argument("-R", "--no-followers",
                  dest="followers",
                  default=True)
args.add_argument("-f", "--file",
                  dest="filename",
                  default=None)

factory = make_session_factory()

bbdb_config = config.BBDBConfig()

twitter_api = bt.api_for_config(bbdb_config, sleep_on_rate_limit=True)

if __name__ == "__main__":
  opts = args.parse_args(sys.argv[1:])

  session = factory()

  if opts.filename:
    with open(opts.filename) as f:
      twitter_user = None
      line = None
      for line in f:
        line = line.strip()
        try:
          twitter_user = twitter_api.GetUser(screen_name=line)
          if isinstance(twitter_user, dict):
            twitter_user = User.NewFromJsonDict(twitter_user)

          persona = personas.personas_by_name(session, line, one=True, exact=True)
          print(bt.insert_user(session, twitter_user, persona))
        except TwitterError as e:
          print(line, line, e)
        except AssertionError as e:
          print(line, twitter_user, e)
          raise e

  else:
    if opts.user:
      user = twitter_api.GetUser(screen_name=opts.user)
    else:
      user = twitter_api.VerifyCredentials()

    # Ensure the seed user is in the db
    crawl_user_id = user.id
    crawl_user = bt.insert_user(session, user)
    print("Crawling user", crawl_user_id, ":", crawl_user)

    try:
      when = arrow.utcnow()

      if opts.followers:
        bt.crawl_followers(session, twitter_api, crawl_user, crawl_user_id=crawl_user_id, when=when)

      if opts.friends:
        bt.crawl_friends(session, twitter_api, crawl_user, crawl_user_id=crawl_user_id, when=when)

    finally:
      session.flush()
      session.close()
