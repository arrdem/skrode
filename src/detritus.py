"""
A bunch of stupid bits and bats in a vaguely functional style.
"""


def with_idx(iter):
  count = 0
  for e in iter:
    yield count, e
    count = count + 1
