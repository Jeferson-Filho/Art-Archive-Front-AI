# Prompt Engineering — Art Archive AI

**Versão:** 1.0
**Data:** 2026-07-03
**Status:** Em revisão — prompts base sujeitos a refinamento iterativo
**Documentos base:** [01 — Visão e Escopo](./01-visao-escopo.md), [02 — Requisitos](./02-requisitos.md), [04 — Arquitetura do Sistema](./04-arquitetura.md), [05 — Banco de Dados](./05-banco-de-dados.md), [06 — Fluxo de Persistência](./06-fluxo-persistencia.md), [09 — Pipeline de IA](./09-pipeline-ia.md)

---

## 1. Objetivo

O doc 09 especificou **como** o pipeline monta e envia o prompt (estrutura em duas mensagens, saída estruturada via JSON Schema, etapas de validação). Este documento especifica **o texto** desse prompt — a versão inicial (`v1`) usada para desenvolvimento — e a estratégia de versionamento, teste e evolução que orientará os refinamentos futuros.

**Este é um documento vivo por natureza:** os prompts abaixo são o ponto de partida. Espera-se que sejam ajustados conforme o autor observar a qualidade real das gerações (doc 14 — Avaliação de Qualidade do Conteúdo Gerado). A Seção 6 define exatamente como registrar essa evolução.

---

## 2. Por que os prompts são escritos em inglês

Os prompts e o conteúdo gerado são em inglês, não em português, pelos seguintes motivos:

- A Harvard Art Museums API retorna metadados predominantemente em inglês (título, técnica, período, cultura) — instruir o modelo em português exigiria tradução implícita dos metadados, aumentando o risco de imprecisão.
- O doc 01 (§8, premissa 6) já assume que "conteúdo gerado em inglês é aceitável" nesta fase do projeto.
- LLMs multimodais como o usado no Azure OpenAI têm desempenho mais consistente quando instrução, contexto e saída esperada estão no mesmo idioma.

---

## 3. Estrutura do Prompt v1

Conforme o doc 09 (§5), o prompt é composto por uma mensagem de sistema e uma mensagem de usuário (texto + imagem), com saída forçada por JSON Schema.

### 3.1 Mensagem de Sistema (`system`)

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

### 3.2 Mensagem de Usuário (`user`) — Template

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

A imagem é anexada como um segundo bloco de conteúdo na mesma mensagem (`image_url`), não como texto — ver payload completo na Seção 4.

### 3.3 JSON Schema de Saída

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

Este schema corresponde exatamente ao contrato de saída `GeneratedContent` definido no doc 09 (§9).

---

## 4. Exemplo de Payload Completo (Azure OpenAI Chat Completions)

```json
{
  "model": "gpt-4o",
  "temperature": 0.35,
  "max_tokens": 900,
  "response_format": {
    "type": "json_schema",
    "json_schema": { "...": "ver Seção 3.3" }
  },
  "messages": [
    { "role": "system", "content": "<mensagem de sistema — Seção 3.1>" },
    {
      "role": "user",
      "content": [
        { "type": "text", "text": "<mensagem de usuário preenchida — Seção 3.2>" },
        { "type": "image_url", "image_url": { "url": "<image_url da obra>" } }
      ]
    }
  ]
}
```

Os valores de `temperature` e `max_tokens` replicam as recomendações já justificadas no doc 09 (§6).

---

## 5. Estratégia de Versionamento

