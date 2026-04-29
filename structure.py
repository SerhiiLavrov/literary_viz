import re
import numpy as np

def analyze_structure(sentences: list, punct_lines: list = None) -> dict:
    lengths = [len(s.split()) for s in sentences]
    
    if punct_lines:
        punctuation = "\n".join(punct_lines)
    else:
        punctuation = ""
        for s in sentences:
            lp = "".join(ch for ch in s if ch in ".,!?;:\u201c\u201d—()")
            if lp:
                punctuation += lp + "\n"

    return {
        "sentence_lengths": lengths,
        "punctuation": punctuation,
        "avg_length": round(float(np.mean(lengths)), 1),
        "total_sentences": len(sentences)
    }