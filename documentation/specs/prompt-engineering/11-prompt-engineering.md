# Prompt Engineering — Art Archive AI

**Version:** 3.0
**Date:** 2026-07-26
**Status:** In review — base prompts subject to iterative refinement
**Base documents:** [02.1 — Insight Card](../requeriments/02.1-insight-card.md), [02.2 — Alt Text](../requeriments/02.2-alt-text.md), [02.5 — Non-Functional](../requeriments/02.5-non-functional.md), [05 — Database](../05-database.md), [06 — Persistence Flow](../06-persistence-flow.md), [09 — AI Pipeline](../09-ai-pipeline.md)
**Family documents:** [11.1 — Historical Context Prompt](./11.1-historical-context-prompt.md), [11.2 — Comparative Analysis Prompt](./11.2-comparative-analysis-prompt.md), [11.3 — Alt Text Prompt](./11.3-alt-text-prompt.md)

---

## 1. Purpose

Doc 09 specifies **how** the pipeline assembles and sends prompts (three independent calls, one per content block, each with its own structured-output schema). This document specifies the **shared conventions** that govern all three prompts — why they are written in English, the common call shape, the versioning strategy, and the evolution/refinement process — plus a **family index** pointing to the three sibling documents that each hold the exact text of one prompt.

**This is a living document family by nature:** the prompts are the starting point. They are expected to be adjusted as the author observes the actual quality of the generations (doc 14 — Quality Evaluation of Generated Content). Section 4 defines exactly how to record that evolution.

> **Change Note (2026-07-26, v3.0):** this document is split into four files, stored under `specs/prompt-engineering/`, to keep each prompt's text independently versionable and reviewable:
>
> - `11-prompt-engineering.md` (this file) — purpose, shared conventions, versioning strategy, evolution process, family-level traceability.
> - [`11.1-historical-context-prompt.md`](./11.1-historical-context-prompt.md) — system message, user template, schema, version log, and traceability for `historical_context`.
> - [`11.2-comparative-analysis-prompt.md`](./11.2-comparative-analysis-prompt.md) — same, for `comparative_analysis`.
> - [`11.3-alt-text-prompt.md`](./11.3-alt-text-prompt.md) — same, for `alt_text`.
>
> Previously (v2.0, 2026-07-26) all three prompts' full text and version logs lived in a single `11-prompt-engineering.md`. That version had itself already split the prompt **content** into three independent prompts (superseding the original single combined prompt) to align with RF-001/RF-013, but kept them physically in one file. This v3.0 change is a pure file reorganization — no prompt text, schema, or versioning rule changes as part of the split.

---

## 2. Why the prompts are written in English

The prompts and the generated content are in English, not Portuguese, for the following reasons:

- The Harvard Art Museums API returns metadata predominantly in English (title, technique, period, culture) — instructing the model in Portuguese would require implicit translation of the metadata, increasing the risk of inaccuracy.
- Doc 01 (§8, premise 6) already assumes that "content generated in English is acceptable" at this stage of the project.
- Multimodal LLMs such as the one used in Azure OpenAI perform more consistently when instruction, context, and expected output are in the same language.

This applies equally to all three prompts (docs 11.1, 11.2, 11.3).

---

## 3. Common Call Shape (Azure OpenAI Chat Completions)

All three prompts — `historical_context`, `comparative_analysis`, and `alt_text` — are sent through the same request shape:

```json
{
  "model": "gpt-4o",
  "temperature": 0.35,
  "max_tokens": "<sized per prompt — see the prompt's own document>",
  "response_format": {
    "type": "json_schema",
    "json_schema": { "...": "the prompt's own Output JSON Schema" }
  },
  "messages": [
    { "role": "system", "content": "<the prompt's own System Message>" },
    {
      "role": "user",
      "content": [
        { "type": "text", "text": "<the prompt's own filled-in User Message>" },
        { "type": "image_url", "image_url": { "url": "<image_url of the artwork>" } }
      ]
    }
  ]
}
```

What varies per prompt (system message, user template, schema, `max_tokens`) is defined in that prompt's own document (11.1 / 11.2 / 11.3, each Section 4). `temperature` is shared across all three as a starting point (Section 5).

---

## 4. Versioning Strategy

