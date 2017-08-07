"""
Basic tests that the schema works literally at all
"""

from bbdb import make_session_factory, schema

import pytest

session_factory = make_session_factory("sqlite:///:memory:")


@pytest.fixture
def session():
  return session_factory()


def test_schema(session):
  assert session.query(schema.Person).all() is not None
  assert session.query(schema.Persona).all() is not None
