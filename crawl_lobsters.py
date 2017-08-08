"""
A quick and shitty lobste.rs bbdb intake script.
"""

import random
import time

from bbdb import schema, make_session_factory, twitter, config
from bbdb.personas import merge_left

import lobsters

factory = make_session_factory()


if __name__ == '__main__':
  bbdb_config = config.BBDBConfig()
  session = factory()
  lobsters_api = lobsters.Api()
  twitter_api = twitter.api_for_config(bbdb_config)

  try:
    users = lobsters_api.users
    random.shuffle(users)

    for user in users:
      try:
        persona = None

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

        print(schema.get_or_create(session, schema.LobstersHandle, handle=user.name, persona=persona))

        if user.github:
           print(schema.get_or_create(session, schema.GithubHandle, persona=persona, handle=user.github))
           schema.get_or_create(session, schema.Name, persona=persona, name=user.github)

        if user.twitter:
          print(twitter.insert_user(session, twitter_api.GetUser(screen_name=user.twitter)))

        time.sleep(20)
      except lobsters.LobstersException:
        time.sleep(10*60)

  finally:
    session.flush()
    session.close()