- **Independent version track per content type.** `historical_context`, `comparative_analysis`, and `alt_text` each have their own `v{N}` sequence (e.g., `historical_context v2` and `comparative_analysis v1` can coexist), stored respectively in `artwork_ai_content.historical_context_prompt_version`, `.comparative_analysis_prompt_version`, and `.alt_text_prompt_version` (doc 05, §5.4). Changing one block's prompt does not bump the other two blocks' versions.
- **Bump rule:** any change to a prompt's system message text, user message template, or output JSON Schema generates a new version for **that content type only** — even small wording changes. This rigidity is intentional: the goal of RNF-006 is to allow precisely correlating which prompt text produced which already-persisted block, for quality audit purposes (doc 14).
- **Changes that do NOT require a new prompt_version:** infrastructure parameter adjustments that do not change the prompt text itself (e.g., swapping `max_tokens` for cost reasons, with no instruction change) — these must be recorded only in the code changelog, not versioned as a prompt.
- **Storage in code:** each prompt version lives in its own file, organized by content type (e.g., `backend/app/prompts/historical_context/v1.py`, `backend/app/prompts/comparative_analysis/v1.py`, `backend/app/prompts/alt_text/v1.py`), never overwritten — this allows old content (generated by a previous version) to remain traceable even after the active version for that content type changes. This mirrors the one-document-per-content-type layout introduced in Section 1.
- **No retroactive regeneration:** switching the active prompt version for one content type does not automatically regenerate already-processed artworks' blocks for that type (consistent with doc 05, Decision 6 — no "outdated" status column). A block is only reprocessed manually, via `POST /admin/artworks/{artwork_id}/regenerate` (doc 07, §6).
- **Where the version log lives:** each prompt's own version log table (its own Section 6) is the source of truth for that content type's history. A new row must be added there **before** any new version becomes the active version in the pipeline.

---

## 5. Evolution and Refinement Process

Since the author intends to refine the prompts iteratively, the recommended process is, per content type:

1. Generate content for a fixed set of test artworks (the same 3–5 artworks used in the doc 09 validation) for each new prompt version of that content type.
2. Compare the outputs side by side with the previous version, evaluating the doc 14 criteria (historical accuracy, absence of hallucination, coherence, appropriate tone).
3. Record the new version in that content type's own document (Section 6 of doc 11.1 / 11.2 / 11.3) before switching it to the active version in the pipeline.
4. Keep previous versions in the code (Section 4 above) to allow retroactive comparison at any time.

### Cross-cutting refinement candidate

- **Temperature calibration:** `0.35` is a starting point shared by all three prompts (Section 3); it may need to be adjusted downward if the quality evaluation (doc 14) reveals hallucination, or upward if the text turns out repetitive across similar artworks. Since this parameter is shared, any change here is recorded once, in this document's own Section 6, rather than in each prompt's individual version log (per the "infrastructure parameter" rule in Section 4) — unless the recalibration also changes prompt text, in which case it is recorded per-prompt as usual.

Prompt-specific refinement candidates (e.g., structural reinforcement of `comparative_analysis`, anti-hallucination wording, source self-filtering reliability) are tracked in each prompt's own document (Section 5 of doc 11.1 / 11.2 / 11.3).

---

## 6. Version Log (this document)

| Version | Date       | Change                                                                                   | Reason                                                                          |
| ------- | ---------- | ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `2.0`   | 2026-07-26 | Split the single combined prompt into three independent prompts (content-level split)    | Align with RF-001 (independent blocks) and RF-013 (dedicated Alt Text call)     |
| `3.0`   | 2026-07-26 | Split the file itself into this core document plus 11.1 / 11.2 / 11.3 (file-level split) | Let each prompt's text and version history evolve and be reviewed independently |

> This log tracks the **document's own** revisions (purpose, conventions, strategy). Each prompt's **content** version log (`v1`, `v2`, ...) lives in its own document (Section 4 above).

---

## 7. Family Index and Traceability

| Document                                                                    | Content Type           | `prompt_version` Column (doc 05, §5.4) |
| --------------------------------------------------------------------------- | ---------------------- | -------------------------------------- |
| [11.1 — Historical Context Prompt](./11.1-historical-context-prompt.md)     | `historical_context`   | `historical_context_prompt_version`    |
| [11.2 — Comparative Analysis Prompt](./11.2-comparative-analysis-prompt.md) | `comparative_analysis` | `comparative_analysis_prompt_version`  |
| [11.3 — Alt Text Prompt](./11.3-alt-text-prompt.md)                         | `alt_text`             | `alt_text_prompt_version`              |

Shared conventions traceability:

| Convention                                                | Related Requirements | Related Documents      |
| --------------------------------------------------------- | -------------------- | ---------------------- |
| English-only prompts and generated content (Section 2)    | —                    | doc 01 (§8, premise 6) |
| Common call shape (Section 3)                             | RF-009               | doc 09 (§6)            |
| Independent `prompt_version` per content type (Section 4) | RNF-006              | doc 05 (§5.4)          |

> Per-prompt instruction-level traceability (which system-message rule maps to which requirement/scenario) lives in each prompt's own document (Section 7 of doc 11.1 / 11.2 / 11.3). The full matrix, connecting requirements to architecture components and test cases, will be formalized in document 16 — Traceability Matrix.
