"""
BBDB schema
"""

from sqlalchemy import Column, ForeignKey, Integer, String, Unicode
from sqlalchemy.types import BigInteger
from sqlalchemy.orm import relationship, backref, composite
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy_utils import ArrowType


class Base(declarative_base()):
  """
  Base class. Provides a repr() and not much more.
  """

  def __repr__(self):
    return "<{} {}>"\
      .format(
        self.__cls__.__name__,
        ", ".join(["%s=%r" % (k, getattr(self, k)) for k in dir(self)
                   if not k.startswith("_") and
                   "_id" not in k and
                   not k == "metadata" and getattr(self, k)]))


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

  For instance a physical mailbox or an email address or a twitter handle which may have many-to-one
  access.

  For instance @arrdemsays is a Twitter account which has multiple contributors. As is @drill etc.
  """

  __tablename__ = "personas"

  id = Column(Integer, primary_key=True, autoincrement=True)
  names = relationship("Name", back_populates="persona")
  handles = relationship("Handle", back_populates="persona")

  suspicions = relationship("Suspicion")
  members = relationship("Member")

  owner_id = Column(BigInteger, ForeignKey("people.id"), nullable=True)
  owner = relationship("Person", back_populates="personas")


class Name(Base):
  """
  Names or Aliases are associated with Personas.
  """

  __tablename__ = "names"

  id = Column(Integer, primary_key=True, autoincrement=True)
  name = Column(String, nullable=False)
  persona_id = Column(BigInteger, ForeignKey("personas.id"))
  persona = relationship("Persona", back_populates="names")

  def __repr__(self):
    return "<Name %r>" % (self.name,)

  def __str__(self):
    return self.name


class Handle(Base):
  """
  Accounts are associated with personas.
  """

  __tablename__ = "twitters"

  id = Column(BigInteger, primary_key=True)
  persona_id = Column(BigInteger, ForeignKey("personas.id"))
  persona = relationship("Persona", back_populates="twitter_accounts")
  display_names = relationship("TwitterDisplayName")
  screen_names = relationship("TwitterScreenName")

  @property
  def screen_name(self):
    return self.screen_names[-1].handle

  @property
  def display_name(self):
    return self.display_names[-1].handle

  def __repr__(self):
    return "<Handle %r \"@%s\">" % (self.id, self.screen_name)


class DisplayName(Base):
  """
  Accounts have rather a lot of data such as display names which may change and isn't essential to
  the concept of the user.

  Display names are what we call the user's easily customized name. Some people change it quite a
  lot, frequently as a joke or other statement. Tracking those may be interesting.
  """

  __tablename__ = "display_names"

  id = Column(Integer, primary_key=True, autoincrement=True)
  handle = Column(String, nullable=False)
  account_id = Column(BigInteger, ForeignKey("twitters.id"))
  account = relationship("TwitterHandle", back_populates="display_names", single_parent=True)
  when = Column(ArrowType)


class ScreenName(Base):
  """
  Twitter accounts have a publicly visible name - the famous @ handle. This is what we call the
  screen name.

  Screen names don't change often, but for various reasons Twitter accounts can change screen name.
  For instance name disputes, or simple fancy may cause users to alter their screen name.

  This table exists in part because mapping screen names to "real" Twitter internal IDs consumes
  Twitter API calls which are expensive and should be used sparingly.
  """

  __tablename__ = "screen_names"

  id = Column(Integer, primary_key=True, autoincrement=True)
  handle = Column(String, nullable=False)
  account_id = Column(BigInteger, ForeignKey("twitters.id"))
  account = relationship("Handle", back_populates="screen_names", single_parent=True)
  when = Column(ArrowType)


class Follows(Base):
  """
  Accounts follow each-other. This table represents one user following another.
  """

  __tablename__ = "follows"

  id = Column(Integer, primary_key=True, autoincrement=True)
  follows_id = Column(BigInteger, ForeignKey("twitters.id"))
  follower_id = Column(BigInteger, ForeignKey("twitters.id"))
  when = Column(ArrowType)


class Website(Base):
  """
  Websites are associated with personas.
  """

  __tablename__ = "websities"

  id = Column(Integer, primary_key=True, autoincrement=True)
  handle = Column(String, nullable=False)
  persona_id = Column(BigInteger, ForeignKey("personas.id"))
  persona = relationship("Persona", back_populates="websites")

  @property
  def url(self):
    return self.handle


class PhoneNumber(Base):
  """
  People still have tellephones for whatever damnfool reason.
  """

  __tablename__ = "telephones"

  id = Column(Integer, primary_key=True, autoincrement=True)
  handle = Column(String, nullable=False)
  persona_id = Column(BigInteger, ForeignKey("personas.id"))
  persona = relationship("Persona", back_populates="phone_numbers")

  def __str__(self):
    return self.handle


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


def get_or_create(session, model, **kwargs):
  instance = session.query(model).filter_by(**kwargs).first()
  if not instance:
    instance = model(**kwargs)
    session.add(instance)
    session.commit()
  return instance
