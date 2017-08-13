"""
BBDB schema
"""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.types import BigInteger
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy_utils.types.arrow import ArrowType


Base = declarative_base()


class Person(Base):
  """
  The record type for an entity in the BBDB.

  People don't actually do much, they just have an identifier.

  People are the identifier against which other records are joined.

  People are immutable.
  """

  __tablename__ = "people"

  id = Column(BigInteger, primary_key=True)
  memberships = relationship("Member")
  suspicions = relationship("Suspicion")
  personas = relationship("Persona")

  def __repr__(self):
    return "<Person {}>".format(", ".join(["%s=%r" % (k, getattr(self, k)) for k in dir(self)
                                           if not k.startswith("_") and
                                           "_id" not in k and
                                           not k == "metadata" and getattr(self, k)]))


class Persona(Base):
  """
  Personas represent an account (access) or set of accesses.

  For instance a physical mailbox or an email address or a twitter handle which may have many-to-one access.

  For instance @arrdemsays is a Twitter account which has multiple contributors. As is @drill etc.
  """

  __tablename__ = "personas"

  id = Column(BigInteger, primary_key=True)
  names = relationship("Name", back_populates="persona")
  twitter_accounts = relationship("TwitterHandle", back_populates="persona")
  email_accounts = relationship("EmailHandle", back_populates="persona")
  github_accounts = relationship("GithubHandle", back_populates="persona")
  keybase_accounts = relationship("KeybaseHandle", back_populates="persona")
  reddit_accounts = relationship("RedditHandle", back_populates="persona")
  lobsters_accounts = relationship("LobstersHandle", back_populates="persona")
  hn_accounts = relationship("HNHandle", back_populates="persona")

  websites = relationship("Website", back_populates="persona")

  suspicions = relationship("Suspicion")
  members = relationship("Member")

  owner_id = Column(BigInteger, ForeignKey("people.id"), nullable=True)
  owner = relationship("Person", back_populates="personas")

  def __repr__(self):
    return "<Persona {}>".format(", ".join(["%s=%r" % (k, getattr(self, k)) for k in dir(self)
                                            if not k.startswith("_") and
                                            "_id" not in k and
                                            not k == "metadata" and getattr(self, k)]))


class Name(Base):
  """
  Names or Aliases are associated with Personas.
  """

  __tablename__ = "names"

  id = Column(BigInteger, primary_key=True)
  name = Column(String, nullable=False)
  persona_id = Column(BigInteger, ForeignKey("personas.id"))
  persona = relationship("Persona", back_populates="names")

  def __repr__(self):
    return "<Name %r>" % (self.name,)

  def __str__(self):
    return self.name


