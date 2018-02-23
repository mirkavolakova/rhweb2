#!/usr/bin/python3
from flask import Flask, render_template, request, flash, redirect, session, abort, url_for, make_response, g

app = Flask('rhweb2')

@app.context_processor
def new_template_globals():
    urls = {
        "facebook": "https://facebook.com/retroherna",
        "youtube": "https://www.youtube.com/channel/UCJNNkhuJNO5dujOhy9r-jdA",
        "twitter": "https://twitter.com/hernihistorie",
        "discord": "https://discord.gg/9jajeqZ",
        "bankaccount": "https://www.moneta.cz/firmy/instituce-a-verejna-sprava/transparentni-ucty/001/-/transparent-account/8686868686",
        "forum": "/forum/",
        "email": "mailto:info@retroherna.org"
    }
    return {
        'zip': zip,
        'urls': urls,
    }

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

if __name__ == "__main__":
    app.run(host="", port=9011, debug=True)
