"""Answer a question with Claude, using only se'ifim retrieved from the index.
Needs ANTHROPIC_API_KEY in the environment."""
import os
import anthropic

MODEL = "claude-opus-5-5"

SYSTEM = """You answer halakha questions strictly according to Kitzur Shulchan Aruch Yalkut Yosef \
(Rav Yitzhak Yosef, based on the rulings of Hacham Ovadia Yosef zt"l).

Rules:
- Use ONLY the provided se'ifim. Never add rulings from memory or from other poskim.
- If the passages do not answer the question, say so plainly and suggest asking a rav.
- Cite the siman and se'if for every ruling. Mention the source in brackets at the end \
of the se'if (e.g. Yabia Omer, Chazon Ovadia) when it is relevant.
- Keep the distinctions the text makes: lechatchila vs. bedi'eved, sha'at hadechak, \
Sephardim vs. Ashkenazim, and conditions like "ויש להחמיר".
- For case-specific or weighty questions (niddah, kashrut of a specific item, aguna, \
mamzerut, medical questions on Shabbat, monetary disputes), give the general rule and \
tell the user to ask a rav about their own case. If there is danger to life, tell them \
to act to save life immediately.
- Answer in the language the user wrote in. Keep Hebrew halakhic terms, with a short \
translation the first time when answering in English."""

QUERY_PROMPT = """Rewrite this halakha question as Hebrew search keywords that would appear \
in the text of Kitzur Shulchan Aruch Yalkut Yosef (rabbinic Hebrew, e.g. בישול אחר בישול, \
ברכה אחרונה, מוקצה). Give 4-12 words, space-separated, nothing else.

Question: {q}"""

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
