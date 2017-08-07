"""
Bits for interacting with python-twitter
"""

import twitter

from bbdb.names import insert_name
from bbdb.schema import (Persona, TwitterDisplayName, TwitterHandle,
                         TwitterScreenName, get_or_create)


def api_for_config(config):
  return twitter.Api(
    consumer_key=config.twitter_api_key,
    consumer_secret=config.twitter_api_secret,
    access_token_key=config.twitter_access_token,
    access_token_secret=config.twitter_access_secret,
  )


def insert_handle(session, user: twitter.User):
  """Insert a Twitter Handle, creating a Persona for it if there isn't one."""

  handle = session.query(TwitterHandle).filter_by(id=user.id).first()
  if not handle:
    persona = Persona()
    session.add(persona)
    handle = TwitterHandle(id=user.id, persona=persona)
    session.add(handle)

  session.commit()

  return handle


def insert_screen_name(session, user: twitter.User):
  """Insert a screen name, attaching it to a handle."""

  handle = get_or_create(session, TwitterHandle, id=user.id)
  screen_name = get_or_create(session, TwitterScreenName, name=user.screen_name, account=handle)
  insert_name(session, handle.persona, user.screen_name)

  return screen_name


def insert_display_name(session, user: twitter.User):
  """Insert a display name, attaching it to a handle."""

  handle = get_or_create(session, TwitterHandle, id=user.id)
  display_name = get_or_create(session, TwitterDisplayName, name=user.name, account=handle)
  insert_name(session, handle.persona, user.name)

  return display_name


def insert_user(session, user):
  """
  Given a SQL session and a Twitter user's handle, find (or create) the handle and write out the
  API user details for that handle at the present point in time.

  Creates and links an empty persona if the handle doesn't exist already.
  """

  assert isinstance(user, twitter.User)

  handle = insert_handle(session, user)
  insert_screen_name(session, user)
  insert_display_name(session, user)
  return handle


def handle_for_screenname(session, screenname):
  return session.query(TwitterHandle)\
             .join(TwitterScreenName)\
             .filter(TwitterScreenName.name == screenname)\
             .group_by(TwitterHandle)\
             .first()


def user_from_handle(api: twitter.Api, handle: TwitterHandle):
  """
  Map a database TwitterHandle to an API User structure.
  """

  return api.User(user_id=handle.id)