class TwitterHandle(Base):
  """
  Twitter accounts are associated with personas.
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
    return "<TwitterHandle %r \"@%s\">" % (self.id, self.screen_name)


class TwitterDisplayName(Base):
  """
  Twitter accounts have rather a lot of data such as display names which may change and isn't
  essential to the concept of the user.

  Display names are what we call the user's easily customized name. Some people change it quite a
  lot, frequently as a joke or other statement. Tracking those may be interesting.
  """

  __tablename__ = "twitter_display_names"

  id = Column(BigInteger, primary_key=True)
  handle = Column(String, nullable=False)
  account_id = Column(BigInteger, ForeignKey("twitters.id"))
  account = relationship("TwitterHandle", back_populates="display_names", single_parent=True)
  when = Column(ArrowType)

  def __repr__(self):
    return "<TwitterDisplayName %r %r>" % (self.account_id, self.handle,)


class TwitterScreenName(Base):
  """
  Twitter accounts have a publicly visible name - the famous @ handle. This is what we call the
  screen name.

  Screen names don't change often, but for various reasons Twitter accounts can change screen name.
  For instance name disputes, or simple fancy may cause users to alter their screen name.

  This table exists in part because mapping screen names to "real" Twitter internal IDs consumes
  Twitter API calls which are expensive and should be used sparingly.
  """

  __tablename__ = "twitter_screen_names"

  id = Column(BigInteger, primary_key=True)
  handle = Column(String, nullable=False)
  account_id = Column(BigInteger, ForeignKey("twitters.id"))
  account = relationship("TwitterHandle", back_populates="screen_names", single_parent=True)
  when = Column(ArrowType)
  
  def __repr__(self):
    return "<TwitterScreenName %r %r>" % (self.account_id, self.handle)


class TwitterFollows(Base):
  """
  Twitter accounts follow each-other. This table represents one user following another.
  """

  __tablename__ = "twitter_follows"

  id = Column(BigInteger, primary_key=True)
  follows_id = Column(BigInteger, ForeignKey("twitters.id"))
  follower_id = Column(BigInteger, ForeignKey("twitters.id"))
  when = Column(ArrowType)


class EmailHandle(Base):
  """
  Email addresses are associated with personas.
  """

  __tablename__ = "emails"

  id = Column(BigInteger, primary_key=True)
  handle = Column(String, nullable=False)
  persona_id = Column(BigInteger, ForeignKey("personas.id"))
  persona = relationship("Persona", back_populates="email_accounts")


class GithubHandle(Base):
  """
  GitHub accounts are associated with personas.
  """

  __tablename__ = "githubs"

  id = Column(BigInteger, primary_key=True)
  handle = Column(String, nullable=False)
  persona_id = Column(BigInteger, ForeignKey("personas.id"))
  persona = relationship("Persona", back_populates="github_accounts")

  @property
  def url(self):
    return "http://github.com/%s" % (self.handle,)
  
  def __repr__(self):
    return "<GithubHandle %r>" % (self.url,)


class KeybaseHandle(Base):
  """
  Keybase accounts are associated with personas.

  This account type can almost be assumed to be 1:1, but you never know and #opsec
  """

  __tablename__ = "keybases"

  id = Column(BigInteger, primary_key=True)
  handle = Column(String, nullable=False)
  persona_id = Column(BigInteger, ForeignKey("personas.id"))
  persona = relationship("Persona", back_populates="keybase_accounts")

  @property
  def url(self):
    return "http://keybase.io/%s" % (self.handle,)
  
  def __repr__(self):
    return "<KeybaseHandle %r>" % (self.url,)


class RedditHandle(Base):
  """
  Reddit accounts are associated with personas.

  This account type can almost be assumed to be 1:1, but you never know and #opsec
  """

  __tablename__ = "reddits"

  id = Column(BigInteger, primary_key=True)
  handle = Column(String, nullable=False)
  persona_id = Column(BigInteger, ForeignKey("personas.id"))
  persona = relationship("Persona", back_populates="reddit_accounts")

  @property
  def url(self):
    return "http://reddit.com/u/%s" % (self.handle,)

  def __repr__(self):
    return "<RedditHandle %r>" % (self.url,)


class LobstersHandle(Base):
  """
  Reddit accounts are associated with personas.

  This account type can almost be assumed to be 1:1, but you never know and #opsec
  """

  __tablename__ = "lobsters"

  id = Column(BigInteger, primary_key=True)
  handle = Column(String, nullable=False)
  persona_id = Column(BigInteger, ForeignKey("personas.id"))
  persona = relationship("Persona", back_populates="lobsters_accounts")

  @property
  def url(self):
    return "http://lobste.rs/u/%s" % (self.handle,)

  def __repr__(self):
    return "<LobstersHandle %r>" % (self.url,)


class HNHandle(Base):
  """
  Reddit accounts are associated with personas.

  This account type can almost be assumed to be 1:1, but you never know and #opsec
  """

  __tablename__ = "orage_websites"

  id = Column(BigInteger, primary_key=True)
  handle = Column(String, nullable=False)
  persona_id = Column(BigInteger, ForeignKey("personas.id"))
  persona = relationship("Persona", back_populates="hn_accounts")

  @property
  def url(self):
    return "https://news.ycombinator.com/user?id=%s" % (self.handle,)

  def __repr__(self):
    return "<HNHandle %r>" % (self.url,)


class Website(Base):
  """
  Websites are associated with personas.
  """

  __tablename__ = "websities"

  id = Column(BigInteger, primary_key=True)
  handle = Column(String, nullable=False)
  persona_id = Column(BigInteger, ForeignKey("personas.id"))
  persona = relationship("Persona", back_populates="websites")

  @property
  def url(self):
    return self.handle

  def __repr__(self):
    return "<Website %r>" % (self.url,)


class Suspicion(Base):
  """
  We don't always know who owns a Profile. There may be many people, there may be one person and we
  just don't have enough information to identify who it is.

  The suspicion class is an adjacency mapping between People and Profiles.
  """

  __tablename__ = "suspicions"

  id = Column(BigInteger, primary_key=True)
  person_id = Column(BigInteger, ForeignKey("people.id"))
  person = relationship("Person", back_populates="suspicions")
  persona_id = Column(BigInteger, ForeignKey("personas.id"))
  persona = relationship("Persona", back_populates="suspicions")


class Member(Base):
  """
  Sometimes we do know who participates in a profile. There may even be many people particularly in
  the case of pen names and groups.

  The Member class is an adjacency mapping between People and Profiles.
  """

  __tablename__ = "memberships"

  id = Column(BigInteger, primary_key=True)
  person_id = Column(BigInteger, ForeignKey("people.id"))
  person = relationship("Person", back_populates="memberships")
  persona_id = Column(BigInteger, ForeignKey("personas.id"))
  persona = relationship("Persona", back_populates="members")


def get_or_create(session, model, **kwargs):
  instance = session.query(model).filter_by(**kwargs).first()
  if not instance:
    instance = model(**kwargs)
    session.add(instance)
    session.commit()
  return instance
