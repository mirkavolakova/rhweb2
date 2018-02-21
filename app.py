#!/usr/bin/python3
from flask import Flask, render_template, request, flash, redirect, session, abort, url_for, make_response, g

app = Flask('rhweb2')

@app.context_processor
def new_template_globals():
    return {
        'zip': zip,
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

if __name__ == "__main__":
    app.run(host="", port=9011, debug=True)
