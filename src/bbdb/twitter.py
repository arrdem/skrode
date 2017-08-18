"""
Bits for interacting with python-twitter
"""

from __future__ import absolute_import

from bbdb.schema import (Persona, TwitterDisplayName, TwitterHandle,
                         TwitterScreenName, get_or_create, Name)

import twitter
from twitter.models import User


def api_for_config(config, **kwargs):
  _api = twitter.Api(
    consumer_key=config.twitter_api_key,
    consumer_secret=config.twitter_api_secret,
    access_token_key=config.twitter_access_token,
    access_token_secret=config.twitter_access_secret,
    cache=twitter._FileCache(config.twitter_cache_dir),
    **kwargs
  )

  _api.SetCacheTimeout(config.twitter_cache_timeout)
  
  return _api


def insert_handle(session, user: User, persona=None):
  """Insert a Twitter Handle, creating a Persona for it if there isn't one."""

  handle = session.query(TwitterHandle).filter_by(id=user.id).first()
  if not handle:
    if not persona:
      persona = Persona()
      session.add(persona)
    handle = TwitterHandle(id=user.id, persona=persona)
    session.add(handle)
    session.commit()

  return handle


def insert_screen_name(session, user: User):
  """Insert a screen name, attaching it to a handle."""

  handle = get_or_create(session, TwitterHandle, id=user.id)
  screen_name = get_or_create(session, TwitterScreenName, handle=user.screen_name, account=handle)
  get_or_create(session, Name, name=user.screen_name, persona=handle.persona)

  return screen_name


def insert_display_name(session, user: User):
  """Insert a display name, attaching it to a handle."""

  handle = get_or_create(session, TwitterHandle, id=user.id)
  display_name = get_or_create(session, TwitterDisplayName, handle=user.name, account=handle)
  get_or_create(session, Name, persona=handle.persona, name=user.name)

  return display_name


def insert_user(session, user, persona=None):
  """
  Given a SQL session and a Twitter user's handle, find (or create) the handle and write out the
  API user details for that handle at the present point in time.

  Creates and links an empty persona if the handle doesn't exist already.
  """

  assert isinstance(user, User)

  handle = insert_handle(session, user, persona)
  insert_screen_name(session, user)
  insert_display_name(session, user)
  return handle


def handle_for_screenname(session, screenname):
  return session.query(TwitterHandle)\
             .join(TwitterScreenName)\
             .filter(TwitterScreenName.handle == screenname)\
             .group_by(TwitterHandle)\
             .first()


def user_from_handle(api: twitter.Api, handle: TwitterHandle):
  """
  Map a database TwitterHandle to an API User structure.
  """

  return User(user_id=handle.id)
