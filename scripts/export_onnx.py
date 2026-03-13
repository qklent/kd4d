"""Export dslim/bert-base-NER to ONNX for Triton Inference Server.

Usage:
    python scripts/export_onnx.py [--output-dir PATH]

The exported model is placed at:
    <output-dir>/bert_base_ner/1/model.onnx

Requirements:
    pip install transformers torch optimum[exporters]
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

MODEL_NAME = "dslim/bert-base-NER"
TRITON_MODEL_NAME = "bert_base_ner"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export dslim/bert-base-NER to ONNX for Triton"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent.parent / "pii_proxy" / "triton_model_repo",
        help="Directory containing Triton model repository (default: pii_proxy/triton_model_repo)",
    )
    return parser.parse_args()


def export_to_onnx(output_dir: Path) -> Path:
    """Download dslim/bert-base-NER from HuggingFace and export to ONNX.

    Args:
        output_dir: Path to Triton model repository root.

    Returns:
        Path to the exported model.onnx file.
    """
    try:
        import torch
        from transformers import AutoModelForTokenClassification, AutoTokenizer
    except ImportError as exc:
        logger.error(
            "Required packages not installed. Run: pip install torch transformers",
            exc_info=True,
        )
        raise SystemExit(1) from exc

    onnx_dir = output_dir / TRITON_MODEL_NAME / "1"
    onnx_dir.mkdir(parents=True, exist_ok=True)
    onnx_path = onnx_dir / "model.onnx"

    if onnx_path.exists():
        logger.info("ONNX model already exists at %s — skipping export", onnx_path)
        return onnx_path

    logger.info("Downloading model %s from HuggingFace...", MODEL_NAME)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForTokenClassification.from_pretrained(MODEL_NAME)
    model.eval()

    logger.info("Model loaded. Label count: %d", model.config.num_labels)
    logger.info("Labels: %s", model.config.id2label)

    # Create a dummy input for tracing (sequence length 16)
    dummy_text = "John Smith works at Acme Corp in New York."
    encoding = tokenizer(
        dummy_text,
        return_tensors="pt",
        truncation=True,
        max_length=512,
    )
    input_ids = encoding["input_ids"]
    attention_mask = encoding["attention_mask"]
    token_type_ids = encoding.get(
        "token_type_ids",
        torch.zeros_like(input_ids),
    )

    logger.info("Exporting model to ONNX at %s...", onnx_path)
    with torch.no_grad():
        torch.onnx.export(
            model,
            (input_ids, attention_mask, token_type_ids),
            str(onnx_path),
            input_names=["input_ids", "attention_mask", "token_type_ids"],
            output_names=["logits"],
            dynamic_axes={
                "input_ids": {0: "batch_size", 1: "sequence_length"},
                "attention_mask": {0: "batch_size", 1: "sequence_length"},
                "token_type_ids": {0: "batch_size", 1: "sequence_length"},
                "logits": {0: "batch_size", 1: "sequence_length"},
            },
            opset_version=14,
            do_constant_folding=True,
        )

    logger.info("ONNX export completed. File size: %.1f MB", onnx_path.stat().st_size / 1e6)
    _validate_onnx(onnx_path)
    return onnx_path


def _validate_onnx(onnx_path: Path) -> None:
    """Run a basic ONNX model check if onnx package is available."""
    try:
        import onnx

        model = onnx.load(str(onnx_path))
        onnx.checker.check_model(model)
        logger.info("ONNX model validation passed.")
    except ImportError:
        logger.warning(
            "onnx package not installed — skipping model validation. "
            "Install with: pip install onnx"
        )
    except Exception as exc:
        logger.error("ONNX model validation failed: %s", exc, exc_info=True)
        raise


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    logger.info("Triton model repository: %s", output_dir)

    onnx_path = export_to_onnx(output_dir)

    logger.info("=" * 60)
    logger.info("Export successful!")
    logger.info("Model path : %s", onnx_path)
    logger.info(
        "Config path: %s",
        output_dir / TRITON_MODEL_NAME / "config.pbtxt",
    )
    logger.info(
        "\nStart Triton with:\n"
        "  docker compose -f pii_proxy/docker-compose.yml up triton"
    )


if __name__ == "__main__":
    main()
