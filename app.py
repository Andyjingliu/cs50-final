import re
import sqlite3
from datetime import datetime

import markdown2
from flask import Flask, abort, redirect, render_template, request, url_for

app = Flask(__name__)

DATABASE = "database.db"


def auto_summary(text, max_chars=200):
    """
    Create a clean summary with these rules:
    1. Never break words in the middle if we can avoid it.
    2. If the cut lands exactly on a word boundary, keep the whole word.
    3. Punctuation right after the cut is treated as a clean boundary.
    4. Only shorten when needed.
    5. Append "..." only when truncation happens.
    """

    # Normalize the text:
    # - strip leading/trailing whitespace
    # - replace newlines with spaces so the summary is single-line friendly
    clean = text.strip().replace("\n", " ")

    # If the whole text fits within the limit, no summary needed
    if len(clean) <= max_chars:
        return clean

    # Take the first max_chars characters as an initial candidate
    snippet = clean[:max_chars]

    # If the snippet ends with a space, we already have a clean word boundary.
    # Just strip the extra space and add "..." to show truncation.
    if snippet.endswith(" "):
        return snippet.rstrip() + "..."

    # At this point, the snippet does NOT end with a space.
    # Look at the next character in the original text (the one right after the cut).
    next_char = clean[max_chars]

    # Case 1: Next character is a letter or digit
    # → we almost certainly cut inside a word ("Flas|k", "202|4", etc.)
    if next_char.isalpha() or next_char.isdigit():
        # Find the last space in the snippet so we can back up to the last full word.
        last_space = snippet.rfind(" ")

        # If there is no space at all, the snippet is one long word.
        # In that edge case, we have no choice but to hard-truncate.
        if last_space == -1:
            return snippet + "..."

        # Otherwise, cut cleanly at the last full word and add "..."
        return snippet[:last_space] + "..."

    # Case 2: Next character is whitespace
    # e.g. "Learning Flask| is"
    # → we actually ended at the end of a complete word already.
    if next_char.isspace():
        return snippet + "..."

    # Case 3: Next character is punctuation or something else
    # e.g. "Learning Flask|."  → "." is punctuation, but the word "Flask" is complete.
    # We treat this as a clean boundary as well.
    return snippet + "..."


def get_db_connection():
    """
    Open a connection to the SQLite database and configure it so that
    each row behaves like a dictionary (accessible by column name).
    """

    # Connect to the SQLite database file whose path is stored in DATABASE.
    # This returns a new connection object each time the function is called.
    conn = sqlite3.connect(DATABASE)

    # Configure the connection so that rows are returned as sqlite3.Row objects.
    # This allows us to do row["title"] instead of row[0], which is cleaner.
    conn.row_factory = sqlite3.Row

    # Return the configured connection to the caller.
    return conn


def slugify(text: str) -> str:
    text = text.strip().lower()
    # replace anything not a–z or 0–9 with hyphens
    text = re.sub(r"[^a-z0-9]+", "-", text)
    # collapse multiple hyphens
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "article"


def generate_unique_slug(title: str, conn) -> str:
    """Generate a slug from title, and if it already exists,
    append -2, -3, ... until it’s unique."""
    base_slug = slugify(title)
    slug = base_slug
    counter = 2

    while True:
        row = conn.execute(
            "SELECT 1 FROM articles WHERE slug = ?",
            (slug,),
        ).fetchone()

        if row is None:
            # slug is free
            return slug

        # slug taken → try base-2, base-3, ...
        slug = f"{base_slug}-{counter}"
        counter += 1


@app.template_filter("nice_date")
def nice_date(value):
    """
    Turn '2025-11-23 09:33:12' into 'Nov 23, 2025'.
    If anything goes wrong, just return the original value.
    """
    if not value:
        return ""
    try:
        dt = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%b %d, %Y")
    except ValueError:
        return value


