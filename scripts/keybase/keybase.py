"""
Join Twitter handles against the Keybase API.
"""

from __future__ import absolute_import, print_function

import argparse
import sys

from keybase import Api, NoSuchUserException
from skrode import config, make_session_factory, schema
from skrode.services.keybase import insert_keybase, insert_user
import skrode.services.twitter as bt


args = argparse.ArgumentParser()
args.add_argument("-f", "--fast", dest="fast",
                  action="store_true",
                  default=False)
args.add_argument("-r", "--refresh",
                  dest="fast",
                  action="store_false")
args.add_argument("-c", "--config",
                  dest="config",
                  default="config.yml")


def main():
  opts = args.parse_args(sys.argv[1:])
  bbdb_config = config.BBDBConfig(config=opts.config)

  # SQL
  ########################################
  factory = make_session_factory(config=bbdb_config)
  session = factory()

  # Keybase API
  kb_api = Api()

  # Twitter API
  twitter_api = bt.api_for_config(bbdb_config, sleep_on_rate_limit=True)

  try:
    _twitter = bt.insert_twitter(session)

    for screenname in session.query(schema.Name)\
                             .join(schema.Account)\
                             .filter(schema.Account.service == _twitter)\
                             .filter(schema.Name.name.op("~")("^@\S+$"))\
                             .all():
      account = screenname.account
      persona = account.persona or account.persona

      keybase_account = \
        session.query(schema.Account)\
               .filter(schema.Account.service_id == insert_keybase(session).id)\
               .filter(schema.Account.persona_id == persona.id)\
               .first()

      if keybase_account and opts.fast:
        print("Skipping handle %s already linked to %s"
              % (screenname.name, keybase_account))
        continue

      try:
        name = screenname.name.replace("@", "")
        print("Trying twitter handle %r" % name)
        kb_user = kb_api.get_users(twitter=name, one=True)
        print("Got keybase user", kb_user.username, kb_user.id)
        insert_user(session, kb_user, persona=persona, twitter_api=twitter_api)
      except NoSuchUserException:
          pass

  finally:
    session.flush()
    session.close()


if __name__ == "__main__":
  main()
