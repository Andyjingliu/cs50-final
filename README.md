# Jing Liu — CS50 Final Project

A Custom CMS + Bilingual Commentary Website (Flask, SQLite, Markdown)

## Overview

For my CS50 final project, I designed and built a fully custom CMS (Content Management System) and website using Flask, SQLite, Markdown, HTML/CSS, and a small layer of JavaScript. The site serves as a platform for my long-form analysis, news commentary, and videos connected to my YouTube channel. I also integrated a dynamic video section connected to my YouTube channel.

## The project includes:

- A public-facing homepage with dynamic hero + about sections
- A custom article publishing workflow (create, edit, display)
- Markdown rendering
- Auto-summary generation
- Automatic slug generation
- A video page with embedded YouTube videos & thumbnails
- A polished admin panel with multiple tools
- A custom 404 page
- A custom 500 page
- A responsive layout for desktop and mobile
- A favicon
- Clean and unified global styling

My goal was to build something real — not a toy demo — and to understand every line of code involved.

## Project Structure

```text
project/
├── app.py
├── requirements.txt
├── database.db
├── README.md
├── static/
│   ├── images/
│   ├── styles.css
│   ├── script.js
│   └── favicon.png
└── templates/
    ├── 404.html
    ├── 500.html
    ├── admin_dashboard.html
    ├── admin_edit_article.html
    ├── admin_homepage.html
    ├── admin_new_article.html
    ├── article_detail.html
    ├── articles.html
    ├── base.html
    ├── homepage.html
    └── videos.html
```

## Main Features

### 1. CMS for Article Publishing

I implemented a full article workflow:

**Create a new article**

- Title, summary (auto-summary fallback), body (Markdown), image path
- Markdown is rendered on the front-end using markdown2
- Title → automatically converted to a slug
- Duplicate slugs handled automatically (slug-1, slug-2, etc.)
- Timestamp is generated using datetime.utcnow()

**Edit existing articles**

- Full editing UI using a consistent admin form layout
- Dynamic loading of article content
- Updates apply instantly

**Article detail page**

- Hero image (optional)
- Beautiful typography (headings, code blocks, blockquotes)
- Responsive layout
- Metadata with timestamps

**Article list page**

- Card-based layout showing title, summary, thumbnail, and timestamp
- Fully responsive
- Clean typography

### 2. Homepage with Editable Content

Originally, the hero and about sections were hard-coded.
I refactored them into a new database table:

**homepage_content fields:**

- id (always 1)
- hero_title
- hero_subtitle
- hero_image_path
- about_title
- about_body

And I built a full admin UI that allows me to edit these fields anytime from:
/admin/homepage

The homepage now dynamically loads all content from the database, including:

- Hero title
- Hero subtitle
- Hero image
- About section title
- About section body
- Latest 4 articles
- Latest 4 YouTube videos

### 3. Videos Page + YouTube Thumbnails

The videos page pulls a list of YouTube video IDs from the database.

For each one, the site generates:

- YouTube thumbnail (automatically)
- Playable embedded video
- Optional descriptions
- A clean shadowed card layout

I also implemented a YouTube thumbnail → iframe swapper using script.js:

- Shows thumbnail first
- When clicked, replaces thumbnail with embedded YouTube player
- Smooth fade-in
- No jumping or flashing
- Faster initial load vs immediate iframe embedding

This greatly improves performance and user experience.

### 4. Admin Dashboard

I created a simple admin dashboard to unify all back-end actions:
/admin

Buttons link to:

- Publish new article
- Edit existing articles
- Edit homepage content

This creates a cleaner workflow and helps prepare the project for future expansion.

### 5. Custom 404 Page

I implemented a custom error handler:

```bash
@app.errorhandler(404)
def page_not_found(error):
return render_template("404.html"), 404
```

The 404 page includes:

- Centered layout
- Clear message
- Link back to the homepage
- Clean professional typography

### 6. Custom 500 Page

I implemented a custom error handler:

```bash
@app.errorhandler(500)
def internal_server_error(error):
return render_template("500.html"), 500
```

