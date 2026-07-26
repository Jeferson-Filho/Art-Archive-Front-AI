# Interface Specification — API Contract — Art Archive AI

**Version:** 1.0
**Date:** 2026-07-03
**Status:** In Review
**Base Documents:** [01 — Vision and Scope](./01-vision-scope.md), [02 — Requirements](./02-requirements.md), [04 — System Architecture](./04-architecture.md), [05 — Database](./05-database.md), [06 — Persistence Flow](./06-persistence-flow.md)

---

## 1. General Conventions

| Aspect                    | Definition                                                                                                                                                                                      |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Base URL**              | Defined by `NEXT_PUBLIC_API_URL` in the front-end (doc 04, §3) — points to the single backend service                                                                                           |
| **Format**                | `application/json` in all requests and responses, except where indicated                                                                                                                        |
| **Authentication**        | `httpOnly` session cookie (`SESSION_COOKIE_NAME`, already used by `src/middleware.ts`), issued by the login endpoint. Endpoints that require authentication return `401` without a valid cookie |
| **CORS**                  | Enabled for the front-end origin, inherited from the current behavior of the Flask proxy (`flask-cors`)                                                                                         |
| **Standard error format** | Every error returns the body below, with the specific `code` documented per endpoint                                                                                                            |

```json
{
  "error": {
    "code": "STRING_CODE",
    "message": "Human-readable error description"
  }
}
```

---

## 2. Naming Alignment with Previous Documents

Docs 04 (§7) and 06 (§2) used, respectively, `{objectId}` and `{artwork_id}` as placeholders for the artwork identifier in the sequence and flow diagrams. This document formalizes `{artwork_id}` as the definitive name of the route parameter, since it is the name already used for the columns in doc 05. The previous diagrams should be read with this equivalence in mind.

---

## 3. Endpoints — Harvard Proxy (Inherited from the MVP)

### `GET /proxy/{path}`

Forwards the request to the Harvard Art Museums API, preserving the contract currently consumed by the front-end (`proxy/object/{id}`, `proxy/object/{id}/people`, `proxy/person/`, etc. — see doc 04, §4). It introduces no changes in this expansion; documented here only to keep the complete API contract in a single place.

- **Authentication:** not required
- **Query params:** forwarded in full to the Harvard API, with the API key attached by the backend (never by the front-end — RNF-005)
- **Response:** forwards the Harvard API's JSON body, with the `info.next` and `info.prev` fields removed (behavior inherited from `proxy/proxy.py`)

| Status                  | When it occurs                                           |
| ----------------------- | -------------------------------------------------------- |
| 200                     | Request forwarded successfully                           |
| 502 `HARVARD_API_ERROR` | The Harvard API returned an error or a non-JSON response |

---

## 4. Endpoints — Insight Card (Persistence on Demand)

### `GET /artworks/{artwork_id}/insight-card`

Implements the verification and generation logic specified in doc 06. It is a **single synchronous request** — the front-end displays the loading state (RF-005) immediately upon firing the request, on the client side, and waits for the response (up to 60s, RNF-002). There is no second polling endpoint or WebSocket: the final response of the `GET` itself already contains the content, whether it comes from the cache or was just generated.

- **Authentication:** not required (RF-001 is accessible to any visitor)
- **Path params:** `artwork_id` (integer) — the artwork's ID in the Harvard Art Museums API

**Success response — 200 OK** (cached or newly generated content; see Section 8 for the persistence failure case)

```json
{
  "artwork_id": 123456,
  "historical_context": "string — historical contextualization",
  "comparative_analysis": "string — comparative analysis",
  "alt_text": "string — image alternative text",
  "prompt_version": "v1",
  "generated_at": "2026-07-03T14:32:00Z"
}
```

> **Note (RF-017, scenario 2):** if generation succeeds but persistence to the database fails, this endpoint still returns **200** with the generated content — the persistence failure is logged on the backend and never exposed to the client (doc 06, §2, node "Database error").

**Error responses**

| Status | Code                 | When it occurs                                                                                              | Reference                                       |
| ------ | -------------------- | ----------------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| 404    | `ARTWORK_NOT_FOUND`  | The `artwork_id` does not exist in the Harvard Art Museums API (verified before triggering the AI Pipeline) | Edge case not covered by doc 06 — see Section 8 |
| 502    | `GENERATION_FAILED`  | The LLM responded with an error or with an incomplete/malformed response                                    | RF-019                                          |
| 504    | `GENERATION_TIMEOUT` | The LLM did not respond within the 60 seconds defined by RNF-002                                            | RF-019, RNF-002                                 |

