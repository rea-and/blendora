# Blendora

Blendora is a tiny smoothie recipe webapp with ingredient filters, adjustable servings, and benefit rankings.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000` in your browser.

## Notes

- Data is stored in `data/blendora.db` using SQLite.
- Seed data lives in `data/blendora.json` and loads on first run.
- To reload the database after editing the JSON:

```bash
flask reset-db
```

## Production Hosting

When hosting Blendora behind a reverse proxy (like Apache or Nginx) under a subpath (e.g., `/blendora`), the application uses `ProxyFix` middleware to handle URL generation correctly.

### Required Header:
Ensure your proxy sends the `X-Forwarded-Prefix` header:
- **Apache**: `RequestHeader set X-Forwarded-Prefix "/blendora"`
- **Protocol**: If using SSL, also send `RequestHeader set X-Forwarded-Proto "https"` to avoid redirect loops.
