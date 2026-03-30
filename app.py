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


def get_apps_script_url() -> str:
    if not APPS_SCRIPT_URL:
        raise RuntimeError(
            "APPS_SCRIPT_URL is not configured. Add it to your environment before running the app."
        )
    return APPS_SCRIPT_URL


def parse_iso_date(value: str | None) -> str:
    if not value:
        return date.today().isoformat()

    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise ValueError("Expected date in YYYY-MM-DD format.") from exc


def normalize_meal(payload: dict[str, Any]) -> dict[str, Any]:
    meal_type = payload.get("mealType") or payload.get("meal_type") or "Meal"
    description = payload.get("description") or payload.get("mealDescription") or payload.get(
        "meal_description"
    )

    return {
        "id": str(payload.get("id") or payload.get("rowId") or payload.get("row_id") or ""),
        "date": payload.get("date"),
        "mealType": meal_type,
        "description": description or "No description provided",
        "calories": payload.get("calories"),
        "notes": payload.get("notes"),
        "status": (payload.get("status") or "Pending").title(),
    }


def normalize_day_response(payload: dict[str, Any], selected_date: str) -> dict[str, Any]:
    meals = payload.get("meals")
    if meals is None and isinstance(payload.get("data"), list):
        meals = payload["data"]
    if meals is None and isinstance(payload.get("rows"), list):
        meals = payload["rows"]
    if meals is None and isinstance(payload.get("items"), list):
        meals = payload["items"]
    if meals is None:
        meals = []

    return {
        "date": payload.get("date") or selected_date,
        "meals": [normalize_meal(item) for item in meals if isinstance(item, dict)],
        "summary": payload.get("summary")
        or {
            "totalMeals": len(meals),
            "completedMeals": sum(
                1
                for item in meals
                if isinstance(item, dict)
                and (item.get("status") or "").strip().lower() == "completed"
            ),
        },
    }


@lru_cache(maxsize=14)
def fetch_day_from_apps_script(selected_date: str) -> dict[str, Any]:
    response = requests.get(
        get_apps_script_url(),
        params={"date": selected_date},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return normalize_day_response(response.json(), selected_date)


def post_update_to_apps_script(payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(
        get_apps_script_url(),
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    fetch_day_from_apps_script.cache_clear()
    return data if isinstance(data, dict) else {"ok": True}


@app.get("/")
def index() -> str:
    return render_template("index.html")


@app.get("/api/health")
def healthcheck():
    configured = bool(APPS_SCRIPT_URL)
    return jsonify({"ok": True, "appsScriptConfigured": configured})


@app.get("/api/meals")
def get_meals():
    try:
        selected_date = parse_iso_date(request.args.get("date"))
        return jsonify(fetch_day_from_apps_script(selected_date))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 500
    except requests.RequestException as exc:
        return jsonify({"error": f"Could not load meals from Apps Script: {exc}"}), 502


@app.post("/api/meals/update")
def update_meal():
    body = request.get_json(silent=True) or {}

    meal_id = str(body.get("id") or "").strip()
    selected_date = body.get("date")
    status = str(body.get("status") or "").strip().title()

    if not meal_id:
        return jsonify({"error": "Meal id is required."}), 400

    if status not in {"Completed", "Pending", "Skipped"}:
        return jsonify({"error": "Status must be Completed, Pending, or Skipped."}), 400

    try:
        payload = {
            "action": "updateMealStatus",
            "id": meal_id,
            "date": parse_iso_date(selected_date),
            "status": status,
        }
        result = post_update_to_apps_script(payload)
        return jsonify(
            {
                "ok": True,
                "meal": {
                    "id": meal_id,
                    "date": payload["date"],
                    "status": status,
                },
                "appsScriptResponse": result,
            }
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 500
    except requests.RequestException as exc:
        return jsonify({"error": f"Could not update meal in Apps Script: {exc}"}), 502


if __name__ == "__main__":
    app.run(debug=True)
