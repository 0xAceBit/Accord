from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any

from flask import Flask, g, jsonify, request, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = Path(os.environ.get("ACCORD_DATABASE", BASE_DIR / "accord.db"))

app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path="")
app.secret_key = os.environ.get("ACCORD_SECRET_KEY", "dev-only-change-me")
REQUIRE_AUTH_FOR_WRITES = os.environ.get("ACCORD_REQUIRE_AUTH", "0") == "1"


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception: BaseException | None = None) -> None:
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def parse_skills(value: Any) -> list[str]:
    if isinstance(value, list):
        values = value
    elif isinstance(value, str):
        values = value.split(",")
    else:
        values = []

    result: list[str] = []
    for item in values:
        skill = str(item).strip().lower()
        if skill and skill not in result:
            result.append(skill)
    return result


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_row(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["skills"] = json.loads(item.pop("skills_json"))
    return item


def init_db() -> None:
    with get_db() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER REFERENCES users(id),
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                skills_json TEXT NOT NULL DEFAULT '[]',
                pay INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER REFERENCES users(id),
                name TEXT NOT NULL,
                resume TEXT NOT NULL DEFAULT '',
                skills_json TEXT NOT NULL DEFAULT '[]',
                rate INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS disputes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role_id INTEGER NOT NULL,
                profile_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'resolved',
                verdict INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(role_id, profile_id),
                FOREIGN KEY(role_id) REFERENCES roles(id),
                FOREIGN KEY(profile_id) REFERENCES profiles(id)
            );
            """
        )

        add_column_if_missing(connection, "roles", "owner_id", "INTEGER REFERENCES users(id)")
        add_column_if_missing(connection, "profiles", "owner_id", "INTEGER REFERENCES users(id)")
        add_column_if_missing(connection, "disputes", "status", "TEXT NOT NULL DEFAULT 'resolved'")

        role_count = connection.execute("SELECT COUNT(*) FROM roles").fetchone()[0]
        profile_count = connection.execute("SELECT COUNT(*) FROM profiles").fetchone()[0]
        if role_count == 0:
            connection.execute(
                "INSERT INTO roles (owner_id, title, description, skills_json, pay, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    None,
                    "Solidity Engineer",
                    "Own the contracts for a small DeFi protocol. Ship, test, and audit-prep.",
                    json.dumps(["solidity", "foundry", "evm"]),
                    4200,
                    now(),
                ),
            )
        if profile_count == 0:
            connection.execute(
                "INSERT INTO profiles (owner_id, name, resume, skills_json, rate, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    None,
                    "M. Okoye",
                    "https://example.com/resume/okoye",
                    json.dumps(["solidity", "rust", "evm"]),
                    4800,
                    now(),
                ),
            )


def add_column_if_missing(connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def required_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key, "")
    return str(value).strip()


def parse_money(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key, 0)
    try:
        amount = int(float(value))
    except (TypeError, ValueError):
        raise ValueError(f"{key} must be a number") from None
    if amount < 0:
        raise ValueError(f"{key} cannot be negative")
    return amount


def bad_request(message: str):
    return jsonify({"error": message}), 400


def user_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {"id": row["id"], "email": row["email"], "name": row["name"]}


def current_user(connection: sqlite3.Connection) -> sqlite3.Row | None:
    user_id = session.get("user_id")
    if not user_id:
        return None
    return connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user(get_db()):
            return jsonify({"error": "you need to log in first"}), 401
        return view(*args, **kwargs)
    return wrapped


def write_access_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if REQUIRE_AUTH_FOR_WRITES and not current_user(get_db()):
            return jsonify({"error": "you need to log in first"}), 401
        return view(*args, **kwargs)
    return wrapped


@app.get("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/api/register")
def register():
    payload = request.get_json(silent=True) or {}
    email = required_text(payload, "email").lower()
    name = required_text(payload, "name")
    password = str(payload.get("password") or "")
    if not email or not name or not password:
        return bad_request("name, email, and password are all required")
    if len(password) < 8:
        return bad_request("password must be at least 8 characters")

    connection = get_db()
    if connection.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
        return jsonify({"error": "an account with that email already exists"}), 409
    cursor = connection.execute(
        "INSERT INTO users (email, name, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (email, name, generate_password_hash(password), now()),
    )
    connection.commit()
    session.clear()
    session["user_id"] = cursor.lastrowid
    return jsonify(user_to_dict(connection.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone())), 201


@app.post("/api/login")
def login():
    payload = request.get_json(silent=True) or {}
    email = required_text(payload, "email").lower()
    password = str(payload.get("password") or "")
    user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "incorrect email or password"}), 401
    session.clear()
    session["user_id"] = user["id"]
    return jsonify(user_to_dict(user))


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.get("/api/me")
def me():
    return jsonify(user_to_dict(current_user(get_db())))


@app.get("/api/roles")
def list_roles():
    with get_db() as connection:
        rows = connection.execute(
            "SELECT id, title, description, skills_json, pay FROM roles ORDER BY id DESC"
        ).fetchall()
    return jsonify([json_row(row) for row in rows])


@app.post("/api/roles")
@write_access_required
def create_role():
    payload = request.get_json(silent=True) or {}
    title = required_text(payload, "title")
    if not title:
        return bad_request("title is required")
    try:
        pay = parse_money(payload, "pay")
    except ValueError as error:
        return bad_request(str(error))

    with get_db() as connection:
        user = current_user(connection)
        cursor = connection.execute(
            "INSERT INTO roles (owner_id, title, description, skills_json, pay, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                user["id"] if user else None,
                title,
                required_text(payload, "description"),
                json.dumps(parse_skills(payload.get("skills"))),
                pay,
                now(),
            ),
        )
        role_id = cursor.lastrowid
    return jsonify({"id": role_id}), 201


@app.get("/api/profiles")
def list_profiles():
    with get_db() as connection:
        rows = connection.execute(
            "SELECT id, name, resume, skills_json, rate FROM profiles ORDER BY id DESC"
        ).fetchall()
    return jsonify([json_row(row) for row in rows])


@app.post("/api/profiles")
@write_access_required
def create_profile():
    payload = request.get_json(silent=True) or {}
    name = required_text(payload, "name")
    if not name:
        return bad_request("name is required")
    try:
        rate = parse_money(payload, "rate")
    except ValueError as error:
        return bad_request(str(error))

    with get_db() as connection:
        user = current_user(connection)
        cursor = connection.execute(
            "INSERT INTO profiles (owner_id, name, resume, skills_json, rate, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                user["id"] if user else None,
                name,
                required_text(payload, "resume"),
                json.dumps(parse_skills(payload.get("skills"))),
                rate,
                now(),
            ),
        )
        profile_id = cursor.lastrowid
    return jsonify({"id": profile_id}), 201


@app.get("/api/matches")
def list_matches():
    with get_db() as connection:
        roles = [json_row(row) for row in connection.execute(
            "SELECT id, title, description, skills_json, pay FROM roles"
        ).fetchall()]
        profiles = [json_row(row) for row in connection.execute(
            "SELECT id, name, resume, skills_json, rate FROM profiles"
        ).fetchall()]
        disputes = {
            (row["role_id"], row["profile_id"]): dict(row)
            for row in connection.execute(
                "SELECT id, role_id, profile_id, verdict FROM disputes"
            ).fetchall()
        }

    matches = []
    for role in roles:
        role_skills = set(role["skills"])
        for profile in profiles:
            shared = sorted(role_skills.intersection(profile["skills"]))
            union = role_skills.union(profile["skills"])
            if not shared:
                continue
            dispute = disputes.get((role["id"], profile["id"]))
            matches.append(
                {
                    "role": role,
                    "profile": profile,
                    "overlap_pct": round(len(shared) / len(union) * 100) if union else 0,
                    "shared_skills": shared,
                    "terms_differ": bool(role["pay"] and profile["rate"] and role["pay"] != profile["rate"]),
                    "dispute": dispute,
                }
            )
    matches.sort(key=lambda match: match["overlap_pct"], reverse=True)
    return jsonify(matches)


@app.post("/api/disputes")
@write_access_required
def create_dispute():
    payload = request.get_json(silent=True) or {}
    try:
        role_id = int(payload["role_id"])
        profile_id = int(payload["profile_id"])
    except (KeyError, TypeError, ValueError):
        return bad_request("role_id and profile_id are required")

    with get_db() as connection:
        role = connection.execute("SELECT pay FROM roles WHERE id = ?", (role_id,)).fetchone()
        profile = connection.execute("SELECT rate FROM profiles WHERE id = ?", (profile_id,)).fetchone()
        if role is None or profile is None:
            return jsonify({"error": "role or profile not found"}), 404
        verdict = round((role["pay"] + profile["rate"]) / 2)
        connection.execute(
            "INSERT INTO disputes (role_id, profile_id, status, verdict, created_at) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(role_id, profile_id) DO UPDATE SET status = excluded.status, verdict = excluded.verdict",
            (role_id, profile_id, "resolved", verdict, now()),
        )
    return jsonify({"role_id": role_id, "profile_id": profile_id, "verdict": verdict}), 201


with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=True)
