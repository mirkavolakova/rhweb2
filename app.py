#!/usr/bin/python
# coding: utf-8
from __future__ import absolute_import, unicode_literals, print_function

import os

import db
from sqlalchemy import or_, and_, not_, asc, desc, func
from datetime import datetime, timedelta
from functools import wraps # We need this to make Flask understand decorated routes.
import hashlib

from lxml.html.clean import Cleaner
from lxml.etree import ParserError

from werkzeug import secure_filename
from flask import Flask, render_template, request, flash, redirect, session, abort, url_for, make_response, g
from wtforms import Form, BooleanField, TextField, TextAreaField, PasswordField, RadioField, SelectField, SelectMultipleField, BooleanField, HiddenField, SubmitField, validators, ValidationError, widgets

class MultiCheckboxField(SelectMultipleField):
    """
    A multiple-select, except displays a list of checkboxes.
    Iterating the field will produce subfields, allowing custom rendering of
    the enclosed checkbox fields.
    Shamelessly stolen from WTForms FAQ.
    """
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

app_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask('rhforum', template_folder=app_dir+"/templates")
app.config.from_pyfile(app_dir+"/config.py") # XXX


class PostForm(Form):
    text = TextAreaField('Text', [validators.required()])
    submit = SubmitField('Odeslat')
    
class EditPostForm(Form):
    text = TextAreaField('Text', [validators.required()])
    submit = SubmitField('Upravit')
    delete = SubmitField('Smazat')
    
class EditThreadForm(Form):
    name = TextField('Nadpis', [validators.required()])
    text = TextAreaField('Text', [validators.required()])
    forum_id = SelectField('Fórum', coerce=int)
    submit = SubmitField('Upravit')
    delete = SubmitField('Smazat')

class ThreadForm(PostForm):
    name = TextField('Nadpis', [validators.required()])

class UserForm(Form):
    fullname = TextField('Nadpis', [validators.required()])
    email = TextField('Email', [validators.required()])
    homepage = TextField('Homepage')
    avatar_url = TextField('URL avataru')
    profile = TextAreaField('Profil')
    submit = SubmitField('Upravit')

class AdminUserForm(UserForm):
    group_ids = MultiCheckboxField('Skupiny', coerce=int)

@app.template_filter('datetime')
def datetime_format(value, format='%d. %m. %Y %H:%M:%S'):
    if not value: return "-"
    if isinstance(value, unicode): return value
    return value.strftime(format)

cleaner = Cleaner(comments=False, style=False, embedded=False, annoying_tags=False)

@app.template_filter('clean')
def clean(value):
    try:
        return cleaner.clean_html(value)
    except ParserError:
        return ""

@app.before_request
def before_request():
    if 'user_id' in session:
        g.user = db.session.query(db.User).get(session['user_id'])
        if not g.user:
            # TODO
            pass
        g.user.laststamp = datetime.now()
    else:
        g.user = db.Guest()
    g.now = datetime.now()
    g.yesterday = g.now - timedelta(days=1)

@app.teardown_request
def shutdown_session(exception=None):
    db.session.close()
    db.session.remove()

class ForumForm(Form):
    name = TextField('Jméno', [validators.required()])
    description = TextField('Popisek', [validators.required()])
    category_id = SelectField('Kategorie', coerce=int)
    move_up = SubmitField('↑')
    move_down = SubmitField('↓')
    save = SubmitField('Uložit')
    new_forum_id = SelectField('Nové fórum', coerce=int, default=0)
    delete = SubmitField('Odstranit')

class CategoryForm(Form):
    name = TextField('Jméno', [validators.required()])
    group_id = SelectField('Nutná skupina', coerce=int)
    move_up = SubmitField('↑')
    move_down = SubmitField('↓')
    save = SubmitField('Uložit')
    delete = SubmitField('Odstranit')