@app.route("/")
def homepage():
    with get_db_connection() as conn:

        # Load hero + about content (single row, id = 1)
        home_content = conn.execute(
            """
            SELECT hero_title,
                   hero_subtitle,
                   hero_image_path,
                   about_title,
                   about_body
            FROM homepage_content
            WHERE id = 1
            """
        ).fetchone()

        # Load latest 4 articles
        articles = conn.execute(
            "SELECT * FROM articles ORDER BY created_at DESC LIMIT 4"
        ).fetchall()

        # Load latest 4 videos
        videos = conn.execute(
            "SELECT * FROM videos ORDER BY id DESC LIMIT 4"
        ).fetchall()

    # ← automatic close happens right here

    return render_template(
        "homepage.html",
        home_content=home_content,
        articles=articles,
        videos=videos,
    )


@app.route("/articles")
def articles():
    # Open a database connection using a context manager.
    # The connection will automatically close after the block finishes.
    with get_db_connection() as conn:

        # Query the database for all articles, retrieving only the columns
        # needed for the articles list page. We order by created_at so
        # the newest articles appear first.
        articles = conn.execute(
            """
            SELECT
                id,
                title,
                summary,
                slug,
                image_path,
                created_at
            FROM articles
            ORDER BY created_at DESC
            """
        ).fetchall()
        # fetchall() returns a list of rows (each row behaves like a dict
        # because row_factory = sqlite3.Row is set in get_db_connection).

    # After exiting the 'with' block, the database connection is closed automatically.

    # Render the articles page and pass the list of articles to the template.
    return render_template("articles.html", articles=articles)


@app.route("/articles/<slug>")
def article_detail(slug):
    conn = get_db_connection()
    article = conn.execute("SELECT * FROM articles WHERE slug = ?", (slug,)).fetchone()
    conn.close()

    if article is None:
        abort(404)

    # Convert Markdown in article["body"] to HTML
    body_html = markdown2.markdown(
        article["body"], extras=["fenced-code-blocks", "tables", "strike", "smarty"]
    )

    return render_template("article_detail.html", article=article, body_html=body_html)