---

## 5. Endpoints — Authentication

These implement, from scratch, on top of PostgreSQL (doc 05), the authentication features equivalent to those offered by the original MVP — login, logout, password recovery, and session persistence (RF-014). No Firebase Auth data is migrated: users who used Firebase need to create a new account via `POST /auth/register`.

### `POST /auth/register`

- **Authentication:** not required

```json
// Request
{
  "email": "user@example.com",
  "password": "plain-text-password",
  "name": "User Name"
}
```

```json
// Response — 201 Created
{
  "id": "uuid",
  "email": "user@example.com",
  "name": "User Name"
}
```

| Status | Code                   | When it occurs                                        |
| ------ | ---------------------- | ----------------------------------------------------- |
| 409    | `EMAIL_ALREADY_EXISTS` | A user with this email already exists                 |
| 400    | `VALIDATION_ERROR`     | Missing fields or password outside the minimum policy |

---

### `POST /auth/login`

Accepts login via email/password **or** via Google OAuth, preserving the two options offered by the original MVP.

```json
// Request — option 1: email and password
{ "email": "user@example.com", "password": "plain-text-password" }
```

```json
// Request — option 2: Google OAuth
{ "google_token": "token-issued-by-google-oauth" }
```

```json
// Response — 200 OK
{
  "user": { "id": "uuid", "email": "user@example.com", "name": "User Name" },
  "expires_at": "2026-07-04T14:32:00Z"
}
```

The response also sets the `httpOnly` session cookie (`Set-Cookie: session=<token>; HttpOnly; Secure; SameSite=Lax`), consumed by `src/middleware.ts`. The response body does not repeat the token — it only exists in the cookie.

| Status | Code                  | When it occurs                                                            |
| ------ | --------------------- | ------------------------------------------------------------------------- |
| 401    | `INVALID_CREDENTIALS` | Incorrect email/password or invalid Google token                          |
| 400    | `VALIDATION_ERROR`    | Request body contains neither an email/password pair nor a `google_token` |

---

### `POST /auth/logout`

- **Authentication:** requires a valid session (cookie)
- **Request:** no body — the session is identified by the cookie
- **Effect:** sets `sessions.revoked_at = now()` for the current session (doc 05, §5.2), replicating the capability of `revoke_refresh_tokens` from the Firebase Admin SDK used today

| Status             | When it occurs                               |
| ------------------ | -------------------------------------------- |
| 204 No Content     | Logout completed successfully                |
| 401 `UNAUTHORIZED` | No valid session associated with the request |

---

### `POST /auth/password-reset/request`

```json
// Request
{ "email": "user@example.com" }
```

```json
// Response — 200 OK (always, regardless of whether the email exists)
{ "message": "If the provided email exists, a reset link has been sent." }
```

The response is always 200 even if the email does not exist, so as not to expose which emails are registered (a security best practice, aligned with the spirit of RNF-005).

---

### `POST /auth/password-reset/confirm`

```json
// Request
{ "token": "token-received-by-email", "new_password": "new-password" }
```

```json
// Response — 200 OK
{ "message": "Password changed successfully." }
```

| Status | Code                       | When it occurs                              |
| ------ | -------------------------- | ------------------------------------------- |
| 400    | `INVALID_OR_EXPIRED_TOKEN` | Nonexistent, already-used, or expired token |

> **Pending issue:** this flow depends on a reset-token storage mechanism with expiration, which **does not exist in the current doc 05**. See Section 8.

---

### `GET /auth/session`

- **Authentication:** requires a valid session (cookie)
- Used by `useUserSession` (front-end) to validate the current session

```json
// Response — 200 OK
{
  "user": { "id": "uuid", "email": "user@example.com", "name": "User Name" },
  "expires_at": "2026-07-04T14:32:00Z"
}
```

| Status | Code           | When it occurs                       |
| ------ | -------------- | ------------------------------------ |
| 401    | `UNAUTHORIZED` | Session missing, expired, or revoked |

---

## 6. Endpoints — Administration

Support the administrative panel described in doc 04 (§4, Admin module) and in doc 99 (Block 7). **All of them require a user session with administrative privilege** — see pending issue in Section 8.

### `GET /admin/artworks`

Lists artworks already processed by the AI pipeline (that is, with a row in `artwork_ai_content` — there is no "pending" state to list, per Decision 7 of doc 05).

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

