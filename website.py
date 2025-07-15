from flask import Flask, render_template,request,jsonify
import os

app= Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route("/special")
def special():
    return render_template("special.html")

if __name__ == '__main__':
    app.run(debug=True)



