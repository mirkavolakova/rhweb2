# encoding: utf-8
from __future__ import absolute_import, unicode_literals, print_function
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker, relationship, backref
from sqlalchemy.schema import Column, ForeignKey, Table
from sqlalchemy.types import DateTime, Integer, Unicode, Enum, UnicodeText, Boolean, TypeDecorator

from flask import Flask, url_for

import bcrypt

app = Flask('rhforum')
app.config.from_pyfile('config.py')

engine = create_engine(app.config['DB'], encoding=b"utf8")#, pool_size = 100, pool_recycle=4200) # XXX
# pool_recycle is to prevent "server has gone away"
session = scoped_session(sessionmaker(bind=engine, autoflush=False))

Base = declarative_base(bind=engine)

class OldHashingMethodException(Exception): pass

class User(Base):
    __tablename__ = 'users'
    
    uid = Column(Integer, primary_key=True, nullable=False)
    login = Column(Unicode(20))
    pass_ = Column('pass', Unicode(60))
    fullname = Column(Unicode(255))
    email = Column(Unicode(255))
    homepage = Column(Unicode(255))
    avatar_url = Column(Unicode(255))
    timestamp = Column(DateTime)
    laststamp = Column(DateTime)
    profile = Column(UnicodeText)
    
    groups = relationship("Group", secondary='usergroups')
    
    @property
    def name(self):
        return self.fullname
    
    @property
    def id(self):
        return self.uid
    
    @property
    def num_posts(self):
        return session.query(Post).filter(Post.author == self).count()
    
    @property
    def admin(self):
        return session.query(Group).filter(Group.name=="admin").scalar() in self.groups
        
    def verify_password(self, password):
        print (password, self.pass_, bcrypt.hashpw(password.encode('utf-8'), self.pass_.encode('utf-8')))
        if self.pass_.startswith('$2a'):
            return bcrypt.hashpw(password.encode('utf-8'), self.pass_.encode('utf-8')) == self.pass_
        else:
            # Old hashing method
            raise OldHashingMethodException

class Group(Base):
    __tablename__="groups"
    uid = Column(Integer, primary_key=True, nullable=False)
    name = Column(Unicode(255))

usergroups = Table('usergroups', Base.metadata,
    Column('uid', Integer, ForeignKey('users.uid')),
    Column('gid', Integer, ForeignKey('groups.uid'))
)

class Forum(Base):
    __tablename__ = 'fora'
    
    id = Column(Integer, primary_key=True, nullable=False)
    identifier = Column(Unicode(255))
    name = Column(Unicode(255))
    description = Column(UnicodeText)
    position = Column(Integer)
    
    @property
    def url(self):
        return url_for('forum', forum_id=self.id, forum_identifier=self.identifier)
        
    @property
    def last_post(self):
        return session.query(Post).join(Post.thread).filter(Thread.forum == self).order_by(Post.timestamp.desc()).first()
    

class Thread(Base):
    __tablename__ = 'threads'
    
    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(Unicode(255))
    description = Column(UnicodeText)
    forum_id = Column(Integer, ForeignKey('fora.id'), nullable=False)
    forum = relationship("Forum", backref='threads', order_by="Thread.laststamp")
    author_id = Column(Integer, ForeignKey('users.uid'), nullable=False)
    author = relationship("User", backref='threads')
    timestamp = Column(DateTime)
    laststamp = Column(DateTime)
    pinned = Column(Boolean)
    
    @property
    def url(self):
        return url_for('thread',
            forum_id=self.forum.id, forum_identifier=self.identifier,
            thread_id=self.id, thread_name=self.name)


class Post(Base):
    __tablename__ = 'posts'
    
    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(Unicode(255))
    thread_id = Column(Integer, ForeignKey('threads.id'), nullable=False)
    thread = relationship("Thread", backref='posts', order_by="Post.timestamp")
    author_id = Column(Integer, ForeignKey('users.uid'), nullable=False)
    author = relationship("User", backref='posts')
    timestamp = Column(DateTime)
    text = Column(UnicodeText)

class ThreadRead(Base):
    __tablename__ = 'threads_read'
    
    id = Column(Integer, primary_key=True, nullable=False)
    thread_id = Column(Integer, ForeignKey('threads.id'), nullable=False)
    thread = relationship("Thread")
    user_id = Column(Integer, ForeignKey('users.uid'), nullable=False)
    user = relationship("User", backref='threads_read')
    last_post = Column(Integer)


if __name__ == "__main__":
    #if raw_input('drop all? ') == 'y':
    #    Base.metadata.drop_all(bind=engine)
    if raw_input('create all? ') == 'y':
        Base.metadata.create_all(bind=engine)

    if raw_input('test entries? ') == 'y':
        f = Forum(name="Novinky", identifier="novinky", description="Novinky ve světě RH", position=0)
        session.add(f)
        f2 = Forum(name="Obecné", identifier="obecne", description="Posty o čemkoli", position=1)
        session.add(f2)
        f3 = Forum(name="Ostatní", identifier="ostatni", description="Popisek", position=2)
        session.add(f3)

        g = Group(name="admin")
        session.add(g)
        u = User(login="admin", fullname="Admin", pass_=bcrypt.hashpw(b"test", bcrypt.gensalt(rounds=9)), groups=[g])
        session.add(u)
        u2 = User(login="uzivatel", fullname="Uživatel", pass_=bcrypt.hashpw(b"test", bcrypt.gensalt(rounds=9)), groups=[])
        session.add(u2)

        t = Thread(name="První téma na fóru", description="Yay!", timestamp=datetime.now(), laststamp=datetime.now(), forum=f, author=u)
        session.add(t)

        p = Post(thread=t, author=u, text="First post!  <b>Test</b>!", timestamp=datetime.now())
        session.add(t)
        p = Post(thread=t, author=u, text="Test ", timestamp=datetime.now())
        session.add(t)

        session.commit()




