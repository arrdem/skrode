"""
A quick and dirty script to ingest my live Twitter feed.
"""

import argparse
import json
import signal
import sys
import time
import logging as log
from multiprocessing import Event, Process

from bbdb import twitter as bt
from bbdb.schema import Account, Post
from bbdb import config, make_session_factory, rds_for_config
from bbdb.redis.workqueue import WorkQueue

from twitter.models import Status, User
from twitter.error import TwitterError
from requests import Session
from requests import exceptions as rex

args = argparse.ArgumentParser()
args.add_argument("-c", "--config",
                  dest="config",
                  default="config.yml")


def have_user(session, id):
  """Get a Twitter account, or None if it doesn't exist yet."""
  return session.query(Account)\
                .filter_by(external_id=bt.twitter_external_user_id(id))\
                .first()\


def ingest_user_queue(shutdown_event, session, rds, twitter_api, user_queue):
  session = session()

  while not shutdown_event.is_set():
    item = user_queue.get()
    if item is not None:
      with item as user_id:
        if not have_user(session, user_id):
          user = twitter_api.GetUser(user_id=user_id)
          print("[DEBUG 'ingest_user_queue']", bt.insert_user(session, user))
    else:
      time.sleep(5)


def have_tweet(session, id):
  """Get the Post for a Tweet ID, or None if it doesn't exist yet."""
  return session.query(Post)\
                .filter_by(external_id=bt.twitter_external_tweet_id(id))\
                .first()


def ingest_tweet(session, rds, twitter_api, tweet_queue, tweet):
  """Actually ingest a single tweet, dealing with the required enqueuing."""

  # Just in case
  session.rollback()
  if tweet.retweeted_status:
    # We don't actually care about retweets, they aren't original content.
    # Just insert the original.
    ingest_tweet(session, rds, twitter_api, tweet_queue, tweet.retweeted_status)

    log.debug(bt.insert_user(session, tweet.user))

  else:
    log.debug(bt.insert_tweet(session, twitter_api, tweet))

    if tweet.in_reply_to_status_id:
      # This tweet is a reply. It links to some other tweet. Or possibly tweets depending on the
      # link content which may link many statuses. However Twitter only considers one status to
      # be the "reply" target. Create a "reply_to" relationship for the post we're inserting by
      # inserting its parent post(s) (recursively!)
      thread_id = str(tweet.in_reply_to_status_id)
      if not have_tweet(session, thread_id):
        # FIXME: insert status ID into queue for later processing
        tweet_queue.put(thread_id)

    if tweet.quoted_status:
      # This is a quote tweet (possibly subtweet or snarky reply, quote tweets have different
      # broadcast mechanics).
      ingest_tweet(session, rds, twitter_api, tweet_queue, tweet.quoted_status)

    for url in tweet.urls or []:
      tweet_id = bt.tweet_id_from_url(url.expanded_url)
      if tweet_id and not have_tweet(session, tweet_id):
        tweet_queue.put(tweet_id)

    for user in tweet.user_mentions or []:
      if not isinstance(user, User):
        user = User.NewFromJsonDict(user)
      log.debug(bt.insert_user(session, user))


def ingest_tweet_queue(shutdown_event, session, rds, twitter_api, tweet_queue):
  """Worker thead which will ingest tweets by ID from a redis queue until the event becomes set."""

  session = session()

  while not shutdown_event.is_set():
    item = tweet_queue.get()
    if item is not None:
      with item as status_id:
        if not have_tweet(session, status_id):
          try:
            ingest_tweet(session, rds, twitter_api, tweet_queue,
                         twitter_api.GetStatus(status_id=status_id))
          except TwitterError as e:
            # This probably means that either:
            # 1) I'm not allowed to see the content because the user is private
            # 2) The tweet has been deleted
            #
            # Either way, just warn and delete the record if one exists.
            log.warn("https://twitter.com/i/status/{}".format(status_id.decode()), e)
            dummy = bt._tweet_or_dummy(session, status_id)
            dummy.tombstone = True
            session.add(dummy)
            session.flush()
      continue
    else:
      # There was nothing to do, wait, don't heat up the room.
      time.sleep(5)



class TimeoutException(Exception):
  """Dummy used for timeouts."""


