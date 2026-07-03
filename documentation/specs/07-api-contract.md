# Especificação de Interface — API Contract — Art Archive AI

**Versão:** 1.0
**Data:** 2026-07-03
**Status:** Em revisão
**Documentos base:** [01 — Visão e Escopo](./01-visao-escopo.md), [02 — Requisitos](./02-requisitos.md), [04 — Arquitetura do Sistema](./04-arquitetura.md), [05 — Banco de Dados](./05-banco-de-dados.md), [06 — Fluxo de Persistência](./06-fluxo-persistencia.md)

---

## 1. Convenções Gerais

| Aspecto                    | Definição                                                                                                                                                                                   |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Base URL**               | Definida por `NEXT_PUBLIC_API_URL` no front-end (doc 04, §3) — aponta para o serviço único de backend                                                                                       |
| **Formato**                | `application/json` em todas as requisições e respostas, exceto onde indicado                                                                                                                |
| **Autenticação**           | Cookie de sessão `httpOnly` (`SESSION_COOKIE_NAME`, já usado por `src/middleware.ts`), emitido pelo endpoint de login. Endpoints que exigem autenticação retornam `401` sem o cookie válido |
| **CORS**                   | Habilitado para a origem do front-end, herdado do comportamento atual do proxy Flask (`flask-cors`)                                                                                         |
| **Formato de erro padrão** | Todo erro retorna o corpo abaixo, com o `code` específico documentado por endpoint                                                                                                          |

```json
{
  "error": {
    "code": "STRING_CODE",
    "message": "Descrição legível do erro"
  }
}
```

---

## 2. Alinhamento de Nomenclatura com Documentos Anteriores

Os docs 04 (§7) e 06 (§2) usaram, respectivamente, `{objectId}` e `{artwork_id}` como placeholders para o identificador da obra nos diagramas de sequência e fluxo. Este documento formaliza `{artwork_id}` como o nome definitivo do parâmetro de rota, por ser o nome já usado nas colunas do doc 05. Os diagramas anteriores devem ser lidos com essa equivalência.

---

## 3. Endpoints — Harvard Proxy (Herdado do MVP)

### `GET /proxy/{path}`

Repassa a requisição à Harvard Art Museums API, preservando o contrato hoje consumido pelo front-end (`proxy/object/{id}`, `proxy/object/{id}/people`, `proxy/person/`, etc. — ver doc 04, §4). Não introduz mudanças nesta expansão; documentado aqui apenas para manter o contrato de API completo em um único lugar.

- **Autenticação:** não requer
- **Query params:** repassados integralmente à Harvard API, com a chave de API anexada pelo backend (nunca pelo front-end — RNF-005)
- **Resposta:** repassa o corpo JSON da Harvard API, com os campos `info.next` e `info.prev` removidos (comportamento herdado de `proxy/proxy.py`)

| Status                  | Quando ocorre                                        |
| ----------------------- | ---------------------------------------------------- |
| 200                     | Requisição repassada com sucesso                     |
| 502 `HARVARD_API_ERROR` | A Harvard API retornou erro ou uma resposta não-JSON |

---

## 4. Endpoints — Insight Card (Persistência sob Demanda)

### `GET /artworks/{artwork_id}/insight-card`

Implementa a lógica de verificação e geração especificada no doc 06. É uma **requisição síncrona única** — o front-end exibe o estado de carregamento (RF-005) imediatamente ao disparar a requisição, no lado cliente, e aguarda a resposta (até 60s, RNF-002). Não há um segundo endpoint de polling nem WebSocket: a resposta final do próprio `GET` já contém o conteúdo, seja ele vindo do cache ou recém-gerado.

- **Autenticação:** não requer (RF-001 é acessível a qualquer visitante)
- **Path params:** `artwork_id` (integer) — ID da obra na Harvard Art Museums API

**Resposta de sucesso — 200 OK** (conteúdo em cache ou recém-gerado; ver Seção 8 sobre o caso de falha de persistência)

