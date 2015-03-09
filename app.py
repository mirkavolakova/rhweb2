# coding: utf-8
from __future__ import absolute_import, unicode_literals, print_function

import os

import db
from sqlalchemy import or_, and_, asc, desc, func
from datetime import datetime
from functools import wraps # We need this to make Flask understand decorated routes.
import hashlib

from werkzeug import secure_filename
from flask import Flask, render_template, request, flash, redirect, session, abort, url_for, make_response, g
from wtforms import Form, BooleanField, TextField, TextAreaField, PasswordField, RadioField, SelectField, SelectMultipleField, BooleanField, HiddenField, SubmitField, validators, ValidationError, widgets

tmpl_dir = '/data/retroherna.cz/rhforum/templates/' # XXX
app = Flask('rhforum', template_folder=tmpl_dir)
app.config.from_pyfile('/data/retroherna.cz/rhforum/config.py') # XXX


class PostForm(Form):
    text = TextAreaField('Text', [validators.required()])
    submit = SubmitField('Odeslat')

class ThreadForm(PostForm):
    name = TextField('Nadpis', [validators.required()])


@app.template_filter('datetime')
def datetime_format(value, format='%d. %m. %Y %H:%M:%S'):
    if not value: return "-"
    if isinstance(value, unicode): return value
    return value.strftime(format)

@app.before_request
def before_request():
    if 'user_id' in session:
        g.user = db.session.query(db.User).get(session['user_id'])
        if not g.user:
            # TODO
            pass
    else:
        g.user = None

@app.teardown_request
def shutdown_session(exception=None):
    db.session.close()
    db.session.remove()

class ForumForm(Form):
    name = TextField('Jméno', [validators.required()])
    description = TextField('Popisek', [validators.required()])
    move_up = SubmitField('↑')
    move_down = SubmitField('↓')
    save = SubmitField('Uložit')

@app.route("/")
def index():
    fora = db.session.query(db.Forum).order_by(db.Forum.position)
    return render_template("index.html", fora=fora, edit_forum = None)

@app.route("/edit-forum/<int:forum_id>", methods="GET POST".split())
@app.route("/edit-forum/new", methods="GET POST".split())
def edit_forum(forum_id=None):
    if not g.user.admin: abort(403) # TODO minrights decorator
    fora = db.session.query(db.Forum).order_by(db.Forum.position).all()
    if forum_id:
        forum = db.session.query(db.Forum).get(forum_id)
    else:
        forum = db.Forum()
        fora = list(fora) + [forum]
    form = ForumForm(request.form, forum)
    if request.method == "POST" and form.validate():
        forum.name = form.name.data
        forum.identifier = forum.name.lower().replace(' ', '-')
        forum.description = form.description.data
        if form.save.data:
            if not forum_id:
                forum.position = len(list(fora))-1
                db.session.add(forum)
                flash("Fórum přidáno.")
            else:
                flash("Fórum upraveno.")
            db.session.commit()
            return redirect(url_for('index'))
        else:
            # moving
            i = forum.position
            fora = list(fora)
            fora.remove(forum)
            if form.move_up and form.move_up.data:
                print("moving up", forum.name, i, fora)
                fora.insert(i-1, forum)
            elif form.move_down and form.move_down.data:
                print("moving down", forum.name, i, fora)
                fora.insert(i+1, forum)
            for i, f in enumerate(fora):
                f.position = i
                db.session.add(f)
            db.session.commit()
    if forum.position == 0:
        del form.move_up
    if forum.position == len(fora)-1:
        del form.move_down
    return render_template("index.html", fora=fora, edit_forum=forum, form=form, new=not bool(forum_id))

class LoginForm(Form):
    name = TextField('Jméno', [validators.required()])
    password = PasswordField('Heslo', [validators.required()])
    submit = SubmitField('Přihlásit se')

