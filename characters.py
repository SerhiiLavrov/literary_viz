import re
import spacy
from collections import Counter, defaultdict

nlp = spacy.load("en_core_web_sm")

TITLE_TOKENS = {
    "mr","mrs","ms","miss","sir","madam","dr","prof","professor",
    "capt","captain","st","saint","rev","reverend"
}

BAD_PERSON_WORDS = {
    "chapter","section","articles","article","christmas","dollars","cents",
    "pneumonia","freezing","square","west","trail","river","creek"
}

ALLOW_SHORT_NAMES = {"jim","sue","bob","tom","sam","ben","dan","ann","amy","eve","joe","max","liz","meg","kate"}

ROLE_HEADS = {
    "man","woman","boy","girl","child","children",
    "old man","old woman","young man","young woman",
    "stranger","friend","mother","father","daughter","son",
    "husband","wife","gentleman","lady","doctor","nurse","policeman","cop",
    "waiter","bartender","servant","soldier","captain","judge","lawyer"
}

ANIMALS = {"dog","wolf","horse","cat","bear","fox","deer","rabbit","bird","crow","snake","fish"}

MIN_PERSON_MENTIONS = 2
MIN_ROLE_MENTIONS   = 5
MIN_ANIMAL_MENTIONS = 2

LINK_WORDS = {
    "called","known","nickname","nicknamed","aka","a.k.a","a.k.a.",
    "short","shorter","shortened","named"
}

ROLE_REL_FRAC = 0.25


