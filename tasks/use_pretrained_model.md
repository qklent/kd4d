# Task: Replace base BERT with pretrained NER model

## Original Request

right now it uses some bert model and i think that i can't completely debug my app with this model since it wasn't done for a ner. So can you please change this model to some small pretrained ner model. I would train my own model later and replace it.

---

## Refined Spec

### Problem
The current NER detector uses `ai-forever/ruBert-base`, a general-purpose BERT model that was never fine-tuned for NER. It produces meaningless entity predictions, making it impossible to debug the full masking pipeline end-to-end.

### Solution
Replace with `dslim/bert-base-NER`, a pretrained NER model (English, CoNLL-2003), served via Triton with ONNX runtime on CPU. This is a temporary debugging model — the user will train and swap in their own model later.

### Key Decisions
- **Model**: `dslim/bert-base-NER` (HuggingFace) — small, pretrained NER, ~430MB
- **Serving**: Triton Inference Server via ONNX export (keep existing Triton architecture)
- **Triton model name**: New name (e.g., `bert_base_ner`) — distinct from old `rubert_ner`
- **Entity types**: Use the model's default labels (CoNLL-2003: PER, LOC, ORG, MISC) — map to proxy's internal types
- **Inference device**: CPU (update Triton config from GPU to CPU instance group)

### Changes Required

1. **Export `dslim/bert-base-NER` to ONNX**
   - Write/update an export script that downloads the model from HuggingFace and exports to ONNX format
   - Place the `.onnx` file in the Triton model repo under `bert_base_ner/1/`

2. **New Triton model config** (`triton_model_repo/bert_base_ner/config.pbtxt`)
   - Platform: `onnxruntime_onnx`
   - Inputs: `input_ids`, `attention_mask`, `token_type_ids` (INT64)
   - Outputs: `logits` (FP32) — output shape matches `dslim/bert-base-NER` label count (9 labels: O, B-PER, I-PER, B-LOC, I-LOC, B-ORG, I-ORG, B-MISC, I-MISC)
   - Instance group: CPU
   - Max batch size: 8

3. **Update `app/config.py`**
   - Change `triton_model_name` default to `"bert_base_ner"`
   - Change `triton_tokenizer_name` default to `"dslim/bert-base-NER"`

4. **Update label map in `app/main.py`**
   - Replace 7-class label map with 9-class map matching `dslim/bert-base-NER` output (adds B-MISC, I-MISC)

5. **Update `app/detection/triton_ner.py`**
   - Update entity type mapping to handle MISC label (map to a reasonable internal type or keep as-is)
   - Ensure `_decode_bio` works with the new label set

6. **Update `docker-compose.yml`**
   - Change Triton instance to CPU mode (remove `--gpus` if present, or adjust deploy config)

7. **Update old Triton model repo**
   - Remove or rename `triton_model_repo/rubert_ner/` to avoid confusion

---

## Acceptance Criteria

- [ ] `dslim/bert-base-NER` exported to ONNX and placed in `triton_model_repo/bert_base_ner/1/`
- [ ] Triton config (`config.pbtxt`) uses CPU instance group and correct input/output shapes for 9 labels
- [ ] `app/config.py` defaults updated to new model/tokenizer names
- [ ] Label map in `app/main.py` updated to 9 classes (O, B/I-PER, B/I-LOC, B/I-ORG, B/I-MISC)
- [ ] `triton_ner.py` entity type mapping handles MISC entities
- [ ] `docker-compose.yml` runs Triton on CPU
- [ ] Old `rubert_ner` model directory removed or clearly deprecated
- [ ] App starts successfully with `docker-compose up` and NER detector connects to Triton
- [ ] Sending a request with English names/locations produces NER detections (end-to-end smoke test)
- [ ] Existing tests pass (`pytest tests/`)

## Files Likely Modified/Created

| File | Action |
|---|---|
| `triton_model_repo/bert_base_ner/config.pbtxt` | Create |
| `triton_model_repo/bert_base_ner/1/model.onnx` | Create (via export script) |
| `scripts/export_onnx.py` (or similar) | Create |
| `pii_proxy/app/config.py` | Modify |
| `pii_proxy/app/main.py` | Modify (label map) |
| `pii_proxy/app/detection/triton_ner.py` | Modify (entity mapping) |
| `pii_proxy/docker-compose.yml` | Modify (CPU mode) |
| `triton_model_repo/rubert_ner/` | Remove |

## Test Scenarios

1. **ONNX export** — export script runs without errors and produces a valid `.onnx` file
2. **Triton startup** — Triton loads the new model successfully (check `is_server_ready()` and `is_model_ready("bert_base_ner")`)
3. **NER detection on English text** — input like `"John Smith lives in New York"` returns PER and LOC spans
4. **Label mapping** — all 9 labels correctly decoded; MISC entities handled gracefully
5. **Confidence filtering** — spans below `ner_confidence_threshold` are filtered out
6. **Pipeline integration** — regex + NER detectors still run in parallel, merger resolves overlaps correctly
7. **End-to-end masking** — a chat completion request with PII produces masked output with `[PERSON_1]`-style placeholders
8. **Fallback** — if Triton is unavailable, app falls back to regex-only (existing behavior preserved)
