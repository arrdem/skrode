from bbdb import schema

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def make_session_factory(db_uri='sqlite:///bbdb.sqlite3'):
  engine = create_engine(db_uri)

  # Note this _is_ reloading safe
  schema.Base.metadata.create_all(engine)

  # Start a session to the database
  session_factory = sessionmaker(bind=engine)
  return session_factory
