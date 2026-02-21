from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from flask import Flask, redirect, render_template, request, url_for
from werkzeug.middleware.proxy_fix import ProxyFix


BASE_DIR = Path(__file__).resolve().parent 
DB_PATH = BASE_DIR / "data" / "blendora.db"
SEED_JSON_PATH = BASE_DIR / "data" / "blendora.json"

app = Flask(__name__)
# Trusts 1 hop (Apache) for all headers
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
app.url_map.strict_slashes = False


@dataclass
class Recipe:
    id: int
    name: str
    description: str
    instructions: list[str]
    image_url: str | None = None
    is_favorite: bool = False


def get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_db()
    ensure_schema(conn)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS count FROM recipes;")
    count = cur.fetchone()["count"]
    if count == 0:
        seed_from_json(conn, load_seed_json())

    conn.close()


def ensure_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            instructions_json TEXT NOT NULL,
            image_url TEXT,
            is_favorite INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS benefits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS recipe_ingredients (
            recipe_id INTEGER NOT NULL,
            ingredient_id INTEGER NOT NULL,
            qty_1 TEXT NOT NULL,
            qty_2 TEXT NOT NULL,
            unit TEXT,
            PRIMARY KEY (recipe_id, ingredient_id),
            FOREIGN KEY (recipe_id) REFERENCES recipes (id),
            FOREIGN KEY (ingredient_id) REFERENCES ingredients (id)
        );

        CREATE TABLE IF NOT EXISTS recipe_benefits (
            recipe_id INTEGER NOT NULL,
            benefit_id INTEGER NOT NULL,
            rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
            PRIMARY KEY (recipe_id, benefit_id),
            FOREIGN KEY (recipe_id) REFERENCES recipes (id),
            FOREIGN KEY (benefit_id) REFERENCES benefits (id)
        );
        """
    )
    conn.commit()
    ensure_recipe_image_column(conn)
    ensure_recipe_favorite_column(conn)


def ensure_recipe_image_column(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(recipes);")
    columns = {row["name"] for row in cur.fetchall()}
    if "image_url" not in columns:
        cur.execute("ALTER TABLE recipes ADD COLUMN image_url TEXT;")
        conn.commit()


def ensure_recipe_favorite_column(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(recipes);")
    columns = {row["name"] for row in cur.fetchall()}
    if "is_favorite" not in columns:
        cur.execute("ALTER TABLE recipes ADD COLUMN is_favorite INTEGER NOT NULL DEFAULT 0;")
        conn.commit()


def load_seed_json() -> dict:
    if not SEED_JSON_PATH.exists():
        raise FileNotFoundError(f"Seed file not found: {SEED_JSON_PATH}")
    with SEED_JSON_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def clear_seed_data(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.executescript(
        """
        DELETE FROM recipe_ingredients;
        DELETE FROM recipe_benefits;
        DELETE FROM recipes;
        DELETE FROM ingredients;
        DELETE FROM benefits;
        """
    )
    conn.commit()


def seed_from_json(conn: sqlite3.Connection, data: dict, reset: bool = False) -> None:
    if reset:
        clear_seed_data(conn)

    ingredients = data["ingredients"]
    benefits = data["benefits"]
    recipes = data["recipes"]

    cur = conn.cursor()

    cur.executemany("INSERT INTO ingredients (name) VALUES (?);", [(i,) for i in ingredients])
    cur.executemany(
        "INSERT INTO benefits (name, description) VALUES (?, ?);",
        [(b["name"], b["description"]) for b in benefits],
    )

    conn.commit()

    cur.execute("SELECT id, name FROM ingredients;")
    ingredient_map = {row["name"]: row["id"] for row in cur.fetchall()}
    cur.execute("SELECT id, name FROM benefits;")
    benefit_map = {row["name"]: row["id"] for row in cur.fetchall()}

    for recipe in recipes:
        cur.execute(
            """
            INSERT INTO recipes (name, description, instructions_json, image_url, is_favorite)
            VALUES (?, ?, ?, ?, ?);
            """,
            (
                recipe["name"],
                recipe["description"],
                json.dumps(recipe["instructions"]),
                recipe.get("image_url"),
                1 if recipe.get("is_favorite") else 0,
            ),
        )
        recipe_id = cur.lastrowid

        for ingredient_name, ingredient_data in recipe["ingredients"].items():
            cur.execute(
                """
                INSERT INTO recipe_ingredients
                    (recipe_id, ingredient_id, qty_1, qty_2, unit)
                VALUES (?, ?, ?, ?, ?);
                """,
                (
                    recipe_id,
                    ingredient_map[ingredient_name],
                    ingredient_data["qty_1"],
                    ingredient_data["qty_2"],
                    ingredient_data.get("unit"),
                ),
            )

        for benefit_name, rating in recipe["benefits"].items():
            cur.execute(
                """
                INSERT INTO recipe_benefits (recipe_id, benefit_id, rating)
                VALUES (?, ?, ?);
                """,
                (recipe_id, benefit_map[benefit_name], rating),
            )

    conn.commit()


def fetch_all_ingredients(conn: sqlite3.Connection) -> list[str]:
    cur = conn.cursor()
    cur.execute("SELECT name FROM ingredients ORDER BY name;")
    return [row["name"] for row in cur.fetchall()]


def fetch_recipes(conn: sqlite3.Connection) -> list[Recipe]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, name, description, instructions_json, image_url, is_favorite
        FROM recipes
        ORDER BY name;
        """
    )
    rows = cur.fetchall()
    return [
        Recipe(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            instructions=json.loads(row["instructions_json"]),
            image_url=row["image_url"],
            is_favorite=bool(row["is_favorite"]),
        )
        for row in rows
    ]


