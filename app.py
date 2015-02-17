# coding: utf-8
from __future__ import absolute_import, unicode_literals, print_function

import db
from sqlalchemy import or_, and_, asc, desc, func
from datetime import datetime
from functools import wraps # We need this to make Flask understand decorated routes.
import hashlib

from werkzeug import secure_filename
from flask import Flask, render_template, request, flash, redirect, session, abort, url_for, make_response, g
from wtforms import Form, BooleanField, TextField, TextAreaField, PasswordField, RadioField, SelectField, SelectMultipleField, BooleanField, HiddenField, SubmitField, validators, ValidationError, widgets

app = Flask('rhforum')
app.config.from_pyfile('config.py')


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

@app.route("/")
def index():
    fora = db.session.query(db.Forum)
    return render_template("index.html", fora=fora)

class LoginForm(Form):
    name = TextField('Jméno', [validators.required()])
    submit = SubmitField('Přihlásit se')

@app.route("/login", methods="GET POST".split())
def login():
    login_form = LoginForm(request.form)
    failed = False
    if request.method == 'POST' and login_form.validate():
        g.user = db.session.query(db.User).filter(db.User.name == login_form.name.data).scalar()
        if not g.user: failed = True
        else:
            session['user_id'] = g.user.id
            session.permanent = True
            flash("Jste přihlášeni.")
            return redirect("/")
    
    return render_template("login.html", login_form=login_form, failed=failed)

class RegisterForm(Form):
    name = TextField('Jméno', [validators.required()])
    email = TextField('Email', [validators.required()])
    submit = SubmitField('Zaregistrovat')

@app.route("/register", methods="GET POST".split())
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        user = db.User(name=form.name.data, email=form.email.data, timestamp=datetime.now())
        db.session.add(user)
        db.session.commit()
        g.user = user
        session['user_id'] = g.user.id
        session.permanent = True
        
        flash("Registrace proběhla úspěšně.")
        return redirect("/")
    
    return render_template("register.html", form=form)

@app.route("/logout")
def logout():
    if 'user_id' in session:
        session.pop('user_id')
        flash("Odhlášení proběhlo úspěšně.")
        return redirect("/")

@app.route("/<int:forum_id>", methods="GET POST".split())
@app.route("/<int:forum_id>-<forum_identifier>", methods="GET POST".split())
def forum(forum_id, forum_identifier=None):
    forum = db.session.query(db.Forum).get(forum_id)
    threads = db.session.query(db.Thread).filter(db.Thread.forum == forum).order_by(db.Thread.laststamp.desc())
    form = ThreadForm(request.form)
    if request.method == 'POST' and form.validate():
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


@app.route("/<int:forum_id>/<int:topic_id>", methods="GET POST".split())
@app.route("/<int:forum_id>-<forum_identifier>/<int:thread_id>-<thread_identifier>", methods="GET POST".split())
def thread(forum_id, thread_id, forum_identifier=None, thread_identifier=None):
    thread = db.session.query(db.Thread).get(thread_id)
    form = PostForm(request.form)
    if request.method == 'POST' and form.validate():
        now = datetime.now()
        post = db.Post(thread=thread, author=g.user, timestamp=now,
            text=form.text.data)
        db.session.add(post)
        thread.laststamp = now
        db.session.commit()
        return redirect(thread.url+"#latest") # TODO id
    
    return render_template("thread.html", thread=thread, forum=thread.forum, form=form, now=datetime.now())

if __name__ == "__main__":
    app.run(host="", port=8080, debug=True, threaded=True)











