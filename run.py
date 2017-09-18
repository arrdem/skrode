"""
Run the entire BBDB topology.
"""

import argparse
import logging
import signal
import sys
import threading
import time
from multiprocessing import Process
import os
from queue import Queue, Empty

from bbdb.config import BBDBConfig


args = argparse.ArgumentParser()
args.add_argument("-c", "--config",
                  dest="config",
                  default="config.yml")


def _import(path):
  """Import a named member from a fully qualified module path."""
  _path = path.split(".")
  module = __import__(".".join(_path[:-1]))
  return getattr(module, _path[-1])


WORKER_REGISTRY = {}


def worker(name):
  def _inner(func):
    global WORKER_REGISTRY
    WORKER_REGISTRY[name] = func
    return func
  return _inner


@worker("map")
def map_worker(event, target, source, session, type=None, sleep=1, **kwargs):
  """A worker which just maps over the items on a queue.

  Tries to read an item from the work queue, processes it if there is one, otherwise waits 5s.
  """

  target = _import(target)

  while not event.is_set():
    item = source.get()
    if item is not None:
      with item as item_contents:
        target(item_contents, session=session, **kwargs)
    else:
      # FIXME: make this a configurable strategy
      time.sleep(sleep)


@worker("custom")
def custom_worker(event, target, type=None, **kwargs):
  """
  A worker that gets to do whatever it wants. Completely unstructured.
  """

  target = _import(target)
  target(event=event, **kwargs)


def mk_sigint_event():
  event = threading.Event()

  def _sig_int(sig, frame):
    logging.getLogger(__name__).fatal("Got SIGINT, shutting down")
    event.set()

  signal.signal(signal.SIGINT, _sig_int)
  return event


def worker(opts, target_name):
  """Process entry point. Runs a worker selected out of the global topology configuration."""

  # Load the config for ourselves, initializing all connections & queues
  config = BBDBConfig(config=opts.config)

  # Provide a graceful shutdown signal handler
  event = mk_sigint_event()

  target = config.get(target_name).dict()
  logging.info("Booting worker %r", target_name)
  # We're gonna load up a single worker, and start running it.
  return WORKER_REGISTRY.get(target.get("type"))(event, **target)


def main(opts):
  logging.basicConfig(format="%(asctime)s %(levelname)s %(process)d %(name)s: %(message)s",
                      level=logging.INFO)
  log = logging.getLogger(__name__)

  config = BBDBConfig(config=opts.config)

  children = {}
  restarts = Queue()

  # Populate the restart queue
  for worker_name in config.get("workers"):
    restarts.put(worker_name)

  def _chld(sig, frame):
    pid, status = os.waitpid(-1, os.WNOHANG|os.WUNTRACED|os.WCONTINUED)
    if os.WIFCONTINUED(status) or os.WIFSTOPPED(status) or pid == 0:
      return
    elif os.WIFEXITED(status):
      job = children[pid]
      restarts.put(job)
      log.warn("Subprocess %d exited, job %r queued for restart", pid, job)
      del children[pid]

  signal.signal(signal.SIGCHLD, _chld)

  event = mk_sigint_event()
  while not event.is_set():
    # Restart all the dead children..
    while True:
      try:
        worker_name = restarts.get_nowait()
      except Empty:
        break

      ps = Process(target=worker, args=(opts, worker_name))
      ps.start()
      children[ps.pid] = worker_name

    time.sleep(5)


if __name__ == "__main__":
  main(args.parse_args(sys.argv[1:]))
