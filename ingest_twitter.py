"""
A quick and dirty script to ingest my live Twitter feed.
"""

import json
import signal
import time
import logging

from skrode import twitter as bt
from skrode.schema import Account, Post, PostRelationship, PostDistribution

from twitter.models import Status, User
from twitter.error import TwitterError
from requests import Session
from requests import exceptions as rex
from sqlalchemy import or_

log = logging.getLogger(__name__)


def have_user(session, id):
  """Get a Twitter account, or None if it doesn't exist yet."""
  return session.query(Account)\
                .filter(Account.external_id==bt.twitter_external_user_id(id))\
                .first()


def ingest_user(user_id, session, twitter_api):
  u = have_user(session, user_id)
  if u is None:
    user = twitter_api.GetUser(user_id=user_id)
    log.info("Created user %s", bt.insert_user(session, user))
  else:
    log.debug("Already had user %s", u)


def ingest_user_object(user, session):
  u = have_user(session, user.id)
  if u is None:
    log.info("Created user %s", bt.insert_user(session, user))
  else:
    log.debug("Already had user %s", u)


def have_tweet(session, id):
  """Get the Post for a Tweet ID, or None if it doesn't exist yet."""
  return session.query(Post)\
                .filter(Post.external_id==bt.twitter_external_tweet_id(id),
                        Post.when != None,
                        Post.service != None,
                        Post.text != None)\
                .first()


def ingest_tweet(tweet, session, twitter_api, tweet_id_queue):
  """Actually ingest a single tweet, dealing with the required enqueuing."""

  if not isinstance(tweet, Status):
    tweet = Status.NewFromJsonDict(tweet)

  if tweet.retweeted_status:
    # We don't actually care about retweets, they aren't original content.
    # Just insert the original.
    ingest_tweet(tweet.retweeted_status, session, twitter_api, tweet_id_queue)

    ingest_user_object(tweet.user, session)

  else:
    flag = have_tweet(session, tweet.id)
    t = bt.insert_tweet(session, twitter_api, tweet)
    if not flag:
      log.info(t)

    if tweet.in_reply_to_status_id:
      # This tweet is a reply. It links to some other tweet. Or possibly tweets depending on the
      # link content which may link many statuses. However Twitter only considers one status to
      # be the "reply" target. Create a "reply_to" relationship for the post we're inserting by
      # inserting its parent post(s) (recursively!)
      thread_id = str(tweet.in_reply_to_status_id)
      if not have_tweet(session, thread_id):
        tweet_id_queue.put(thread_id)
        pass

    if tweet.quoted_status:
      # This is a quote tweet (possibly subtweet or snarky reply, quote tweets have different
      # broadcast mechanics).
      ingest_tweet(tweet.quoted_status, session, twitter_api, tweet_id_queue)

    for url in tweet.urls or []:
      tweet_id = bt.tweet_id_from_url(url.expanded_url)
      if tweet_id and not have_tweet(session, tweet_id):
        tweet_id_queue.put(tweet_id)
        pass

    for user in tweet.user_mentions or []:
      if not isinstance(user, User):
        user = User.NewFromJsonDict(user)
      ingest_user_object(user, session)


def ingest_tweet_id(status_id, session, twitter_api, tweet_id_queue):
  """Mapped worker which will ingest tweets by ID."""

  status_id = str(status_id)  # Just to be sure...

  p = have_tweet(session, status_id)
  if p:
    log.info("Referenced existing tweet %s", p)
  else:
    try:
      ingest_tweet(twitter_api.GetStatus(status_id=status_id), session, twitter_api, tweet_id_queue)
    except TwitterError as e:
      # This probably means that either:
      # 1) I'm not allowed to see the content because the user is private
      # 2) The tweet has been deleted
      #
      # Either way, just warn and delete the record if one exists.
      log.warn("https://twitter.com/i/status/%s unavailable - %s", status_id, e)
      dummy = bt._tweet_or_dummy(session, status_id)
      dummy.tombstone = True
      session.add(dummy)
      session.flush()


