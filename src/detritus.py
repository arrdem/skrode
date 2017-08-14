"""
A bunch of stupid bits and bats in a vaguely functional style.
"""

from functools import wraps


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
