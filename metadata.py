import re
import spacy
import requests
import wordninja
from transformers import pipeline as hf_pipeline

summarizer = None
classifier = None

GENRES = [
    "short story", "novel", "adventure", "romance", "mystery",
    "thriller", "drama", "horror", "science fiction", "fantasy",
    "historical fiction", "comedy", "tragedy", "philosophical fiction"
]


def get_summarizer():
    global summarizer
    if summarizer is None:
        summarizer = hf_pipeline(
            "text2text-generation", model="google/flan-t5-base")
    return summarizer


def get_classifier():
    global classifier
    if classifier is None:
        classifier = hf_pipeline(
            "zero-shot-classification", model="facebook/bart-large-mnli")
    return classifier


def split_camel_case(text: str) -> str:
    return re.sub(r"([a-z])([A-Z])", r"\1 \2", text)


def title_words_match(our_title: str, ol_title: str) -> bool:
    our_words = our_title.lower().split()
    ol_title_lower = ol_title.lower()
    pos = 0
    for word in our_words:
        idx = ol_title_lower.find(word, pos)
        if idx == -1:
            return False
        pos = idx + len(word)
    return True


def search_open_library(title: str, author: str) -> dict:
    try:
        clean_title = split_camel_case(title).strip()
        print(f"Searching Open Library: '{clean_title}'")

        headers = {
            "User-Agent": "LiteraryViz/1.0 (student project; contact@example.com)"}
        params = {"title": clean_title, "limit": 3}

        response = requests.get(
            "https://openlibrary.org/search.json",
            params=params,
            timeout=35,
            headers=headers
        )
        print(f"Open Library status: {response.status_code}")
        if response.status_code != 200:
            return {}

        data = response.json()
        print(f"Open Library docs found: {data.get('numFound', 0)}")

        if not data.get("docs"):
            print("Open Library: no results found")
            return {}

        doc = data["docs"][0]
        result = {
            "title": doc.get("title", ""),
            "author": doc.get("author_name", [""])[0],
            "genre": doc.get("subject", [""])[0].lower() if doc.get("subject") else "",
            "description": ""
        }

        if not title_words_match(clean_title, result["title"]):
            print(
                f"Title mismatch: '{result['title']}' doesn't match '{clean_title}'")
            return {}

        work_key = doc.get("key", "")
        if work_key:
            work_url = f"https://openlibrary.org{work_key}.json"
            work_resp = requests.get(work_url, timeout=35, headers=headers)
            if work_resp.status_code == 200:
                work_data = work_resp.json()
                desc = work_data.get("description", "")
                if isinstance(desc, dict):
                    desc = desc.get("value", "")
                if desc:
                    result["description"] = desc
                    print(f"Got description from Open Library")

        print(f"Open Library found: {result['title']} by {result['author']}")
        return result

    except Exception as e:
        print(f"Open Library error: {e}")
    return {}


def detect_genre(text: str) -> str:
    sample = " ".join(text.split()[:500])
    try:
        clf = get_classifier()
        result = clf(sample, GENRES)
        genre = result["labels"][0]
        print(f"Genre detected: {genre}")
        return genre
    except Exception as e:
        print(f"Genre detection error: {e}")
        return "unknown"


def generate_summary(text: str) -> str:
    sample = " ".join(text.split()[:300])
    prompt = f"Summarize this story in 2 sentences. Who are the main characters and what they are doing?\n\n{sample}"
    try:
        summ = get_summarizer()
        result = summ(prompt, max_new_tokens=100, no_repeat_ngram_size=3)
        summary = result[0]["generated_text"]
        print(f"Summary generated: '{summary[:100]}'")
        return summary
    except Exception as e:
        print(f"Summary error: {e}")
        return "Could not generate summary."


def fix_merged_words(line: str) -> str:
    words = line.split()
    fixed = []
    for word in words:
        if len(word) > 5 and word[0].isupper():
            split = wordninja.split(word)
            if len(split) > 1:
                fixed.extend([split[0].capitalize()] + split[1:])
            else:
                fixed.append(word)
        else:
            fixed.append(word)
    return " ".join(fixed)


def extract_title_author_from_lines(raw_lines: list) -> tuple:
    nlp = spacy.load("en_core_web_sm")
    title = ""
    author = ""

    cleaned_lines = [fix_merged_words(l.strip()) for l in raw_lines[:15]]

    for idx, line in enumerate(cleaned_lines):
        if not line or len(line) < 3:
            continue

        # Строка вида "Animal Farm by George Orwell" — сразу берём название и автора
        if ' by ' in line.lower() and not title and not author:
            parts = re.split(r'\s+by\s+', line, flags=re.IGNORECASE)
            if len(parts) == 2:
                title = parts[0].strip()
                author = parts[1].strip()
                continue

        clean_line = re.sub(r"^by\s+", "", line, flags=re.IGNORECASE).strip()

        for attempt in [clean_line, clean_line.title()]:
            doc = nlp(attempt)
            persons = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
            if persons and not author:
                if not any(p.lower() in title.lower() for p in persons):
                    author = persons[0]
                    break

        if not title and len(line) < 60:
            words = line.split()
            capital_words = [w for w in words if w[0].isalpha()]
            capital_ratio = sum(
                1 for w in capital_words if w[0].isupper()) / max(1, len(capital_words))
            if (capital_ratio >= 0.5
                and not any(ch in line for ch in [".", ",", "!", "?", ";"])
                and line != author
                    and len(words) >= 2):
                title = line.title() if line.isupper() else line

                # Check if next line is continuation of title
                if idx + 1 < len(cleaned_lines):
                    next_line = cleaned_lines[idx + 1]
                    next_words = next_line.split()
                    if (1 <= len(next_words) <= 3
                        and next_words
                        and next_words[0][0].isupper()
                        and not any(ch in next_line for ch in [".", ",", "!", "?", ";"])
                            and not re.match(r"^by\s+", cleaned_lines[idx + 1], re.IGNORECASE)):
                        title = title + " " + next_line

        if title and author:
            break

    if not author:
        for line in cleaned_lines:
            doc = nlp(line.title())
            persons = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
            if persons:
                author = persons[0]
                break

    print(f"spaCy found — title: '{title}', author: '{author}'")
    return title, author


def extract_metadata(raw_lines: list, full_text: str) -> dict:
    title, author = extract_title_author_from_lines(raw_lines)
    print(f"Candidates — title: '{title}', author: '{author}'")

    ol = search_open_library(title, author)

    if ol.get("title"):
        title = ol["title"]
        ol_author = ol.get("author", "")
        if ol_author and len(ol_author.split()) >= 2:
            author = ol_author
        genre = ol.get("genre") or detect_genre(full_text)


    else:
        genre = detect_genre(full_text)
        if not ol and len(author.split()) < 2:
            author = "Unknown"

    ol_description = ol.get("description", "") if ol else ""
    summary = ol_description if ol_description else generate_summary(full_text)

    return {
        "title": title or "Unknown",
        "author": author or "Unknown",
        "genre": genre or "unknown",
        "summary": summary
    }