@app.route("/")
def index():
    categories = db.session.query(db.Category).order_by(db.Category.position).all()
    uncategorized_fora = db.session.query(db.Forum).filter(db.Forum.category == None, db.Forum.trash == False).order_by(db.Forum.position).all()
    trash = db.session.query(db.Forum).filter(db.Forum.trash == True).scalar()
    if uncategorized_fora:
        categories.append(None)
    latest_posts = db.session.query(db.Post).join(db.Thread).join(db.Forum).outerjoin(db.Category)\
        .filter(or_(db.Forum.category_id==None, db.Category.group_id.in_([None, 0]), db.Category.group_id.in_(group.id for group in g.user.groups)))\
        .filter(db.Forum.trash == False) \
        .filter(db.Post.deleted==False).order_by(db.Post.timestamp.desc())[0:10]
    
    return render_template("index.html", categories=categories, uncategorized_fora=uncategorized_fora, edit_forum = None, latest_posts=latest_posts, trash=trash)

@app.route("/edit-forum/<int:forum_id>", endpoint="edit_forum", methods="GET POST".split())
@app.route("/edit-forum/new", endpoint="edit_forum", methods="GET POST".split())
@app.route("/edit-catgory/<int:category_id>", endpoint="edit_category", methods="GET POST".split())
@app.route("/edit-category/new", endpoint="edit_category", methods="GET POST".split())
def edit_forum_or_category(forum_id=None, category_id=None):
    if not g.user.admin: abort(403) # TODO minrights decorator
    categories = db.session.query(db.Category).order_by(db.Category.position).all()
    uncategorized_fora = db.session.query(db.Forum).filter(db.Forum.category == None, db.Forum.trash == False).order_by(db.Forum.position)
    trash = db.session.query(db.Forum).filter(db.Forum.trash == True).scalar()
    if request.endpoint == 'edit_forum':
        if forum_id:
            forum = db.session.query(db.Forum).get(forum_id)
            #forum.last = forum.position == len(forum.category.fora) - 1 if forum.category else True
            if not forum.category: forum.position = 0
        else:
            forum = db.Forum()
            uncategorized_fora = list(uncategorized_fora) + [forum]
            forum.position = 0
            forum.last = True
        form = ForumForm(request.form, forum)
        form.category_id.choices = [(0, "-")] + [(c.id, c.name) for c in categories if c]
        fora = db.session.query(db.Forum).outerjoin(db.Category).order_by(db.Category.position, db.Forum.position).all()
        form.new_forum_id.choices = [(0, "-")] + [(f.id, f.name) for f in fora]
        editable = forum
    elif request.endpoint == 'edit_category':
        if category_id:
            category = db.session.query(db.Category).get(category_id)
            #category.last = category.position == len(categories) - 1
        else:
            category = db.Category()
            categories = list(categories) + [category]
            category.position = 0
            category.last = True
        form = CategoryForm(request.form, category)
        form.group_id.choices = [(0, "-")] + [(group.id, group.name) for group in db.session.query(db.Group)]
        editable = category
    if request.method == "POST" and form.validate():
        if request.endpoint == 'edit_forum':
            forum.name = form.name.data
            forum.identifier = forum.name.lower().replace(' ', '-')
            forum.description = form.description.data
            forum.category_id = form.category_id.data or None
            forum.category = db.session.query(db.Category).get(form.category_id.data)
        elif request.endpoint == 'edit_category':
            category.name = form.name.data
            category.group_id = form.group_id.data
        if form.save.data:
            if request.endpoint == 'edit_forum':
                if not forum_id:
                    if forum.category_id:
                        forum.position = len(forum.category.fora) - 1
                    db.session.add(forum)
                    flash("Fórum vytvořeno.")
                else:
                    flash("Fórum upraveno.")
            elif request.endpoint == 'edit_category':
                if not category_id:
                    category.position = len(categories) - 1
                    db.session.add(category)
                    flash("Kategorie vytvořena.")
                else:
                    flash("Kategorie upravena.")
            db.session.commit()
            return redirect(url_for('index'))
        elif form.delete.data:
            if request.endpoint == 'edit_forum':
                if not form.new_forum_id.data and forum.threads:
                    flash("Je nutno témata někam přesunout.")
                else:
                    moved = False
                    if form.new_forum_id.data:
                        moved = True
                        new_forum = db.session.query(db.Forum).get(form.new_forum_id.data)
                        for thread in forum.threads:
                            thread.forum = new_forum
                        else:
                            moved = False
                    db.session.delete(forum)
                    if moved:
                        flash("Fórum odstraněno a témata přesunuty.")
                    else:
                        flash("Fórum odstraněno.")
                    db.session.commit()
                    return redirect(url_for('index'))
            elif request.endpoint == 'edit_category':
                db.session.delete(category)
                flash("Kategorie odstraněna.")
                db.session.commit()
                return redirect(url_for('index'))
        else:
            # moving
            i = editable.position
            if request.endpoint == 'edit_forum':
                items = list(forum.category.fora)
            elif request.endpoint == 'edit_category':
                items = list(categories)
            items.remove(editable)
            if form.move_up and form.move_up.data:
                items.insert(i-1, editable)
            elif form.move_down and form.move_down.data:
                items.insert(i+1, editable)
            for i, x in enumerate(items):
                x.position = i
                db.session.add(x)
            db.session.commit()
            if request.endpoint == 'edit_category':
                categories = items
    if editable.position == 0:
        del form.move_up
    if request.endpoint == 'edit_forum':
        if not forum.category or forum.position == len(forum.category.fora) - 1:
            del form.move_down
    elif request.endpoint == 'edit_category':
        if not category.id or category.position == len(categories) - 1:
            del form.move_down
    return render_template("index.html", categories=categories+[None], uncategorized_fora=uncategorized_fora, editable=editable, form=form, new=not bool(forum_id), trash=trash)

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
    login = TextField('Login', [validators.required()])
    fullname = TextField('Jméno', [validators.required()])
    password = PasswordField('Heslo', [
        validators.Required(),
        validators.EqualTo('confirm_password', message='Hesla se musí schodovat')
    ])
    confirm_password = PasswordField('Heslo znovu')
    email = TextField('Email', [validators.required()])
    submit = SubmitField('Zaregistrovat se')

