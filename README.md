# Yalkut Yosef Halakha Bot

Search and (with an Anthropic API key) ask questions about **Kitzur Shulchan Aruch Yalkut Yosef**
(Rav Yitzhak Yosef, following the rulings of Hacham Ovadia Yosef zt"l). Every answer cites siman and se'if.

## Run it

**Windows (easiest):** on GitHub click **Code → Download ZIP**, unzip it, and double-click
`start.bat`. It sets everything up and opens http://localhost:5000 in your browser.
You need Python installed first (python.org/downloads, tick "Add python.exe to PATH").

**Mac / Linux:**

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py          # open http://localhost:5000
```

On first run the app downloads and parses the book from toratemetfreeware.com into
`data/` (the text itself is not stored in this repo, since it is under copyright).

Without a key: Hebrew keyword search over all 11,726 se'ifim.
With a key: a chat where questions in any language get a short English answer (1-3 sentences)
built only from the se'ifim the search found, plus 1-3 quotes translated into English with
siman and se'if. Every Hebrew quote is checked against the book's text before it is shown;
quotes that don't match are dropped. "Show Hebrew" displays the original se'if.

Or, with no terminal: create a file named `api_key.txt` in the project folder containing
only your key. (It's in .gitignore - never share or commit it.)

```bash
export ANTHROPIC_API_KEY=sk-ant-...
.venv/bin/python app.py
```

## Files

- `data/yalkut_yosef_kitzur.jsonl` - the book, one record per se'if (created on first run)
- `scripts/build_data.py` - re-downloads and re-parses the book from toratemetfreeware.com
- `bot/search.py` - BM25 search with Hebrew prefix handling
- `bot/answer.py` - Claude: question -> Hebrew search terms -> cited answer
- `app.py`, `static/index.html` - local web app

## Copyright

The text is (c) Rav Yitzhak Yosef; the source requires citation when quoting. Fine for
personal learning; get permission before publishing this as a public site.
This is a learning tool, not a psak - for your own case, ask a rav.
