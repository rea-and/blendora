from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from flask import Flask, redirect, render_template, request, url_for


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "blendora.db"

app = Flask(__name__)


@dataclass
class Recipe:
    id: int
    name: str
    description: str
    instructions: list[str]


def get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_db()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            instructions_json TEXT NOT NULL
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

    cur.execute("SELECT COUNT(*) AS count FROM recipes;")
    count = cur.fetchone()["count"]
    if count == 0:
        seed_data(conn)

    conn.close()


def seed_data(conn: sqlite3.Connection) -> None:
    ingredients = [
        "Banana",
        "Strawberry",
        "Blueberry",
        "Spinach",
        "Kale",
        "Almond Milk",
        "Greek Yogurt",
        "Honey",
        "Chia Seeds",
        "Mango",
        "Pineapple",
        "Oats",
        "Cocoa Powder",
        "Avocado",
        "Coconut Water",
    ]

    benefits = [
        ("Immunity", "Supports immune system health and recovery."),
        ("Strength", "Aids muscle support and daily strength."),
        ("Anti-virality", "Packed with antioxidants to support wellness."),
        ("Energy", "Helps keep energy levels steady through the day."),
    ]

    recipes = [
        {
            "name": "Sunrise Mango Boost",
            "description": "Tropical and bright with a creamy finish.",
            "instructions": [
                "Add almond milk to the blender.",
                "Add mango, banana, and honey.",
                "Blend until smooth and creamy.",
                "Top with chia seeds before serving.",
            ],
            "ingredients": {
                "Mango": ("1 cup", "2 cups", None),
                "Banana": ("1/2", "1", None),
                "Almond Milk": ("3/4 cup", "1 1/2 cups", None),
                "Honey": ("1 tsp", "2 tsp", None),
                "Chia Seeds": ("1 tsp", "2 tsp", None),
            },
            "benefits": {"Immunity": 4, "Energy": 5, "Strength": 3, "Anti-virality": 4},
        },
        {
            "name": "Berry Shield",
            "description": "A berry-forward blend for a crisp, cool taste.",
            "instructions": [
                "Add almond milk and yogurt to the blender.",
                "Add strawberries and blueberries.",
                "Blend until velvety.",
                "Pour and enjoy immediately.",
            ],
            "ingredients": {
                "Strawberry": ("1 cup", "2 cups", None),
                "Blueberry": ("1/2 cup", "1 cup", None),
                "Greek Yogurt": ("1/2 cup", "1 cup", None),
                "Almond Milk": ("1/2 cup", "1 cup", None),
            },
            "benefits": {"Immunity": 5, "Energy": 4, "Strength": 2, "Anti-virality": 5},
        },
        {
            "name": "Green Strength",
            "description": "Leafy greens balanced with a touch of honey.",
            "instructions": [
                "Add almond milk and spinach.",
                "Add kale, banana, and honey.",
                "Blend until bright green and smooth.",
                "Serve chilled.",
            ],
            "ingredients": {
                "Spinach": ("1 cup", "2 cups", None),
                "Kale": ("1/2 cup", "1 cup", None),
                "Banana": ("1/2", "1", None),
                "Honey": ("1 tsp", "2 tsp", None),
                "Almond Milk": ("3/4 cup", "1 1/2 cups", None),
            },
            "benefits": {"Immunity": 4, "Energy": 3, "Strength": 5, "Anti-virality": 4},
        },
        {
            "name": "Protein Orchard",
            "description": "Creamy protein-packed smoothie with orchard fruit.",
            "instructions": [
                "Add almond milk and Greek yogurt.",
                "Add mango, banana, and chia seeds.",
                "Blend until thick and smooth.",
                "Let sit 1 minute for chia to hydrate.",
            ],
            "ingredients": {
                "Greek Yogurt": ("3/4 cup", "1 1/2 cups", None),
                "Mango": ("1/2 cup", "1 cup", None),
                "Banana": ("1/2", "1", None),
                "Chia Seeds": ("1 tsp", "2 tsp", None),
                "Almond Milk": ("1/2 cup", "1 cup", None),
            },
            "benefits": {"Immunity": 3, "Energy": 4, "Strength": 5, "Anti-virality": 3},
        },
        {
            "name": "Garden Berry Glow",
            "description": "Refreshing greens with a berry sparkle.",
            "instructions": [
                "Add almond milk to the blender.",
                "Add spinach, strawberries, and blueberries.",
                "Blend until smooth and frothy.",
                "Finish with a drizzle of honey.",
            ],
            "ingredients": {
                "Spinach": ("1/2 cup", "1 cup", None),
                "Strawberry": ("3/4 cup", "1 1/2 cups", None),
                "Blueberry": ("1/3 cup", "2/3 cup", None),
                "Honey": ("1 tsp", "2 tsp", None),
                "Almond Milk": ("3/4 cup", "1 1/2 cups", None),
            },
            "benefits": {"Immunity": 5, "Energy": 4, "Strength": 3, "Anti-virality": 5},
        },
        {
            "name": "Tropical Green Wave",
            "description": "Pineapple freshness with leafy greens and coconut water.",
            "instructions": [
                "Add coconut water to the blender.",
                "Add pineapple, spinach, and kale.",
                "Blend until smooth and bright.",
                "Taste and add a touch of honey if desired.",
            ],
            "ingredients": {
                "Pineapple": ("3/4 cup", "1 1/2 cups", None),
                "Spinach": ("1/2 cup", "1 cup", None),
                "Kale": ("1/2 cup", "1 cup", None),
                "Coconut Water": ("1 cup", "2 cups", None),
                "Honey": ("1 tsp", "2 tsp", None),
            },
            "benefits": {"Immunity": 4, "Energy": 5, "Strength": 3, "Anti-virality": 4},
        },
        {
            "name": "Cocoa Oat Lift",
            "description": "Creamy cocoa oats with a gentle sweetness.",
            "instructions": [
                "Add almond milk and oats to the blender.",
                "Add banana, Greek yogurt, and cocoa powder.",
                "Blend until thick and silky.",
                "Serve immediately.",
            ],
            "ingredients": {
                "Oats": ("1/3 cup", "2/3 cup", None),
                "Almond Milk": ("1 cup", "2 cups", None),
                "Banana": ("1/2", "1", None),
                "Greek Yogurt": ("1/3 cup", "2/3 cup", None),
                "Cocoa Powder": ("1 tsp", "2 tsp", None),
            },
            "benefits": {"Immunity": 3, "Energy": 4, "Strength": 4, "Anti-virality": 3},
        },
        {
            "name": "Avocado Berry Silk",
            "description": "Velvety avocado balanced with bright berries.",
            "instructions": [
                "Add almond milk and avocado.",
                "Add strawberries, blueberries, and honey.",
                "Blend until creamy and smooth.",
                "Pour into chilled glasses.",
            ],
            "ingredients": {
                "Avocado": ("1/2", "1", None),
                "Strawberry": ("1/2 cup", "1 cup", None),
                "Blueberry": ("1/3 cup", "2/3 cup", None),
                "Almond Milk": ("3/4 cup", "1 1/2 cups", None),
                "Honey": ("1 tsp", "2 tsp", None),
            },
            "benefits": {"Immunity": 4, "Energy": 3, "Strength": 4, "Anti-virality": 4},
        },
        {
            "name": "Pineapple Protein Splash",
            "description": "Protein-rich tropical blend with yogurt.",
            "instructions": [
                "Add almond milk and Greek yogurt to the blender.",
                "Add pineapple and mango.",
                "Blend until smooth and creamy.",
                "Sprinkle chia seeds on top.",
            ],
            "ingredients": {
                "Pineapple": ("1/2 cup", "1 cup", None),
                "Mango": ("1/2 cup", "1 cup", None),
                "Greek Yogurt": ("1/2 cup", "1 cup", None),
                "Almond Milk": ("1/2 cup", "1 cup", None),
                "Chia Seeds": ("1 tsp", "2 tsp", None),
            },
            "benefits": {"Immunity": 4, "Energy": 4, "Strength": 5, "Anti-virality": 3},
        },
        {
            "name": "Coconut Mango Recharge",
            "description": "Hydrating coconut water with mango and spinach.",
            "instructions": [
                "Add coconut water to the blender.",
                "Add mango, banana, and spinach.",
                "Blend until smooth and vibrant.",
                "Serve over ice if desired.",
            ],
            "ingredients": {
                "Coconut Water": ("1 cup", "2 cups", None),
                "Mango": ("1/2 cup", "1 cup", None),
                "Banana": ("1/2", "1", None),
                "Spinach": ("1/2 cup", "1 cup", None),
            },
            "benefits": {"Immunity": 4, "Energy": 5, "Strength": 3, "Anti-virality": 4},
        },
    ]

    cur = conn.cursor()

    cur.executemany("INSERT INTO ingredients (name) VALUES (?);", [(i,) for i in ingredients])
    cur.executemany(
        "INSERT INTO benefits (name, description) VALUES (?, ?);",
        benefits,
    )

    conn.commit()

    cur.execute("SELECT id, name FROM ingredients;")
    ingredient_map = {row["name"]: row["id"] for row in cur.fetchall()}
    cur.execute("SELECT id, name FROM benefits;")
    benefit_map = {row["name"]: row["id"] for row in cur.fetchall()}

    for recipe in recipes:
        cur.execute(
            "INSERT INTO recipes (name, description, instructions_json) VALUES (?, ?, ?);",
            (recipe["name"], recipe["description"], json.dumps(recipe["instructions"])),
        )
        recipe_id = cur.lastrowid

        for ingredient_name, (qty_1, qty_2, unit) in recipe["ingredients"].items():
            cur.execute(
                """
                INSERT INTO recipe_ingredients
                    (recipe_id, ingredient_id, qty_1, qty_2, unit)
                VALUES (?, ?, ?, ?, ?);
                """,
                (recipe_id, ingredient_map[ingredient_name], qty_1, qty_2, unit),
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
    cur.execute("SELECT id, name, description, instructions_json FROM recipes ORDER BY name;")
    rows = cur.fetchall()
    return [
        Recipe(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            instructions=json.loads(row["instructions_json"]),
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

    conn = get_db()
    all_ingredients = fetch_all_ingredients(conn)
    recipes = fetch_recipes(conn)

    if include or exclude or have:
        allowed_ids = set(filter_recipes(conn, include, exclude, have))
        recipes = [recipe for recipe in recipes if recipe.id in allowed_ids]

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
        ingredients=all_ingredients,
    )


@app.route("/recipe/<int:recipe_id>")
def recipe_detail(recipe_id: int):
    servings = 2 if request.args.get("servings") == "2" else 1
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, description, instructions_json FROM recipes WHERE id = ?;",
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


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
