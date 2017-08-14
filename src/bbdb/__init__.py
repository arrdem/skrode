from detritus import once
from bbdb import schema

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def make_session_factory(db_uri='sqlite:///bbdb.sqlite3'):
  """Returns a session factory for the given db URI. By default uses a local sqlite3 db."""
  engine = create_engine(db_uri)

  # Note this _is_ reloading safe
  schema.Base.metadata.create_all(engine)

  # Start a session to the database
  session_factory = sessionmaker(bind=engine)
  return session_factory


@once
def session():
  """A constructor for the \"default\" session. Just a REPL helper."""
  factory = make_session_factory()
  return factory()