def clean_text_token(s: str) -> str:
    s = s.strip().replace("\u2019", "'")
    s = re.sub(r'["""]', "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def clean_person_name(name: str) -> str:
    s = clean_text_token(name)
    s = s.strip(" ,.;:!?()[]{}")
    s = re.sub(r"[\u2019\u2018']s$", "", s)
    s = re.sub(r"[\u2019\u2018']$", "", s)
    return s


def strip_titles(name: str) -> str:
    parts = name.split()
    while parts and re.sub(r"\.", "", parts[0].lower()) in TITLE_TOKENS:
        parts = parts[1:]
    return " ".join(parts)


def looks_like_initial_only(s: str) -> bool:
    s2 = s.replace(".", "").strip()
    return bool(re.fullmatch(r"[A-Z]", s2))


def is_garbage_person(name: str) -> bool:
    if not name:
        return True
    low = name.lower()
    if len(name.split()) == 1 and name.islower() and low not in ALLOW_SHORT_NAMES:
        return True
    if len(low) <= 2 and low not in ALLOW_SHORT_NAMES:
        return True
    if low in BAD_PERSON_WORDS:
        return True
    if any(w.lower() in BAD_PERSON_WORDS for w in name.split()):
        return True
    if len(name.split()) > 4:
        return True
    if len(name.split()) >= 2 and name[:1].islower():
        return True
    return False


def normalize_person(name: str) -> str:
    s = clean_person_name(name)
    s = strip_titles(s).strip()
    if looks_like_initial_only(s):
        return ""
    if is_garbage_person(s):
        return ""
    return s


def normalize_phrase(s: str) -> str:
    s = clean_text_token(s).lower()
    s = s.strip(" ,.;:!?()[]{}")
    s = re.sub(r"\bthe\b\s+", "", s)
    s = re.sub(r"\ba\b\s+|\ban\b\s+", "", s)
    s = re.sub(r"\bthis\b\s+|\bthat\b\s+", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def extract_entities(sentences: list):
    text = " ".join(sentences)
    doc = nlp(text)

    people = []
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            nm = normalize_person(ent.text)
            if nm:
                people.append(nm)

    roles = []
    animals = []
    for chunk in doc.noun_chunks:
        head_lemma = chunk.root.lemma_.lower()
        if head_lemma in ANIMALS:
            animals.append(head_lemma.upper())
            continue
        ch_low = normalize_phrase(chunk.text)
        toks = [t.lemma_.lower() for t in chunk if t.is_alpha]
        toks = [t for t in toks if t not in {"the","a","an","this","that","his","her","my","your","our","their"}]
        two = " ".join(toks[-2:]) if len(toks) >= 2 else None
        if ch_low in ROLE_HEADS or head_lemma in ROLE_HEADS or (two and two in ROLE_HEADS):
            label = (two if two in ROLE_HEADS else head_lemma)
            roles.append(label.upper())

    return people, roles, animals


def name_key(s: str) -> str:
    return re.sub(r"[^A-Za-z ]", "", s).strip().lower()


def is_initials_variant(n: str) -> bool:
    toks = n.replace(".", "").split()
    return len(toks) == 3 and len(toks[1]) == 1 and toks[0][:1].isupper() and toks[-1][:1].isupper()


def build_alias_map(people_names):
    raw_cnt = Counter(people_names)
    print(f"raw_cnt: {raw_cnt.most_common(30)}")
    alias = {}
    reasons = {}

    full = [n for n in raw_cnt if len(n.split()) >= 2]
    print(f"full names: {full[:20]}")
    by_first = defaultdict(list)
    by_last = defaultdict(list)

    for n in full:
        toks = n.split()
        by_first[toks[0]].append(n)
        by_last[toks[-1]].append(n)

    for first, fns in by_first.items():
        if len(fns) == 1 and first in raw_cnt:
            full_name = fns[0]
            last_word = full_name.split()[-1]
            if last_word[0].islower():
                continue
            alias[first] = full_name
            reasons[first] = "first name -> unique full name"

    for last, fns in by_last.items():
        if len(fns) == 1 and last in raw_cnt:
            alias[last] = fns[0]
            reasons[last] = "last name -> unique full name"

    for n in list(raw_cnt.keys()):
        if is_initials_variant(n):
            toks = n.replace(".", "").split()
            first, _, last = toks
            cand = [f for f in full if f.split()[0] == first and f.split()[-1] == last]
            if cand:
                canon = max(cand, key=lambda x: raw_cnt[x])
                alias[n] = canon
                reasons[n] = "initials -> matching full name"

    singles = [n for n in raw_cnt if len(n.split()) == 1]
    singles_key = {n: name_key(n) for n in singles}
    full_first_key = {f: name_key(f.split()[0]) for f in full}

    for short in singles:
        s_key = singles_key[short]
        if len(s_key) < 3:
            continue
        cand = []
        for long in singles:
            if long == short:
                continue
            l_key = singles_key[long]
            if len(l_key) >= len(s_key) + 1 and l_key.startswith(s_key):
                cand.append(long)
        for fn in full:
            f_key = full_first_key[fn]
            if len(f_key) >= len(s_key) + 1 and f_key.startswith(s_key):
                cand.append(fn)
        cand = list(dict.fromkeys(cand))
        if len(cand) == 1:
            alias[short] = cand[0]
            reasons[short] = "nickname/prefix -> unique longer name"

    return alias, raw_cnt, reasons


def apply_alias(name: str, alias: dict) -> str:
    return alias.get(name, name)


def merge_plural_variants(canon_cnt: Counter):
    updated = Counter(canon_cnt)
    merges = []
    for n in list(updated.keys()):
        if len(n) > 3 and n.endswith("s"):
            base = n[:-1]
            if base in updated:
                merges.append((n, base))
    for plural, base in merges:
        updated[base] += updated[plural]
        del updated[plural]
    return updated, merges


def _sent_contains_name(sent: str, name: str) -> bool:
    return bool(re.search(rf"\b{re.escape(name)}\b", sent))


def build_evidence_aliases(sentences: list, people_raw: list, window_sent=1):
    sents = [re.sub(r"\s+", " ", s) for s in sentences]
    cnt = Counter(people_raw)
    short_names = [n for n in cnt if len(n.split()) == 1 and n[:1].isupper()]
    full_names  = [n for n in cnt if len(n.split()) >= 2 and n[:1].isupper()]

    if not short_names or not full_names:
        return {}, {}

    hits = defaultdict(list)
    for i, sent in enumerate(sents):
        for n in set(short_names + full_names):
            if _sent_contains_name(sent, n):
                hits[n].append(i)

    alias = {}
    reasons = {}

    def has_strict_pattern(full, short, sent_text):
        if re.search(rf"\b{re.escape(full)}\b\s*\(\s*{re.escape(short)}\s*\)", sent_text):
            return "pattern: FULL (SHORT)"
        if re.search(rf"\b{re.escape(short)}\b\s*\(\s*{re.escape(full)}\s*\)", sent_text):
            return "pattern: SHORT (FULL)"
        low = sent_text.lower()
        if _sent_contains_name(sent_text, full) and _sent_contains_name(sent_text, short):
            if any(w in low for w in LINK_WORDS) or "known as" in low:
                return "pattern: link-word in same sentence"
        return None

    for short in short_names:
        for full in full_names:
            common = set(hits[short]).intersection(hits[full])
            for si in common:
                r = has_strict_pattern(full, short, sents[si])
                if r:
                    if short not in alias or cnt[full] > cnt[alias[short]]:
                        alias[short] = full
                        reasons[short] = r

    for short in short_names:
        if short in alias:
            continue
        hs = hits.get(short, [])
        if not hs:
            continue
        hs_set = set(hs)
        scored = []
        for full in full_names:
            hf = hits.get(full, [])
            if not hf:
                continue
            near = 0
            for fi in hf:
                for d in range(-window_sent, window_sent + 1):
                    if (fi + d) in hs_set:
                        near += 1
                        break
            scored.append((full, near))
        if not scored:
            continue
        scored.sort(key=lambda x: x[1], reverse=True)
        best_full, best_score = scored[0]
        second_score = scored[1][1] if len(scored) > 1 else 0
        if best_score >= 2 and best_score >= 2 * max(1, second_score) and cnt[best_full] >= 2:
            # Не связываем если короткое имя уже часто встречается само по себе
            if cnt[short] >= 10:
                continue
            alias[short] = best_full
            reasons[short] = f"proximity: near={best_score}, second={second_score}"

    return alias, reasons


def select_main_roles(role_cnt: Counter, min_abs=5, rel_frac=0.25):
    if not role_cnt:
        return set()
    max_c = max(role_cnt.values())
    thr = max(min_abs, int((rel_frac * max_c) + 0.9999))
    return {r for r, c in role_cnt.items() if c >= thr}


def build_entity_forms(people_raw, alias_map, main_people, main_roles, main_animals):
    forms = defaultdict(set)
    for p in people_raw:
        canon = apply_alias(p, alias_map)
        if canon in main_people:
            forms[canon].add(p)
    for r in main_roles:
        forms[r].add(r)
    for a in main_animals:
        forms[a].add(a)
    return forms


def safe_word_pattern(term: str):
    term = term.strip()
    esc = re.escape(term)
    esc = esc.replace(r"\ ", r"\s+")
    esc = esc.replace(r"\.", r"\.?")
    return re.compile(rf"\b{esc}\b", flags=re.IGNORECASE)


def build_surface_patterns(surface_forms):
    surface_forms = sorted(set(surface_forms), key=len, reverse=True)
    return {sf: safe_word_pattern(sf) for sf in surface_forms}


def count_mentions_in_sentence(sent: str, compiled_patterns: dict):
    out = {}
    for sf, pat in compiled_patterns.items():
        m = pat.findall(sent)
        if m:
            out[sf] = len(m)
    return out


def extract_characters(sentences: list) -> dict:
    print("Extracting characters...")
    people, roles, animals = extract_entities(sentences)

    e_alias, e_reasons = build_evidence_aliases(sentences, people, window_sent=1)
    print(f"e_alias: {e_alias}")
    alias_map, raw_people_cnt, reasons = build_alias_map(people)
    print(f"Alias map (before evidence): {alias_map}")
    # Фильтруем e_alias — не перезаписываем часто встречающиеся имена
    filtered_e_alias = {
        k: v for k, v in e_alias.items()
        if raw_people_cnt.get(k, 0) < 10
    }
    alias_map = {**alias_map, **filtered_e_alias}

    canon_people_cnt = Counter()
    for p in people:
        canon_people_cnt[apply_alias(p, alias_map)] += 1

    canon_people_cnt, _ = merge_plural_variants(canon_people_cnt)

    # Убираем имена у которых первое слово само по себе есть как отдельный персонаж
    # Например "Napoleon Mill" удаляется если "Napoleon" уже есть
    single_names = {n for n in canon_people_cnt if len(n.split()) == 1}
    to_remove = set()
    for name in list(canon_people_cnt.keys()):
        if len(name.split()) >= 2:
            first_word = name.split()[0]
            if first_word in single_names and first_word in canon_people_cnt:
                to_remove.add(name)
    for name in to_remove:
        # Переносим упоминания на однословную версию
        canon_people_cnt[name.split()[0]] += canon_people_cnt[name]
        del canon_people_cnt[name]

    role_cnt = Counter(roles)
    animal_cnt = Counter(animals)

    main_people  = {n for n, c in canon_people_cnt.items() if c >= MIN_PERSON_MENTIONS}
    main_roles   = select_main_roles(role_cnt, min_abs=MIN_ROLE_MENTIONS, rel_frac=ROLE_REL_FRAC)
    main_animals = {n for n, c in animal_cnt.items() if c >= MIN_ANIMAL_MENTIONS}

    entity_forms_map = build_entity_forms(people, alias_map, main_people, main_roles, main_animals)

    print(f"Characters found: people={sorted(main_people)}, roles={sorted(main_roles)}, animals={sorted(main_animals)}")
    print(f"Alias map (final): {alias_map}")

    return {
        "main_cast": {
            "people": sorted(list(main_people)),
            "roles": sorted(list(main_roles)),
            "animals": sorted(list(main_animals)),
        },
        "alias_map": alias_map,
        "entity_forms": {k: list(v) for k, v in entity_forms_map.items()},
    }


def compute_character_focus(sentences: list, parts: list, characters_data: dict) -> dict:
    main_cast = characters_data["main_cast"]
    entity_forms_map = characters_data["entity_forms"]

    canonical_entities = list(dict.fromkeys(
        main_cast["people"] + main_cast["roles"] + main_cast["animals"]
    ))

    if not canonical_entities:
        return {}

    sf2canon = {}
    surface_forms = set()
    for canon in canonical_entities:
        forms = entity_forms_map.get(canon, [])
        for sf in forms:
            sf = str(sf).strip()
            if sf:
                surface_forms.add(sf)
                if sf not in sf2canon or len(str(canon)) > len(str(sf2canon[sf])):
                    sf2canon[sf] = canon

    if not surface_forms:
        surface_forms = set(canonical_entities)
        sf2canon = {sf: sf for sf in surface_forms}

    compiled = build_surface_patterns(surface_forms)
    n = len(sentences)
    focus_data = {e: [] for e in canonical_entities}

    for part in parts:
        sent_range = part["sent_range"]
        a, b = sent_range.split("-")
        a, b = max(1, int(a)), min(n, int(b))
        chunk = sentences[a-1:b]
        denom = max(1, len(chunk))

        focus_hits = {e: 0 for e in canonical_entities}

        for sent in chunk:
            mention_map = count_mentions_in_sentence(sent, compiled)
            hit_this_sent = set()
            for sf, cnt in mention_map.items():
                canon = sf2canon.get(sf)
                if canon and canon in focus_hits:
                    hit_this_sent.add(canon)
            for canon in hit_this_sent:
                focus_hits[canon] += 1

        for e in canonical_entities:
            focus_data[e].append(round(focus_hits[e] / denom, 3))

    return focus_data