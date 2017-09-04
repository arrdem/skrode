"""
The heart of bbdb. Session & DB state stuff.
"""

from detritus import once
from bbdb import schema
from bbdb.config import BBDBConfig

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def make_session_factory(config=None, db_uri=None):
  """Returns a session factory for the given db URI. By default uses a local sqlite3 db."""

  if not config:
    db_uri = BBDBConfig().sql_uri

  engine = create_engine(db_uri)

  # Note this _is_ reloading safe, but is bad at schema migrations
  schema.Base.metadata.create_all(engine, checkfirst=True)

  # Start a session to the database
  session_factory = sessionmaker(bind=engine)
  return session_factory


@once
def session():
  """A constructor for the \"default\" session. Just a REPL helper."""

  factory = make_session_factory()
  return factory()
