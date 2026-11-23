"""Load and apply a locally trained L3 metadata screen."""

import json
from pathlib import Path

from .canonical import tool_view

ENCODER = "intfloat/e5-base-v2"
REVISION = "f52bf8ec8c7124536f0efb74aca902b2995e5bcd"
MAX_TOKENS = 512
BATCH_SIZE = 8


def metadata_text(tool, siblings=(), *, use_context=False, description_only=False):
    view = tool_view(tool)
    schema = json.dumps(view["inputSchema"], sort_keys=True, ensure_ascii=False)
    text = f"Name: {view['name']}\nDescription: {view['description']}"
    if not description_only:
        text += f"\nSchema: {schema}"
    if use_context:
        names = sorted({tool_view(sibling)["name"] for sibling in siblings} - {view["name"]})
        context = json.dumps([name[:80] for name in names[:12]], ensure_ascii=False)
        text = f"Related tools: {context}\n{text}"
    return text


def tokenize(tokenizer, texts):
    return tokenizer(
        ["query: " + text for text in texts],
        max_length=MAX_TOKENS,
        padding=True,
        truncation=True,
        return_tensors="pt",
    )


def embed(encoder, inputs):
    import torch.nn.functional as F

    hidden = encoder(**inputs).last_hidden_state
    mask = inputs["attention_mask"].unsqueeze(-1)
    return F.normalize((hidden * mask).sum(1) / mask.sum(1).clamp(min=1), dim=-1)


class Scorer:
    """Screen tools using an artifact produced by eval.train_l3."""

    def __init__(self, path, device="cpu"):
        import joblib

        path = Path(path)
        self.manifest = json.loads((path / "manifest.json").read_text())
        self.kind = self.manifest["model"]
        if self.kind not in {"tfidf", "frozen_e5", "finetuned_e5"}:
            raise ValueError(f"Unknown L3 model type: {self.kind}")
        self.threshold = self.manifest["threshold"]
        self.use_context = self.manifest["context"]
        self.description_only = self.manifest.get("description_only", False)
        self.device = device
        if self.kind == "tfidf":
            self.model = joblib.load(path / "classifier.joblib")
        else:
            from transformers import AutoModel, AutoModelForSequenceClassification, AutoTokenizer

            self.tokenizer = AutoTokenizer.from_pretrained(path / "encoder", local_files_only=True)
            model_class = AutoModelForSequenceClassification if self.kind == "finetuned_e5" else AutoModel
            self.encoder = model_class.from_pretrained(path / "encoder", local_files_only=True).to(device).eval()
            if self.kind == "frozen_e5":
                self.model = joblib.load(path / "classifier.joblib")

    def probabilities(self, texts):
        if not texts:
            return []
        if self.kind == "tfidf":
            return self.model.predict_proba(texts)[:, 1].tolist()

        import torch

        scores = []
        with torch.inference_mode():
            for start in range(0, len(texts), BATCH_SIZE):
                inputs = tokenize(self.tokenizer, texts[start:start + BATCH_SIZE]).to(self.device)
                if self.kind == "finetuned_e5":
                    scores.extend(self.encoder(**inputs).logits.softmax(-1)[:, 1].tolist())
                else:
                    features = embed(self.encoder, inputs).cpu().numpy()
                    scores.extend(self.model.predict_proba(features)[:, 1].tolist())
        return scores

    def score_listing(self, tools):
        tools = list(tools)
        texts = [metadata_text(tool, tools, use_context=self.use_context, description_only=self.description_only)
                 for tool in tools]
        return [
            {"tool": tool_view(tool)["name"], "score": score, "threshold": self.threshold,
             "verdict": "flagged" if score >= self.threshold else "below_threshold"}
            for tool, score in zip(tools, self.probabilities(texts), strict=True)
        ]
