from text_extractor import extract_sentences, get_raw_lines, punct_lines
from metadata import extract_metadata
from emotions import analyze_emotions_tension
from characters import extract_characters, compute_character_focus
from structure import analyze_structure

def analyze_text(pdf_path: str) -> dict:
    print("=== Starting analysis ===")

    print("Step 1: Extracting text...")
    sentences = extract_sentences(pdf_path)
    full_text = " ".join(sentences)

    print("Step 2: Analyzing emotions and tension...")
    arcs = analyze_emotions_tension(sentences)

    print("Step 3: Extracting metadata...")
    raw_lines = get_raw_lines(pdf_path)
    metadata = extract_metadata(raw_lines, full_text)

    print("Step 4: Extracting characters...")
    characters_data = extract_characters(sentences)

    print("Step 5: Computing character focus...")
    focus = compute_character_focus(sentences, arcs["parts"], characters_data)

    print("Step 6: Analyzing structure...")
    structure = analyze_structure(sentences, punct_lines)

    print("=== Analysis complete ===")

    return {
        "title": metadata["title"],
        "author": metadata["author"],
        "genre": metadata["genre"],
        "summary": metadata["summary"],
        "sentences": sentences,
        "valence": arcs["valence"],
        "tension": arcs["tension"],
        "peak_part": arcs["peak_part"],
        "parts": [{"part": p["part"], "sent_range": p["sent_range"], "sentences": p["sentences"], "dominant_emotion": p["dominant_emotion"], "emotion_dist": p["emotion_dist"], "spike": p["spike"], "turn": p["turn"]} for p in arcs["parts"]],
        "characters": characters_data["main_cast"],
        "character_focus": focus,
        "structure": structure,
        "locations": extract_locations(sentences, characters_data)
    }

def extract_locations(sentences: list, characters_data: dict = None) -> list:
    import spacy
    from collections import Counter
    nlp = spacy.load("en_core_web_sm")
    full_text = " ".join(sentences)
    doc = nlp(full_text)
    
    DIRECTION_WORDS = {"east", "west", "north", "south", "island", "sound", "bay", "lake", "sea"}

    char_names = set()
    if characters_data:
        main_cast = characters_data.get("main_cast", {})
        for name in main_cast.get("people", []) + main_cast.get("roles", []) + main_cast.get("animals", []):
            for word in name.split():
                char_names.add(word.lower())
        for name in characters_data.get("all_person_names", set()):
            for word in name.split():
                char_names.add(word.lower())

    raw = [
        ent.text.strip() for ent in doc.ents
        if ent.label_ in ("GPE", "LOC")
        and len(ent.text.strip()) > 2
        and ent.text.strip()[0].isupper()
        and len(ent.text.strip().split()) <= 3
        and ent.text.strip().lower() not in char_names
        and ent.text.strip().lower() not in DIRECTION_WORDS
        and not (len(ent.text.strip().split()) == 1 and len(ent.text.strip()) < 5)
    ]

    freq = Counter(raw)
    locations = sorted([loc for loc, cnt in freq.items() if cnt >= 2])

    print(f"Locations found: {locations}")
    return locations