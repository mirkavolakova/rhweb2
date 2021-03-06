# encoding: utf-8

from datetime import datetime

from unidecode import unidecode

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker, relationship, backref
from sqlalchemy.schema import Column, ForeignKey, Table
from sqlalchemy.types import DateTime, Integer, String, Enum, Text, Boolean, TypeDecorator

from flask import Flask, url_for

import bcrypt

import os
app = Flask('rhforum')
app_dir = os.path.dirname(os.path.abspath(__file__))
app.config.from_pyfile(app_dir+"/config.py") # XXX

debug = app.config.get("DEBUG", False)

def url_friendly(string):
    return unidecode(string).lower().replace(' ', '-').replace('/', '-')

if 'mysql' in app.config['DB']:
    engine = create_engine(app.config['DB'], encoding="utf8", pool_size = 100, pool_recycle=4200, echo=debug) # XXX
    # pool_recycle is to prevent "server has gone away"
else:
    engine = create_engine(app.config['DB'], encoding="utf8", echo=debug)

session = scoped_session(sessionmaker(bind=engine, autoflush=False))

Base = declarative_base(bind=engine)

class OldHashingMethodException(Exception): pass

class User(Base):
    __tablename__ = 'users'
    
    uid = Column(Integer, primary_key=True, nullable=False)
    login = Column(String(20))
    pass_ = Column('pass', String(60))
    fullname = Column(String(255))
    email = Column(String(255))
    homepage = Column(String(255), default='')
    minipic_url = Column(String(255), default='')
    avatar_url = Column(String(255), default='')
    timestamp = Column(DateTime)
    laststamp = Column(DateTime)
    profile = Column(Text, default='')
    
    
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
        return url_for('.user', user_id=self.id, name=unidecode(self.login))
    
    @property
    def representative_group(self):
        return max(self.groups, key=lambda group: group.rank if group.display else -1)
    
    @property
    def title(self):
        group = self.representative_group
        if not group: return ""
        if not group.display: return ""
        return "{} {}".format(group.symbol or "", group.title or "").strip()
    
    def num_unread(self, thread):
        last_read = self.unread(thread)
        if not last_read: return 0
        return session.query(Post).filter(Post.thread == thread, Post.deleted == False, Post.timestamp > last_read.timestamp).count()
    
    def unread(self, thread):
        if not self.id: return False
        thread_read = session.query(ThreadRead).filter(ThreadRead.user==self, ThreadRead.thread==thread).first() # XXX should be .scalar()
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
    
    def in_group(self, group_name):
        group = session.query(Group).filter(Group.name==group_name).scalar()
        if not group: return False
        return group in self.groups
        
    def read(self, post):
        if not post: return
        if not self.id: return
        thread_read = session.query(ThreadRead).filter(ThreadRead.user==self, ThreadRead.thread==post.thread).first()
        if not thread_read:
            thread_read = ThreadRead(user=self, thread=post.thread, last_post_id=post.original.id if post.original else post.id)
        else:
            thread_read.last_post_id=post.id # XXX why no post?
        session.add(thread_read)
        session.commit()
    
    def verify_password(self, password):
        pass_ = self.pass_
        if isinstance(pass_, bytes):
            pass_ = pass_.decode('ascii')
        if pass_.startswith('$2a') or pass_.startswith('$2b'):
            #return bcrypt.hashpw(password.encode('utf-8'), pass_.encode('utf-8')).decode('ascii') == pass_
            return bcrypt.checkpw(password.encode('utf-8'), pass_.encode('ascii'))
        else:
            # Old hashing method
            raise OldHashingMethodException
    
    def read_all(self):
        # Kinda heavy, I suppose...
        for thread in session.query(Thread):
            self.read(thread.last_post) # XXX each does a commit..
    
    def set_password(self, password):
        pass_ = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('ascii')
        # for DokuWiki compatibility
        if pass_.startswith('$2b'):
            pass_ = '$2a' + pass_[3:]
        self.pass_ = pass_
    
    
    def __bool__(self): # this is fine.
        #if not self.in_group("user"):
        #    return False
        return True

class Guest(User):
    def __bool__(self): # hi yes I'm a responsible programmer
        return False

class Group(Base):
    __tablename__="groups"
    gid = Column(Integer, primary_key=True, nullable=False)
    name = Column(String(255))
    
    symbol = Column(String(16))
    title = Column(String(255))
    rank = Column(Integer, default=0)
    display = Column(Boolean)
    
    users = relationship("User", secondary='usergroup')
    
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
    name = Column(String(255))
    position = Column(Integer)
    
    group_id = Column(Integer, ForeignKey('groups.gid'))
    group = relationship("Group", backref='categories')
    
    @property
    def url(self):
        return url_for('.index', _anchor="category-{}".format(self.id))
    
    @property
    def symbol_name(self):
        if self.group and self.group.display:
            return "{} {}".format(self.group.symbol, self.name)
        else:
            return self.name

class Forum(Base):
    __tablename__ = 'fora'
    
    id = Column(Integer, primary_key=True, nullable=False)
    identifier = Column(String(255))
    name = Column(String(255))
    description = Column(Text)
    position = Column(Integer)
    
    category_id = Column(Integer, ForeignKey('categories.id'))
    category = relationship("Category", backref=backref('fora', order_by="Forum.position"))
    
    trash = Column(Boolean, nullable=False, default=False)
    
    @property
    def url(self):
        if self.id:
            return url_for('.forum', forum_id=self.id, forum_identifier=self.identifier)
        else:
            return None
        
    @property
    def last_post(self):
        return session.query(Post).join(Post.thread).filter(Thread.forum == self, Post.deleted==False).order_by(Post.timestamp.desc()).first()
    
    @property
    def symbol_name(self):
        if self.category and self.category.group and self.category.group.display:
            return "{} {}".format(self.category.group.symbol, self.name)
        else:
            return self.name

