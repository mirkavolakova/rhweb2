#!/usr/bin/python3
import os

from flask import Flask, render_template, render_template_string, request, flash, redirect, session, abort, url_for, make_response, g

from dokuwiki import DokuWiki, DokuWikiError
from bs4 import BeautifulSoup

app = Flask('rhweb2')
app_dir = os.path.dirname(os.path.abspath(__file__))

DOKUUSER = "rhweb"
DOKUPASS = open(app_dir+'/DOKUPASS').read().strip()

wiki = DokuWiki("http://routeer.retroherna.org/wiki", DOKUUSER, DOKUPASS)

def wikipage(name, force=False):
    name = name.replace("/", ":")
    
    if not force and not g.purge:
        try:
            page = open(app_dir+"/cache/"+name+".html").read()
            g.caching_comment += "{} read from cache\n".format(name)
            return page
        except Exception as ex:
            g.caching_comment += "{} cache open fail: {}\n".format(name, ex)
    
    page = None
    for i in range(3):
        try:
            page = wiki.pages.html(name)
            break
        except Exception as ex:
            g.caching_comment += "{} get wiki page fail {}: {}\n".format(name, i, ex)
    
    if page:
        g.caching_comment += "{} got fresh wiki page\n".format(name)
    
    if not page and force:
        try:
            return open(app_dir+"/cache/"+page+".html").read().decode('utf-8')
        except Exception as ex:
            g.caching_comment += "cache open fail w force: {}\n".format(ex)
    
    if not page:
        return None
    
    open(app_dir+"/cache/"+name+".html", "w").write(page)
    
    return page

def transform_wikipage(page):
    page = page.replace("~CLEAR~", '<div style="clear: both;"></div>')
    page = page.replace("retroherna.cz", "retroherna.org")
    page = BeautifulSoup(page, "lxml")
    for a in page.find_all('a'):
        if a.get('href') and "/wiki/doku.php" in a['href']:
            a['href'] = a['href'].replace("/wiki/doku.php?id=web:", "/").replace(':', '/')
    
    if False:
        for img in page.find_all('img'):
            img['src'] = img['src'].replace("/wiki/lib/exe/fetch.php", "http://routeer.retroherna.org/wiki/lib/exe/fetch.php")
            title = img.get('title')
            
            parent = img.parent
            if parent.name == "a" and parent['href'].startswith("/wiki"):
                parent.name = "div"
                del parent['href']
            else:
                parent = page.new_tag("div")
                img.wrap(parent)
            parent['class'] = img['class'] + [" mediawrap"]
            if 'mediacenter' in img['class'] and img.get('width'):
                # life is too short
                parent['style'] = 'width: {}px;'.format(img['width'])
            del img['class']
            
            # XXX yes this is necessary, thanks dokuwiki
            if title and not any(title.endswith(t) for t in ("png", "jpg", "jpeg", "gif")):
                title = page.new_tag("div")
                title['class'] = "mediatitle"
                if img.get('width'):
                    title['style'] = "max-width: {}px;".format(img['width'])
                title.string = img['title']
                parent.append(title)
    
    return page

@app.before_request
def before_request():
    g.caching_comment = ""
    
    g.purge = False
    if 'purge' in request.args:
        g.purge = True
        g.caching_comment += "purging\n"

    g.banner = transform_wikipage(wikipage("web:banner"))
    g.footer = transform_wikipage(wikipage("web:footer"))
    
    g.pagetitle = None

@app.context_processor
def new_template_globals():
    urls = {
        "facebook": "https://facebook.com/retroherna",
        "youtube": "https://www.youtube.com/channel/UCJNNkhuJNO5dujOhy9r-jdA",
        "twitter": "https://twitter.com/hernihistorie",
        "discord": "https://discord.gg/9jajeqZ",
        "bankaccount": "https://www.moneta.cz/firmy/instituce-a-verejna-sprava/transparentni-ucty/001/-/transparent-account/8686868686",
        "forum": "/forum/",
        "email": "mailto:info@retroherna.org",
        "hernihistorie": "https://hernihistorie.cz/",
    }
    return {
        'zip': zip,
        'urls': urls,
    }

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def page(path):
    if not path: path = "index"
    path = path.rstrip('/')
    if ':' in path:
        return redirect('/'+path.replace(':', '/'))
    #if path not in DOKUPAGES: abort(404)
    
    page = None
    #if path.startswith("encyklopedie/"):
    #    page = wikipage(path.replace("/", ":"))
    #else:
    page = wikipage("web2:"+path.replace("/", ":"))
    if not page: abort(404)
    
    page = transform_wikipage(page)
    
    h1 = page.find('h1')
    if h1:
        g.pagetitle = h1.string
    elif path == "index":
        g.pagetitle = None
    else:
        g.pagetitle = path
    
    page = """{% extends '_base.html' %}
{% block content %}
""" + page.prettify() + """
{% endblock %}
"""
    
    return render_template_string(page, path=path, page=page)


"""
@app.route("/")
def o_nas():
    return render_template("o-nas.html")

@app.route("/kontakt")
def kontakt():
    return render_template("kontakt.html")
    
@app.route("/komunita")
def komunita():
    return render_template("komunita.html")

@app.route("/vyjezdy")
def vyjezdy():
    return render_template("vyjezdy.html")

@app.route("/clanky")
def clanky():
    return render_template("clanky.html")
"""

if __name__ == "__main__":
    app.run(host="", port=9011, debug=True)
