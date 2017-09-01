"""
Join Twitter handles against the Keybase API.
"""

from keybase import Api
from bbdb import schema, config, keybase, make_session_factory


factory = make_session_factory()

bbdb_config = config.BBDBConfig()

if __name__ == '__main__':
  session = factory()
  kb_api = Api()

  try:
    keybase.link_keybases(session, kb=kb_api)

  finally:
    session.flush()
    session.close()
