"""Local web app: search Yalkut Yosef, and (with an API key) ask Claude.
Run:  .venv/bin/python app.py   then open http://localhost:5000"""
from flask import Flask, jsonify, request, send_from_directory
from bot.search import Index, DATA
from bot import answer as claude

if not DATA.exists():   # first run: download and parse the book
    import subprocess, sys
    subprocess.run([sys.executable, "scripts/build_data.py"], check=True)

app = Flask(__name__, static_folder="static")
index = Index()

@app.get("/")
def home():
    return send_from_directory("static", "index.html")

@app.get("/api/status")
def status():
    return jsonify(claude=claude.available(), sections=index.sections(), count=len(index.docs))

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
    terms = claude.search_terms(q)
    passages = index.search(f"{q} {terms}", k=12, section=body.get("section") or None)
    result = claude.answer(q, passages)
    return jsonify(**result, terms=terms, passages=passages)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
