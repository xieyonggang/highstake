import logging
import re

logger = logging.getLogger(__name__)

FILLER_WORDS = {
    "um", "uh", "like", "you know", "basically", "actually",
    "sort of", "kind of", "i mean", "right",
}

HEDGING_PHRASES = {
    "i think", "maybe", "probably", "i guess", "hopefully",
    "we'll see", "it depends",
}


class ScoringEngine:
    """Analyzes presentation transcript to produce scores."""

    def __init__(
        self,
        transcript: list[dict],
        agent_questions: list[dict],
        slide_count: int,
        duration_secs: int,
    ):
        self.transcript = transcript
        self.agent_questions = agent_questions
        self.slide_count = slide_count
        self.duration = duration_secs
        self.presenter_segments = [
            t for t in transcript if t.get("speaker") == "presenter"
        ]

    def calculate_all_scores(self) -> dict:
        """Calculate all scoring dimensions and overall score."""
        clarity = self._score_clarity()
        confidence = self._score_confidence()
        data_support = self._score_data_support()
        handling = self._score_handling()
        structure = self._score_structure()

        overall = int(
            clarity * 0.20
            + confidence * 0.20
            + data_support * 0.20
            + handling * 0.25
            + structure * 0.15
        )

        return {
            "overall": max(0, min(100, overall)),
            "clarity": max(0, min(100, clarity)),
            "confidence": max(0, min(100, confidence)),
            "data_support": max(0, min(100, data_support)),
            "handling": max(0, min(100, handling)),
            "structure": max(0, min(100, structure)),
        }

    def _score_clarity(self) -> int:
        """Score 0-100 based on filler word frequency and sentence complexity."""
        full_text = " ".join(s.get("text", "") for s in self.presenter_segments).lower()
        words = full_text.split()
        word_count = len(words)

        if word_count < 10:
            return 65  # Not enough data

        # Filler word penalty
        filler_count = sum(full_text.count(f) for f in FILLER_WORDS)
        filler_ratio = filler_count / max(word_count, 1)
        filler_score = max(0, 100 - int(filler_ratio * 500))

        # Sentence complexity (optimal is 10-20 words per sentence)
        sentences = re.split(r'[.!?]+', full_text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if sentences:
            avg_length = sum(len(s.split()) for s in sentences) / len(sentences)
            length_score = 100 - int(abs(avg_length - 15) * 4)
            length_score = max(0, min(100, length_score))
        else:
            length_score = 70

        return int(filler_score * 0.6 + length_score * 0.4)

    def _score_confidence(self) -> int:
        """Score based on hedging language frequency and response latency."""
        full_text = " ".join(s.get("text", "") for s in self.presenter_segments).lower()
        words = full_text.split()
        word_count = len(words)

        if word_count < 10:
            return 65

        # Hedging language penalty
        hedge_count = sum(full_text.count(h) for h in HEDGING_PHRASES)
        hedge_ratio = hedge_count / max(word_count, 1)
        hedge_score = max(0, 100 - int(hedge_ratio * 800))

        # Response latency after agent questions
        latency_scores = []
        for q in self.agent_questions:
            q_end = q.get("end_time", 0)
            responses = [
                t for t in self.presenter_segments
                if t.get("start_time", 0) > q_end
            ]
            if responses:
                latency = responses[0]["start_time"] - q_end
                if latency < 2:
                    latency_scores.append(100)
                elif latency < 5:
                    latency_scores.append(75)
                elif latency < 10:
                    latency_scores.append(50)
                else:
                    latency_scores.append(max(0, 100 - int(latency * 5)))

        avg_latency_score = (
            sum(latency_scores) / len(latency_scores) if latency_scores else 70
        )

        return int(hedge_score * 0.5 + avg_latency_score * 0.5)

    def _score_data_support(self) -> int:
        """Score based on presence of numbers, percentages, evidence."""
        full_text = " ".join(s.get("text", "") for s in self.presenter_segments)
        words = full_text.split()
        word_count = len(words)

        if word_count < 10:
            return 65

        # Count data references
        number_matches = re.findall(
            r'\d+[%$BbMmKk]|\$[\d,.]+|\d+\.\d+|\d{2,}', full_text
        )
        data_density = len(number_matches) / max(word_count, 1)

        # Score: 50 base + bonus for data density
        score = min(100, int(50 + data_density * 3000))
        return score

    def _score_handling(self) -> int:
        """Score based on Q&A response quality."""
        if not self.agent_questions:
            return 70  # No questions asked = neutral

        addressed_count = 0
        directness_scores = []

        for q in self.agent_questions:
            q_end = q.get("end_time", 0)
            # Find responses within 60 seconds of the question
            responses = [
                t for t in self.presenter_segments
                if q_end < t.get("start_time", 0) < q_end + 60
            ]
            if responses:
                addressed_count += 1
                first_response = responses[0].get("text", "").lower().strip()
                if any(first_response.startswith(h) for h in HEDGING_PHRASES):
                    directness_scores.append(60)
                else:
                    directness_scores.append(90)

        addressed_ratio = addressed_count / len(self.agent_questions)
        avg_directness = (
            sum(directness_scores) / len(directness_scores)
            if directness_scores
            else 70
        )

        return int(addressed_ratio * 50 + avg_directness * 0.5)

    def _score_structure(self) -> int:
        """Score based on time distribution across slides."""
        if self.slide_count <= 1:
            return 70

        # Calculate time per slide
        slide_times: dict[int, float] = {}
        for seg in self.presenter_segments:
            si = seg.get("slide_index", 0)
            duration = seg.get("end_time", 0) - seg.get("start_time", 0)
            slide_times[si] = slide_times.get(si, 0) + duration

        if not slide_times:
            return 60

        times = list(slide_times.values())
        avg_time = sum(times) / len(times)
        if avg_time == 0:
            return 60

        # Coefficient of variation (lower = more even distribution)
        variance = sum((t - avg_time) ** 2 for t in times) / len(times)
        cv = (variance ** 0.5) / max(avg_time, 0.1)
        distribution_score = max(0, 100 - int(cv * 80))

        return distribution_score
