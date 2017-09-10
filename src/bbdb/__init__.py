"""
The heart of bbdb. Session & DB state stuff.
"""

import sys

from bbdb import schema
from bbdb.config import BBDBConfig

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class SneakyBBDBModule(object):
  def make_session_factory(self, config=None, db_uri=None):
    """Returns a session factory for the given db URI. By default uses a local sqlite3 db."""

    if not config and not db_uri:
      print("Warning: using default config file!")
      config = BBDBConfig("config.yml")

    if config and not db_uri:
      db_uri = config.sql_uri

    engine = create_engine(db_uri)

    # Note this _is_ reloading safe, but is bad at schema migrations
    schema.Base.metadata.create_all(engine, checkfirst=True)

    # Start a session to the database
    session_factory = sessionmaker(bind=engine)
    return session_factory

  @property
  def session(self):
    """A constructor for the \"default\" session. Just a REPL helper."""

    factory = self.make_session_factory()
    return factory()

sys.modules[__name__] = SneakyBBDBModule()
