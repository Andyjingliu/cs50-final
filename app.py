import sqlite3
from flask import Flask, render_template

app = Flask(__name__)

DATABASE = "database.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/articles")
def articles():
    conn = get_db_connection()
    articles = conn.execute(
        "SELECT id, title, summary, slug, image_path FROM articles ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return render_template("articles.html", articles=articles)

@app.route("/videos")
def videos():
    conn = get_db_connection()
    videos = conn.execute(
        "SELECT id, title, youtube_id, description FROM videos ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return render_template("videos.html", videos=videos)

if __name__ == "__main__":
    app.run(debug=True)