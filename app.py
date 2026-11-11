"""Local web app: search Yalkut Yosef, and (with an API key) ask Claude.
Run:  .venv/bin/python app.py   then open http://localhost:5000"""
import pathlib, re
from flask import Flask, abort, jsonify, request, send_file, send_from_directory
from bot.search import Index, DATA
from bot import answer as claude
from bot.sections_en import SECTIONS_EN

if not DATA.exists():   # first run: download and parse the book
    import subprocess, sys
    subprocess.run([sys.executable, "scripts/build_data.py"], check=True)

app = Flask(__name__, static_folder="static")
index = Index()

@app.after_request
def no_cache(resp):
    # always load the newest page after an update
    resp.headers["Cache-Control"] = "no-store"
    return resp

@app.get("/")
def home():
    return send_from_directory("static", "index.html")

ROOT = pathlib.Path(__file__).resolve().parent

def photo_file():
    """A picture the user saved in the project folder as rabbi.jpg / rabbi.png / etc."""
    for f in sorted(ROOT.iterdir()):
        if f.is_file() and re.match(r"(rabbi|ovadia|photo)[^/]*\.(jpe?g|jfif|png|webp|gif|avif)$", f.name, re.I):
            return f
    return None

@app.get("/photo")
def photo():
    f = photo_file()
    if not f:
        abort(404)
    return send_file(f, mimetype="image/jpeg" if f.suffix.lower() == ".jfif" else None)

@app.get("/api/status")
def status():
    return jsonify(claude=claude.available(), key_problem=claude.KEY_PROBLEM, has_photo=photo_file() is not None,
                   sections=[{"he": s, "en": SECTIONS_EN.get(s, s)} for s in index.sections()], count=len(index.docs))

@app.get("/api/search")
def search():
    q = request.args.get("q", "").strip()
    sec = request.args.get("section") or None
    return jsonify(results=index.search(q, k=int(request.args.get("k", 15)), section=sec) if q else [])

@app.post("/api/ask")
def ask():
    if not claude.available():
        return jsonify(error="No ANTHROPIC_API_KEY set - showing search results only."), 400
    body = request.get_json(force=True)
    q = body.get("question", "").strip()
    history = body.get("history") or []
    try:
        terms = claude.search_terms(q, history)
        passages = index.search(f"{q} {terms}", k=12, section=body.get("section") or None)
        result = claude.answer(q, passages, history)
    except claude.anthropic.AuthenticationError:
        return jsonify(error="The API key was rejected. Check that you copied the whole key (it starts with sk-ant-)."), 400
    except claude.anthropic.PermissionDeniedError as e:
        return jsonify(error=f"The key is not allowed to do this: {e.message}"), 400
    except claude.anthropic.RateLimitError:
        return jsonify(error="Too many requests right now. Wait a minute and try again."), 429
    except claude.anthropic.APIStatusError as e:
        msg = e.message
        if "credit" in msg.lower() or "billing" in msg.lower():
            msg = "Your Anthropic account has no credits. Add credits under Billing at platform.claude.com. (" + msg + ")"
        return jsonify(error=msg), 400
    except claude.anthropic.APIConnectionError:
        return jsonify(error="Could not reach Anthropic. Check your internet connection (a school/work network may block it)."), 502
    except Exception as e:   # anything unexpected: show it instead of hanging
        app.logger.exception("ask failed")
        return jsonify(error=f"Something went wrong: {e}"), 500
    return jsonify(**result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