```json
{
  "artwork_id": 123456,
  "historical_context": "string — contextualização histórica",
  "comparative_analysis": "string — análise comparativa",
  "alt_text": "string — texto alternativo da imagem",
  "prompt_version": "v1",
  "generated_at": "2026-07-03T14:32:00Z"
}
```

> **Nota (RF-017, cenário 2):** se a geração for bem-sucedida mas a persistência no banco falhar, este endpoint ainda retorna **200** com o conteúdo gerado — a falha de persistência é registrada em log no backend e nunca exposta ao cliente (doc 06, §2, nó "Erro de banco de dados").

**Respostas de erro**

| Status | Código               | Quando ocorre                                                                                       | Referência                                          |
| ------ | -------------------- | --------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| 404    | `ARTWORK_NOT_FOUND`  | O `artwork_id` não existe na Harvard Art Museums API (verificado antes de acionar o Pipeline de IA) | Caso de borda não coberto pelo doc 06 — ver Seção 8 |
| 502    | `GENERATION_FAILED`  | O LLM respondeu com erro ou com uma resposta incompleta/malformada                                  | RF-019                                              |
| 504    | `GENERATION_TIMEOUT` | O LLM não respondeu dentro dos 60 segundos definidos pela RNF-002                                   | RF-019, RNF-002                                     |

---

## 5. Endpoints — Autenticação

Implementam do zero, sobre o PostgreSQL (doc 05), as funcionalidades de autenticação equivalentes às oferecidas pelo MVP original — login, logout, recuperação de senha e persistência de sessão (RF-014). Nenhum dado do Firebase Auth é migrado: usuários que utilizavam o Firebase precisam criar uma nova conta via `POST /auth/register`.

### `POST /auth/register`

- **Autenticação:** não requer

```json
// Request
{
  "email": "usuario@exemplo.com",
  "password": "senha-em-texto-puro",
  "name": "Nome do Usuário"
}
```

```json
// Response — 201 Created
{
  "id": "uuid",
  "email": "usuario@exemplo.com",
  "name": "Nome do Usuário"
}
```

| Status | Código                 | Quando ocorre                                    |
| ------ | ---------------------- | ------------------------------------------------ |
| 409    | `EMAIL_ALREADY_EXISTS` | Já existe um usuário com este e-mail             |
| 400    | `VALIDATION_ERROR`     | Campos ausentes ou senha fora da política mínima |

---

### `POST /auth/login`

Aceita login por e-mail/senha **ou** por Google OAuth, preservando as duas opções oferecidas no MVP original.

```json
// Request — opção 1: e-mail e senha
{ "email": "usuario@exemplo.com", "password": "senha-em-texto-puro" }
```

```json
// Request — opção 2: Google OAuth
{ "google_token": "token-emitido-pelo-google-oauth" }
```

```json
// Response — 200 OK
{
  "user": { "id": "uuid", "email": "usuario@exemplo.com", "name": "Nome do Usuário" },
  "expires_at": "2026-07-04T14:32:00Z"
}
```

A resposta também define o cookie de sessão `httpOnly` (`Set-Cookie: session=<token>; HttpOnly; Secure; SameSite=Lax`), consumido por `src/middleware.ts`. O corpo da resposta não repete o token — ele só existe no cookie.

| Status | Código                | Quando ocorre                                                          |
| ------ | --------------------- | ---------------------------------------------------------------------- |
| 401    | `INVALID_CREDENTIALS` | E-mail/senha incorretos ou token do Google inválido                    |
| 400    | `VALIDATION_ERROR`    | Corpo da requisição não contém nem par e-mail/senha nem `google_token` |

---

### `POST /auth/logout`

- **Autenticação:** requer sessão válida (cookie)
- **Request:** sem corpo — a sessão é identificada pelo cookie
- **Efeito:** marca `sessions.revoked_at = now()` para a sessão atual (doc 05, §5.2), replicando a capacidade de `revoke_refresh_tokens` do Firebase Admin SDK usada hoje

