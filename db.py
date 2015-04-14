# encoding: utf-8
from __future__ import absolute_import, unicode_literals, print_function
from datetime import datetime

from unidecode import unidecode

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker, relationship, backref
from sqlalchemy.schema import Column, ForeignKey, Table
from sqlalchemy.types import DateTime, Integer, Unicode, Enum, UnicodeText, Boolean, TypeDecorator

from flask import Flask, url_for

import bcrypt

import os
app = Flask('rhforum')
app_dir = os.path.dirname(os.path.abspath(__file__))
app.config.from_pyfile(app_dir+"/config.py") # XXX

if 'mysql' in app.config['DB']:
    engine = create_engine(app.config['DB'], encoding=b"utf8", pool_size = 100, pool_recycle=4200) # XXX
    # pool_recycle is to prevent "server has gone away"
else:
    engine = create_engine(app.config['DB'], encoding=b"utf8")

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
    homepage = Column(Unicode(255), default='')
    minipic_url = Column(Unicode(255), default='')
    avatar_url = Column(Unicode(255), default='')
    timestamp = Column(DateTime)
    laststamp = Column(DateTime)
    profile = Column(UnicodeText, default='')
    
    groups = relationship("Group", secondary='usergroup')
    
    @property
    def name(self):
        return self.fullname
    
    @property
    def id(self):
        return self.uid
    
    @property
    def num_posts(self):
        return session.query(Post).filter(Post.author == self, Post.deleted==False).count()
    
    @property
    def admin(self):
        return session.query(Group).filter(Group.name=="admin").scalar() in self.groups
    
    @property
    def url(self):
        return url_for('user', user_id=self.id, name=unidecode(self.login))
    
    def unread(self, thread):
        if not self.id: return False
        thread_read = session.query(ThreadRead).filter(ThreadRead.user==self, ThreadRead.thread==thread).scalar()
        if not thread_read:
            return thread
        if thread_read.last_post.current == thread.last_post:
            return False
        return thread_read.last_post.current
    
    def unread_post(self, post):
        if not self.id: return False
        thread_read = session.query(ThreadRead).filter(ThreadRead.user==self, ThreadRead.thread==post.thread).scalar()
        if not thread_read:
            return post.thread
        if thread_read.last_post.current.timestamp >= post.timestamp:
            return False
        return post
        
        
    def read(self, post):
        if not post: return
        if not self.id: return
        thread_read = session.query(ThreadRead).filter(ThreadRead.user==self, ThreadRead.thread==post.thread).scalar()
        if not thread_read:
            thread_read = ThreadRead(user=self, thread=post.thread, last_post_id=post.original.id if post.original else post.id)
        else:
            thread_read.last_post_id=post.id # XXX why no post?
        session.add(thread_read)
        session.commit()
    
    def verify_password(self, password):
        if self.pass_.startswith('$2a'):
            return bcrypt.hashpw(password.encode('utf-8'), self.pass_.encode('utf-8')) == self.pass_
        else:
            # Old hashing method
            raise OldHashingMethodException
    
    def read_all(self):
        # Kinda heavy, I suppose...
        for thread in session.query(Thread):
            self.read(thread.last_post) # XXX each does a commit..
    
    def set_password(self, password):
        self.pass_ = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

class Guest(User):
    def __nonzero__(self): # hi yes I'm a responsible programmer
        return False

class Group(Base):
    __tablename__="groups"
    gid = Column(Integer, primary_key=True, nullable=False)
    name = Column(Unicode(255))
    
    @property
    def id(self):
        return self.gid

usergroup = Table('usergroup', Base.metadata,
    Column('uid', Integer, ForeignKey('users.uid')),
    Column('gid', Integer, ForeignKey('groups.gid'))
)

class Category(Base):
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(Unicode(255))
    position = Column(Integer)
    
    group_id = Column(Integer, ForeignKey('groups.gid'))
    group = relationship("Group", backref='categories')

