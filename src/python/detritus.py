"""
A bunch of stupid bits and bats in a vaguely functional style.
"""

from __future__ import absolute_import, print_function

from functools import wraps
import re


def with_idx(iter):
  """Iterate over pairs idx, e for all e in the iterable."""

  count = 0
  for e in iter:
    yield count, e
    count = count + 1


def once(f):
  """Calls f once and only once. Future calls will yield the first result."""
  val = [None]

  @wraps(f)
  def inner(*args, **kwargs):
    if val[0] is None:
      val[0] = f(*args, **kwargs)
    return val[0]

  return inner


def camel2snake(name):
  """Map a string from camel case to snake case."""

  s1 = re.sub("(.)([A-Z][a-z]+)", r'\1_\2', name)
  return re.sub("([a-z0-9])([A-Z])", r'\1_\2', s1).lower()


def unique_by(coll, fn):
  """Takes a collection and a transformer, yielding the unique (un-transformed!) elements, where
  uniqueness is judged with respect to the transformer's value(s) over the source.

  """

  acc = set()
  for e in coll:
    x = fn(e)
    if x not in acc:
      acc.add(x)
      yield e
