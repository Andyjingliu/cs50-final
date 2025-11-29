import re
import sqlite3
import string
import unicodedata
from contextlib import closing
from datetime import datetime

import markdown2
from flask import Flask, abort, flash, redirect, render_template, request, url_for

app = Flask(__name__)

app.secret_key = "dev_key_123"

DATABASE = "database.db"


import string


def auto_summary(text: str, max_chars: int = 200) -> str:
    """
    Return a shortened, clean summary without breaking words.
    """
    # 1. Normalize whitespace (handles \n, \t, and double spaces)
    clean = " ".join(text.split())

    if len(clean) <= max_chars:
        return clean

    # 2. Initial cut
    snippet = clean[:max_chars]

    # 3. If the next character in 'clean' is NOT a space, we are likely mid-word.
    # We must backtrack to the last space to avoid cutting the word.
    if clean[max_chars] != " ":
        last_space = snippet.rfind(" ")
        # Only slice back if there is actually a space (avoid empty string on long words)
        if last_space != -1:
            snippet = snippet[:last_space]

    # 4. Clean up trailing punctuation (avoids "word,..." or "end....")
    # string.punctuation includes !"#$%&'()*+,-./:;<=>?@[\]^_`{|}~
    snippet = snippet.rstrip(string.punctuation + " ")

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
    """
    Convert a string into a URL-friendly slug.
    """
    # 1. Normalize Unicode characters (e.g., convert 'é' to 'e')
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")

    # 2. Lowercase and strip whitespace
    text = text.lower().strip()

    # 3. Replace non-alphanumeric characters with hyphens
    # Note: We replaced the redundant step here by trusting the '+' quantifier
    text = re.sub(r"[^a-z0-9]+", "-", text)

    # 4. Remove leading/trailing hyphens
    text = text.strip("-")

    # 5. Fallback
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
        return dt.strftime("%b %d, %Y %H:%M:%S")
    except ValueError:
        return value


@app.route("/")
def homepage():
    """
    Homepage route.
    """
    # Open a database connection. It will be closed automatically
    # when we exit this 'with' block.
    with get_db_connection() as conn:

        # Load the single homepage content row (hero + about section).
        # We assume homepage_content has exactly one row with id = 1.
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

        # Load the 4 newest articles to show in the "Latest Articles" section.
        # ORDER BY created_at DESC ensures that the most recently created
        # articles appear first.
        articles = conn.execute(
            "SELECT * FROM articles ORDER BY created_at DESC LIMIT 4"
        ).fetchall()

        # Load the 4 most recent videos for the "Latest Videos" section.
        videos = conn.execute(
            "SELECT * FROM videos ORDER BY id DESC LIMIT 4"
        ).fetchall()

    # At this point, the database connection is closed, but we still have
    # the data in memory (home_content, articles, videos).

    # Render the homepage template with all the data needed to display
    # the hero section, about section, latest articles, and latest videos.
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
    # Open a database connection using a context manager.
    # The connection will automatically close when the block ends.
    with get_db_connection() as conn:

        # Fetch the article whose slug matches the one from the URL.
        # fetchone() is used because we expect exactly one article.
        article = conn.execute(
            "SELECT * FROM articles WHERE slug = ?", (slug,)
        ).fetchone()

    # After leaving the 'with' block, the database connection is automatically closed.

    # If no article is found, return a 404 Not Found page.
    if article is None:
        abort(404)

    # Convert the Markdown body into HTML for safe display in the template.
    # Extras enable support for code blocks, tables, strike-through, etc.
    body_html = markdown2.markdown(
        article["body"], extras=["fenced-code-blocks", "tables", "strike", "smarty"]
    )

    # Render the article detail page with the article data and converted HTML body.
    return render_template("article_detail.html", article=article, body_html=body_html)


@app.route("/videos")
def videos():
    # Open a database connection. The connection will automatically close
    # once we exit the 'with' block below.
    with get_db_connection() as conn:

        # Retrieve all videos from the database, ordered by newest first.
        # fetchall() is correct here because we expect multiple rows.
        videos = conn.execute(
            "SELECT id, title, youtube_id, description FROM videos ORDER BY id DESC"
        ).fetchall()

    # After the 'with' block, the database connection is automatically closed.

    # Render the videos page, passing the list of videos to the template.
    return render_template("videos.html", videos=videos)


