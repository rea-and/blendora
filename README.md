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
- The database seeds itself on first run with 5 filler recipes.
