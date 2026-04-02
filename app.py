import os
from datetime import date, datetime
from functools import lru_cache
from typing import Any

import requests
from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv

load_dotenv()

APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL", "").strip()
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "15"))

app = Flask(__name__)


# ========================
# CONFIG HELPERS
# ========================

def get_apps_script_url() -> str:
    if not APPS_SCRIPT_URL:
        raise RuntimeError(
            "APPS_SCRIPT_URL is not configured. Add it to your environment."
        )
    return APPS_SCRIPT_URL


def parse_iso_date(value: str | None) -> str:
    if not value:
        return date.today().isoformat()

    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise ValueError("Expected date in YYYY-MM-DD format.") from exc


# ========================
# NORMALISERS (MEALS)
# ========================

def normalize_meal(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(payload.get("id") or ""),
        "date": payload.get("date"),
        "mealType": payload.get("mealType") or "Meal",
        "description": payload.get("description") or "No description provided",
        "calories": payload.get("calories"),
        "notes": payload.get("notes"),
        "status": (payload.get("status") or "Pending").title(),
    }


def normalize_day_response(payload: dict[str, Any], selected_date: str) -> dict[str, Any]:
    meals = payload.get("meals") or []

    return {
        "date": payload.get("date") or selected_date,
        "meals": [normalize_meal(item) for item in meals],
        "summary": payload.get("summary") or {
            "totalMeals": len(meals),
            "completedMeals": sum(
                1 for m in meals if (m.get("status") or "").lower() == "completed"
            ),
        },
    }


# ========================
# NORMALISERS (GROCERIES)
# ========================

def normalize_grocery(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "category": item.get("category"),
        "name": item.get("name"),
        "toBuy": item.get("toBuy"),
        "quantity": item.get("quantity"),
        "price": item.get("price"),
        "total": item.get("total"),
    }


# ========================
# APPS SCRIPT CALLS
# ========================

@lru_cache(maxsize=14)
def fetch_day_from_apps_script(selected_date: str) -> dict[str, Any]:
    response = requests.get(
        get_apps_script_url(),
        params={"date": selected_date},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return normalize_day_response(response.json(), selected_date)


def fetch_groceries_from_apps_script() -> dict[str, Any]:
    response = requests.get(
        get_apps_script_url(),
        params={"action": "groceries"},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()

    groceries = data.get("groceries", [])
    return {
        "groceries": [normalize_grocery(item) for item in groceries]
    }


def post_update_to_apps_script(payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(
        get_apps_script_url(),
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    fetch_day_from_apps_script.cache_clear()
    return response.json()


# ========================
# ROUTES
# ========================

@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/health")
def healthcheck():
    return jsonify({
        "ok": True,
        "appsScriptConfigured": bool(APPS_SCRIPT_URL)
    })


# ========================
# MEALS ROUTES
# ========================

@app.get("/api/meals")
def get_meals():
    try:
        selected_date = parse_iso_date(request.args.get("date"))
        return jsonify(fetch_day_from_apps_script(selected_date))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.post("/api/meals/update")
def update_meal():
    body = request.get_json(silent=True) or {}

    meal_id = str(body.get("id") or "").strip()
    status = str(body.get("status") or "").title()
    selected_date = body.get("date")

    if not meal_id:
        return jsonify({"error": "Meal id required"}), 400

    if status not in {"Completed", "Pending", "Skipped"}:
        return jsonify({"error": "Invalid status"}), 400

    try:
        payload = {
            "action": "updateMealStatus",
            "id": meal_id,
            "date": parse_iso_date(selected_date),
            "status": status,
        }

        result = post_update_to_apps_script(payload)

        return jsonify({
            "ok": True,
            "meal": {
                "id": meal_id,
                "status": status
            },
            "appsScriptResponse": result
        })

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# ========================
# GROCERIES ROUTES
# ========================

@app.get("/api/groceries")
def get_groceries():
    try:
        return jsonify(fetch_groceries_from_apps_script())
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.post("/api/groceries/update")
def update_grocery():
    body = request.get_json() or {}

    try:
        payload = {
            "action": "updateGrocery",
            "id": body.get("id"),
            "toBuy": body.get("toBuy"),
            "quantity": body.get("quantity"),
            "price": body.get("price"),
        }

        result = post_update_to_apps_script(payload)
        return jsonify({"ok": True, "appsScriptResponse": result})

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.post("/api/groceries/add")
def add_grocery():
    body = request.get_json() or {}

    try:
        payload = {
            "action": "addGrocery",
            "category": body.get("category"),
            "name": body.get("name"),
            "toBuy": body.get("toBuy"),
            "quantity": body.get("quantity"),
            "price": body.get("price"),
        }

        result = post_update_to_apps_script(payload)
        return jsonify({"ok": True, "appsScriptResponse": result})

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# ========================
# RUN
# ========================

if __name__ == "__main__":
    app.run(debug=True)