@app.route("/admin")
def admin_dashboard():
    # Open a database connection. It will automatically close
    # once the 'with' block finishes, even if an error occurs.
    with get_db_connection() as conn:

        # Fetch the 5 most recent articles for quick editing access.
        articles = conn.execute(
            """
            SELECT id, title, created_at
            FROM articles
            ORDER BY created_at DESC
            LIMIT 5
            """
        ).fetchall()

        # Fetch the 5 most recent videos (optional dashboard section).
        videos = conn.execute(
            """
            SELECT id, title
            FROM videos
            ORDER BY id DESC
            LIMIT 5
            """
        ).fetchall()

    # Connection auto-closes here.

    # Render the admin dashboard, passing recent articles and videos.
    return render_template(
        "admin_dashboard.html",
        articles=articles,
        videos=videos,
    )


@app.route("/admin/homepage", methods=["GET", "POST"])
def admin_homepage():
    # Initialize error as None. It will stay None if this is a GET request
    # or if a POST request succeeds.
    error = None

    # Open the database connection.
    # It will automatically close when we exit this 'with' block.
    with get_db_connection() as conn:

        # --- PHASE 1: Handle Form Submission (POST) ---
        if request.method == "POST":
            # 1. Read and clean form fields
            # We use .strip() to remove accidental whitespace at start/end
            hero_title = request.form.get("hero_title", "").strip()
            hero_subtitle = request.form.get("hero_subtitle", "").strip()
            hero_image_path = request.form.get("hero_image_path", "").strip()
            about_title = request.form.get("about_title", "").strip()
            about_body = request.form.get("about_body", "").strip()

            # 2. Validation
            # If mandatory fields are empty, set the error message.
            if not hero_title or not hero_subtitle or not about_title:
                error = "Hero title, hero subtitle, and about title are required."

            # 3. Update Database (Only if no error)
            else:
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
                    (
                        hero_title,
                        hero_subtitle,
                        hero_image_path,
                        about_title,
                        about_body,
                    ),
                )
                # 🚨 IMPORTANT: Save the changes!
                conn.commit()

                # Post/Redirect/Get Pattern:
                # After a successful POST, redirect the user back to the same page.
                # This prevents the browser from resubmitting the form if the user hits "Refresh".
                return redirect(url_for("homepage"))

        # --- PHASE 2: Fetch Data for Display (GET or Failed POST) ---
        # If we are here, it means either:
        # A) It's a normal GET request (user just arrived).
        # B) It was a POST request but had an error (we need to show the form again).

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

    # Exit 'with' block -> Connection closes automatically here.

    # Render the template, passing the current DB data and any error message.
    return render_template(
        "admin_homepage.html",
        homepage=homepage,
        error=error,
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


@app.route("/admin/articles/<int:article_id>/delete", methods=["POST"])
def delete_article(article_id: int):
    """
    Handle POST request to delete a specific article by ID from the admin dashboard.
    - Tries to delete the row in a single DELETE statement (no extra SELECT).
    - Uses cursor.rowcount to determine whether anything was actually deleted.
    - On DB failure, returns a 500 error via the global error handler.
    """
    try:
        # Open a DB connection for this request.
        # The connection will be closed automatically when we leave the 'with' block.
        with closing(get_db_connection()) as conn:
            # Delete the article in one step. If the ID doesn't exist, this affects 0 rows.
            cursor = conn.execute(
                "DELETE FROM articles WHERE id = ?",
                (article_id,),
            )
            # Persist the change to disk.
            conn.commit()

    except Exception as e:
        # In a real app, you'd use app.logger.error(...) instead of print.
        print(f"Database error while deleting article {article_id}: {e}")
        # Let the 500 error handler render a friendly error page.
        abort(500, description="An error occurred while trying to delete the article.")

    # Check how many rows the DELETE actually touched.
    if cursor.rowcount == 0:
        # No matching article ID in the database.
        flash("Article not found.", "error")
    else:
        # At least one row was deleted (normally exactly 1).
        flash("Article deleted successfully.", "success")

    # Always send the admin back to the dashboard after the operation.
    return redirect(url_for("admin_dashboard"))


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


# Register a custom handler for HTTP 404 errors (page not found)
@app.errorhandler(404)
def page_not_found(error):
    """
    Handles all 404 Not Found errors.
    This function is triggered in two cases:
    1) When a user requests a URL that does not match any route.
    2) When a route exists but the code explicitly calls abort(404),
       usually because a database record or resource was not found.
    It returns a custom 404 page along with the correct HTTP status code.
    """
    # Render custom 404 template and return the correct status code
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_server_error(error):
    """
    Custom handler for HTTP 500 errors (Internal Server Error).
    This runs whenever:
    - Flask encounters an unexpected exception, OR
    - The code calls abort(500).
    It lets the app return a clean, user-friendly error page
    instead of Flask's default debug-style 500 page.
    """
    # Render a custom template for internal errors.
    # The ", 500" ensures the browser receives the correct HTTP status code
    # (important for SEO, caching, and client behavior).
    return render_template("500.html"), 500


if __name__ == "__main__":
    app.run(debug=True)
