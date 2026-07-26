# Prompt Engineering — Art Archive AI

**Version:** 1.0
**Date:** 2026-07-03
**Status:** In review — base prompts subject to iterative refinement
**Base documents:** [01 — Vision and Scope](./01-vision-scope.md), [02 — Requirements](./02-requirements.md), [04 — System Architecture](./04-architecture.md), [05 — Database](./05-database.md), [06 — Persistence Flow](./06-persistence-flow.md), [09 — AI Pipeline](./09-ai-pipeline.md)

---

## 1. Purpose

Doc 09 specified **how** the pipeline assembles and sends the prompt (two-message structure, structured output via JSON Schema, validation steps). This document specifies **the text** of that prompt — the initial version (`v1`) used for development — and the versioning, testing, and evolution strategy that will guide future refinements.

**This is a living document by nature:** the prompts below are the starting point. They are expected to be adjusted as the author observes the actual quality of the generations (doc 14 — Quality Evaluation of Generated Content). Section 6 defines exactly how to record that evolution.

---

## 2. Why the prompts are written in English

The prompts and the generated content are in English, not Portuguese, for the following reasons:

- The Harvard Art Museums API returns metadata predominantly in English (title, technique, period, culture) — instructing the model in Portuguese would require implicit translation of the metadata, increasing the risk of inaccuracy.
- Doc 01 (§8, premise 6) already assumes that "content generated in English is acceptable" at this stage of the project.
- Multimodal LLMs such as the one used in Azure OpenAI perform more consistently when instruction, context, and expected output are in the same language.

---

## 3. Structure of Prompt v1

Per doc 09 (§5), the prompt is composed of a system message and a user message (text + image), with output enforced via JSON Schema.

### 3.1 System Message (`system`)

```text
You are an expert art historian and museum curator writing for a general audience
with no prior art history background. Your goal is to make art accessible,
engaging, and educational for visitors of a digital art archive.

Given an image of an artwork and its available metadata, produce exactly three
pieces of content:

1. historical_context — A concise, engaging narrative (3 to 5 short paragraphs)
   covering the historical period, artistic movement, and cultural influences
   of the artwork and its artist(s). Include relevant biographical context about
   the artist(s) when it helps the reader understand the work. Write for a
   curious adult with no formal training in art history.

2. comparative_analysis — A narrative (2 to 4 short paragraphs) comparing this
   artwork to at least two other artists or artworks with similar palette,
   technique, or style. Be concrete about what makes them comparable (shared
   color palette, similar brushwork, same movement, thematic parallels, etc.).

3. alt_text — A descriptive, accessible alternative text for the artwork's
   image, written for screen reader users. Describe what is visually depicted:
   subjects, composition, dominant colors, and visible technique. Do not start
   with "Image of" or "Picture of". Length must be between 50 and 300 characters.

Rules:
- Base your response only on verifiable art-historical knowledge. If specific
  facts (exact dates, names, events) are not reasonably well-established, rely
  on general historical and stylistic context instead of inventing specifics.
- If some metadata fields are not provided, do not mention that they are
  missing — simply write using the information available.
- Do not repeat the raw metadata verbatim; synthesize it into fluent prose.
- Write in English.
- Respond using only the provided JSON schema. Do not include any text outside
  the structured output.
```

### 3.2 User Message (`user`) — Template

```text
Artwork metadata:
- Title: {title}
- Artist(s): {artists}
- Date: {date_display}
- Period: {period}
- Culture: {culture}
- Classification: {classification}
- Technique: {technique}
- Medium: {medium}

(Fields with no available value are omitted above — see ArtworkMetadata, doc 09 §3.)

Analyze the attached image together with this metadata and produce the three
required fields.
```

The image is attached as a second content block in the same message (`image_url`), not as text — see the full payload in Section 4.

### 3.3 Output JSON Schema

```json
{
  "name": "insight_card_content",
  "schema": {
    "type": "object",
    "properties": {
      "historical_context": { "type": "string", "minLength": 1 },
      "comparative_analysis": { "type": "string", "minLength": 1 },
      "alt_text": { "type": "string", "minLength": 50, "maxLength": 300 }
    },
    "required": ["historical_context", "comparative_analysis", "alt_text"],
    "additionalProperties": false
  }
}
```

This schema corresponds exactly to the `GeneratedContent` output contract defined in doc 09 (§9).

---

## 4. Example of a Complete Payload (Azure OpenAI Chat Completions)

