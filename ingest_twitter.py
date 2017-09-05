"""
A quick and dirty script to ingest my live Twitter feed.
"""

import argparse
import sys
import signal

from bbdb import schema, twitter as bt, config, make_session_factory, personas

import arrow
from twitter.models import Status
from twitter.error import TwitterError

args = argparse.ArgumentParser()
args.add_argument("-c", "--config",
                  dest="config",
                  default="config.yml")


if __name__ == '__main__':
  opts = args.parse_args(sys.argv[1:])

  bbdb_config = config.BBDBConfig(config=opts.config)

  session_factory = make_session_factory(config=bbdb_config)

  twitter_api = bt.api_for_config(bbdb_config, sleep_on_rate_limit=True)
  current_user = twitter_api.VerifyCredentials()

  # Establish signal handlers so that we'll run and shut down gracefully
  live = True

  def _handler(signum, frame):
    global live
    live = False

  for sig in (signal.SIGINT,):
    signal.signal(sig, _handler)

  # Ingest my Twitter stream
  while live:
    session = session_factory()

    # api.GetStreamFilter will return a generator that yields one status
    # message (i.e., Tweet) at a time as a JSON dictionary.
    for tweet in map(Status.NewFromJsonDict,
                     twitter_api.GetStreamFilter(follow=list(
                       str(id) for id in twitter_api.GetFriendIDs(user_id=current_user.id)))):
      if tweet:
        print(bt.insert_tweet(session, twitter_api, tweet))

      if not live:
        break
