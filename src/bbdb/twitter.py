"""
Bits for interacting with python-twitter
"""

from __future__ import absolute_import

from bbdb.schema import (Persona, Human, Account, AccountName, Service, get_or_create, Name)

from arrow import now
from detritus import once
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


def twitter_external_id(fk):
  return "twitter:{}".format(fk)


@once
def insert_twitter(session):
  """Insert the Twitter Service record, returning it."""

  return get_or_create(session, Service,
                       url="http://twitter.com",
                       name="Twitter")


def insert_handle(session, user: User, persona=None):
  """Insert a Twitter Handle, creating a Persona for it if there isn't one."""

  external_id = twitter_external_id(user.id)
  handle = session.query(Account).filter_by(external_id=external_id).first()
  if not handle:
    if not persona:
      persona = Persona()
      session.add(persona)

    handle = Account(service=insert_twitter(session),
                     external_id=external_id,
                     persona=persona)
    
    session.add(handle)
    session.commit()

  return handle


def insert_screen_name(session, user: User, handle=None):
  """Insert a screen name, attaching it to a handle."""

  external_id = twitter_external_id(user.id)
  handle = handle or get_or_create(session, Account, external_id=external_id)
  screen_name = get_or_create(session, AccountName,
                              name=user.screen_name,
                              account=handle,
                              when=now())

  return screen_name


def insert_display_name(session, user: User, handle=None):
  """Insert a display name, attaching it to a handle."""

  external_id = twitter_external_id(user.id)
  handle = handle or get_or_create(session, Account, external_id=external_id)
  display_name = get_or_create(session, AccountName,
                               name=user.name,
                               account=handle,
                               when=now())

  return display_name


def insert_user(session, user, persona=None):
  """
  Given a SQL session and a Twitter user's handle, find (or create) the handle and write out the
  API user details for that handle at the present point in time.

  Creates and links an empty persona if the handle doesn't exist already.
  """

  assert isinstance(user, User)

  handle = insert_handle(session, user, persona)
  insert_screen_name(session, user, handle)
  insert_display_name(session, user, handle)
  return handle


def handle_for_screenname(session, screenname):
  return session.query(Account)\
             .join(AccountName)\
             .filter(AccountName.name == screenname)\
             .group_by(Account)\
             .one()
