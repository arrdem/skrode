"""
A quick and dirty script to ingest my live Twitter feed.
"""

import argparse
import json
import signal
import sys
import time
from threading import Event, Thread

from bbdb import twitter as bt
from bbdb.schema import Post
from bbdb import config, make_session_factory, rds_for_config
from bbdb.redis.workqueue import WorkQueue

from twitter.models import Status, User
from twitter.error import TwitterError


args = argparse.ArgumentParser()
args.add_argument("-c", "--config",
                  dest="config",
                  default="config.yml")


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

    print("[DEBUG]", bt.insert_user(session, tweet.user))

  else:
    print("[DEBUG]", bt.insert_tweet(session, twitter_api, tweet))

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
      print("[DEBUG]", bt.insert_user(session, user))


def ingest_tweet_queue(shutdown_event, session, rds, twitter_api, tweet_queue):
  """Worker thead which will ingest tweets by ID from a redis queue until the event becomes set."""

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
            print("[WARN] https://twitter.com/i/status/{}".format(status_id.decode()), e)
            dummy = bt._tweet_or_dummy(session, status_id)
            dummy.tombstone = True
            session.add(dummy)
            session.flush()
      continue
    else:
      # There was nothing to do, wait, don't heat up the room.
      time.sleep(5)


def ingest_twitter_stream(shutdown_event, session, rds, twitter_api, tweet_queue, stream):
  """
  Ingest a Twitter stream, enqueuing tweets and users for eventual processing.
  """

  def _ingest_event(event):
    """Helper function which does the individual inserts.

    Used to factor inserts like retweets and quotes which may contain their substructures directly,
    and thus avoid needing to become queued and get processed from a work queue.

    """

    if event and event.get("event"):
      # This is the case of a non-message event

      # FIXME: see other interesting cases here:
      # https://dev.twitter.com/streaming/overview/messages-types

      print("[INFO]", json.dumps(event))

      if event.get("source"):
        print("[INFO]", bt.insert_user(session, User.NewFromJsonDict(event.get("source"))))

      if event.get("target"):
        print("[INFO]", bt.insert_user(session, User.NewFromJsonDict(event.get("target"))))

      if event.get("event") in ["favorite", "unfavorite", "quoted_tweet"]:
        # We're ingesting a tweet here
        _ingest_event(event.get("target_object"))

    elif event.get("delete"):
      # For compliance with the developer rules.
      # Sadly.

      entity = bt._tweet_or_dummy(session, event.get("delete")
                                  .get("status")
                                  .get("id"))
      entity.tombstone = True
      session.add(entity)
      session.commit()

    elif event and "id" in event and "user" in event:
      if "extended_tweet" in event:
        # This is the case of having gotten a new "extended" tweet.
        # Need to munge the text representation.
        #
        # And by munge I just mean copy, because the twitter-python driver drops this on the floor
        event["text"] = event["extended_tweet"]["full_text"]

      ingest_tweet(session, rds, twitter_api, tweet_queue, Status.NewFromJsonDict(event))
    else:
      print("[DEBUG]", json.dumps(event))

  with open("log.json", "a") as f:
    for event in stream:
      _ingest_event(event)

      f.write(json.dumps(event) + "\n")
      f.flush()

      if shutdown_event.is_set():
        break


def main():
  # Opts
  ########################################
  opts = args.parse_args(sys.argv[1:])
  bbdb_config = config.BBDBConfig(config=opts.config)

  # SQL
  ########################################
  session_factory = make_session_factory(config=bbdb_config)
  session = session_factory()

  # Redis
  ########################################
  rds = rds_for_config(config=bbdb_config)
  tweet_queue = WorkQueue(rds, "/queue/twitter/tweets", inflight="/queue/twitter/tweets/inflight")
  user_queue = WorkQueue(rds, "/queue/twitter/users", inflight="/queue/twitter/users/inflight")

  # Twitter
  ########################################
  twitter_api = bt.api_for_config(bbdb_config, sleep_on_rate_limit=True)
  twitter_stream = twitter_api.GetUserStream(withuser="followings",
                                             stall_warnings=True,
                                             replies='all')

  # Signal handlers
  ########################################
  # Establish signal handlers so that we'll run and shut down gracefully
  shutdown = Event()

  def _handler(signum, frame):
    shutdown.set()

  for sig in (signal.SIGINT,):
    signal.signal(sig, _handler)

  stream_thread = Thread(target=ingest_twitter_stream,
                         args=(shutdown, session_factory(), rds, twitter_api, tweet_queue, twitter_stream)
  ).start()

  queue_thread = Thread(target=ingest_tweet_queue,
                        args=(shutdown, session_factory(), rds, twitter_api, tweet_queue)
  ).start()

  while not shutdown.is_set():
    count = len(tweet_queue)
    if count != 0:
      print("[INFO] {} items in the tweet queue".format(count))

    for post_id, in session.query(Post.external_id)\
                           .filter(Post.poster==None,
                                   Post.service==bt.insert_twitter(session),
                                   Post.tombstone==False)\
                          .all():
      tweet_queue.put(post_id.split(":")[1])

    time.sleep(5)


if __name__ == "__main__":
  main()
