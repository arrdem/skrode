"""
A quick and shitty lobste.rs bbdb intake script.
"""

import random
import time

from bbdb import schema, make_session_factory, twitter, config
from bbdb.personas import merge_left
from detritus import with_idx
import lobsters

import requests
import progressbar
from twitter.error import TwitterError

factory = make_session_factory()


if __name__ == '__main__':
  bbdb_config = config.BBDBConfig()

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
      ' [', progressbar.Timer(), '] ',
      progressbar.Bar(),
      ' (', progressbar.ETA(), ') ',
    ])

    delay = 1
    for user in bar(users):
      persona = None

      time.sleep(delay)

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

      existing = session.query(schema.LobstersHandle).filter_by(handle=user.name).first()
      if existing:
        persona = existing.persona
        if persona.twitter_accounts or persona.github_accounts:
          # This user is already linked, continue
          continue

      if user.github:
        gh = session.query(schema.GithubHandle).filter_by(handle=user.github).first()
        if gh:
          merge_left(session, persona, gh.persona)

      if user.twitter and not persona:
        t = session.query(schema.TwitterScreenName).filter_by(handle=user.twitter).first()
        if t:
          merge_left(session, persona, t.account.persona)

      if not persona:
        persona = schema.Persona()
        session.add(persona)

      schema.get_or_create(session, schema.Name, persona=persona, name=user.name)

      print("\r{}".format(schema.get_or_create(session, schema.LobstersHandle, handle=user.name, persona=persona)))

      if user.github:
        print(schema.get_or_create(session, schema.GithubHandle, persona=persona, handle=user.github))
        schema.get_or_create(session, schema.Name, persona=persona, name=user.github)

      if user.twitter:
        try:
          print(twitter.insert_user(session, twitter_api.GetUser(screen_name=user.twitter)))
        except TwitterError:
          pass

  finally:
    session.flush()
    session.close()
