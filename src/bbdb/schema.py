"""
BBDB schema
"""

import uuid

from sqlalchemy import Column, ForeignKey, Integer, Unicode, CheckConstraint, column
from sqlalchemy.types import Enum
from sqlalchemy.sql import select, join
from sqlalchemy.orm import relationship, Query
from sqlalchemy.orm.session import object_session
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy_utils import ArrowType, UUIDType
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property

from detritus import cammel2snake as convert


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
    return convert(cls.__name__)

  @declared_attr
  def more(cls):
    return Column(JSONB)


Base = declarative_base(cls=Base)


UUID = UUIDType()


class UUIDed(object):
  """A mixin used for UUID indexes."""

  @declared_attr
  def id(cls):
    return Column(UUID,
                  primary_key=True,
                  default=uuid.uuid4)


class Named(object):
  """A mixin for things which have interned name strings."""

  @declared_attr
  def name(cls):
    return Column(Unicode)


class Human(Base, UUIDed):
  """
  The record type for an entity in the BBDB.

  People don't actually do much, they just have an identifier.

  People are the identifier against which other records are joined.

  People are immutable.
  """

  memberships = relationship("Persona",
                             secondary="persona_control",
                             primaryjoin="and_(Human.id==PersonaControl.human_id, or_(PersonaControl.rel=='owns', PersonaControl.rel=='participates'))")
  suspicions = relationship("Persona",
                            secondary="persona_control",
                            primaryjoin="and_(Human.id==PersonaControl.human_id, PersonaControl.rel=='suspected')")
  personas = relationship("Persona",
                          secondary="persona_control",
                          primaryjoin="and_(Human.id==PersonaControl.human_id, PersonaControl.rel=='owns')")


class Persona(Base, UUIDed):
  """
  Personas represent an account (access) or set of accesses.

  For instance a physical mailbox or an email address or a twitter handle which may have many-to-one
  access.

  For instance @arrdemsays is a Twitter account which has multiple contributors. As is @drill etc.
  """

  @hybrid_property
  def names(self):
    return set(self.account_names + self.linked_names)

  linked_names = relationship("Name",
                              cascade="all, delete-orphan")

  account_names = relationship("Name",
                               secondary="account",
                               primaryjoin="Account.persona_id == Persona.id",
                               secondaryjoin="Name.account_id == Account.id")

  accounts = relationship("Account", back_populates="persona",
                          cascade="all, delete-orphan")

  def __repr__(self):
    return "<Persona {0!r} on {1!r}>".format([name.name for name in self.names],
                                             [account.service.name for account in self.accounts])


PERSONARELATIONSHIP = Enum("owns", "participates", "suspected",
                           name="_persona_rel")


class PersonaControl(Base, UUIDed):
  """Associates Humans and Personas with PERSONARELATIONSHIPs.

  This allows us to somewhat decouple the idea of relating personas to humans from a hardcoded
  schema which may be subject to refactoring or future evolution while retaining indexable
  relations.

  """

  human_id = Column(UUID, ForeignKey("human.id"))
  human = relationship("Human")

  persona_id = Column(UUID, ForeignKey("persona.id"))
  persona = relationship("Persona")

  rel = Column(PERSONARELATIONSHIP)


class Service(Base, Named, UUIDed):
  """
  Services are records for where an account exists.
  """

  urls = relationship("ServiceURL")

  def __repr__(self):
    return "<Service %r>" % self.name


class ServiceURL(Base, UUIDed):
  """Records a URL corresponding to a service."""

  service_id = Column(UUID, ForeignKey("service.id"), nullable=True)
  service = relationship("Service")

  url = Column(Unicode, unique=True, index=True, nullable=False)


class Account(Base, UUIDed):
  """
  Handles are accounts on services, associated with personas.

  Some services let an account take on multiple names, or change a transitory "display" name while
  retaining a somewhat permanent name or internal identifier which may be exposed.
  """

  external_id = Column(Unicode, nullable=False, unique=True, index=True)

  service_id = Column(UUID, ForeignKey("service.id"))
  service = relationship("Service")

  # The relationship with the persona type
  persona_id = Column(UUID, ForeignKey("persona.id"), nullable=False)
  persona = relationship("Persona", back_populates="accounts")

  names = relationship("Name", uselist=True, cascade="all, delete-orphan")

  def __repr__(self):
    return "<Account %r %r>" % (self.external_id, [n.name for n in self.names][-3:])


class Name(Base, Named, UUIDed):
  """
  Names or Aliases are associated with Personas, Accounts and many other structures.

  Name strings are interned, although names references are unique to a persona.
  """

  account_id = Column(UUID, ForeignKey("account.id"))
  account = relationship("Account", single_parent=True)

  persona_id = Column(UUID, ForeignKey("persona.id"), nullable=True)
  persona = relationship("Persona", single_parent=True)

  when = Column(ArrowType)

  some_fk = CheckConstraint("persona_id IS NOT NULL OR account_id IS NOT NULL")

  def __repr__(self):
    return "<Name %r>" % (self.name,)

  def __str__(self):
    return self.name


ACCOUNTREL = Enum("follows", "blocks", "ignores",
                  name="_account_rel")


class AccountRelationship(Base, UUIDed):
  """A Left and Right account, related by an ACCOUNTREL. a->b"""

  left_id = Column(UUID, ForeignKey("account.id"))
  left = relationship("Account", foreign_keys=[left_id])

  right_id = Column(UUID, ForeignKey("account.id"))
  right = relationship("Account", foreign_keys=[right_id])

  rel = Column(ACCOUNTREL)
  when = Column(ArrowType)


class ListMembership(Base, UUIDed):
  """Side table. Relates Accounts to Lists, where appropriate."""

  list_id = Column(UUID, ForeignKey("list.id"))
  account_id = Column(UUID, ForeignKey("account.id"))


class List(Base, UUIDed, Named):
  """Used to group Posts and Threads of Posts together."""

  # Lists are hosted on a service
  service_id = Column(UUID, ForeignKey("service.id"))
  service = relationship("Service")

  members = relationship("Account", secondary="list_membership")
  threads = relationship("Post", secondary="post_distribution")


class Post(Base, UUIDed):
  """Used to record a post by an account."""

  # Who posted
  poster_id = Column(UUID, ForeignKey("account.id"), index=True)
  poster = relationship("Account")

  # Posts come in parent/child threads
  thread_id = Column(UUID, ForeignKey("post.id"), nullable=True, index=True)
  thread = relationship("Post", back_populates="children")
  children = relationship("Post")

  # Who all saw it
  distribution = relationship("PostDistribution")
  when = Column(ArrowType)

  # The post itself
  text = Column(Unicode)


POSTDIST = Enum("broadcast", "to", "cc", "bcc",
                name="_post_rel")


class PostDistribution(Base, UUIDed):
  """Used to record the distribution of a post."""

  post_id = Column(UUID, ForeignKey("post.id"), nullable=True)
  post = relationship("Post", back_populates="distribution", single_parent=True)
  recipient_id = Column(UUID, ForeignKey("account.id"), nullable=True)
  recipient = relationship("Account", single_parent=True)
  list_id = Column(UUID, ForeignKey("list.id"))
  list = relationship("List")

  rel = Column(POSTDIST)

  some_fk = CheckConstraint("post_id IS NOT NULL OR recipient_id IS NOT NULL")
