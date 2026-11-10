"""Download Kitzur Shulchan Aruch Yalkut Yosef from toratemetfreeware.com and split it
into one JSON record per se'if (data/yalkut_yosef_kitzur.jsonl)."""
import html, json, pathlib, re, urllib.request

URL = "https://www.toratemetfreeware.com/online/f_01355_all.html"
OUT = pathlib.Path(__file__).resolve().parent.parent / "data" / "yalkut_yosef_kitzur.jsonl"

TOKEN = re.compile(
    r'<a name="HtmpReportNum\d+_L3"></a>.*?<u>(?P<sec>[^<]+)</u>'      # section heading (הלכות ...)
    r'|<a name="HtmpReportNum\d+_L2"></a>.*?<u>(?P<siman>[^<]+)</u>'   # siman heading
    r'|<a name="(?P<anchor>סימן[^"]*-(?P<letter>[א-ת]+))"></a>',       # se'if anchor
    re.S)

def clean(s: str) -> str:
    s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s).replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()

def main():
    raw = urllib.request.urlopen(URL, timeout=120).read().decode("windows-1255", errors="replace")
    matches = list(TOKEN.finditer(raw))
    section = siman = None
    records = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        if m.group("sec"):
            section = m.group("sec").strip()
        elif m.group("siman"):
            siman = m.group("siman").strip()
        else:
            letter = m.group("letter")
            text = re.sub(r"^" + letter + r"\s+", "", clean(raw[m.end():end]))
            records.append({"id": f"{siman} - {letter}", "section": section,
                            "siman": siman, "seif": letter, "text": text})
    OUT.parent.mkdir(exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(records)} se'ifim to {OUT}")

if __name__ == "__main__":
    main()
