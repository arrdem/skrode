"""
Helpers for dealing with SQL connections.
"""

from skrode import schema

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


CONN_FORMAT = "{dialect}://{username}:{password}@{hostname}:{port}/{database}"


def make_uri(**kwargs):
  return CONN_FORMAT.format(**kwargs)


def make_engine_session_factory(config=None, uri=None):
  """Returns a session factory for the given db URI. By default uses a local sqlite3 db."""

  assert config or uri

  if config and not uri:
    db_uri = config.sql.uri

  engine = create_engine(uri)

  # Note this _is_ reloading safe, but is bad at schema migrations
  schema.Base.metadata.create_all(engine, checkfirst=True)

  # Start a session to the database
  session_factory = sessionmaker(bind=engine)
  return engine, session_factory


def make_session(config=None, uri=None):
  _engine, factory = make_engine_session_factory(config, uri)
  return factory()