def fetch_recipe_ingredients(
    conn: sqlite3.Connection, recipe_id: int, servings: int
) -> list[dict]:
    qty_col = "qty_2" if servings == 2 else "qty_1"
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT i.name AS name, ri.{qty_col} AS qty, ri.unit AS unit
        FROM recipe_ingredients ri
        JOIN ingredients i ON i.id = ri.ingredient_id
        WHERE ri.recipe_id = ?
        ORDER BY i.name;
        """,
        (recipe_id,),
    )
    return [
        {"name": row["name"], "qty": row["qty"], "unit": row["unit"]}
        for row in cur.fetchall()
    ]


def fetch_recipe_benefits(conn: sqlite3.Connection, recipe_id: int) -> list[dict]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT b.name AS name, b.description AS description, rb.rating AS rating
        FROM recipe_benefits rb
        JOIN benefits b ON b.id = rb.benefit_id
        WHERE rb.recipe_id = ?
        ORDER BY b.name;
        """,
        (recipe_id,),
    )
    return [
        {"name": row["name"], "description": row["description"], "rating": row["rating"]}
        for row in cur.fetchall()
    ]


def fetch_all_benefits(conn: sqlite3.Connection) -> list[dict]:
    cur = conn.cursor()
    cur.execute("SELECT name, description FROM benefits ORDER BY name;")
    return [{"name": row["name"], "description": row["description"]} for row in cur.fetchall()]


