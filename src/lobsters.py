"""
A quick and shitty lobste.rs read-only driver.
"""

from collections import namedtuple
from functools import lru_cache
import re

from bbdb.twitter import _tw_user_pattern
from bbdb.github import _gh_user_pattern
from bbdb.reddit import _reddit_user_pattern

from detritus import once
from bs4 import BeautifulSoup
import requests
from retrying import retry


_lobsters_user_pattern = re.compile("(https?://)lobste.rs/(u|user)/(?P<username>[^/?]+)")


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
    self.name = re.match(_lobsters_user_pattern, url).group("username")

  @property
  @lru_cache(16)
  def soup(self):
    _soup = get_soup(self.url, self._session)
    if "resource you requested was not found" in _soup:
      print("404 on user", self.url)
      raise LobstersException("No such user or rate limited!")
    return _soup

  @property
  def github(self):
    _github = next((link for link in links(self.soup) if "github.com" in link and "/lobsters/wiki" not in link), None)
    if _github:
      m = re.match(_gh_user_pattern, _github)
      return m.group("username") if m else None

  @property
  def twitter(self):
    _twitter = next((link for link in links(self.soup) if "twitter.com" in link), None)
    if _twitter:
      m = re.match(_tw_user_pattern, _twitter)
      return m.group("username") if m else None

  @property
  def reddit(self):
    _reddit = next((link for link in links(self.soup) if "reddit.com" in link), None)
    if _reddit:
      m = re.match(_reddit_user_pattern, _reddit)
      return m.group("username") if m else None

  def __repr__(self):
    return "<lobsters.User %r>" % self.name


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