Returns the complete content generated for an artwork (same format as the public endpoint in Section 4).

| Status | Code                        | When it occurs                                         |
| ------ | --------------------------- | ------------------------------------------------------ |
| 404    | `ARTWORK_CONTENT_NOT_FOUND` | The artwork has not yet been processed by the pipeline |

### `POST /admin/artworks/{artwork_id}/regenerate` _(optional — low priority, doc 99 Phase 9)_

Forces a new generation for an artwork already processed, overwriting the existing content. Reuses the logic from doc 06, skipping the initial verification step.

```json
// Response — 200 OK — same format as the insight-card endpoint
```

---

## 7. Error Catalog

| Code                        | HTTP Status | Endpoints where it appears                                                                |
| --------------------------- | ----------- | ----------------------------------------------------------------------------------------- |
| `HARVARD_API_ERROR`         | 502         | `GET /proxy/{path}`                                                                       |
| `ARTWORK_NOT_FOUND`         | 404         | `GET /artworks/{artwork_id}/insight-card`                                                 |
| `GENERATION_FAILED`         | 502         | `GET /artworks/{artwork_id}/insight-card`, `POST /admin/artworks/{artwork_id}/regenerate` |
| `GENERATION_TIMEOUT`        | 504         | `GET /artworks/{artwork_id}/insight-card`, `POST /admin/artworks/{artwork_id}/regenerate` |
| `EMAIL_ALREADY_EXISTS`      | 409         | `POST /auth/register`                                                                     |
| `VALIDATION_ERROR`          | 400         | `POST /auth/register`, `POST /auth/login`                                                 |
| `INVALID_CREDENTIALS`       | 401         | `POST /auth/login`                                                                        |
| `UNAUTHORIZED`              | 401         | `POST /auth/logout`, `GET /auth/session`, `/admin/*` endpoints                            |
| `INVALID_OR_EXPIRED_TOKEN`  | 400         | `POST /auth/password-reset/confirm`                                                       |
| `ARTWORK_CONTENT_NOT_FOUND` | 404         | `GET /admin/artworks/{artwork_id}`                                                        |
| `FORBIDDEN`                 | 403         | `/admin/*` endpoints (valid session, but without administrative privilege)                |

---

## 8. Identified Pending Issues

The drafting of this contract revealed three gaps not covered by the previous documents:

1. **Missing administrative privilege in the schema:** doc 05 does not define any field in `users` to distinguish an administrator from a regular visitor, but the `/admin/*` endpoints need this distinction (`FORBIDDEN` error). Proposed solution: add `is_admin BOOLEAN NOT NULL DEFAULT false` to the `users` table.
2. **Missing password reset token storage:** `POST /auth/password-reset/confirm` depends on a token with expiration that has no corresponding table in doc 05. Proposed solution: add a `password_reset_tokens` table (`id`, `user_id` FK, `token_hash`, `expires_at`, `used_at`).
3. **Artwork nonexistent in the Harvard API:** the flow in doc 06 does not explicitly handle the case of an `artwork_id` that does not exist in the Harvard Art Museums API — this document adds this case as `404 ARTWORK_NOT_FOUND`, verified before triggering the AI Pipeline.

None of these gaps were fixed in documents 05 or 06 as part of this task — both would need a small addendum. I recommend reviewing these three pending issues before moving forward with implementation (doc 99, Phase 2 and Phase 8).

---

## 9. Traceability

| Endpoint                                        | Related Requirements                                                       | Related Use Cases   |
| ----------------------------------------------- | -------------------------------------------------------------------------- | ------------------- |
| `GET /proxy/{path}`                             | — (inherited from the MVP)                                                 | —                   |
| `GET /artworks/{artwork_id}/insight-card`       | RF-001, RF-002, RF-003, RF-007, RF-009, RF-016 to RF-019, RNF-001, RNF-002 | UC-01, UC-02, UC-03 |
| `POST /auth/register`                           | RF-014 (functional parity)                                                 | —                   |
| `POST /auth/login`                              | RF-013, RF-014                                                             | UC-06               |
| `POST /auth/logout`                             | RF-014                                                                     | UC-06               |
| `POST /auth/password-reset/request`, `/confirm` | RF-014 (functional parity)                                                 | —                   |
| `GET /auth/session`                             | RF-013                                                                     | UC-06               |
| `GET/POST /admin/*`                             | — (Block 7 of doc 99)                                                      | —                   |

> The complete matrix, connecting requirements to architecture components and test cases, will be formalized in document 16 — Traceability Matrix.