- **Formato do identificador:** `v{N}` (inteiro incremental) — ex.: `v1`, `v2` — armazenado em `artwork_ai_content.prompt_version` (doc 05, RNF-006).
- **Regra de bump:** qualquer alteração no texto da mensagem de sistema, no template da mensagem de usuário, ou no JSON Schema de saída gera uma nova versão — mesmo mudanças pequenas de wording. Essa rigidez é intencional: o objetivo do RNF-006 é permitir correlacionar precisamente qual texto de prompt produziu qual conteúdo já persistido, para fins de auditoria de qualidade (doc 14).
- **Mudanças que NÃO exigem novo prompt_version:** ajustes de parâmetros de infraestrutura que não alteram o texto do prompt em si (ex.: troca de `max_tokens` por motivo de custo, sem mudança de instrução) — devem ser registrados apenas no changelog do código, não versionados como prompt.
- **Armazenamento no código:** cada versão do prompt vive em um arquivo próprio (ex.: `backend/app/prompts/insight_card/v1.py`, `v2.py`), nunca sobrescrita — permite que conteúdo antigo (gerado por uma versão anterior) continue rastreável mesmo após a versão ativa mudar.
- **Sem regeneração retroativa:** trocar a versão ativa do prompt não regenera automaticamente obras já processadas (consistente com a doc 05, Decisão 7 — nenhuma coluna de status "desatualizado"). Uma obra só é reprocessada manualmente, via `POST /admin/artworks/{artwork_id}/regenerate` (doc 07, §6).

---

## 6. Processo de Evolução e Refinamento

Como o autor pretende refinar os prompts iterativamente, o processo recomendado é:

1. Gerar conteúdo para um conjunto fixo de obras de teste (as mesmas 3–5 obras usadas na validação do doc 09, Fase 3 do doc 99) a cada nova versão de prompt.
2. Comparar as saídas lado a lado com a versão anterior, avaliando os critérios do doc 14 (precisão histórica, ausência de alucinação, coerência, tom adequado).
3. Registrar a nova versão na tabela da Seção 7 antes de trocá-la como versão ativa no pipeline.
4. Manter as versões anteriores no código (Seção 5) para permitir comparação retroativa a qualquer momento.

### Pontos já identificados como candidatos a refinamento futuro

- **Reforço estrutural de `comparative_analysis`:** hoje a exigência de "pelo menos duas referências" (RF-003) é apenas instrução textual, sem validação estrutural. Uma v2 poderia mudar o schema para um array de objetos (`{ "artist_or_work": string, "similarity": string }` com `minItems: 2`), tornando o requisito verificável programaticamente em vez de apenas por instrução.
- **Calibração de temperatura:** `0.35` é um ponto de partida; pode exigir ajuste para baixo se a avaliação de qualidade (doc 14) revelar alucinação, ou para cima se o texto sair repetitivo entre obras semelhantes.
- **Instrução anti-alucinação:** a regra atual ("rely on general historical and stylistic context instead of inventing specifics") é uma primeira tentativa; pode precisar de exemplos explícitos (few-shot) se a avaliação qualitativa mostrar invenção de datas ou nomes.

---

## 7. Registro de Versões

| Versão | Data       | Mudança                                                                                                                                                                     | Motivo                                      |
| ------ | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| `v1`   | 2026-07-03 | Versão inicial — prompt único gerando os três campos (`historical_context`, `comparative_analysis`, `alt_text`) em uma única chamada, com saída estruturada via JSON Schema | Primeira implementação do pipeline (doc 09) |

> Novas linhas devem ser adicionadas a esta tabela **antes** de qualquer nova versão se tornar a versão ativa no pipeline (Seção 5).

---

## 8. Rastreabilidade

| Elemento do Prompt                              | Requisitos Relacionados | Documentos Relacionados |
| ----------------------------------------------- | ----------------------- | ----------------------- |
| Instrução de `historical_context`               | RF-002                  | doc 09 (§3, §5)         |
| Instrução de `comparative_analysis`             | RF-003                  | doc 09 (§3, §5)         |
| Instrução de `alt_text` (50–300 caracteres)     | RF-007                  | doc 09 (§7)             |
| Regra "omitir campos ausentes"                  | RF-002 (cenário 2)      | doc 09 (§3)             |
| Geração conjunta dos três campos em uma chamada | RF-009                  | doc 09 (§8, decisão 4)  |
| `prompt_version`                                | RNF-006                 | doc 05 (§5.4)           |

> A matriz completa, conectando requisitos a componentes de arquitetura e casos de teste, será formalizada no documento 16 — Matriz de Rastreabilidade.
