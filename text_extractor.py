import os
import re
import pdfplumber
import spacy
from collections import Counter
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
POPPLER_PATH = r"C:\Program Files\poppler-25.12.0\Library\bin"
punct_lines = []  
PUNCT_CHARS = set(".,!?;:\u201c\u201d\u2018\u2019—()")
nlp = spacy.blank("en")
if "sentencizer" not in nlp.pipe_names:
    nlp.add_pipe("sentencizer")

first_lines = []

def normalize_line(line: str) -> str:
    line = line.strip()
    line = re.sub(r"\s+", " ", line)
    line = re.sub(r"\b(?:[A-Za-z]\s){2,}[A-Za-z]\b", lambda m: re.sub(r"([a-z])([A-Z])", r"\1 \2", m.group(0).replace(" ", "")), line)
    line = re.sub(r"([a-z])([A-Z][a-z])", r"\1 \2", line)
    line = re.sub(r"\b([A-Za-z])\s*\.\s*", r"\1. ", line)
    line = re.sub(r"([a-z])p([A-Z])", r"\1 \2", line)
    line = re.sub(r"\s{2,}", " ", line).strip()
    line = re.sub(r"\b([A-Z])\s+([A-Z]{2,})\b", r"\1\2", line)
    line = re.sub(r"\b([A-Z]{1,2})\s+([A-Z])\b", r"\1\2", line)
    return line.strip()

def is_noise_line(line: str) -> bool:
    l = line.strip()
    if len(l) < 3:
        return True
    if re.fullmatch(r"\d+", l):
        return True
    letters = sum(ch.isalpha() for ch in l)
    if letters >= 6 and (l.count(" ") / max(1, letters)) > 0.45:
        return True
    if re.fullmatch(r"(p|P)", l):
        return True
    SKIP_PATTERNS = ["chapter", "section", "contents", "table of contents", "index", "part "]
    if any(line.lower().startswith(p) for p in SKIP_PATTERNS):
        return True
    if re.search(r"https?://", l):
        return True
    if re.search(r"\d{1,2}/\d{1,2}/\d{4}", l):
        return True
    return False

def fix_missing_spaces(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
    return s.strip()

def fix_split_caps_start(s: str) -> str:
    s = s.strip()
    s = re.sub(r"^HE\s+COP\b", "THE COP", s)
    s = re.sub(r"^NE\s+DOLLAR\b", "ONE DOLLAR", s)
    s = re.sub(r"^AY\s+HAD\b", "DAY HAD", s)
    return s

def cut_merged_title_prefix(s: str) -> str:
    s = s.strip()
    m = re.search(r"\b[A-Z]{2,}\b", s)
    if m and m.start() > 0:
        prefix = s[:m.start()].strip()
        if 5 <= len(prefix) <= 80:
            words = prefix.split()
            titleish = sum(w[:1].isupper() for w in words if any(ch.isalpha() for ch in w))
            if len(words) >= 2 and titleish / len(words) > 0.7:
                s = s[m.start():].strip()
    return s

def polish(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    s = s.replace("for- est", "forest")
    s = re.sub(r"\bIhave\b", "I have", s)
    s = re.sub(r"\bIam\b", "I am", s)
    s = re.sub(r"\bIcan\b", "I can", s)
    s = re.sub(r"\bIdo\b", "I do", s)
    s = re.sub(r"\bA(?=[A-Z][a-z])", "A ", s)
    s = re.sub(r"\bAn(?=[A-Z][a-z])", "An ", s)
    return s.strip()

punct_lines = []  
PUNCT_CHARS = set(".,!?;:\u201c\u201d—()")

def extract_text_universal(pdf_path: str) -> str:
    global punct_lines
    punct_lines = []
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            lines = [normalize_line(x) for x in t.split("\n")]
            lines = [x for x in lines if x and not is_noise_line(x)]
            pages.append(lines)

    all_lines = [ln for p in pages for ln in p]
    freq = Counter(all_lines)
    num_pages = max(1, len(pages))
    thr = max(2, int(0.4 * num_pages))

    cleaned_pages = []
    for p in pages:
        cleaned = [ln for ln in p if freq[ln] < thr]
        cleaned_pages.append(cleaned)
        # Collect punctuation per line
        for line in cleaned:
            lp = "".join(ch for ch in line if ch in PUNCT_CHARS)
            if lp:
                punct_lines.append(lp)

    text = "\n".join("\n".join(p) for p in cleaned_pages)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def extract_text_ocr(pdf_path: str) -> str:
    global first_lines
    first_lines = []
    print(f"Using OCR for {pdf_path}...")
    try:
        images = convert_from_path(pdf_path, dpi=200, poppler_path=POPPLER_PATH)
        pages_raw = []
        for i, image in enumerate(images):
            text = pytesseract.image_to_string(image, lang="eng")
            lines = [normalize_line(x) for x in text.split("\n")]
            lines = [x for x in lines if x and not is_noise_line(x)]
            if i < 2:
                first_lines.extend(lines)
            pages_raw.append(lines)
            print(f"OCR page {i+1}/{len(images)}")

        
        all_lines = [ln for page in pages_raw for ln in page]
        num_pages = max(1, len(pages_raw))
        thr = max(2, int(0.4 * num_pages))
        freq = Counter(re.sub(r'\d+', '', ln).strip() for ln in all_lines)

        pages_text = []
        for page in pages_raw:
            lines = [ln for ln in page if freq[re.sub(r'\d+', '', ln).strip()] < thr]
            page_text = " ".join(lines)
            page_text = re.sub(r'(\w+)-\s+([a-z])', r'\1\2', page_text)
            pages_text.append(page_text)
        

        return "\n".join(pages_text)
    except Exception as e:
        print(f"OCR error: {e}")
        return ""

def extract_text_txt(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    lines = [normalize_line(x) for x in text.split("\n")]
    lines = [x for x in lines if x and not is_noise_line(x)]
    return " ".join(lines)

def extract_sentences(file_path: str) -> list:
    global first_lines
    first_lines = []

    if file_path.endswith(".txt"):
        raw_text = extract_text_txt(file_path)
    else:
        raw_text = extract_text_universal(file_path)
        if len(raw_text.strip()) < 100:
            print("Text extraction failed, switching to OCR...")
            raw_text = extract_text_ocr(file_path)

    if not raw_text.strip():
        print("Could not extract text from PDF")
        return []

    if not first_lines:
        first_lines = [l for l in raw_text.split("\n")[:20] if l.strip()]

    doc = nlp(raw_text)
    sents = [s.text.strip() for s in doc.sents]
    sents = [s for s in sents if len(s) >= 10]
    sents = [fix_missing_spaces(s) for s in sents]
    sents = [polish(s) for s in sents]

    if sents:
        sents[0] = cut_merged_title_prefix(sents[0])
        sents[0] = fix_split_caps_start(sents[0])

    print(f"Extracted {len(sents)} sentences from {file_path}")
    return sents

def get_raw_lines(file_path: str) -> list:
    raw_lines = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages[:2]:
            t = page.extract_text() or ""
            lines = [normalize_line(l.strip()) for l in t.split("\n")]
            lines = [l for l in lines if l and not is_noise_line(l)]
            raw_lines.extend(lines)

    if raw_lines:
        # Убираем дубли но сохраняем порядок
        seen = set()
        filtered = []
        for ln in raw_lines:
            if ln not in seen:
                filtered.append(ln)
                seen.add(ln)
        print(f"Raw lines from pdfplumber: {filtered[:10]}")
        return filtered

    print(f"Using first_lines: {first_lines[:10]}")
    return first_lines