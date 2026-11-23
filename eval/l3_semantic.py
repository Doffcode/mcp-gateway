"""GPU training and embedding helpers. Runtime inference lives in gateway.l3."""

from gateway.l3 import BATCH_SIZE, ENCODER, REVISION, embed, tokenize

from .split import SEED


def components(classifier=False):
    from transformers import AutoModel, AutoModelForSequenceClassification, AutoTokenizer

    model_class = AutoModelForSequenceClassification if classifier else AutoModel
    tokenizer = AutoTokenizer.from_pretrained(ENCODER, revision=REVISION)
    model = model_class.from_pretrained(ENCODER, revision=REVISION, use_safetensors=True)
    return tokenizer, model


def features(texts, device):
    import numpy as np
    import torch

    tokenizer, model = components()
    model.to(device).eval()
    batches = []
    with torch.inference_mode():
        for start in range(0, len(texts), BATCH_SIZE):
            inputs = tokenize(tokenizer, texts[start:start + BATCH_SIZE]).to(device)
            batches.append(embed(model, inputs).cpu().numpy())
    return np.concatenate(batches)


def save_encoder(output):
    tokenizer, model = components()
    model.save_pretrained(output / "encoder")
    tokenizer.save_pretrained(output / "encoder")


def finetune(texts, labels, device, epochs, validation=None, output=None):
    import numpy as np
    import torch

    torch.manual_seed(SEED)
    rng = np.random.default_rng(SEED)
    tokenizer, model = components(classifier=True)
    model.to(device).train()
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-5, fused=device == "cuda")
    weights = torch.as_tensor(len(labels) / (2 * np.bincount(labels)), dtype=torch.float32, device=device)
    loss_fn = torch.nn.CrossEntropyLoss(weight=weights)
    epoch_scores = []
    for _ in range(epochs):
        model.train()
        order = rng.permutation(len(texts))
        for start in range(0, len(order), BATCH_SIZE):
            batch = order[start:start + BATCH_SIZE]
            inputs = tokenize(tokenizer, texts[batch]).to(device)
            expected = torch.as_tensor(labels[batch], device=device)
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type="cuda", dtype=torch.bfloat16, enabled=device == "cuda"):
                loss = loss_fn(model(**inputs).logits, expected)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
        if validation is not None:
            model.eval()
            scores = []
            with torch.inference_mode():
                for start in range(0, len(validation), BATCH_SIZE):
                    batch = validation[start:start + BATCH_SIZE]
                    inputs = tokenize(tokenizer, batch).to(device)
                    scores.extend(model(**inputs).logits.softmax(-1)[:, 1].tolist())
            epoch_scores.append(scores)
    if output is not None:
        model.save_pretrained(output / "encoder")
        tokenizer.save_pretrained(output / "encoder")
    return epoch_scores
