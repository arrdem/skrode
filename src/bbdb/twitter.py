"""
Bits for interacting with python-twitter
"""

from __future__ import absolute_import

import re

from bbdb.schema import (Persona, Human, Account, Name, AccountRelationship, Service,
                         get_or_create)
from bbdb.services import mk_service

from arrow import utcnow as now
import twitter
from twitter.models import User


_tw_user_pattern = re.compile("(https?://)twitter.com/(?P<username>[^/?]+)(/.+)?(&.+)?")


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


insert_twitter = mk_service("Twitter", ["http://twitter.com"])


def insert_handle(session, user: User, persona=None):
  """
  Insert a Twitter Handle, creating a Persona for it if there isn't one.


  If the Handle is already known, just linked to another Persona, steal it.
  """

  external_id = twitter_external_id(user.id)
  handle = session.query(Account).filter_by(external_id=external_id).first()
  if not handle:
    if not persona:
      persona = Persona()
      session.add(persona)

    handle = Account(service=insert_twitter(session),
                     external_id=external_id,
                     persona=persona)

  elif handle and persona:
    handle.persona = persona

  session.add(handle)
  session.commit()

  return handle


def insert_screen_name(session, user: User, handle=None):
  """Insert a screen name, attaching it to a handle."""

  external_id = twitter_external_id(user.id)
  handle = handle or get_or_create(session, Account, external_id=external_id)
  screen_name = get_or_create(session, Name,
                              name="@" + user.screen_name,
                              account=handle)
  screen_name.when = now()
  session.add(screen_name)

  return screen_name


def insert_display_name(session, user: User, handle=None):
  """Insert a display name, attaching it to a handle."""

  external_id = twitter_external_id(user.id)
  handle = handle or get_or_create(session, Account, external_id=external_id)
  display_name = get_or_create(session, Name,
                               name=user.name,
                               account=handle)
  display_name.when = now()
  session.add(display_name)

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
  session.commit()
  session.refresh(handle)
  return handle 


def handle_for_screenname(session, screenname):
  return session.query(Account)\
             .join(Name)\
             .filter(Name.name == screenname)\
             .filter(Account.service_id == insert_twitter(session).id)\
             .group_by(Account)\
             .one()


def crawl_followers(session, twitter_api, crawl_user,
                    crawl_user_id=None, when=None):
  if not crawl_user_id:
    crawl_user_id = crawl_user.id

  if when is None:
    when = now()

  for user_id in twitter_api.GetFollowerIDs(user_id=crawl_user_id):
    try:
      extid = twitter_external_id(user_id)
      handle = session.query(Account)\
                      .filter_by(external_id=extid)\
                      .first()

      if handle and handle.names:
        print("Already know of user", user_id, "AKA",
              ", ".join([an.name for an in handle.names]))
        continue

      else:
        # Hydrate the one user explicitly
        user = twitter_api.GetUser(user_id=user_id)
        new_account = insert_user(session, user)
        print(new_account)
        get_or_create(session, AccountRelationship,
                      left=new_account, right=crawl_user,
                      rel="follows",
                      when=when)

    except twitter.error.TwitterError as e:
      print(user_id, e)
      continue


def crawl_friends(session, twitter_api, crawl_user,
                  crawl_user_id=None, when=None):
  if not crawl_user_id:
    crawl_user_id = crawl_user.id

  if when is None:
    when = now()

  for user_id in twitter_api.GetFriendIDs(user_id=crawl_user_id):
    try:
      if session.query(Account)\
                .filter_by(external_id=twitter_external_id(user_id))\
                .first():
        continue

      else:
        user = twitter_api.GetUser(user_id=user_id)
        new_user = insert_user(session, user)
        print(new_user)
        get_or_create(session, AccountRelationship,
                      left=crawl_user, right=new_user,
                      rel="follows",
                      when=when)

    except twitter.error.TwitterError as e:
      print(user_id, e)
      continue