| Status             | Quando ocorre                                |
| ------------------ | -------------------------------------------- |
| 204 No Content     | Logout realizado com sucesso                 |
| 401 `UNAUTHORIZED` | Nenhuma sessão válida associada à requisição |

---

### `POST /auth/password-reset/request`

```json
// Request
{ "email": "usuario@exemplo.com" }
```

```json
// Response — 200 OK (sempre, independentemente de o e-mail existir)
{ "message": "Se o e-mail informado existir, um link de redefinição foi enviado." }
```

A resposta é sempre 200 mesmo se o e-mail não existir, para não expor quais e-mails estão cadastrados (boa prática de segurança, alinhada ao espírito da RNF-005).

---

### `POST /auth/password-reset/confirm`

```json
// Request
{ "token": "token-recebido-por-email", "new_password": "nova-senha" }
```

```json
// Response — 200 OK
{ "message": "Senha alterada com sucesso." }
```

| Status | Código                     | Quando ocorre                           |
| ------ | -------------------------- | --------------------------------------- |
| 400    | `INVALID_OR_EXPIRED_TOKEN` | Token inexistente, já usado ou expirado |

> **Pendência:** este fluxo depende de um mecanismo de armazenamento de token de redefinição com expiração, que **não existe no doc 05 atual**. Ver Seção 8.

---

### `GET /auth/session`

- **Autenticação:** requer sessão válida (cookie)
- Usado por `useUserSession` (front-end) para validar a sessão atual

```json
// Response — 200 OK
{
  "user": { "id": "uuid", "email": "usuario@exemplo.com", "name": "Nome do Usuário" },
  "expires_at": "2026-07-04T14:32:00Z"
}
```

| Status | Código         | Quando ocorre                        |
| ------ | -------------- | ------------------------------------ |
| 401    | `UNAUTHORIZED` | Sessão ausente, expirada ou revogada |

---

## 6. Endpoints — Administração

Suportam o painel administrativo descrito no doc 04 (§4, módulo Admin) e no doc 99 (Bloco 7). **Todos exigem sessão de usuário com privilégio administrativo** — ver pendência na Seção 8.

### `GET /admin/artworks`

Lista as obras já processadas pelo pipeline de IA (isto é, com uma linha em `artwork_ai_content` — não existe estado "pendente" a listar, conforme Decisão 7 do doc 05).

- **Query params:** `page` (default 1), `page_size` (default 20)

```json
// Response — 200 OK
{
  "items": [
    {
      "artwork_id": 123456,
      "prompt_version": "v1",
      "created_at": "2026-07-03T14:32:00Z",
      "updated_at": "2026-07-03T14:32:00Z"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 134
}
```

### `GET /admin/artworks/{artwork_id}`

Retorna o conteúdo completo gerado para uma obra (mesmo formato do endpoint público da Seção 4).

| Status | Código                      | Quando ocorre                                 |
| ------ | --------------------------- | --------------------------------------------- |
| 404    | `ARTWORK_CONTENT_NOT_FOUND` | A obra ainda não foi processada pelo pipeline |

### `POST /admin/artworks/{artwork_id}/regenerate` _(opcional — baixa prioridade, doc 99 Fase 9)_

Força uma nova geração para uma obra já processada, sobrescrevendo o conteúdo existente. Reaproveita a lógica do doc 06, ignorando a etapa de verificação inicial.

```json
// Response — 200 OK — mesmo formato do endpoint de insight-card
```

---

## 7. Catálogo de Erros

