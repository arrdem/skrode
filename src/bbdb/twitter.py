"""
Bits for interacting with python-twitter
"""

from __future__ import absolute_import

import re
import json
from datetime import datetime

from bbdb.schema import (Persona, Human, Account, Name, AccountRelationship, Service,
                         get_or_create, Post, PostDistribution)
from bbdb.services import mk_service

from arrow import utcnow as now, get as aget
import twitter
from twitter.models import User


_tw_user_pattern = re.compile("(https?://)twitter.com/(?P<username>[^/?]+)(/.+)?(&.+)?")
_tw_datetime_pattern = "%a %b %d %H:%M:%S +0000 %Y"

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


def twitter_external_user_id(fk):
  return "twitter:{}".format(fk)


insert_twitter = mk_service("Twitter", ["http://twitter.com"])


def insert_handle(session, user: User, persona=None):
  """
  Insert a Twitter Handle, creating a Persona for it if there isn't one.


  If the Handle is already known, just linked to another Persona, steal it.
  """

  external_id = twitter_external_user_id(user.id)
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


def insert_screen_name(session, user: User, handle=None, when=None):
  """Insert a screen name, attaching it to a handle."""

  external_id = twitter_external_user_id(user.id)
  handle = handle or get_or_create(session, Account, external_id=external_id)
  screen_name = get_or_create(session, Name,
                              name="@" + user.screen_name,
                              account=handle)
  screen_name.when = when or now()
  session.add(screen_name)

  return screen_name


def insert_display_name(session, user: User, handle=None, when=None):
  """Insert a display name, attaching it to a handle."""

  external_id = twitter_external_user_id(user.id)
  handle = handle or get_or_create(session, Account, external_id=external_id)
  display_name = get_or_create(session, Name,
                               name=user.name,
                               account=handle)
  display_name.when = when or now()
  session.add(display_name)

  return display_name


def insert_user(session, user, persona=None, when=None):
  """
  Given a SQL session and a Twitter user's handle, find (or create) the handle and write out the
  API user details for that handle at the present point in time.

  Creates and links an empty persona if the handle doesn't exist already.
  """

  assert isinstance(user, User)

  when = when or now()

  handle = insert_handle(session, user, persona)
  insert_screen_name(session, user, handle, when=when)
  insert_display_name(session, user, handle, when=when)
  session.commit()
  session.refresh(handle)
  return handle


def insert_user_from_json(twitter_api, session, user):
  pass


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
      extid = twitter_external_user_id(user_id)
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
                .filter_by(external_id=twitter_external_user_id(user_id))\
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


def twitter_external_tweet_id(tweet_id):
  return "twitter+tweet:{0}".format(str(tweet_id))


def _get_tweet_text(tweet):
  """Tweets text may be truncated, and it may also be deferred to the retweeted_status
  payload. Consequently we need a depth-1 recursion to actually reliably recover the text for a
  tweet, as we have to look at the embedded retweet_stats record and apply the same logic there.

  """

  if tweet.truncated and tweet.retweeted_status:
    return _get_tweet_text(tweet.retweeted_status)
  else:
    return tweet.full_text or tweet.text


def insert_tweet(session, twitter_api, tweet):
  """Insert a tweet (status using the old API terminology) into the backing datastore.

  This means inserting the original poster, inserting the service, inserting the post and inserting
  the post distribution.

  """

  _tw = insert_twitter(session)
  try:
    poster = insert_user(session, tweet.user)
  except AssertionError as e:
    print("Encountered exception", e, "Processing tweet", tweet)
    return None

  therad = None
  if tweet.in_reply_to_status_id:
    thread = session.query(Post)\
                    .filter_by(external_id=twitter_external_tweet_id(tweet.in_reply_to_status_id))\
                    .first()
  elif tweet.retweeted_status:
    thread = insert_tweet(session, twitter_api, tweet.retweeted_status)

  post = get_or_create(session, Post,
                       text=_get_tweet_text(tweet),
                       external_id=twitter_external_tweet_id(tweet.id_str),
                       poster=poster,
                       when=aget(datetime.strptime(tweet.created_at, _tw_datetime_pattern)),
                       more=tweet.AsDict())

  for user in tweet.user_mentions:
    get_or_create(session, PostDistribution,
                  post=post,
                  recipient=insert_user_from_json(twitter_api, session, user),
                  rel="to")

  session.commit()

  return post
