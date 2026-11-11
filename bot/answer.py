"""Answer a question with Claude, using only se'ifim retrieved from the index.
Needs an API key (environment variable or api_key file)."""
import json, os, pathlib, re
import anthropic
from bot.sections_en import SECTIONS_EN

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
    files = [f for f in sorted(_ROOT.iterdir())
             if f.is_file() and re.match(r"api[ _-]?key", f.name, re.I)]
    for _f in files:
        _m = re.search(r"sk-ant-[A-Za-z0-9_\-]+", _read(_f))
        if _m:
            os.environ["ANTHROPIC_API_KEY"] = _m.group(0)
            break
    else:
        if not files:
            KEY_PROBLEM = (f"No file named api_key (or api-key) found in {_ROOT}. Other files there: "
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

MODEL = "claude-opus-5-5"
MAX_QUOTES = 3

SYSTEM = """You answer halakha questions using ONLY the passages provided from Kitzur Shulchan \
Aruch Yalkut Yosef (Rav Yitzhak Yosef, following the rulings of Hacham Ovadia Yosef zt"l).

How to answer:
- Base everything on the passages. Never add rulings from memory or from other poskim.
- "answer": the bottom line in plain English, 1-3 short sentences. No preamble, no repeating \
the question. Keep the conditions that matter (lechatchila / bedi'eved, Sephardim vs. Ashkenazim, \
sha'at hadechak). Hebrew terms are fine with a brief gloss, e.g. "muktzeh (set aside)".
- "quotes": 1-3 quotes that support the answer. For each, "hebrew" is copied EXACTLY, word for \
word, from one passage (a sentence or two, not the whole passage, and not the bracketed sources), \
and "english" is a faithful English translation of exactly that Hebrew.
- If the passages don't answer the question, set "found" to false, say so in "answer" in one \
sentence, and give no quotes. Don't guess.
- For case-specific or weighty questions (niddah, kashrut of a specific item, medical questions \
on Shabbat, aguna, monetary disputes) add one short sentence: "Ask a rav about your own case." \
If life may be in danger, say to act to save life immediately."""

SCHEMA = {
    "type": "object",
    "properties": {
        "found": {"type": "boolean"},
        "answer": {"type": "string"},
        "quotes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "passage": {"type": "integer", "description": "number of the passage quoted"},
                    "hebrew": {"type": "string"},
                    "english": {"type": "string"},
                },
                "required": ["passage", "hebrew", "english"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["found", "answer", "quotes"],
    "additionalProperties": False,
}

QUERY_PROMPT = """Rewrite the user's latest halakha question as Hebrew search keywords that would \
appear in the text of Kitzur Shulchan Aruch Yalkut Yosef (rabbinic Hebrew, e.g. בישול אחר בישול, \
ברכה אחרונה, מוקצה). If it is a follow-up, use the earlier conversation to fill in the topic. \
Give 4-12 words, space-separated, nothing else.

{history}Latest question: {q}"""


def _text(resp) -> str:
    return "".join(b.text for b in resp.content if b.type == "text")


def _history_text(history: list[dict]) -> str:
    if not history:
        return ""
    lines = [f"{'User' if m['role'] == 'user' else 'Bot'}: {m['content']}" for m in history[-6:]]
    return "Earlier conversation:\n" + "\n".join(lines) + "\n\n"


def search_terms(question: str, history: list[dict] | None = None) -> str:
    """Turn a question in any language into Hebrew keywords for the search index."""
    resp = client().messages.create(
        model=MODEL, max_tokens=2000,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": QUERY_PROMPT.format(
            q=question, history=_history_text(history or []))}],
    )
    return _text(resp).strip()


_GEMATRIA = dict(zip("אבגדהוזחטיכלמנסעפצקרשתךםןףץ",
                     [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 200, 300, 400,
                      20, 40, 50, 80, 90]))


def gematria(s: str) -> int:
    return sum(_GEMATRIA.get(c, 0) for c in s)


def reference(p: dict) -> dict:
    """Readable reference for a passage, e.g. Siman 318, Se'if 12."""
    m = re.match(r"סימן\s+([א-ת\"']+)\s*-\s*(.*)", p["siman"])
    num, title = (gematria(m.group(1)), m.group(2).strip()) if m else (None, p["siman"])
    return {"section": p["section"], "section_en": SECTIONS_EN.get(p["section"], p["section"]), "siman": num, "siman_title": title, "seif": gematria(p["seif"])}


def _norm(s: str) -> str:
    # compare letters only, so spacing/punctuation/quote-mark differences don't matter
    return re.sub(r"[^א-ת0-9]", "", s)


def _clean_history(history: list[dict] | None) -> list[dict]:
    msgs = [{"role": m["role"], "content": str(m["content"])} for m in (history or [])[-6:]
            if m.get("role") in ("user", "assistant") and m.get("content")]
    while msgs and msgs[0]["role"] != "user":
        msgs.pop(0)
    # roles must alternate and the history must end with the bot's turn
    out = []
    for m in msgs:
        if out and out[-1]["role"] == m["role"]:
            out[-1] = m
        else:
            out.append(m)
    if out and out[-1]["role"] == "user":
        out.pop()
    return out


def answer(question: str, passages: list[dict], history: list[dict] | None = None) -> dict:
    blocks = "\n\n".join(
        f'<passage number="{i}" ref="{p["section"]} | {p["siman"]} | סעיף {p["seif"]}">\n{p["text"]}\n</passage>'
        for i, p in enumerate(passages, 1))
    messages = _clean_history(history) + [
        {"role": "user", "content": f"{blocks}\n\nQuestion: {question}"}]

    resp = client().beta.messages.create(
        model=MODEL, max_tokens=16000,
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",     # if a request is declined, retry on a fallback model
        system=SYSTEM,
        messages=messages,
    )
    if resp.stop_reason == "refusal":
        return {"found": False, "answer": "Sorry, I can't answer that one. Please ask a rav.", "quotes": []}
    if resp.stop_reason == "max_tokens":
        return {"found": False, "answer": "That answer came out too long. Try asking more specifically.", "quotes": []}
    data = json.loads(_text(resp))

    # Keep only quotes whose Hebrew really appears in the passage they point to.
    quotes = []
    for q in data.get("quotes", [])[:MAX_QUOTES]:
        i = q.get("passage", 0)
        if not (1 <= i <= len(passages)) or not q.get("hebrew") or not q.get("english"):
            continue
        p = passages[i - 1]
        if _norm(q["hebrew"]) and _norm(q["hebrew"]) in _norm(p["text"]):
            quotes.append({"english": q["english"].strip(), "hebrew": q["hebrew"].strip(),
                           "full_hebrew": p["text"], "ref": reference(p)})
    text = data.get("answer", "").strip()
    if data.get("found") and not quotes:
        text = "I couldn't find a clear source for this in Yalkut Yosef. Please ask a rav."
    return {"found": bool(data.get("found")) and bool(quotes), "answer": text, "quotes": quotes}