@app.route("/login", methods="GET POST".split())
def login():
    form = LoginForm(request.form)
    failed = False
    if request.method == 'POST' and form.validate():
        user = db.session.query(db.User).filter(db.User.login == form.name.data.lower()).scalar()
        if not user: failed = True
        else:
            try:
                password_matches = user.verify_password(form.password.data)
            except db.OldHashingMethodException:
                failed = True
                password_matches = False
                flash("Prosím, změňte si heslo na DokuWiki..")
            if password_matches:
                g.user = user
                session['user_id'] = g.user.id
                session.permanent = True
                flash("Jste přihlášeni.")
                return redirect(url_for('index'))
            else:
                failed = True
    
    return render_template("login.html", form=form, failed=failed)

class RegisterForm(Form):
    name = TextField('Jméno', [validators.required()])
    email = TextField('Email', [validators.required()])
    submit = SubmitField('Zaregistrovat')

@app.route("/register", methods="GET POST".split())
def register():
    form = RegisterForm(request.form)
    '''
    if request.method == 'POST' and form.validate():
        user = db.User(name=form.name.data, email=form.email.data, timestamp=datetime.now())
        db.session.add(user)
        db.session.commit()
        g.user = user
        session['user_id'] = g.user.id
        session.permanent = True
        
        flash("Registrace proběhla úspěšně.")
        return redirect("/")
    '''
    
    return render_template("register.html", form=form)

@app.route("/logout")
def logout():
    if 'user_id' in session:
        session.pop('user_id')
        flash("Odhlášení proběhlo úspěšně.")
    return redirect(url_for('index'))

@app.route("/<int:forum_id>", methods="GET POST".split())
@app.route("/<int:forum_id>-<forum_identifier>", methods="GET POST".split())
def forum(forum_id, forum_identifier=None):
    if not g.user: abort(403)
    forum = db.session.query(db.Forum).get(forum_id)
    if not forum: abort(404)
    threads = db.session.query(db.Thread).filter(db.Thread.forum == forum).order_by(db.Thread.laststamp.desc())
    form = ThreadForm(request.form)
    if g.user and request.method == 'POST' and form.validate():
        now = datetime.now()
        thread = db.Thread(forum=forum, author=g.user, timestamp=now, laststamp=now,
            name=form.name.data)
        db.session.add(thread)
        post = db.Post(thread=thread, author=g.user, timestamp=now,
            text=form.text.data)
        db.session.add(post)
        db.session.commit()
        return redirect(thread.url)
    return render_template("forum.html", forum=forum, threads=threads, form=form)


# TODO <path:thread_identificator>
@app.route("/<int:forum_id>/<int:topic_id>", methods="GET POST".split())
@app.route("/<int:forum_id>-<forum_identifier>/<int:thread_id>-<thread_identifier>", methods="GET POST".split())
def thread(forum_id, thread_id, forum_identifier=None, thread_identifier=None):
    if not g.user: abort(403)
    thread = db.session.query(db.Thread).get(thread_id)
    if not thread: abort(404)
    form = PostForm(request.form)
    if g.user and request.method == 'POST' and form.validate():
        now = datetime.now()
        post = db.Post(thread=thread, author=g.user, timestamp=now,
            text=form.text.data)
        db.session.add(post)
        thread.laststamp = now
        db.session.commit()
        return redirect(thread.url+"#latest") # TODO id
    
    return render_template("thread.html", thread=thread, forum=thread.forum, form=form, now=datetime.now())

@app.route("/users/<int:user_id>")
@app.route("/users/<int:user_id>-<name>")
def user(user_id, name=None):
    pass

'''

@app.route("/reload")
def reload():
    if g.user and g.user.admin:
        if request.envion['mod_swgi.process_group
'''

if not app.debug:
    import logging
    from logging import FileHandler
    file_handler = FileHandler('/data/retroherna.cz/flask.log')
    file_handler.setLevel(logging.WARNING)
    app.logger.addHandler(file_handler)

if __name__ == "__main__":
    app.run(host="", port=8082, debug=True, threaded=True)











