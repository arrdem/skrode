"""
BBDB schema
"""

from enum import Enum as _Enum

from sqlalchemy import Column, ForeignKey, Integer, Unicode
from sqlalchemy.types import BigInteger, Enum
from sqlalchemy.orm import relationship, backref, composite
from sqlalchemy.orm.session import object_session
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy_utils import ArrowType
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method


def get_or_create(session, model, **kwargs):
  instance = session.query(model).filter_by(**kwargs).first()
  if not instance:
    instance = model(**kwargs)
    session.add(instance)
    session.commit()
  return instance


class Base(object):
  """
  Base class. Provides a repr() and not much more.
  """

  @property
  def session(self):
    return object_session(self)
  
  @declared_attr
  def __tablename__(cls):
    return cls.__name__.lower()

  def __repr__(self):
    return "<{} {}>"\
      .format(
        self.__cls__.__name__,
        ", ".join(["%s=%r" % (k, getattr(self, k)) for k in dir(self)
                   if not k.startswith("_") and
                   "_id" not in k and
                   not k == "metadata" and getattr(self, k)]))

Base = declarative_base(cls=Base)

class UUIDed(object):
  """A mixin used for UUID indexes."""

  @declared_attr
  def id(cls):
    return Column(UUID, primary_key=True)


class InternedUnicode(Base, UUIDed):
  """
  A table used for storing interned strings. Everything joins against this. May be indexed.
  """

  text = Column(Unicode, nullable=False)

  def __str__(self):
    return self.text


class Named(object):
  """A mixin for things which have interned name strings."""

  @declared_attr
  def _name_id(cls):
    return Column(UUID, ForeignKey("internedunicode.id"))

  @declared_attr
  def _name(cls):
    return relationship("InternedUnicode")

  @hybrid_property
  def name(self):
    if self._name:
      return self._name.text
    else:
      return ""

  @name.setter
  def name(self, value):
    self._name_id = get_or_create(self.session, session.InternedUnicode,
                                  text=unicode(value))


class Human(Base, UUIDed):
  """
  The record type for an entity in the BBDB.

  People don't actually do much, they just have an identifier.

  People are the identifier against which other records are joined.

  People are immutable.
  """

  memberships = relationship("Member")
  suspicions = relationship("Suspicion")
  personas = relationship("Persona")


class Persona(Base, UUIDed):
  """
  Personas represent an account (access) or set of accesses.

  For instance a physical mailbox or an email address or a twitter handle which may have many-to-one
  access.

  For instance @arrdemsays is a Twitter account which has multiple contributors. As is @drill etc.
  """

  id = Column(UUID, primary_key=True)
  names = relationship("PersonaName", back_populates="persona")
  account = relationship("Accounts", back_populates="persona")
  urls = relationship("Url", back_populates="persona")

  suspicions = relationship("Suspicion")
  members = relationship("Member")

  owner_id = Column(UUID, ForeignKey("human.id"), nullable=True)
  owner = relationship("Human", back_populates="personas")


class Name(Base, Named, UUIDed):
  """
  Names or Aliases are associated with Personas.

  Name strings are interned, although names references are unique to a persona.
  """

  persona_id = Column(UUID, ForeignKey("persona.id"))
  persona = relationship("Persona", back_populates="names")

  def __repr__(self):
    return "<Name %r>" % (self.name,)

  def __str__(self):
    return self.name


class Service(Base, Named, UUIDed):
  """
  Services are records for where an account exists.
  """

  url = Column(Unicode, nullable=False)


class Account(Base, UUIDed):
  """
  Handles are accounts on services, associated with personas.

  Some services let an account take on multiple names, or change a transitory "display" name while
  retaining a somewhat permanent name or internal identifier which may be exposed.
  """

  external_id = Column(Unicode, nullable=False)

  service_id = Column(UUID, ForeignKey("service.id"))
  service = relationship("Service")

  # The relationship with the persona type
  persona_id = Column(UUID, ForeignKey("persona.id"))
  persona = relationship("Persona", back_populates="accounts")

  names = relationship("AccountName")

  # Want more shit? Throw it here.
  more = Column(JSONB)

  def __repr__(self):
    return "<Account %r \"@%s\">" % self.id


class AccountName(Base, Named, UUIDed):
  """
  Accounts have rather a lot of data such as display names which may change and isn't essential to
  the concept of the user.

  Account names or screen names are what we call the user's easily customized name. Some people
  change it quite a lot, frequently as a joke or other statement. Tracking those may be interesting.
  """

  account_id = Column(UUID, ForeignKey("account.id"))
  account = relationship("Account", back_populates="names", single_parent=True)
  when = Column(ArrowType)


class ACCOUNTRELATIONSHIP(_Enum):
  none = 0
  follows = 1
  ignores = 2
  blocks = 3


class AccountRelationship(Base, UUIDed):
  """A Left and Right account, related by an ACCOUNTRELATIONSHIP. a->b"""

  id = Column(UUID, primary_key=True)
  left_id = Column(UUID, ForeignKey("account.id"))
  right_id = Column(UUID, ForeignKey("account.id"))
  rel = Column(Enum(ACCOUNTRELATIONSHIP))


class POSTDISTRIBUTION(_Enum):
  broadcast = 0
  to = 1
  cc = 2
  bcc = 3


class Post(Base, UUIDed):
  """Used to record a post by an account."""

  # Who posted
  poster_id = Column(UUID, ForeignKey("account.id"))
  poster = relationship("Account")

  # Who all saw it
  distribution = relationship("PostDistribution")

  # The post itself
  text = Column(Unicode)

  # Got more? Stick it here.
  more = Column(JSONB)


class PostDistribution(Base, UUIDed):
  """Used to record the distribution of a post."""

  post_id = Column(UUID, ForeignKey("post.id"))
  post = relationship("Post", back_populates="distribution", single_parent=True)
  recipient_id = Column(UUID, ForeignKey("account.id"))
  recipient = relationship("Account", single_parent=True)
  distribution = Column(Enum(POSTDISTRIBUTION))


  class Suspicion(Base, UUIDed):
  """
  We don't always know who owns a Profile. There may be many people, there may be one person and we
  just don't have enough information to identify who it is.

  The suspicion class is an adjacency mapping between People and Profiles.
  """

  person_id = Column(UUID, ForeignKey("human.id"))
  person = relationship("Person", back_populates="suspicions")
  persona_id = Column(UUID, ForeignKey("persona.id"))
  persona = relationship("Persona", back_populates="suspicions")


class Member(Base, UUIDed):
  """
  Sometimes we do know who participates in a profile. There may even be many people particularly in
  the case of pen names and groups.

  The Member class is an adjacency mapping between People and Profiles.
  """

  person_id = Column(UUID, ForeignKey("human.id"))
  person = relationship("Person", back_populates="memberships")
  persona_id = Column(UUID, ForeignKey("persona.id"))
  persona = relationship("Persona", back_populates="members")

