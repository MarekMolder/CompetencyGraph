from flask import Flask, session, redirect, url_for, request, render_template, flash
from app.routes.graph_routes import main_bp
import config
import os, sys

sys.path.insert(0, os.path.dirname(__file__))

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# --- Login ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == config.ADMIN_USERNAME and password == config.ADMIN_PASSWORD:
            session["logged_in"] = True
            flash("Sisselogimine õnnestus!", "success")
            return redirect(url_for("main.index"))
        else:
            flash("Vale kasutajanimi või parool.", "danger")
    return render_template("login.html")

# --- Logout ---
@app.route("/logout")
def logout():
    session.clear()
    flash("Oled välja logitud.", "info")
    return redirect(url_for("main.index"))

# --- Blueprint ---
app.register_blueprint(main_bp)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
