from __future__ import annotations

import logging

import numpy as np

from .base import PIISpan

logger = logging.getLogger(__name__)

# Maps NER entity types from CoNLL-2003 labels to internal proxy types.
# MISC covers miscellaneous named entities (e.g. nationalities, products, events).
_ENTITY_TYPE_MAP: dict[str, str] = {
    "PER": "PERSON",
    "LOC": "ADDRESS",
    "ORG": "ORG",
    "MISC": "MISC",
}


class TritonNERDetector:
    def __init__(
        self,
        triton_url: str,
        model_name: str,
        tokenizer_name: str,
        label_map: dict[int, str],
        confidence_threshold: float = 0.7,
    ):
        import tritonclient.grpc.aio as grpcclient
        from transformers import AutoTokenizer

        logger.info(
            "Initializing TritonNERDetector: url=%s model=%s tokenizer=%s threshold=%.2f",
            triton_url,
            model_name,
            tokenizer_name,
            confidence_threshold,
        )
        self.client = grpcclient.InferenceServerClient(url=triton_url)
        self._grpcclient = grpcclient
        self.model_name = model_name
        self.label_map = label_map
        self.threshold = confidence_threshold

        logger.info("Loading tokenizer %s...", tokenizer_name)
        self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
        logger.info(
            "TritonNERDetector initialized. Label map: %s",
            {v: k for k, v in label_map.items()},
        )

    async def detect(self, text: str) -> list[PIISpan]:
        logger.debug("Running NER detection on text of length %d", len(text))

        encoding = self.tokenizer(
            text,
            return_tensors="np",
            truncation=True,
            max_length=512,
            return_offsets_mapping=True,
        )
        offsets = encoding.pop("offset_mapping")[0]

        inputs = []
        for name in ("input_ids", "attention_mask", "token_type_ids"):
            arr = encoding[name].astype(np.int64)
            inp = self._grpcclient.InferInput(name, arr.shape, "INT64")
            inp.set_data_from_numpy(arr)
            inputs.append(inp)

        outputs = [self._grpcclient.InferRequestedOutput("logits")]

        logger.debug(
            "Sending inference request to Triton: model=%s tokens=%d",
            self.model_name,
            encoding["input_ids"].shape[1],
        )
        result = await self.client.infer(
            model_name=self.model_name,
            inputs=inputs,
            outputs=outputs,
        )
        logits = result.as_numpy("logits")[0]
        logger.debug("Received logits from Triton: shape=%s", logits.shape)

        spans = self._decode_bio(logits, offsets, text)
        logger.debug(
            "NER detected %d spans (above threshold %.2f)", len(spans), self.threshold
        )
        return spans

    def _decode_bio(
        self, logits: np.ndarray, offsets: np.ndarray, text: str
    ) -> list[PIISpan]:
        from scipy.special import softmax

        probs = softmax(logits, axis=-1)
        pred_ids = probs.argmax(axis=-1)
        confidences = probs.max(axis=-1)

        spans: list[PIISpan] = []
        current: tuple[int, int, str, list[float]] | None = None

        for idx, (pred_id, conf) in enumerate(zip(pred_ids, confidences)):
            label = self.label_map.get(int(pred_id), "O")
            char_start, char_end = int(offsets[idx][0]), int(offsets[idx][1])

            # Skip special tokens ([CLS], [SEP], padding)
            if char_start == char_end:
                continue

            if label.startswith("B-"):
                if current:
                    spans.append(self._make_span(current, text))
                etype = label[2:]
                current = (char_start, char_end, etype, [float(conf)])

            elif label.startswith("I-") and current and label[2:] == current[2]:
                current = (current[0], char_end, current[2], current[3] + [float(conf)])

            else:
                if current:
                    spans.append(self._make_span(current, text))
                    current = None

        if current:
            spans.append(self._make_span(current, text))

        filtered = [s for s in spans if s.confidence >= self.threshold]
        logger.debug(
            "BIO decode: %d raw spans → %d after threshold %.2f",
            len(spans),
            len(filtered),
            self.threshold,
        )
        return filtered

    @staticmethod
    def _make_span(current: tuple[int, int, str, list[float]], text: str) -> PIISpan:
        start, end, etype, confs = current
        internal_type = _ENTITY_TYPE_MAP.get(etype, etype)
        span = PIISpan(
            start=start,
            end=end,
            entity_type=internal_type,
            text=text[start:end],
            confidence=float(np.mean(confs)),
            source="ner",
        )
        logger.debug(
            "Span: [%d:%d] %r → type=%s conf=%.3f",
            start,
            end,
            span.text,
            internal_type,
            span.confidence,
        )
        return span