@app.route("/register", methods="GET POST".split())
def register():
    if g.user:
        if g.user.admin:
            flash("Pro ruční registraci účtů ostatním použijte prosím DokuWiki.")
        return redirect(url_for("index"))
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        if db.session.query(db.User).filter(db.User.login == form.login.data.lower()).scalar():
            flash("Tento login je už zabraný, vyberte si prosím jiný.")
        else:
            user = db.User(login=form.login.data.lower(), fullname=form.fullname.data, email=form.email.data, timestamp=datetime.now(), laststamp=datetime.now())
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            g.user = user
            session['user_id'] = g.user.id
            session.permanent = True
            
            flash("Registrace proběhla úspěšně.")
            return redirect(url_for("index"))
    
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
    forum = db.session.query(db.Forum).get(forum_id)
    if not forum: abort(404)
    if forum.category and forum.category.group and forum.category.group not in g.user.groups: abort(403)
    if forum.trash and not g.user.admin: abort(403)
    threads = db.session.query(db.Thread).filter(db.Thread.forum == forum).order_by(db.Thread.laststamp.desc())
    form = None
    if not forum.trash:
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
    thread = db.session.query(db.Thread).get(thread_id)
    if not thread: abort(404)
    if thread.forum.category and thread.forum.category.group and thread.forum.category.group not in g.user.groups: abort(403)
    if thread.forum.trash and not g.user.admin: abort(403)
    posts = thread.posts.filter(db.Post.deleted==False)
    form = None
    if not thread.forum.trash:
        form = PostForm(request.form)
        if g.user and request.method == 'POST' and form.validate():
            now = datetime.now()
            post = db.Post(thread=thread, author=g.user, timestamp=now,
                text=form.text.data)
            db.session.add(post)
            thread.laststamp = now
            db.session.commit()
            return redirect(thread.url+"#latest") # TODO id
    
    g.user.read(thread.last_post)
    
    return render_template("thread.html", thread=thread, forum=thread.forum, posts=posts, form=form, now=datetime.now())

