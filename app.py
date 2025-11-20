from flask import Flask, render_template

app = Flask(__name__)

ARTICLES = [
    {
        "title": "First Article",
        "Summary": "This is a short summary of the first article.",
        "Slug": "first-article",
    },
    {
        "title": "Second Article",
        "summary": "Another example article summary.",
        "slug": "second-article",
    },
]

VIDEOS = [
    {
        "title": "Sample Video 1",
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    },
    {
        "title": "Sample Video 2",
        "url": "https://www.youtube.com/watch?v=o-YBDTqX_ZU",
    },
]

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/articles")
def articles():
    return render_template("articles.html", articles=ARTICLES)

@app.route("/videos")
def videos():
    return render_template("videos.html", videos=VIDEOS)

if __name__ == "__main__":
    app.run(debug=True)