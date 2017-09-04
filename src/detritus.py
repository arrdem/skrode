"""
A bunch of stupid bits and bats in a vaguely functional style.
"""

from functools import wraps
import re


def with_idx(iter):
  count = 0
  for e in iter:
    yield count, e
    count = count + 1


def once(f):
  """Calls f once and only once. Future calls will yield the first result."""
  val = None

  @wraps(f)
  def inner(*args, **kwargs):
    nonlocal val
    if val is None:
      val = f(*args, **kwargs)
    return val

  return inner


def cammel2snake(name):
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
