# Daily Meal Plan Viewer & Tracker

A mobile-friendly Flask web app for viewing and tracking daily meals stored in Google Sheets through a Google Apps Script web API.

## Stack

- Python + Flask backend
- HTML, CSS, and vanilla JavaScript frontend
- Google Apps Script as the data API layer

## Features

- Loads today's meals automatically
- Card-based meal layout with meal type, description, calories, notes, and status
- Instant status toggling with POST updates to Apps Script
- Previous day, next day, today, and date picker navigation
- Responsive interface designed for phone, tablet, and desktop screens

## Expected API Contract

### GET request

The Flask backend calls your Apps Script endpoint like this:

```http
GET https://your-apps-script-url?date=2026-03-30
```

Expected JSON response:

```json
{
  "date": "2026-03-30",
  "meals": [
    {
      "id": "row-1",
      "date": "2026-03-30",
      "mealType": "Breakfast",
      "description": "Greek yogurt, berries, and granola",
      "calories": 420,
      "notes": "Add chia seeds",
      "status": "Pending"
    }
  ],
  "summary": {
    "totalMeals": 4,
    "completedMeals": 1
  }
}
```

Accepted fallback keys:

- `data`, `rows`, or `items` instead of `meals`
- `meal_type` / `mealType`
- `meal_description` / `mealDescription` / `description`
- `rowId` / `row_id` / `id`

### POST request

The Flask backend sends updates like this:

```json
{
  "action": "updateMealStatus",
  "id": "row-1",
  "date": "2026-03-30",
  "status": "Completed"
}
```

Expected Apps Script success response:

```json
{
  "ok": true,
  "updated": true
}
```

## Local setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env`.
4. Set `APPS_SCRIPT_URL` to your deployed Google Apps Script web app URL.
5. Run the app:

```bash
flask --app app run --debug
```

Then open `http://127.0.0.1:5000`.

## Updating the Apps Script URL

Edit your environment configuration and replace:

```env
APPS_SCRIPT_URL=https://script.google.com/macros/s/your-script-id/exec
```

You can use `.env` locally or set the variable in your deployment platform.

## Adjusting the JSON schema

If your Apps Script uses a different payload shape, update these functions in [app.py](/C:/Users/chukw/OneDrive/Career%20and%20Employement/Academcics/Sheffield%20Hallam%20University%20Folder/Documents/New%20project/app.py):

- `normalize_meal`
- `normalize_day_response`
- `post_update_to_apps_script`

These are the only places where the backend maps the Apps Script response into the frontend format.

## Deployment options

### Recommended: Render, Railway, or another small Python host

GitHub Pages cannot run Python. A practical GitHub-based workflow is:

1. Push this repository to GitHub.
2. Connect the repo to a Python-friendly host such as Render or Railway.
3. Set `APPS_SCRIPT_URL` as an environment variable in that host.
4. Deploy the Flask app.

This repository already includes [render.yaml](/C:/Users/chukw/OneDrive/Career%20and%20Employement/Academcics/Sheffield%20Hallam%20University%20Folder/Documents/New%20project/render.yaml) for a simple Render deployment.

If you want the frontend on GitHub Pages later, you can split the frontend into static files and keep only the `/api/*` proxy on a hosted Python service.

### Example Procfile-style command

Use a start command similar to:

```bash
gunicorn app:app
```

### Optional GitHub Actions

You can add a workflow that runs linting or tests on push, then let your host redeploy from GitHub automatically.

## File overview

- [app.py](/C:/Users/chukw/OneDrive/Career%20and%20Employement/Academcics/Sheffield%20Hallam%20University%20Folder/Documents/New%20project/app.py) - Flask backend and Apps Script proxy
- [templates/index.html](/C:/Users/chukw/OneDrive/Career%20and%20Employement/Academcics/Sheffield%20Hallam%20University%20Folder/Documents/New%20project/templates/index.html) - main page
- [static/styles.css](/C:/Users/chukw/OneDrive/Career%20and%20Employement/Academcics/Sheffield%20Hallam%20University%20Folder/Documents/New%20project/static/styles.css) - responsive styling
- [static/app.js](/C:/Users/chukw/OneDrive/Career%20and%20Employement/Academcics/Sheffield%20Hallam%20University%20Folder/Documents/New%20project/static/app.js) - frontend logic
