"""Score one solution-relevance case with the scorer every repository's relevance metric shares (recall of the gold solutions, a
precision floor); ``aggregate`` reports mean recall, mean precision and the cases that missed a solution."""
from esoi.understanding.solution_relevance.relevance_cases import aggregate, score_case

__all__ = ["aggregate", "score_case"]
