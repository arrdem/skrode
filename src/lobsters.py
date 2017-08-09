"""
A quick and shitty lobste.rs read-only driver.
"""

from collections import namedtuple
import time

from bs4 import BeautifulSoup
import requests
from retrying import retry


class LobstersException(Exception):
  """An exception subclass used for signaling request failures."""


def get_soup(url, session=None):
  """
  Get the soup for a given URL.
  """

  session = session or requests
  resp = session.get(url)
  if resp.status_code == 200:
    return BeautifulSoup(resp.text, "html.parser")
  else:
    print(resp.text)
    raise LobstersException("Unable to slurp URL {}\n{}".format(url, resp))


def links(soup):
  return [a.get("href") for a in soup.find_all("a")]


class User(object):
  def __init__(self, url, session=None):
    self._session = session
    self.url = url
    self._soup = None
    self._github = None
    self._twitter = None

  @property
  def soup(self):
    if not self._soup:
      _soup = get_soup(self.url, self._session)
      if "resource you requested was not found" in _soup:
        print("404 on user", self.url)
        raise LobstersException("No such user or rate limited!")
      else:
        self._soup = _soup

    return self._soup

  @property
  def github(self):
    if not self._github:
      self._github = next((link for link in links(self.soup) if "github.com" in link and "/lobsters/wiki" not in link), None)
      if self._github:
        self._github = [t for t in self._github.split("/") if t][-1]
    return self._github

  @property
  def twitter(self):
    if not self._twitter:
      self._twitter = next((link for link in links(self.soup) if "twitter.com" in link), None)
      if self._twitter:
        self._twitter = [t for t in self._twitter.split("/") if t][-1]
    return self._twitter

  @property
  def name(self):
    return [t for t in self.url.split("/")][-1]


class Api(object):
  """
  A Lobsters API client based on screen-scraping.
  """

  def __init__(self, session=None):
    self._session = session or requests.Session()
    self._users = None

  @property
  def users(self):
    if not self._users:
      self._users = self._crawl_users()
    return list(self._users)

  def _crawl_users(self):
    soup = get_soup("https://lobste.rs/u", self._session)
    links = soup.find_all("a")
    users = []
    for link in links:
      href = link.get("href")
      if href and "/u/" in href:
        users.append(User("https://lobste.rs" + href, self._session))
    return users