| Código                      | Status HTTP | Endpoints onde aparece                                                                    |
| --------------------------- | ----------- | ----------------------------------------------------------------------------------------- |
| `HARVARD_API_ERROR`         | 502         | `GET /proxy/{path}`                                                                       |
| `ARTWORK_NOT_FOUND`         | 404         | `GET /artworks/{artwork_id}/insight-card`                                                 |
| `GENERATION_FAILED`         | 502         | `GET /artworks/{artwork_id}/insight-card`, `POST /admin/artworks/{artwork_id}/regenerate` |
| `GENERATION_TIMEOUT`        | 504         | `GET /artworks/{artwork_id}/insight-card`, `POST /admin/artworks/{artwork_id}/regenerate` |
| `EMAIL_ALREADY_EXISTS`      | 409         | `POST /auth/register`                                                                     |
| `VALIDATION_ERROR`          | 400         | `POST /auth/register`, `POST /auth/login`                                                 |
| `INVALID_CREDENTIALS`       | 401         | `POST /auth/login`                                                                        |
| `UNAUTHORIZED`              | 401         | `POST /auth/logout`, `GET /auth/session`, endpoints `/admin/*`                            |
| `INVALID_OR_EXPIRED_TOKEN`  | 400         | `POST /auth/password-reset/confirm`                                                       |
| `ARTWORK_CONTENT_NOT_FOUND` | 404         | `GET /admin/artworks/{artwork_id}`                                                        |
| `FORBIDDEN`                 | 403         | Endpoints `/admin/*` (sessão válida, mas sem privilégio administrativo)                   |

---

## 8. Pendências Identificadas

A elaboração deste contrato revelou três lacunas não cobertas pelos documentos anteriores:

1. **Privilégio administrativo inexistente no schema:** o doc 05 não define nenhum campo em `users` para distinguir um administrador de um visitante comum, mas os endpoints `/admin/*` precisam dessa distinção (erro `FORBIDDEN`). Solução proposta: adicionar `is_admin BOOLEAN NOT NULL DEFAULT false` à tabela `users`.
2. **Armazenamento do token de redefinição de senha inexistente:** `POST /auth/password-reset/confirm` depende de um token com expiração que não tem tabela correspondente no doc 05. Solução proposta: adicionar uma tabela `password_reset_tokens` (`id`, `user_id` FK, `token_hash`, `expires_at`, `used_at`).
3. **Obra inexistente na Harvard API:** o fluxo do doc 06 não trata explicitamente o caso de um `artwork_id` que não existe na Harvard Art Museums API — este documento adiciona esse caso como `404 ARTWORK_NOT_FOUND`, verificado antes de acionar o Pipeline de IA.

Nenhuma dessas lacunas foi corrigida nos documentos 05 ou 06 nesta tarefa — ambos precisariam de um pequeno adendo. Recomendo revisar essas três pendências antes de avançar para a implementação (doc 99, Fase 2 e Fase 8).

---

## 9. Rastreabilidade

| Endpoint                                        | Requisitos Relacionados                                                   | Casos de Uso Relacionados |
| ----------------------------------------------- | ------------------------------------------------------------------------- | ------------------------- |
| `GET /proxy/{path}`                             | — (herdado do MVP)                                                        | —                         |
| `GET /artworks/{artwork_id}/insight-card`       | RF-001, RF-002, RF-003, RF-007, RF-009, RF-016 a RF-019, RNF-001, RNF-002 | UC-01, UC-02, UC-03       |
| `POST /auth/register`                           | RF-014 (paridade funcional)                                               | —                         |
| `POST /auth/login`                              | RF-013, RF-014                                                            | UC-06                     |
| `POST /auth/logout`                             | RF-014                                                                    | UC-06                     |
| `POST /auth/password-reset/request`, `/confirm` | RF-014 (paridade funcional)                                               | —                         |
| `GET /auth/session`                             | RF-013                                                                    | UC-06                     |
| `GET/POST /admin/*`                             | — (Bloco 7 do doc 99)                                                     | —                         |

> A matriz completa, conectando requisitos a componentes de arquitetura e casos de teste, será formalizada no documento 16 — Matriz de Rastreabilidade.