@app.route("/<int:forum_id>/<int:thread_id>/edit/<int:post_id>", methods="GET POST".split())
@app.route("/<int:forum_id>-<forum_identifier>/<int:thread_id>-<thread_identifier>/edit/<int:post_id>", methods="GET POST".split())
def edit_post(forum_id, thread_id, post_id, forum_identifier=None, thread_identifier=None):
    post = db.session.query(db.Post).get(post_id)
    thread = db.session.query(db.Thread).get(thread_id)
    if not post: abort(404)
    if thread.forum.category and thread.forum.category.group and thread.forum.category.group not in g.user.groups: abort(403)
    if post.thread != thread: abort(400)
    if post.deleted:
        # The user probably hit edit multiple times.  Let's just be helpful.
        return redirect(thread.url)
    if post.author != g.user and not g.user.admin: abort(403)
    if post.thread.forum.trash and not g.user.admin: abort(403)
    posts = thread.posts.filter(db.Post.deleted==False)
    
    if post == posts[0] and g.user.admin:
        edit_thread = True
        form = EditThreadForm(request.form, text=post.text, name=thread.name, forum_id=thread.forum_id)
        forums = db.session.query(db.Forum).outerjoin(db.Category).order_by(db.Category.position, db.Forum.position).all()
        form.forum_id.choices = [(f.id, f.name) for f in forums]
    else:
        edit_thread = False
        form = EditPostForm(request.form, text=post.text)
    
    if not g.user.admin: del form.delete
    
    if request.method == 'POST' and form.validate():
        if form.submit.data:
            now = datetime.now()
            new_post = db.Post(thread=thread, author=post.author, timestamp=post.timestamp, editstamp=now,
                text=form.text.data, original=post.original if post.original else post, editor=g.user)
            db.session.add(new_post)
            post.deleted=True
            if edit_thread:
               thread.name = form.name.data
               thread.forum_id = form.forum_id.data
               #forum.fix_laststamp() # TODO
            db.session.commit()
            if edit_thread:
                return redirect(thread.url)
            else:
                return redirect(new_post.url)
        elif form.delete.data:
            post.deleted = True
            db.session.commit()
            return redirect(thread.url)
    
    return render_template("thread.html", thread=thread, forum=thread.forum, posts=posts, form=form, now=datetime.now(), edit_post=post, edit_thread=edit_thread)

@app.route("/users/<int:user_id>")
@app.route("/users/<int:user_id>-<name>")
def user(user_id, name=None):
    user = db.session.query(db.User).get(user_id)
    if not user: abort(404)
    return render_template("user.html", user=user)

@app.route("/users/<int:user_id>/edit", methods="GET POST".split())
@app.route("/users/<int:user_id>-<name>/edit", methods="GET POST".split())
def edit_user(user_id, name=None):
    user = db.session.query(db.User).get(user_id)
    if not user: abort(404)
    if user != g.user and not user.admin: abort(403)
    
    if g.user.admin:
        form = AdminUserForm(request.form, user)
        form.group_ids.choices = []
        for group in db.session.query(db.Group):
            form.group_ids.choices.append((group.id, group.name))
        if form.group_ids.data == None:
            form.group_ids.data = [group.id for group in user.groups]
    else:
        form = UserForm(request.form, user)
        
        
    if request.method == 'POST' and form.validate():
        user.fullname = form.fullname.data
        user.email = form.email.data
        user.homepage = form.homepage.data
        user.avatar_url = form.avatar_url.data
        if g.user.admin:
            user.groups = []
            for group_id in form.group_ids.data:
                user.groups.append(db.session.query(db.Group).get(group_id))
        db.session.commit()
        flash("Uživatel upraven.")
        return redirect(user.url)
    
    return render_template("user.html", user=user, edit=True, form=form)

if not app.debug:
    import logging
    from logging import FileHandler
    file_handler = FileHandler(app_dir+'/flask.log')
    file_handler.setLevel(logging.WARNING)
    app.logger.addHandler(file_handler)

if __name__ == "__main__":
    app.run(host="", port=8080, debug=True, threaded=True)