```json
{
  "model": "gpt-4o",
  "temperature": 0.35,
  "max_tokens": 900,
  "response_format": {
    "type": "json_schema",
    "json_schema": { "...": "see Section 3.3" }
  },
  "messages": [
    { "role": "system", "content": "<system message — Section 3.1>" },
    {
      "role": "user",
      "content": [
        { "type": "text", "text": "<filled-in user message — Section 3.2>" },
        { "type": "image_url", "image_url": { "url": "<image_url of the artwork>" } }
      ]
    }
  ]
}
```

The `temperature` and `max_tokens` values replicate the recommendations already justified in doc 09 (§6).

---

## 5. Versioning Strategy

- **Identifier format:** `v{N}` (incremental integer) — e.g., `v1`, `v2` — stored in `artwork_ai_content.prompt_version` (doc 05, RNF-006).
- **Bump rule:** any change to the system message text, the user message template, or the output JSON Schema generates a new version — even small wording changes. This rigidity is intentional: the goal of RNF-006 is to allow precisely correlating which prompt text produced which already-persisted content, for quality audit purposes (doc 14).
- **Changes that do NOT require a new prompt_version:** infrastructure parameter adjustments that do not change the prompt text itself (e.g., swapping `max_tokens` for cost reasons, with no instruction change) — these must be recorded only in the code changelog, not versioned as a prompt.
- **Storage in code:** each prompt version lives in its own file (e.g., `backend/app/prompts/insight_card/v1.py`, `v2.py`), never overwritten — this allows old content (generated by a previous version) to remain traceable even after the active version changes.
- **No retroactive regeneration:** switching the active prompt version does not automatically regenerate already-processed artworks (consistent with doc 05, Decision 7 — no "outdated" status column). An artwork is only reprocessed manually, via `POST /admin/artworks/{artwork_id}/regenerate` (doc 07, §6).

---

## 6. Evolution and Refinement Process

Since the author intends to refine the prompts iteratively, the recommended process is:

1. Generate content for a fixed set of test artworks (the same 3–5 artworks used in the doc 09 validation, Phase 3 of doc 99) for each new prompt version.
2. Compare the outputs side by side with the previous version, evaluating the doc 14 criteria (historical accuracy, absence of hallucination, coherence, appropriate tone).
3. Record the new version in the Section 7 table before switching it to the active version in the pipeline.
4. Keep previous versions in the code (Section 5) to allow retroactive comparison at any time.

### Points already identified as candidates for future refinement

- **Structural reinforcement of `comparative_analysis`:** today the requirement of "at least two references" (RF-003) is only a textual instruction, with no structural validation. A v2 could change the schema to an array of objects (`{ "artist_or_work": string, "similarity": string }` with `minItems: 2`), making the requirement programmatically verifiable instead of only instruction-based.
- **Temperature calibration:** `0.35` is a starting point; it may need to be adjusted downward if the quality evaluation (doc 14) reveals hallucination, or upward if the text turns out repetitive across similar artworks.
- **Anti-hallucination instruction:** the current rule ("rely on general historical and stylistic context instead of inventing specifics") is a first attempt; it may need explicit examples (few-shot) if the qualitative evaluation shows invented dates or names.

---

## 7. Version Log

| Version | Date       | Change                                                                                                                                                                            | Reason                                        |
| ------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------- |
| `v1`    | 2026-07-03 | Initial version — a single prompt generating the three fields (`historical_context`, `comparative_analysis`, `alt_text`) in a single call, with structured output via JSON Schema | First implementation of the pipeline (doc 09) |

> New rows must be added to this table **before** any new version becomes the active version in the pipeline (Section 5).

---

## 8. Traceability

| Prompt Element                                   | Related Requirements | Related Documents       |
| ------------------------------------------------ | -------------------- | ----------------------- |
| `historical_context` instruction                 | RF-002               | doc 09 (§3, §5)         |
| `comparative_analysis` instruction               | RF-003               | doc 09 (§3, §5)         |
| `alt_text` instruction (50–300 characters)       | RF-007               | doc 09 (§7)             |
| "Omit missing fields" rule                       | RF-002 (scenario 2)  | doc 09 (§3)             |
| Joint generation of the three fields in one call | RF-009               | doc 09 (§8, decision 4) |
| `prompt_version`                                 | RNF-006              | doc 05 (§5.4)           |

> The full matrix, connecting requirements to architecture components and test cases, will be formalized in document 16 — Traceability Matrix.
