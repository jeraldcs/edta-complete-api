from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class SemanticSimilarityModel:
    def score(self, context_text: str, candidate_text: str) -> float:
        if not context_text or not candidate_text:
            return 0.0
        vectorizer = TfidfVectorizer()
        vectors = vectorizer.fit_transform([context_text, candidate_text])
        return round(float(cosine_similarity(vectors[0], vectors[1])[0][0]), 4)