def fetch_benefit_ratings(conn: sqlite3.Connection) -> dict[int, dict[str, int]]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT rb.recipe_id AS recipe_id, b.name AS benefit_name, rb.rating AS rating
        FROM recipe_benefits rb
        JOIN benefits b ON b.id = rb.benefit_id;
        """
    )
    ratings: dict[int, dict[str, int]] = {}
    for row in cur.fetchall():
        ratings.setdefault(row["recipe_id"], {})[row["benefit_name"]] = row["rating"]
    return ratings


def filter_recipes(
    conn: sqlite3.Connection,
    include_ingredients: Iterable[str],
    exclude_ingredients: Iterable[str],
    have_ingredients: Iterable[str],
) -> list[int]:
    include_set = {name.strip() for name in include_ingredients if name.strip()}
    exclude_set = {name.strip() for name in exclude_ingredients if name.strip()}
    have_set = {name.strip() for name in have_ingredients if name.strip()}

    cur = conn.cursor()
    cur.execute(
        """
        SELECT r.id AS recipe_id, i.name AS ingredient_name
        FROM recipes r
        JOIN recipe_ingredients ri ON r.id = ri.recipe_id
        JOIN ingredients i ON i.id = ri.ingredient_id;
        """
    )

    recipe_ingredient_map: dict[int, set[str]] = {}
    for row in cur.fetchall():
        recipe_ingredient_map.setdefault(row["recipe_id"], set()).add(row["ingredient_name"])

    filtered_ids = []
    for recipe_id, ingredient_names in recipe_ingredient_map.items():
        if include_set and not include_set.issubset(ingredient_names):
            continue
        if exclude_set and exclude_set.intersection(ingredient_names):
            continue
        if have_set and not ingredient_names.issubset(have_set):
            continue
        filtered_ids.append(recipe_id)

    return filtered_ids


def parse_multi_value(name: str) -> list[str]:
    raw_values = request.args.getlist(name)
    if len(raw_values) == 1:
        return [v.strip() for v in raw_values[0].split(",") if v.strip()]
    return [v.strip() for v in raw_values if v.strip()]


@app.route("/")
def index():
    servings = 2 if request.args.get("servings") == "2" else 1
    include = parse_multi_value("include")
    exclude = parse_multi_value("exclude")
    have = parse_multi_value("have")
    prioritize = parse_multi_value("prioritize")
    favorites_only = request.args.get("favorites_only") == "1"

    conn = get_db()
    all_ingredients = fetch_all_ingredients(conn)
    all_benefits = fetch_all_benefits(conn)
    recipes = fetch_recipes(conn)

    if favorites_only:
        recipes = [recipe for recipe in recipes if recipe.is_favorite]
    elif include or exclude or have:
        allowed_ids = set(filter_recipes(conn, include, exclude, have))
        recipes = [recipe for recipe in recipes if recipe.id in allowed_ids]

    if prioritize:
        benefit_ratings = fetch_benefit_ratings(conn)

        def priority_score(recipe: Recipe) -> int:
            ratings = benefit_ratings.get(recipe.id, {})
            return sum(ratings.get(name, 0) for name in prioritize)

        recipes.sort(key=priority_score, reverse=True)

    recipes.sort(key=lambda recipe: recipe.is_favorite, reverse=True)

    recipe_cards = []
    for recipe in recipes:
        recipe_cards.append(
            {
                "recipe": recipe,
                "ingredients": fetch_recipe_ingredients(conn, recipe.id, servings),
                "benefits": fetch_recipe_benefits(conn, recipe.id),
            }
        )

    conn.close()

    return render_template(
        "index.html",
        recipes=recipe_cards,
        servings=servings,
        include=include,
        exclude=exclude,
        have=have,
        prioritize=prioritize,
        favorites_only=favorites_only,
        ingredients=all_ingredients,
        benefits=all_benefits,
    )


@app.route("/recipe/<int:recipe_id>")
def recipe_detail(recipe_id: int):
    servings = 2 if request.args.get("servings") == "2" else 1
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, name, description, instructions_json, image_url, is_favorite
        FROM recipes
        WHERE id = ?;
        """,
        (recipe_id,),
    )
    row = cur.fetchone()
    if row is None:
        conn.close()
        return redirect(url_for("index"))

    recipe = Recipe(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        instructions=json.loads(row["instructions_json"]),
        image_url=row["image_url"],
        is_favorite=bool(row["is_favorite"]),
    )
    ingredients = fetch_recipe_ingredients(conn, recipe_id, servings)
    benefits = fetch_recipe_benefits(conn, recipe_id)
    conn.close()

    return render_template(
        "recipe.html",
        recipe=recipe,
        servings=servings,
        ingredients=ingredients,
        benefits=benefits,
    )


@app.post("/recipe/<int:recipe_id>/favorite")
def toggle_favorite(recipe_id: int):
    conn = get_db()
    ensure_schema(conn)
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE recipes
        SET is_favorite = CASE WHEN is_favorite = 1 THEN 0 ELSE 1 END
        WHERE id = ?;
        """,
        (recipe_id,),
    )
    conn.commit()
    conn.close()
    next_url = request.form.get("next") or url_for("index")
    return redirect(next_url)


@app.cli.command("reset-db")
def reset_db_command():
    """Drops all tables and re-seeds from blendora.json."""
    conn = get_db()
    seed_from_json(conn, load_seed_json(), reset=True)
    conn.close()
    print("Database reset and re-seeded from blendora.json.")


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
