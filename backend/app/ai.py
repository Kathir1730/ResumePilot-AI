"""Conservative offline resume suggestion engine.

Uses deterministic text rules and job-description overlap only. It never reorders
skills, invents achievements, or pretends to be a trained language model.
"""
import re
from collections import Counter

WORD_RE = re.compile(r"[A-Za-z][A-Za-z+#.\-]{1,}")
STOP_WORDS = {
    "about","after","also","and","are","been","being","but","can","could","for",
    "from","have","into","its","job","more","our","over","role","should","such",
    "than","that","the","their","them","then","there","these","they","this","those",
    "through","under","using","very","was","were","what","when","where","which",
    "while","will","with","you","your","years","year","work","working","required",
    "preferred","responsibilities","responsibility","candidate","team","including",
    "ability","strong","excellent","good","experience","knowledge","looking","seeking"
}
SECTION_HEADINGS = {
    "summary", "professional summary", "profile", "objective", "skills",
    "technical skills", "core skills", "key skills", "experience",
    "work experience", "professional experience", "employment", "projects",
    "academic projects", "personal projects", "education", "certifications",
    "certificates", "achievements", "publications", "awards", "internships",
    "volunteer experience", "languages", "interests", "activities", "coursework"
}
# These edits change phrasing only; they never add a result, metric, or skill.
WEAK_REWRITES = [
    (re.compile(r"^\s*responsible for\b", re.I), "Managed"),
    (re.compile(r"^\s*worked on\b", re.I), "Contributed to"),
    (re.compile(r"^\s*helped with\b", re.I), "Supported"),
    (re.compile(r"^\s*helped\b", re.I), "Supported"),
    (re.compile(r"^\s*good knowledge of\b", re.I), "Knowledge of"),
    (re.compile(r"^\s*familiar with\b", re.I), "Familiar with"),
    (re.compile(r"^\s*I am responsible for\b", re.I), "Responsible for"),
]

def words(text):
    return [
        w.lower().strip(".-")
        for w in WORD_RE.findall(text)
        if len(w) > 2 and w.lower() not in STOP_WORDS
    ]

def _heading_key(line):
    return re.sub(r"[:\s]+$", "", line.strip().lower())

def section_for(lines, index):
    current = "Other"
    for line in lines[:index]:
        heading = _heading_key(line)
        if heading in SECTION_HEADINGS:
            if "skill" in heading:
                current = "Skills"
            elif any(k in heading for k in ("summary", "profile", "objective")):
                current = "Summary"
            elif "project" in heading:
                current = "Projects"
            elif "experience" in heading or heading == "employment":
                current = "Experience"
            elif "education" in heading:
                current = "Education"
            elif "certification" in heading or "certificate" in heading:
                current = "Certifications"
    return current

def local_generate(resume, jd):
    """Suggest only safe edits with visible relevance to the target role."""
    lines = resume.splitlines()
    jd_tokens = Counter(words(jd))
    suggestions = []
    seen = set()

    for index, line in enumerate(lines):
        original = line.strip()
        if len(original) < 18 or len(original) > 450:
            continue
        if _heading_key(original) in SECTION_HEADINGS:
            continue
        # Do not touch contact details, URLs, email addresses, or likely name lines.
        if "@" in original or "://" in original or re.search(r"\b(?:linkedin|github)\.com\b", original, re.I):
            continue

        proposed = None
        for pattern, replacement in WEAK_REWRITES:
            if pattern.search(original):
                proposed = pattern.sub(replacement, original, count=1)
                break
        if not proposed or proposed == original:
            continue

        old_tokens = set(words(original))
        overlap = old_tokens & set(jd_tokens)
        # Do not suggest generic edits unrelated to the target job.
        if not overlap:
            continue
        key = (original, proposed)
        if key in seen:
            continue
        seen.add(key)
        section = section_for(lines, index)
        relevant = ", ".join(sorted(overlap)[:5])
        suggestions.append({
            "section": section,
            "original_text": original,
            "proposed_text": proposed,
            "rationale": (
                f"Rephrases the opening more directly without changing the underlying claim. "
                f"This line shares these terms with the job description: {relevant}. "
                "No new skills, metrics, or achievements were added."
            ),
            "_score": len(overlap) + sum(jd_tokens[w] for w in overlap) * 0.1,
        })

    # Sort suggestions by relevance only. Never reorder content inside the resume.
    suggestions.sort(key=lambda item: item["_score"], reverse=True)
    result = []
    for item in suggestions[:8]:
        item.pop("_score", None)
        result.append(item)
    return result

async def generate(resume, jd):
    # Offline: no API key, network calls, downloads, or third-party NLP dependencies.
    return local_generate(resume, jd), "local"
