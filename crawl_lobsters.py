"""
A quick and shitty lobste.rs bbdb intake script.
"""

import argparse
import sys
import random
import time

from bbdb import make_session_factory, twitter, config, schema
from bbdb.lobsters import insert_user, lobsters_external_id
import lobsters

import requests
import progressbar

factory = make_session_factory()

args = argparse.ArgumentParser()
args.add_argument("-f", "--fast", dest="fast",
                  action="store_true",
                  default=True)
args.add_argument("-r", "--refresh",
                  dest="fast",
                  action="store_false")
args.add_argument("-c", "--config",
                  dest="config",
                  default="config.yml")


if __name__ == "__main__":
  opts = args.parse_args(sys.argv[1:])
  bbdb_config = config.BBDBConfig(opts.config)

  factory = make_session_factory(config=bbdb_config)
  session = factory()

  requests_session = requests.Session()
  requests_session.headers = {"User-Agent": "Googlebot/2.1 (+http://www.googlebot.com/bot.html)"}

  lobsters_api = lobsters.Api(requests_session)

  twitter_api = twitter.api_for_config(bbdb_config)

  try:
    users = lobsters_api.users
    user_count = len(users)
    random.shuffle(users)

    bar = progressbar.ProgressBar(widgets=[
      "[", progressbar.Timer(), "] ",
      progressbar.Bar(),
      " (", progressbar.ETA(), ") ",
    ])

    delay = 1
    for user in bar(users):
      eu = session.query(schema.Account)\
                  .filter_by(external_id=lobsters_external_id(user.name))\
                  .first()
      if eu and opts.fast:
        print("Already know about user", eu)
        continue

      while True:
        try:
          user.soup
          # Reduce the back-off interval
          if delay > 0.01:
            delay = delay - 0.01
          break

        except lobsters.LobstersException as e:
          # Linear backoff faster than we tune in
          delay = delay + 3
          time.sleep(delay)

      print(insert_user(session, twitter_api, user, fast=opts.fast))

  finally:
    session.flush()
    session.close()
