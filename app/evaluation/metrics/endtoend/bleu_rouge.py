from app.evaluation.base import BaseMetric


class BleuRouge(BaseMetric):
    """Computes BLEU and ROUGE-L scores between answer and ground truth."""

    name = "bleu_rouge"

    async def compute(
        self,
        query: str,
        answer: str,
        contexts: list[str],
        ground_truth: str | None = None,
    ) -> dict[str, float]:
        if not ground_truth or not answer:
            return {"bleu": 0.0, "rouge_l": 0.0}
        try:
            from rouge_score import rouge_scorer

            scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)
            rouge_scores = scorer.score(ground_truth, answer)
            rouge_l = rouge_scores["rougeL"].fmeasure
        except Exception:
            rouge_l = 0.0

        # Simple BLEU-1 approximation (unigram overlap)
        gt_tokens = ground_truth.lower().split()
        ans_tokens = answer.lower().split()
        if not ans_tokens or not gt_tokens:
            bleu = 0.0
        else:
            matches = sum(1 for t in ans_tokens if t in gt_tokens)
            bleu = matches / len(ans_tokens)

        return {"bleu": bleu, "rouge_l": rouge_l}
