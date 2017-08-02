"""
BBDB schema
"""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


class Person(Base):
  """
  The record type for an entity in the BBDB.

  People don't actually do much, they just have an identifier.

  People are the identifier against which other records are joined.

  People are immutable.
  """

  __tablename__ = 'people'

  id = Column(Integer, primary_key=True)


class Persona(Base):
  """
  Personas represent an account (access) or set of accesses.

  For instance a physical mailbox or an email address or a twitter handle which may have many-to-one access.

  For instance @arrdemsays is a Twitter account which has multiple contributors. As is @drill etc.
  """

  __tablename__ = 'personas'

  id = Column(Integer, primary_key=True)


class Name(Base):
  """
  Names or Aliases are associated with Personas.
  """

  __tablename__ = 'names'

  id = Column(Integer, primary_key=True)
  name = Column(String, nullable=False)
  persona = relationship("Persona", back_populates="names")


class TwitterHandle(Base):
  """
  Twitter accounts are associated with personas.
  """

  __tablename__ = 'twitters'

  id = Column(Integer, primary_key=True)
  handle = Column(String, nullable=False)
  persona_id = Column(Integer, ForeignKey('personas.id'))
  persona = relationship("Persona", back_populates="twitter_accounts")


class EmailHandle(Base):
  """
  Email addresses are associated with personas.
  """

  __tablename__ = 'emails'

  id = Column(Integer, primary_key=True)
  handle = Column(String, nullable=False)
  persona_id = Column(Integer, ForeignKey('personas.id'))
  persona = relationship("Persona", back_populates="email_accounts")


class GithubHandle(Base):
  """
  GitHub accounts are associated with personas.
  """

  __tablename__ = 'githubs'

  id = Column(Integer, primary_key=True)
  handle = Column(String, nullable=False)
  persona_id = Column(Integer, ForeignKey('personas.id'))
  persona = relationship("Persona", back_populates="github_accounts")


class KeybaseHandle(Base):
  """
  Keybase accounts are associated with personas.

  This account type can almost be assumed to be 1:1, but you never know and #opsec
  """

  __tablename__ = 'keybases'

  id = Column(Integer, primary_key=True)
  handle = Column(String, nullable=False)
  persona_id = Column(Integer, ForeignKey('personas.id'))
  persona = relationship("Persona", back_populates="keybase_accounts")


class Website(Base):
  """
  Websites are associated with personas.
  """

  __tablename__ = 'websities'

  id = Column(Integer, primary_key=True)
  handle = Column(String, nullable=False)
  persona_id = Column(Integer, ForeignKey('personas.id'))
  persona = relationship("Persona", back_populates="websites")
1
