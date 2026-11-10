"""BM25 keyword search over the se'ifim, with Hebrew-aware normalization.

Hebrew attaches prefixes (ו ה ב כ ל מ ש) to words, so "בשבת", "והשבת" and "שבת" should
match each other. Each word is indexed under its own form plus forms with up to two
prefix letters removed."""
import json, math, pathlib, re
from collections import Counter, defaultdict

DATA = pathlib.Path(__file__).resolve().parent.parent / "data" / "yalkut_yosef_kitzur.jsonl"
PREFIXES = set("והבכלמש")
FINALS = str.maketrans("ךםןףץ", "כמנפצ")
NIQQUD = re.compile(r"[֑-ׇ]")
WORD = re.compile(r"[א-ת]+")
# very common words that carry no meaning for search
STOP = {"של", "את", "על", "אם", "או", "כי", "לא", "גם", "הוא", "היא", "זה", "זו", "כל", "יש",
        "אין", "אלא", "מה", "עם", "אבל", "וכן", "כן", "רק", "אף", "שלא", "וכו", "עיין", "שם",
        "כמו", "אל", "הם", "הן", "בו", "בה", "לו", "לה", "מן", "עד", "אחר", "כך", "וכ", "וכמ"}

def variants(word: str) -> list[str]:
    w = NIQQUD.sub("", word).translate(FINALS)
    out = [w]
    for _ in range(2):
        if len(w) > 3 and w[0] in PREFIXES:
            w = w[1:]
            out.append(w)
    return out

def tokenize(text: str) -> list[str]:
    text = text.replace('"', "").replace("''", "").replace("״", "").replace("׳", "").replace("'", "")
    toks = []
    for word in WORD.findall(text):
        if word in STOP:
            continue
        toks.extend(variants(word))
    return toks

class Index:
    def __init__(self, path=DATA, k1=1.4, b=0.75):
        self.docs = [json.loads(l) for l in open(path, encoding="utf-8")]
        self.k1, self.b = k1, b
        self.postings = defaultdict(list)   # term -> [(doc_idx, tf)]
        self.lengths = []
        for i, d in enumerate(self.docs):
            # siman title counted twice so the topic of the siman weighs in
            tf = Counter(tokenize(f"{d['siman']} {d['siman']} {d['text']}"))
            self.lengths.append(sum(tf.values()))
            for term, n in tf.items():
                self.postings[term].append((i, n))
        self.avglen = sum(self.lengths) / len(self.lengths)
        N = len(self.docs)
        self.idf = {t: math.log(1 + (N - len(p) + 0.5) / (len(p) + 0.5)) for t, p in self.postings.items()}

    def search(self, query: str, k: int = 10, section: str | None = None) -> list[dict]:
        scores = Counter()
        for term in set(tokenize(query)):
            idf = self.idf.get(term)
            if idf is None:
                continue
            for i, tf in self.postings[term]:
                norm = tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * self.lengths[i] / self.avglen))
                scores[i] += idf * norm
        results = []
        for i, s in scores.most_common():
            d = self.docs[i]
            if section and d["section"] != section:
                continue
            results.append({**d, "score": round(s, 2)})
            if len(results) == k:
                break
        return results

    def sections(self) -> list[str]:
        return list(dict.fromkeys(d["section"] for d in self.docs))