@app.route("/videos")
def videos():
    conn = get_db_connection()
    videos = conn.execute(
        "SELECT id, title, youtube_id, description FROM videos ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return render_template("videos.html", videos=videos)


@app.route("/admin")
def admin_dashboard():
    conn = get_db_connection()

    # Latest 5 articles for quick editing
    articles = conn.execute(
        """
        SELECT id, title, created_at
        FROM articles
        ORDER BY created_at DESC
        LIMIT 5
        """
    ).fetchall()

    # Latest 5 videos (optional section on dashboard)
    videos = conn.execute(
        """
        SELECT id, title
        FROM videos
        ORDER BY id DESC
        LIMIT 5
        """
    ).fetchall()

    conn.close()

    return render_template(
        "admin_dashboard.html",
        articles=articles,
        videos=videos,
    )


@app.route("/admin/homepage", methods=["GET", "POST"])
def admin_homepage():
    conn = get_db_connection()

    if request.method == "POST":
        hero_title = request.form.get("hero_title", "").strip()
        hero_subtitle = request.form.get("hero_subtitle", "").strip()
        hero_image_path = request.form.get("hero_image_path", "").strip()
        about_title = request.form.get("about_title", "").strip()
        about_body = request.form.get("about_body", "").strip()

        error = None
        if not hero_title or not hero_subtitle or not about_title or not about_body:
            error = (
                "Hero title, hero subtitle, about title, and about body are required."
            )

        if error:
            homepage = conn.execute(
                """
                SELECT hero_title,
                       hero_subtitle,
                       hero_image_path,
                       about_title,
                       about_body
                FROM homepage_content
                WHERE id = 1
                """
            ).fetchone()
            conn.close()
            return render_template(
                "admin_homepage.html",
                homepage=homepage,
                error=error,
            )

        # Update the single homepage row
        conn.execute(
            """
            UPDATE homepage_content
            SET hero_title = ?,
                hero_subtitle = ?,
                hero_image_path = ?,
                about_title = ?,
                about_body = ?
            WHERE id = 1
            """,
            (hero_title, hero_subtitle, hero_image_path, about_title, about_body),
        )
        conn.commit()
        conn.close()
        return redirect(url_for("homepage"))

    # GET request — load existing data
    homepage = conn.execute(
        """
        SELECT hero_title,
               hero_subtitle,
               hero_image_path,
               about_title,
               about_body
        FROM homepage_content
        WHERE id = 1
        """
    ).fetchone()
    conn.close()

    return render_template(
        "admin_homepage.html",
        homepage=homepage,
        error=None,
    )


@app.route("/admin/new-article", methods=["GET", "POST"])
def new_article():
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        summary = (request.form.get("summary") or "").strip()
        body = (request.form.get("body") or "").strip()
        image_path = (request.form.get("image_path") or "").strip()

        # Basic validation
        if not title or not body:
            error = "Title and body are required."
            return render_template(
                "admin_new_article.html",
                error=error,
                mode="new",
                submit_label="Publish Article",
                form={
                    "title": title,
                    "summary": summary,
                    "body": body,
                    "image_path": image_path,
                },
            )

        # Open DB before generating slug
        conn = get_db_connection()

        # Generate unique slug using the DB
        slug = generate_unique_slug(title, conn)

        # Auto summary if empty
        if not summary:
            summary = auto_summary(body)

        # Insert into DB
        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO articles (title, slug, summary, body, image_path)
            VALUES (?, ?, ?, ?, ?)
            """,
            (title, slug, summary, body, image_path),
        )
        conn.commit()
        conn.close()

        # Redirect to new article
        return redirect(url_for("article_detail", slug=slug))

    # GET → show empty form
    return render_template(
        "admin_new_article.html",
        error=None,
        mode="new",
        submit_label="Publish Article",
        form={"title": "", "summary": "", "body": "", "image_path": ""},
    )


@app.route("/admin/articles/<int:article_id>/edit", methods=["GET", "POST"])
def edit_article(article_id):
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row

    # Load existing article
    article = conn.execute(
        "SELECT * FROM articles WHERE id = ?",
        (article_id,),
    ).fetchone()

    if article is None:
        conn.close()
        abort(404)

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        summary = (request.form.get("summary") or "").strip()
        body = (request.form.get("body") or "").strip()
        image_path = (request.form.get("image_path") or "").strip()

        # Basic validation
        if not title or not body:
            error = "Title and body are required."

            conn.close()
            return render_template(
                "admin_edit_article.html",
                error=error,
                form={
                    "title": title,
                    "summary": summary,
                    "body": body,
                    "image_path": image_path,
                },
                article=article,
            )

        # New slug from title
        slug = slugify(title)

        # Check slug uniqueness, excluding this article itself
        existing = conn.execute(
            "SELECT id FROM articles WHERE slug = ? AND id != ?",
            (slug, article_id),
        ).fetchone()

        if existing:
            error = "Another article already uses this title. Please choose a different title."
            conn.close()
            return render_template(
                "admin_edit_article.html",
                error=error,
                form={
                    "title": title,
                    "summary": summary,
                    "body": body,
                    "image_path": image_path,
                },
                article=article,
            )

        # If summary left empty, auto-generate
        if not summary:
            summary = auto_summary(body)

        # UPDATE instead of INSERT
        conn.execute(
            """
            UPDATE articles
            SET title = ?, slug = ?, summary = ?, body = ?, image_path = ?
            WHERE id = ?
            """,
            (title, slug, summary, body, image_path, article_id),
        )
        conn.commit()
        conn.close()

        # Redirect to detail page
        return redirect(url_for("article_detail", slug=slug))

    # GET request → show form prefilled with existing article
    form = {
        "title": article["title"],
        "summary": article["summary"] or "",
        "body": article["body"],
        "image_path": article["image_path"] or "",
    }
    conn.close()
    return render_template(
        "admin_edit_article.html",
        error=None,
        form=form,
        article=article,
    )


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)