def ingest_twitter_stream(shutdown_event, sql_session_factory, rds, twitter_api, tweet_queue,
                          user_queue, stream_factory):
  """
  Ingest a Twitter stream, enqueuing tweets and users for eventual processing.
  """

  sql_session = sql_session_factory()

  def _timeout_handler(sig, stack):
    raise TimeoutException()

  signal.signal(signal.SIGALRM, _timeout_handler)

  def _ingest_event(event):
    """Helper function which does the individual inserts.

    Used to factor inserts like retweets and quotes which may contain their substructures directly,
    and thus avoid needing to become queued and get processed from a work queue.

    """

    if event and event.get("event"):
      # This is the case of a non-message event

      # FIXME: see other interesting cases here:
      # https://dev.twitter.com/streaming/overview/messages-types
      log.info(json.dumps(event))

      if event.get("source"):
        log.info(bt.insert_user(sql_session, User.NewFromJsonDict(event.get("source"))))

      if event.get("target"):
        log.info(bt.insert_user(sql_session, User.NewFromJsonDict(event.get("target"))))

      if event.get("event") in ["favorite", "unfavorite", "quoted_tweet"]:
        # We're ingesting a tweet here
        _ingest_event(event.get("target_object"))

    elif event.get("delete"):
      # For compliance with the developer rules.
      # Sadly.
      log.info(json.dumps(event))

      entity = bt._tweet_or_dummy(sql_session, event.get("delete")
                                  .get("status")
                                  .get("id"))
      entity.tombstone = True
      sql_session.add(entity)
      sql_session.commit()

    elif event and "id" in event and "user" in event:
      if "extended_tweet" in event:
        # This is the case of having gotten a new "extended" tweet.
        # Need to munge the text representation.
        #
        # And by munge I just mean copy, because the twitter-python driver drops this on the floor
        event["text"] = event["extended_tweet"]["full_text"]

      ingest_tweet(sql_session, rds, twitter_api, tweet_queue, Status.NewFromJsonDict(event))

    elif "friends" in event:
      for friend in event.get("friends"):
        user_queue.put(str(friend))

    else:
      log.info(json.dumps(event))

  stream = None
  http_session = None
  while not shutdown_event.is_set():
    if not http_session:
      http_session = Session()

    if not stream:
      stream = stream_factory(http_session)

    try:
      signal.alarm(90)
      for event in stream:
        if event:
          _ingest_event(event)
          signal.alarm(90)
        else:
          log.debug("keepalive....")

        if shutdown_event.is_set():
          break

    except (TimeoutException, rex.ReadTimeout, rex.ConnectTimeout):
      stream = None
      http_session = None
      print("[DEBUG] Resetting stream due to timeout...")
      pass


def main():
  log.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=log.DEBUG)

# Opts
  ########################################
  opts = args.parse_args(sys.argv[1:])
  bbdb_config = config.BBDBConfig(config=opts.config)

  # SQL
  ########################################
  engine, session_factory = make_session_factory(config=bbdb_config)
  sql_session = session_factory()

  # Redis
  ########################################
  rds = rds_for_config(config=bbdb_config)
  tweet_queue = WorkQueue(rds, "/queue/twitter/tweets", inflight="/queue/twitter/tweets/inflight")
  user_queue = WorkQueue(rds, "/queue/twitter/users",
                         inflight="/queue/twitter/users/inflight",
                         decoder=lambda t: t.decode("utf-8"))

  # Twitter
  ########################################
  twitter_api = bt.api_for_config(bbdb_config, sleep_on_rate_limit=True)
  twitter_stream_factory = lambda session: twitter_api.GetUserStream(withuser="followings",
                                                                     stall_warnings=True,
                                                                     replies='all',
                                                                     include_keepalive=True,
                                                                     session=session)

  # Signal handlers
  ########################################
  # Establish signal handlers so that we'll run and shut down gracefully
  shutdown = Event()

  def _handler(signum, frame):
    shutdown.set()

  for sig in (signal.SIGINT,):
    signal.signal(sig, _handler)

  engine.dispose()

  stream_thread = Process(target=ingest_twitter_stream,
                          args=(shutdown, session_factory, rds, twitter_api, tweet_queue,
                                user_queue, twitter_stream_factory)
  ).start()

  queue_thread = Process(target=ingest_tweet_queue,
                         args=(shutdown, session_factory, rds, twitter_api, tweet_queue)
  ).start()

  user_thread = Process(target=ingest_user_queue,
                        args=(shutdown, session_factory, rds, twitter_api, user_queue)
  ).start()

  while not shutdown.is_set():
    count = len(tweet_queue)
    if count != 0:
      print("[INFO] {} items in the tweet queue".format(count))

    for post_id, in sql_session.query(Post.external_id)\
                               .filter(Post.poster==None,
                                       Post.service==bt.insert_twitter(sql_session),
                                       Post.tombstone==False)\
                               .all():
      tweet_queue.put(post_id.split(":")[1])

    time.sleep(5)


if __name__ == "__main__":
  main()
