# OpenRouter Translator Request Template

Initial OpenRouter call for the translator model. The user content should be one sanitized row from translator_input_packets.jsonl.

- Endpoint: `https://openrouter.ai/api/v1/chat/completions`
- Auth env: `OPENROUTER_API_KEY`
- Disabled by default: `True`

## Request Settings

- `model`: `OPENROUTER_TRANSLATOR_MODEL_ID`
- `temperature`: `0.4`
- `max_tokens`: `1200`

## System Message

```text
You are a CAD-QA question translator. Rewrite approved hidden CAD clues into a natural public benchmark question. Preserve all approved clues, do not add facts, do not reveal forbidden strings, and return only valid JSON matching the requested output_schema.
```

## User Message

The user message should be one full JSON object from `translator_input_packets.jsonl`.

```text
TRANSLATOR_INPUT_PACKET_JSON_GOES_HERE
```

## Critical Policy

### Must Not Send

- `gold_answer`
- `answer`
- `predicate`
- `candidate_ids_after_clause`
- `evidence_chain`
- `distractors`
- `verifier_status`

### Must Send

- `public_source_code`
- `render_request`
- `approved_clues`
- `forbidden_question_strings`
- `output_schema`

## Metadata To Store

```json
{
  "role": "question_translator",
  "packet_version": "cadqa_translator_input_mock_v0",
  "model": "OPENROUTER_TRANSLATOR_MODEL_ID",
  "temperature": 0.4,
  "attempt": 1
}
```