class Thread(Base):
    __tablename__ = 'threads'
    
    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String(255))
    description = Column(Text)
    forum_id = Column(Integer, ForeignKey('fora.id'), nullable=False)
    forum = relationship("Forum", backref='threads', order_by="Thread.laststamp")
    author_id = Column(Integer, ForeignKey('users.uid'), nullable=False)
    author = relationship("User", backref='threads')
    wiki_article = Column(String(255))
    timestamp = Column(DateTime)
    laststamp = Column(DateTime)
    pinned = Column(Boolean, default=False, nullable=False)
    locked = Column(Boolean, default=False, nullable=False)
    archived = Column(Boolean, default=False, nullable=False)
    
    posts = relationship("Post", order_by="Post.timestamp", lazy="dynamic")#, viewonly=True, primaryjoin="foreign(Post.deleted)==False")
    
    @property
    def last_post(self):
        return session.query(Post).filter(Post.thread == self, Post.deleted==False).order_by(Post.timestamp.desc()).first()
    
    @property
    def num_posts(self):
        return session.query(Post).filter(Post.thread == self, Post.deleted==False).count()
    
    @property
    def url(self):
        return url_for('.thread',
            forum_id=self.forum.id, forum_identifier=self.forum.identifier,
            thread_id=self.id, thread_identifier=url_friendly(self.name))
            
    @property
    def short_url(self):
        return url_for('.thread', forum_id=self.forum.id, thread_id=self.id)


class Post(Base):
    __tablename__ = 'posts'
    
    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String(255))
    thread_id = Column(Integer, ForeignKey('threads.id'), nullable=False)
    thread = relationship("Thread", order_by="Post.timestamp")
    author_id = Column(Integer, ForeignKey('users.uid'), nullable=False)
    author = relationship("User", foreign_keys=[author_id], backref='posts')
    timestamp = Column(DateTime)
    text = Column(Text)
    
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
    def short_url(self):
        return self.thread.short_url + "#post-{}".format(self.id)
    
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

class Task(Base):
    __tablename__ = 'tasks'
    
    id = Column(Integer, primary_key=True, nullable=False)
    
    text = Column(Text)
    created_time = Column(DateTime)
    due_time = Column(DateTime, nullable=True)
    status = Column(Enum("todo", "inprogress", "done", name="status"), nullable=True)
    
    author_id = Column(Integer, ForeignKey('users.uid'))
    author = relationship("User", foreign_keys=[author_id])
    
    user_id = Column(Integer, ForeignKey('users.uid'))
    user = relationship("User", backref='tasks', foreign_keys=[user_id])
    
    thread_id = Column(Integer, ForeignKey('threads.id'))
    thread = relationship("Thread")
    

# XXX Watch out!  Code below main!

if __name__ == "__main__":
    print('this is db.py.  make sure you know where you are.')
    if input('fix thread.{pinned,archived} = NULL? ') == 'y':
        for thread in session.query(Thread):
            if thread.pinned == None:
                thread.pinned = False
            if thread.archived == None:
                thread.archived = False
        session.commit()
        print("fixed")
    if input('make everybody user?') == 'y':
        g = Group(name="user")
        session.add(g)
        for user in session.query(User):
            user.groups.append(g)
        session.commit()
        print("done")
    #if raw_input('mark everything as read for everybody? ') == 'y':
    #    for user in session.query(User):
    #        user.read_all()
    if input('do dangerous stuff?  type yes. ') == 'yes':
        #which = raw_input('drop which? ')
        #db.Base.metadata.drop_all(tables=[db.Task.__table__])
        #if which:
        #    print("... DROP TABLE "+which)
        #    session.query("DROP TABLE "+which)
        #    session.commit()
        if input('drop all? ') == 'y':
            print("... drop all")
            Base.metadata.drop_all(bind=engine)
        if input('create all? ') == 'y':
            print("... create all")
            Base.metadata.create_all(bind=engine)

        if input('test entries? ') == 'y':
            print("... test entries")
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
            g2 = Group(name="retroherna")
            session.add(g2)
            u = User(login="admin", fullname="Admin", pass_=bcrypt.hashpw(b"test", bcrypt.gensalt(rounds=9)), groups=[g, g2])
            session.add(u)
            u2 = User(login="uzivatel", fullname="Uživatel", pass_=bcrypt.hashpw(b"test", bcrypt.gensalt(rounds=9)), groups=[g2])
            session.add(u2)

            t = Thread(name="První téma na fóru", description="", timestamp=datetime.utcnow(), laststamp=datetime.utcnow(), forum=f, author=u)
            session.add(t)

            p = Post(thread=t, author=u, text="First post!  <b>Test</b>!", timestamp=datetime.utcnow())
            session.add(t)
            p = Post(thread=t, author=u, text="Test ", timestamp=datetime.utcnow())
            session.add(t)

            session.commit()


if not session.query(Forum).filter(Forum.trash == True).scalar():
    print("No trash forum detected, making one")
    f = Forum(name="Koš", identifier="kos", description="Smazané posty.", trash=True, position=255)
    session.add(f)
    session.commit()