class Forum(Base):
    __tablename__ = 'fora'
    
    id = Column(Integer, primary_key=True, nullable=False)
    identifier = Column(Unicode(255))
    name = Column(Unicode(255))
    description = Column(UnicodeText)
    position = Column(Integer)
    
    category_id = Column(Integer, ForeignKey('categories.id'))
    category = relationship("Category", backref=backref('fora', order_by=b"Forum.position"))
    
    trash = Column(Boolean, nullable=False, default=False)
    
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
    
    posts = relationship("Post", order_by="Post.timestamp", lazy="dynamic")#, viewonly=True, primaryjoin="foreign(Post.deleted)==False")
    
    @property
    def last_post(self):
        return session.query(Post).filter(Post.thread == self, Post.deleted==False).order_by(Post.timestamp.desc()).first()
    
    @property
    def num_posts(self):
        return session.query(Post).filter(Post.thread == self, Post.deleted==False).count()
    
    @property
    def url(self):
        return url_for('thread',
            forum_id=self.forum.id, forum_identifier=self.forum.identifier,
            thread_id=self.id, thread_identifier=unidecode(self.name).replace(' ', '-'))


class Post(Base):
    __tablename__ = 'posts'
    
    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(Unicode(255))
    thread_id = Column(Integer, ForeignKey('threads.id'), nullable=False)
    thread = relationship("Thread", order_by="Post.timestamp")
    author_id = Column(Integer, ForeignKey('users.uid'), nullable=False)
    author = relationship("User", foreign_keys=[author_id], backref='posts')
    timestamp = Column(DateTime)
    text = Column(UnicodeText)
    
    deleted = Column(Boolean, default=False, nullable=False)
    editstamp = Column(DateTime)
    original_id = Column(Integer, ForeignKey('posts.id'))
    original = relationship("Post", remote_side=id, backref="edits")
    editor_id = Column(Integer, ForeignKey('users.uid'))
    editor = relationship("User", foreign_keys=[editor_id])
    
    @property
    def url(self):
        return self.thread.url + "#post-{}".format(self.id)
    
    @property
    def current(self):
        return session.query(Post).filter(Post.original == self).order_by(Post.editstamp.desc()).first() or self

class ThreadRead(Base):
    __tablename__ = 'threads_read'
    
    id = Column(Integer, primary_key=True, nullable=False)
    thread_id = Column(Integer, ForeignKey('threads.id'), nullable=False)
    thread = relationship("Thread")
    user_id = Column(Integer, ForeignKey('users.uid'), nullable=False)
    user = relationship("User", backref='threads_read')
    last_post_id = Column(Integer, ForeignKey('posts.id'))
    last_post = relationship("Post")

# XXX Watch out!  Code below main!

if __name__ == "__main__":
    print('this is db.py.  make sure you know where you are.')
    if raw_input('mark everything as read for everybody? ') == 'y':
        for user in session.query(User):
            user.read_all()
    if raw_input('do dangerous stuff?  type yes. ') == 'yes':
        if raw_input('drop all? ') == 'y':
            Base.metadata.drop_all(bind=engine)
        if raw_input('create all? ') == 'y':
            Base.metadata.create_all(bind=engine)

        if raw_input('test entries? ') == 'y':
            fc = Category(name="Kategorie 1")
            fc2 = Category(name="Druhá kategorie")
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

            t = Thread(name="První téma na fóru", description="", timestamp=datetime.now(), laststamp=datetime.now(), forum=f, author=u)
            session.add(t)

            p = Post(thread=t, author=u, text="First post!  <b>Test</b>!", timestamp=datetime.now())
            session.add(t)
            p = Post(thread=t, author=u, text="Test ", timestamp=datetime.now())
            session.add(t)

            session.commit()


if not session.query(Forum).filter(Forum.trash == True).scalar():
    print("No trash forum detected, making one")
    f = Forum(name="Koš", identifier="kos", description="Smazané posty.", trash=True, position=255)
    session.add(f)
    session.commit()


