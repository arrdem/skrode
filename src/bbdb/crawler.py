"""
A simple crawler, designed to check several services for data about a specific handle.
"""

from argparse import ArgumentParser

from bbdb import schema

import requests
from bs4 import BeautifulSoup
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


parser = ArgumentParser(__doc__)


def get_soup(url):
  """
  Get the soup for a given URL.
  """

  return BeautifulSoup(requests.get(url).text)


def crawl_keybase(session, persona, url=None, handle=None):
  """
  Spider a keybase url or handle, inserting records linked to the given persona.
  """

  if handle:
    url = "http://keybase.io/%s" % handle,

  soup = get_soup(url)

  results = {}

  user_attr_items = soup.find_all(class_="it-item")
  user_name = soup.find(class_="full-name").text.strip()
  user_handle = soup.find(class_="username").text.strip()

  session.insert(schema.Name(name=user_name, persona=persona))
  session.insert(schema.Name(name=user_handle, persona=persona))


def crawl_persona(session, handles):
  """
  """


def make_session_factory(db_uri='sqlite:///bbdb.sqlite3'):
  engine = create_engine(db_uri)

  # Note this _is_ reloading safe
  schema.Base.metadata.create_all(engine)

  # Start a session to the database
  session_factory = sessionmaker(bind=engine)
  return session_factory

  
def main(args):
  """
  Actually boot the schema and the database.
  """


  


if __name__ == '__main__':
  args = parser.parse_args()
  main(args)
