"""Lightweight offline resume tailoring engine.

This module intentionally uses only Python's standard library. It ranks existing
resume content against the target job description and proposes conservative edits;
it does not call an external LLM or invent qualifications.
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
    "ability","strong","excellent","good","experience","knowledge"
}
SKILL_TERMS = [
    "python","sql","excel","power bi","tableau","machine learning","deep learning",
    "data analysis","data analytics","statistics","pandas","numpy","scikit-learn",
    "tensorflow","pytorch","nlp","computer vision","generative ai","llm","aws",
    "azure","gcp","docker","kubernetes","git","linux","fastapi","flask","django",
    "javascript","typescript","react","java","c++","communication","research",
    "bioinformatics"," genomics","clinical data","healthcare","etl","data cleaning",
    "data visualization","regression","classification","model evaluation","api",
    "postgresql","mysql","mongodb","powerpoint","project management"
]
WEAK_REWRITES = [
    (re.compile(r"^\s*responsible for\b", re.I), "Managed"),
    (re.compile(r"^\s*worked on\b", re.I), "Contributed to"),
    (re.compile(r"^\s*helped with\b", re.I), "Supported"),
    (re.compile(r"^\s*helped\b", re.I), "Supported"),
    (re.compile(r"^\s*did\b", re.I), "Completed"),
    (re.compile(r"^\s*good knowledge of\b", re.I), "Knowledge of"),
    (re.compile(r"^\s*familiar with\b", re.I), "Applied familiarity with"),
]

def words(text):
    return [w.lower().strip(".-") for w in WORD_RE.findall(text) if len(w) > 2 and w.lower() not in STOP_WORDS]

def section_for(lines, index):
    heading = ""
    for line in lines[:index + 1]:
        s = line.strip().lower().rstrip(":")
        if len(s) < 45 and any(k in s for k in (
            "summary", "profile", "objective", "skill", "experience", "project",
            "education", "certification", "publication", "achievement"
        )):
            heading = s
    if "skill" in heading: return "Skills"
    if "summary" in heading or "profile" in heading or "objective" in heading: return "Summary"
    if "project" in heading: return "Projects"
    if "experience" in heading: return "Experience"
    if "education" in heading: return "Education"
    if "certification" in heading: return "Certifications"
    return "Other"

def job_terms(jd):
    tokens = words(jd)
    counts = Counter(tokens)
    phrases = [term for term in SKILL_TERMS if term.strip() and term in jd.lower()]
    return counts, phrases

def local_generate(resume, jd):
    """Return meaningful, reviewable edits based only on existing resume facts."""
    lines = resume.splitlines()
    counts, phrases = job_terms(jd)
    suggestions = []
    seen = set()

    def add(section, old, new, reason, score):
        old, new = old.strip(), new.strip()
        key = (old, new)
        if old and new and old != new and old in resume and key not in seen:
            seen.add(key)
            suggestions.append({
                "section": section, "original_text": old, "proposed_text": new,
                "rationale": reason, "_score": score
            })

    # Prioritize skill terms that already exist in the resume and match the role.
    for i, line in enumerate(lines):
        raw = line.strip()
        if not raw or len(raw) > 500 or len(raw) < 12:
            continue
        section = section_for(lines, i)
        low = raw.lower()
        if section == "Skills" and ("," in raw or "|" in raw or "•" in raw or ";" in raw):
            # Reorder only terms already present on this line; never add a skill.
            sep = "|" if "|" in raw else (";" if ";" in raw else ("," if "," in raw else "•"))
            items = [x.strip() for x in raw.split(sep) if x.strip()]
            if len(items) >= 3:
                ranked = sorted(enumerate(items), key=lambda pair: (
                    -sum(counts.get(w, 0) for w in words(pair[1])),
                    pair[0]
                ))
                reordered = [item for _, item in ranked]
                proposed = (f" {sep} " if sep in ",;|" else f" {sep} ").join(reordered)
                if proposed != raw:
                    matched = [x for x in items if any(t in jd.lower() for t in [x.lower()]) or any(w in counts for w in words(x))]
                    if matched:
                        add("Skills", raw, proposed,
                            "Prioritizes skills already listed in your resume that overlap with terms used in the target job description. No new skills were added.",
                            7 + len(matched))
        # Strengthen weak bullet openings without adding results or metrics.
        for pattern, replacement in WEAK_REWRITES:
            match = pattern.search(raw)
            if match:
                proposed = pattern.sub(replacement, raw, count=1)
                add(section, raw, proposed,
                    "Uses a clearer, more direct action phrase while preserving the original statement and avoiding invented achievements.",
                    5 + sum(counts.get(w, 0) for w in words(raw)))
                break
        # Remove first-person wording from a sentence where the rest of the facts stay the same.
        if re.match(r"^(I am|I have|I was|I worked|My responsibilities include)\b", raw, re.I):
            proposed = re.sub(r"^(I am|I have|I was|I worked|My responsibilities include)\s*", "", raw, flags=re.I)
            if proposed and proposed[0].islower():
                proposed = proposed[0].upper() + proposed[1:]
            add(section, raw, proposed,
                "Makes the wording more concise and resume-appropriate without adding claims.",
                4 + sum(counts.get(w, 0) for w in words(raw)))

    # Relevance scoring is based on overlap between the job description and each existing line.
    for item in suggestions:
        overlap = set(words(item["original_text"])) & set(counts)
        item["_score"] += len(overlap) * 0.25
    suggestions.sort(key=lambda x: x["_score"], reverse=True)
    result = []
    for item in suggestions:
        item.pop("_score", None)
        result.append(item)
        if len(result) >= 8:
            break
    return result

async def generate(resume, jd):
    # No API key, network request, model download, or third-party NLP dependency.
    return local_generate(resume, jd), "local"