def _ingest_event(stream_event, session, twitter_api, tweet_queue, user_queue):
  """Helper function which does the individual inserts.

  Used to factor inserts like retweets and quotes which may contain their substructures directly,
  and thus avoid needing to become queued and get processed from a work queue.

  """

  log.debug(json.dumps(stream_event))

  if stream_event and stream_event.get("event"):
    # This is the case of a non-message stream_event

    # FIXME: see other interesting cases here:
    # https://dev.twitter.com/streaming/overview/messages-types

    if stream_event.get("source"):
      ingest_user_object(User.NewFromJsonDict(stream_event.get("source")), session)

    if stream_event.get("target"):
      ingest_user_object(User.NewFromJsonDict(stream_event.get("target")), session)

    if stream_event.get("event") in ["favorite", "unfavorite", "quoted_tweet"]:
      # We're ingesting a tweet here
      _ingest_event(stream_event.get("target_object"), session, twitter_api, tweet_queue, user_queue)

  elif stream_event.get("delete"):
    # For compliance with the developer rules.
    # Sadly.
    event_id = stream_event.get("delete").get("status").get("id")
    log.warn("Honoring delete %s", event_id)
    entity = bt._tweet_or_dummy(session, event_id)
    entity.tombstone = True
    session.add(entity)
    session.commit()

  elif stream_event and "id" in stream_event and "user" in stream_event:
    if "extended_tweet" in stream_event:
      # This is the case of having gotten a new "extended" tweet.
      # Need to munge the text representation.
      #
      # And by munge I just mean copy, because the twitter-python driver drops this on the floor
      stream_event["text"] = stream_event["extended_tweet"]["full_text"]

    ingest_tweet(stream_event, session, twitter_api, tweet_queue)

  elif "friends" in stream_event:
    for friend in stream_event.get("friends"):
      user_queue.put(str(friend))

  else:
    blob = json.dumps(stream_event)
    with open("mystery.log", "a") as f:
      f.write(blob + "\n")
    log.warn(blob)


class TimeoutException(Exception):
  """Dummy used for timeouts."""


def user_stream(event, session, twitter_api, tweet_queue, user_queue, **stream_kwargs):
  """
  Ingest a Twitter stream, enqueuing tweets and users for eventual processing.
  """

  def _timeout_handler(sig, stack):
    raise TimeoutException()

  signal.signal(signal.SIGALRM, _timeout_handler)

  stream = None
  http_session = None
  while not event.is_set():
    if not http_session:
      http_session = Session()

    if not stream:
      stream = twitter_api.GetUserStream(**stream_kwargs)

    try:
      signal.alarm(35)
      for stream_event in stream:
        if stream_event:
          _ingest_event(stream_event, session, twitter_api, tweet_queue, user_queue)
        else:
          log.debug("keepalive....")

        # Update the alarm we're using for the keepalive signal...
        signal.alarm(35)

        if event.is_set():
          break

    except (TimeoutException, rex.ReadTimeout, rex.ConnectTimeout):
      stream = None
      http_session.close()
      http_session = None
      log.warn("Resetting stream due to timeout...")


def collect_empty_tweets(event, session, tweet_id_queue):
  while not event.is_set():
    for post_id, in session.query(Post.external_id)\
                           .filter(Post.poster==None,
                                   Post.service==bt.insert_twitter(session),
                                   Post.tombstone==False)\
                           .all():
      tweet_id_queue.put(post_id.split(":")[1])
      if event.is_set():
        break

    time.sleep(5)


def ensure_tombstones_empty(event, session):
  """Garbage collect posts to twitter which are tagged as tombstones.

  The Twitter API terms of service require that you not persist data for posts which have been
  deleted by their original author. This provides a worker which will garbage collect populated but
  deleted posts to maintain compliance.

  Amusingly this is literally how gnip solved the problem.

  """

  _t = bt.insert_twitter(session)
  while not event.is_set():
    # Delete post relationships where the post is deleted
    q = session.query(PostRelationship.id)\
               .join(Post, PostRelationship.left_id == Post.id)\
               .filter(Post.tombstone == True,
                       Post.service == _t)

    session.query(PostRelationship)\
           .filter(PostRelationship.id.in_(q.subquery()))\
           .delete(synchronize_session='fetch')

    # Delete post distribution records where the post is deleted
    q = session.query(PostDistribution.id)\
               .join(Post)\
               .filter(Post.tombstone == True,
                       Post.service == _t)

    session.query(PostDistribution)\
           .filter(PostDistribution.id.in_(q.subquery()))\
           .delete(synchronize_session='fetch')

    # "Delete" posts where the post is deleted
    log.info("Deleted %d posts",
             session.query(Post)\
                    .filter(Post.tombstone == True,
                            or_(Post.text != None,
                                Post.more != None),
                            Post.service == _t)\
                    .update({Post.text: None,
                             Post.more: None}))

    session.commit()

    time.sleep(5)
