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

  __tablename__ = "people"

  id = Column(Integer, primary_key=True)
  memberships = relationship("Member")
  suspicions = relationship("Suspicion")
  personas = relationship("Persona")


class Persona(Base):
  """
  Personas represent an account (access) or set of accesses.

  For instance a physical mailbox or an email address or a twitter handle which may have many-to-one access.

  For instance @arrdemsays is a Twitter account which has multiple contributors. As is @drill etc.
  """

  __tablename__ = "personas"

  id = Column(Integer, primary_key=True)
  names = relationship("Name", back_populates="persona")
  twitter_accounts = relationship("TwitterHandle", back_populates="persona")
  email_accounts = relationship("EmailHandle", back_populates="persona")
  github_accounts = relationship("GithubHandle", back_populates="persona")
  keybase_accounts = relationship("KeybaseHandle", back_populates="persona")
  websites = relationship("Website", back_populates="persona")

  suspicions = relationship("Suspicion")
  members = relationship("Member")

  owner_id = Column(Integer, ForeignKey("people.id"), nullable=True)
  owner = relationship("Person", back_populates="personas", single_parent=True)


class Name(Base):
  """
  Names or Aliases are associated with Personas.
  """

  __tablename__ = "names"

  id = Column(Integer, primary_key=True)
  name = Column(String, nullable=False)
  persona_id = Column(Integer, ForeignKey("personas.id"))
  persona = relationship("Persona", back_populates="names")


class TwitterHandle(Base):
  """
  Twitter accounts are associated with personas.
  """

  __tablename__ = "twitters"

  id = Column(Integer, primary_key=True)
  handle = Column(String, nullable=False)
  persona_id = Column(Integer, ForeignKey("personas.id"))
  persona = relationship("Persona", back_populates="twitter_accounts")


class EmailHandle(Base):
  """
  Email addresses are associated with personas.
  """

  __tablename__ = "emails"

  id = Column(Integer, primary_key=True)
  handle = Column(String, nullable=False)
  persona_id = Column(Integer, ForeignKey("personas.id"))
  persona = relationship("Persona", back_populates="email_accounts")


class GithubHandle(Base):
  """
  GitHub accounts are associated with personas.
  """

  __tablename__ = "githubs"

  id = Column(Integer, primary_key=True)
  handle = Column(String, nullable=False)
  persona_id = Column(Integer, ForeignKey("personas.id"))
  persona = relationship("Persona", back_populates="github_accounts")


class KeybaseHandle(Base):
  """
  Keybase accounts are associated with personas.

  This account type can almost be assumed to be 1:1, but you never know and #opsec
  """

  __tablename__ = "keybases"

  id = Column(Integer, primary_key=True)
  handle = Column(String, nullable=False)
  persona_id = Column(Integer, ForeignKey("personas.id"))
  persona = relationship("Persona", back_populates="keybase_accounts")


class Website(Base):
  """
  Websites are associated with personas.
  """

  __tablename__ = "websities"

  id = Column(Integer, primary_key=True)
  handle = Column(String, nullable=False)
  persona_id = Column(Integer, ForeignKey("personas.id"))
  persona = relationship("Persona", back_populates="websites")


class Suspicion(Base):
  """
  We don't always know who owns a Profile. There may be many people, there may be one person and we
  just don't have enough information to identify who it is.

  The suspicion class is an adjacency mapping between People and Profiles.
  """

  __tablename__ = "suspicions"
  
  id = Column(Integer, primary_key=True)
  person_id = Column(Integer, ForeignKey("people.id"))
  person = relationship("Person", back_populates="suspicions")
  persona_id = Column(Integer, ForeignKey("personas.id"))
  persona = relationship("Persona", back_populates="suspicions")


class Member(Base):
  """
  Sometimes we do know who participates in a profile. There may even be many people particularly in
  the case of pen names and groups.

  The Member class is an adjacency mapping between People and Profiles.
  """

  __tablename__ = "memberships"
  
  id = Column(Integer, primary_key=True)
  person_id = Column(Integer, ForeignKey("people.id"))
  person = relationship("Person", back_populates="memberships")
  persona_id = Column(Integer, ForeignKey("personas.id"))
  persona = relationship("Persona", back_populates="members")