The 500 page includes:

- Centered layout
- Clear message
- Link back to the homepage
- Clean professional typography

### 7. Visual and UX Polish

I put a significant amount of effort into making the project look polished:

- Unified button design
- Unified global link styling
- Standardized card spacing
- Consistent grid layouts
- Responsive video wrapper
- Integrated favicon
- Soft shadows, rounded corners
- Matching typography across all pages
- Mobile responsiveness

The final result is visually cohesive and surprisingly close to a production site.

**Technologies Used**

- Python / Flask (routing, sessions, rendering, backend logic)
- SQLite (database storage)
- Jinja2 (template rendering)
- Markdown2 (article body parsing)
- HTML5 / CSS3 (structure + styling)
- Custom responsive CSS grid layouts
- JavaScript (YouTube thumbnail swapper)
- Git + GitHub Desktop (version control)
- Virtual environment for dependency management

## How to Run the Project

### 1. Clone the repository

```bash
git clone https://github.com/Andyjingliu/cs50-final
cd cs50-final

```

### 2. Create and activate a virtual environment

- **macOS / Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
```

- **Windows (PowerShell):**

```bash
python -m venv venv
venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the application

**Option A — Run with Python:**

```bash
python app.py
```

**Option B — Run with Flask:**

- **On macOS / Linux:**

```bash
export FLASK_APP=app.py
export FLASK_ENV=development  # optional for auto-reload
flask run
```

- **On Windows (PowerShell):**

```bash
$env:FLASK_APP = "app.py"
$env:FLASK_ENV = "development"  # optional for auto-reload
flask run
```

### 5. Open your browser and visit:

```bash
http://127.0.0.1:5000/
```

## Future Improvements

### This CMS is a foundation I plan to grow. Features I may add:

- Image upload
- Pagination for articles
- Live search
- Tag system
- Dark mode toggle
- Better admin editor (rich text / WYSIWYG)
- authentication

### Helper function improvements I may add:

- auto_summary: In rare edge cases (<1%), it may drop a word when punctuation follows the cutoff; refining boundary detection would fix this.
- slugify: Apostrophes inside words currently split terms like "China’s" → "china-s"; treating apostrophes as letters would improve slug quality.
- generate_unique_slug: The linear collision approach works now but could be upgraded to an optimistic concurrency method for better scalability.
- Article creation flow: Slug generation and insertion occur in separate steps; an atomic "create article with unique slug" helper would avoid race conditions.

### Homepage Table Robustness (Iron-Clad Design)

- Single-row protection: The homepage_content table can be strengthened by adding a constraint such as CHECK (id = 1) so that only one record can ever exist. This prevents accidental duplicate rows and guarantees the homepage always reads the correct data.

## AI Usage Disclosure

This project was built in accordance with CS50’s final project policy regarding the use of AI tools. I used AI (ChatGPT and Gemini 3 Pro) as a helper to accelerate my workflow, clarify concepts, and improve readability, but all architectural decisions, core logic, database design, routing structure, templates, and front-end implementation were written and fully understood by me.

Specifically, AI assistance was used for:

- Brainstorming approaches to structuring Flask routes and templates
- Reviewing Python, SQL, and Jinja syntax questions
- Debugging guidance during development
- Refining code comments for clarity and consistency
- Suggestions for CSS styling, layout organization, and UI polish
- Assistance in drafting and refining this README

The _implementation itself_ — including the CMS workflow, slug generation, database schema, Markdown integration, YouTube thumbnail loader, custom admin panel, homepage editor, and all HTML/CSS/JS — was written manually and reviewed line-by-line to ensure complete understanding.

All AI involvement adhered strictly to CS50’s requirement that the “essence of the work” be my own, and any AI-assisted parts are documented here.

## Conclusion

This project is the single most ambitious coding project I’ve done so far. I treated it as a real product — not a classroom exercise — and this helped me understand Flask, SQL, routing, design patterns, CSS organization, and overall full-stack architecture at a much deeper level.

CS50 has changed the way I think about building things, and this project is proof of how far I’ve come.
