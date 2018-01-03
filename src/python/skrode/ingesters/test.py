"""
A test data source.

Pushes a stream of random numbers to the given stream.
"""

import logging as log
from random import randint
from time import sleep


def random(event, queue, rate):
  """Custom queue worker.

  Puts random numbers on a queue, until the event becomes set.
  """
  while not event.is_set():
    for i in range(100):
      queue.put(randint(1, 10000))
    log.info("Wrote, napping")
    sleep(rate)


def do_print(number):
  """Queue map worker target.

  Just logs a number off a queue for diagnostics.
  """
  log.info(number)
