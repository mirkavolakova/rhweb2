# encoding: utf-8
from __future__ import absolute_import, unicode_literals, print_function
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker, relationship, backref
from sqlalchemy.schema import Column, ForeignKey, Table
from sqlalchemy.types import DateTime, Integer, Unicode, Enum, UnicodeText, Boolean, TypeDecorator

engine = create_engine(open("db").read(), encoding=b"utf8")#, pool_size = 100, pool_recycle=4200) # XXX
# pool_recycle is to prevent "server has gone away"
session = scoped_session(sessionmaker(bind=engine, autoflush=False))

Base = declarative_base(bind=engine)

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(Unicode(256))
    email = Column(Unicode(256))
    homepage = Column(Unicode(256))
    avatar_url = Column(Unicode(256))
    rights = Column(Integer)
    timestamp = Column(DateTime)
    laststamp = Column(DateTime)
    rights = Column(Integer)
    profile = Column(UnicodeText)
    
    @property
    def num_posts(self):
        return session.query(Post).filter(Post.author == self).count()

class Forum(Base):
    __tablename__ = 'fora'
    
    id = Column(Integer, primary_key=True, nullable=False)
    identifier = Column(Unicode(256))
    name = Column(Unicode(256))
    description = Column(UnicodeText)
    minviewrights = Column(Integer)
    minpostrights = Column(Integer)
    
    @property
    def url(self):
        return "/{}-{}".format(self.id, self.identifier)
        
    @property
    def last_post(self):
        return session.query(Post).join(Post.thread).filter(Thread.forum == self).order_by(Post.timestamp.desc()).first()
    

class Thread(Base):
    __tablename__ = 'threads'
    
    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(Unicode(256))
    description = Column(UnicodeText)
    forum_id = Column(Integer, ForeignKey('fora.id'), nullable=False)
    forum = relationship("Forum", backref='threads', order_by="Thread.laststamp")
    author_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    author = relationship("User", backref='threads')
    timestamp = Column(DateTime)
    laststamp = Column(DateTime)
    pinned = Column(Boolean)
    
    @property
    def url(self):
        return "/{}-{}/{}-{}".format(self.forum.id, self.forum.identifier, self.id, self.name)


class Post(Base):
    __tablename__ = 'posts'
    
    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(Unicode(256))
    thread_id = Column(Integer, ForeignKey('threads.id'), nullable=False)
    thread = relationship("Thread", backref='posts', order_by="Post.timestamp")
    author_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    author = relationship("User", backref='posts')
    timestamp = Column(DateTime)
    text = Column(UnicodeText)

class ThreadRead(Base):
    __tablename__ = 'threads_read'
    
    id = Column(Integer, primary_key=True, nullable=False)
    thread_id = Column(Integer, ForeignKey('threads.id'), nullable=False)
    thread = relationship("Thread")
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user = relationship("User", backref='threads_read')
    last_post = Column(Integer)

#if __name__ == "__main__":
#if raw_input('Drop all? ') == 'y':
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

f = Forum(name="Novinky", identifier="novinky", description="Novinky ve světě RH")
session.add(f)
f2 = Forum(name="Obecné", identifier="obecne", description="Posty o čemkoli")
session.add(f2)
f3 = Forum(name="Ostatní", identifier="ostatni", description="Popisek")
session.add(f3)

u = User(name="Uživatel")
session.add(u)

t = Thread(name="První téma na fóru", description="Yay!", timestamp=datetime.now(), laststamp=datetime.now(), forum=f, author=u)
session.add(t)

p = Post(thread=t, author=u, text="First post!  <b>Test</b>!", timestamp=datetime.now())
session.add(t)
p = Post(thread=t, author=u, text="Second post made to test the layout. \nLorizzle ipsizzle cool da bomb amizzle, dawg adipiscing dawg. Dope sapizzle gangsta, mammasay mammasa mamma oo sa volutpizzle, suscipizzle izzle, gravida vel, arcu. Pellentesque eget tortor. Sizzle erizzle. Brizzle at dolor dapibus turpis tempizzle gangsta. Mauris fizzle nibh things turpizzle. Vestibulum in tortor. Pellentesque doggy rhoncizzle nisi. In hac stuff its fo rizzle dictumst. Its fo rizzle dapibizzle. Curabitizzle tellus gangster, pretium shizzlin dizzle, yippiyo mofo, eleifend vitae, nunc. Shizzlin dizzle suscipizzle. Integizzle sempizzle fo shizzle my nizzle sizzle doggy. Donizzle shizznit doggy mauris. Phasellizzle shiz elit izzle yo mammasay mammasa mamma oo sa tincidunt. Crunk a owned. Vestibulizzle cool check out this sed maurizzle elementum tristique. Nunc izzle its fo rizzle sit fo shizzle erizzle ultricizzle check out this. Bizzle crazy i'm in the shizzle, rizzle izzle, i saw beyonces tizzles and my pizzle went crizzle quis, adipiscing the bizzle, dui. Hizzle velit shut the shizzle up, aliquizzle consequat, pharetra non, dictizzle sizzle, turpizzle. Shiz mah nizzle. Izzle lorem. Brizzle vitae pizzle izzle libero commodo adipiscing. Fusce fo shizzle mah nizzle fo rizzle, mah home g-dizzle augue its fo rizzle gizzle dizzle phat. \nCrazy fermentum shizzle my nizzle crocodizzle non dawg. Suspendisse lorizzle dope, sollicitudin bling bling, you son of a bizzle izzle, that's the shizzle nizzle, justo. Donizzle faucibus porttitizzle boofron. Nunc feugiat, tellizzle shizzlin dizzle ornare fo shizzle mah nizzle fo rizzle, mah home g-dizzle, sapien ass tincidunt owned, egizzle dapibus pede enim izzle lorem. Phasellizzle doggy leo, bling bling izzle, tempus izzle, dope izzle, sapizzle. Things ma nizzle check out this vizzle ipsum. Sizzle ante mammasay mammasa mamma oo sa, suscipizzle vitae, vestibulizzle et, rutrizzle eu, velizzle. Maurizzle black mauris. Sizzle magna sizzle amizzle risus iaculizzle dizzle.", timestamp=datetime.now())
session.add(t)

session.commit()




