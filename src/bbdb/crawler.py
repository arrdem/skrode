"""
A simple crawler, designed to check several services for data about a specific handle.
"""

from argparse import ArgumentParser

from bbdb.names import insert_name
from bbdb import schema

import requests
from bs4 import BeautifulSoup


def get_soup(url):
  """
  Get the soup for a given URL.
  """

  return BeautifulSoup(requests.get(url).text, "html.parser")


def crawl_keybase(session, persona, url=None, handle=None):
  """
  Spider a keybase url or handle, inserting records linked to the given persona.
  """

  if handle:
    url = "http://keybase.io/%s" % (handle,)

  if url:
    print(url)
    soup = get_soup(url)

    results = {}

    user_attr_items = soup.find_all(class_="it-item")
    user_name = soup.find(class_="full-name").text.strip()
    user_handle = soup.find(class_="username").text.strip()

    insert_name(session, persona, user_name)
    insert_name(session, persona, user_handle)
    schema.get_or_create(session, schema.KeybaseHandle, handle=url.split("/")[-1], persona=persona)
    session.commit()

  else:
    for twitter in persona.twitter_accounts:
      try:
        crawl_keybase(session, persona, handle=name.name)
      except:
        pass
