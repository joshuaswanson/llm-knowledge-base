from __future__ import annotations

from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from kb.config import CONCEPTS_DIR, SOURCES_DIR


def _gather_docs() -> list[tuple[Path, str]]:
    docs = []
    for d in [CONCEPTS_DIR, SOURCES_DIR]:
        if d.exists():
            for p in d.glob("*.md"):
                docs.append((p, p.read_text()))
    return docs


def search(query: str, top_k: int = 10) -> list[tuple[Path, float, str]]:
    docs = _gather_docs()
    if not docs:
        return []

    paths = [d[0] for d in docs]
    texts = [d[1] for d in docs]

    vectorizer = TfidfVectorizer(stop_words="english", max_features=10000)
    tfidf_matrix = vectorizer.fit_transform(texts + [query])

    query_vec = tfidf_matrix[-1]
    doc_vecs = tfidf_matrix[:-1]

    similarities = cosine_similarity(query_vec, doc_vecs).flatten()

    results = []
    for idx in similarities.argsort()[::-1][:top_k]:
        score = similarities[idx]
        if score > 0.01:
            # Extract first non-frontmatter paragraph as snippet
            text = texts[idx]
            if text.startswith("---"):
                parts = text.split("---", 2)
                text = parts[2] if len(parts) >= 3 else text
            lines = [l.strip() for l in text.strip().split("\n") if l.strip() and not l.startswith("#")]
            snippet = lines[0][:200] if lines else ""
            results.append((paths[idx], float(score), snippet))

    return results
