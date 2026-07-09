from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class SemanticSimilarityModel:
    """TF-IDF semantic similarity with a reusable vectorizer per process."""

    def __init__(self):
        self._vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=5000,
            stop_words="english",
        )
        self._fitted = False
        self._catalog_docs: list[str] = []

    def warm_start(self, documents: list[str]) -> None:
        unique = list(dict.fromkeys(doc.strip() for doc in documents if doc and doc.strip()))
        if not unique:
            return
        self._vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=5000,
            stop_words="english",
        )
        self._vectorizer.fit(unique)
        self._catalog_docs = unique
        self._fitted = True

    def _vectorizer_for(self, documents: list[str]) -> TfidfVectorizer:
        if self._fitted:
            try:
                return self._vectorizer
            except Exception:
                self._fitted = False
        self._vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=5000,
            stop_words="english",
        )
        self._vectorizer.fit(documents)
        self._fitted = True
        return self._vectorizer

    def score(self, context_text: str, candidate_text: str) -> float:
        if not context_text or not candidate_text:
            return 0.0
        vectorizer = self._vectorizer_for([context_text, candidate_text])
        vectors = vectorizer.transform([context_text, candidate_text])
        return round(float(cosine_similarity(vectors[0], vectors[1])[0][0]), 4)

    def score_batch(self, context_text: str, candidate_texts: list[str]) -> list[float]:
        if not context_text or not candidate_texts:
            return [0.0 for _ in candidate_texts]
        documents = [context_text, *candidate_texts]
        vectorizer = self._vectorizer_for(documents)
        vectors = vectorizer.transform(documents)
        context_vector = vectors[0]
        return [
            round(float(cosine_similarity(context_vector, vectors[index + 1])[0][0]), 4)
            for index in range(len(candidate_texts))
        ]
