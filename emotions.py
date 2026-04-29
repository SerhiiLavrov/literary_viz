import numpy as np
from transformers import pipeline
from scipy.spatial.distance import jensenshannon

emo_pipeline = None

def get_emo_pipeline():
    global emo_pipeline
    if emo_pipeline is None:
        print("Loading emotion model...")
        emo_pipeline = pipeline(
            "text-classification",
            model="j-hartmann/emotion-english-distilroberta-base",
            top_k=None,
            truncation=True,
        )
    return emo_pipeline

EMO_LABELS = ["anger", "disgust", "fear", "joy", "sadness", "surprise", "neutral"]

def emotion_dist(text: str) -> dict:
    emo = get_emo_pipeline()
    preds = emo(text)[0]
    out = {p["label"].lower(): float(p["score"]) for p in preds}
    for k in EMO_LABELS:
        out.setdefault(k, 0.0)
    s = sum(out.values())
    if s > 0:
        for k in out:
            out[k] /= s
    return out

def robust_z(x: np.ndarray, eps=1e-9) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    med = np.median(x)
    iqr = np.percentile(x, 75) - np.percentile(x, 25)
    if abs(iqr) < eps:
        return np.zeros_like(x)
    return (x - med) / (iqr + eps)

def smooth_ema(x: np.ndarray, alpha=0.35) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    if len(x) == 0:
        return x
    y = np.empty_like(x)
    y[0] = x[0]
    for i in range(1, len(x)):
        y[i] = alpha * x[i] + (1 - alpha) * y[i-1]
    return y

def clamp01(x):
    return float(max(0.0, min(1.0, x)))

def q_rate(sent_list):
    if not sent_list:
        return 0.0
    return sum(1 for s in sent_list if "?" in s) / len(sent_list)

def e_rate(sent_list):
    if not sent_list:
        return 0.0
    return sum(1 for s in sent_list if "!" in s) / len(sent_list)

def avg_sent_len(sent_list):
    if not sent_list:
        return 0.0
    lens = [len(s.split()) for s in sent_list if s.strip()]
    return float(np.mean(lens)) if lens else 0.0

def choose_k(num_sentences, target=10, k_min=8, k_max=50):
    k = int(round(num_sentences / max(1, target)))
    return max(k_min, min(k_max, k))

def split_into_bins(n, k):
    idx = np.arange(n)
    return np.array_split(idx, k)

def analyze_emotions_tension(sentences: list) -> dict:
    n = len(sentences)
    print(f"Analyzing emotions for {n} sentences...")

    emo_rows = []
    for i, s in enumerate(sentences):
        d = emotion_dist(s)
        d["sent_id"] = i
        d["sentence"] = s
        emo_rows.append(d)

    import pandas as pd
    sent_emo = pd.DataFrame(emo_rows)

    val_sent = (
        sent_emo["joy"].to_numpy()
        - (sent_emo["sadness"] + sent_emo["fear"] + sent_emo["anger"] + sent_emo["disgust"]).to_numpy()
    )
    val_sent_sm = smooth_ema(val_sent)

    spike_sent = (
        sent_emo["fear"].to_numpy()
        + 0.8 * sent_emo["anger"].to_numpy()
        + 0.6 * sent_emo["surprise"].to_numpy()
    )
    spike_sent_sm = smooth_ema(spike_sent)

    k = choose_k(n)
    bins = split_into_bins(n, k)

    parts = []
    prev_dist = None
    prev_len = None

    for part_id, b in enumerate(bins, start=1):
        if len(b) == 0:
            continue

        a = int(b[0])
        c = int(b[-1])
        chunk_sents = [sentences[i] for i in b]

        seg_dist = sent_emo.loc[b, EMO_LABELS].mean(axis=0).to_numpy(dtype=float)
        seg_dist = np.clip(seg_dist, 1e-9, None)
        seg_dist = seg_dist / seg_dist.sum()

        seg_val = float(np.mean(val_sent_sm[b]))

        turn = 0.0 if prev_dist is None else float(jensenshannon(prev_dist, seg_dist))
        prev_dist = seg_dist.copy()

        seg_spike = float(np.mean(spike_sent_sm[b]))

        qr = q_rate(chunk_sents)
        er = e_rate(chunk_sents)
        L = avg_sent_len(chunk_sents)
        dlen = 0.0 if prev_len is None else prev_len - L
        prev_len = L

        punct = clamp01(0.8 * qr + 1.0 * er)
        pace = clamp01(1.0 / (1.0 + np.exp(-1.5 * dlen)))

        tension_raw = (
            0.70 * seg_spike +
            0.25 * turn +
            0.03 * punct +
            0.02 * pace
        )
        
        non_neutral = {k: v for k, v in zip(EMO_LABELS, seg_dist) if k != "neutral"}
        parts.append({
            "part": part_id,
            "sent_range": f"{a+1}-{c+1}",
            "sentences": chunk_sents,
            "valence_raw": seg_val,
            "tension_raw": float(tension_raw),
            "dominant_emotion": max(non_neutral, key=non_neutral.get),
            "emotion_dist": {k: round(float(v), 3) for k, v in zip(EMO_LABELS, seg_dist)},
            "spike": round(float(seg_spike), 3),
            "turn": round(float(turn), 3),
        })

    valence_raw = np.array([p["valence_raw"] for p in parts])
    vz = robust_z(valence_raw)
    valence_smooth = smooth_ema(np.tanh(vz))

    tension_raw_arr = np.array([p["tension_raw"] for p in parts])
    tz = robust_z(tension_raw_arr)
    tension_scaled = 10.0 * (1.0 / (1.0 + np.exp(-1.2 * tz)))
    tension_smooth = smooth_ema(tension_scaled)

    peak_idx = int(np.argmax(tension_smooth))

    print(f"Analysis complete: {len(parts)} parts, peak at part {peak_idx + 1}")

    return {
        "parts": parts,
        "valence": valence_smooth.tolist(),
        "tension": tension_smooth.tolist(),
        "peak_part": peak_idx + 1
    }