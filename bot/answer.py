"""Answer a question with Claude, using only se'ifim retrieved from the index.
Needs ANTHROPIC_API_KEY in the environment."""
import os, pathlib, re
import anthropic

# Optional: put the key in a file called api_key.txt in the project folder
# (handy when you can't set environment variables). Never commit that file.
# Windows hides extensions, so also accept "api_key", "api_key.txt.txt", etc.
_ROOT = pathlib.Path(__file__).resolve().parent.parent
KEY_PROBLEM = ""          # explains to the user why no key was found
def _read(f: pathlib.Path) -> str:
    raw = f.read_bytes()
    for enc in ("utf-8-sig", "utf-16"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return raw.decode("latin-1")
if os.environ.get("ANTHROPIC_API_KEY"):
    pass
else:
    files = [f for f in sorted(_ROOT.glob("api_key*")) if f.is_file()]
    for _f in files:
        _m = re.search(r"sk-ant-[A-Za-z0-9_\-]+", _read(_f))
        if _m:
            os.environ["ANTHROPIC_API_KEY"] = _m.group(0)
            break
    else:
        if not files:
            KEY_PROBLEM = (f"No file named api_key found in {_ROOT}. Other files there: "
                           + ", ".join(p.name for p in sorted(_ROOT.iterdir()) if p.is_file()))
        else:
            KEY_PROBLEM = (f"Found {', '.join(f.name for f in files)} but it has no key in it "
                           "(a key starts with sk-ant-). Paste the key, save with Ctrl+S, and restart.")

def available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))

_client = None
def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client

def _text(resp) -> str:
    return "".join(b.text for b in resp.content if b.type == "text")

def search_terms(question: str) -> str:
    """Turn a question in any language into Hebrew keywords for the search index."""
    resp = client().messages.create(
        model=MODEL, max_tokens=2000,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": QUERY_PROMPT.format(q=question)}],
    )
    return _text(resp).strip()

def answer(question: str, passages: list[dict], history: list[dict] | None = None) -> dict:
    docs = [{
        "type": "document",
        "source": {"type": "text", "media_type": "text/plain", "data": p["text"]},
        "title": f"{p['section']} | {p['siman']} | סעיף {p['seif']}",
        "citations": {"enabled": True},
    } for p in passages]
    messages = list(history or []) + [
        {"role": "user", "content": [*docs, {"type": "text", "text": question}]}]
    resp = client().beta.messages.create(
        model=MODEL, max_tokens=16000,
        output_config={"effort": "high"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",     # if a request is declined, retry on a fallback model
        system=SYSTEM,
        messages=messages,
    )
    if resp.stop_reason == "refusal":
        return {"text": "Sorry, I can't answer that one. Please ask a rav.", "citations": []}
    parts, cites = [], []
    for b in resp.content:
        if b.type != "text":
            continue
        parts.append(b.text)
        for c in (b.citations or []):
            cites.append({"title": c.document_title, "quote": c.cited_text})
            parts.append(f" [{len(cites)}]")
    return {"text": "".join(parts), "citations": cites}
