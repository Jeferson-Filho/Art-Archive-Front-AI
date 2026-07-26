# Vision and Scope Document — Art Archive AI

**Version:** 1.0
**Date:** 2026-06-23
**Status:** Approved

---

## 1. Project Identification

| Field                    | Value                                                                              |
| ------------------------ | ---------------------------------------------------------------------------------- |
| **Project Name**         | Art Archive: Expansion with Generative AI for Art Contextualization and Comparison |
| **Institution**          | UNESP — São Paulo State University, Rio Claro Campus                               |
| **Program**              | Bachelor's Degree in Computer Science                                              |
| **Course**               | Computing Projects I — 1st Semester/2026                                           |
| **Advisor**              | Prof. Alexandro Jose Baldassin (DEMAC)                                             |
| **Student / Developer**  | Jeferson Patrick Dietrich Filho (RA 221154231)                                     |
| **External Member**      | Pedro Henrique Potenza Fernandes (author of the original MVP)                      |
| **Front-end Repository** | `Art-Archive-Front-AI`                                                             |
| **Execution Period**     | 2026-03-14 — 2026-07-10                                                            |

---

## 2. Problem

Qualified access to art history remains concentrated in privileged contexts: physical museums with specialized mediation, academic training courses, or professional guides. Outside these environments, most digital art platforms — including the MVP version of Art Archive — offer the user only basic metadata about a work: title, author, date, and dimensions.

This approach is insufficient to create a meaningful cultural experience. A user who accesses an isolated artwork does not receive:

- **Historical contextualization**: the period, the artistic movement, and the influences that shaped the work and its author.
- **Comparative analysis**: references to other artists and works with similar palette, technique, or style.
- **Descriptive accessibility**: an adequate description of the image for users who rely on screen readers.

The result is a barrier to accessing cultural knowledge that disproportionately affects users without specialized training, those outside urban centers, or those with visual impairments — exactly the audience a digital platform should prioritize reaching.

---

## 3. Product Objective

### 3.1 General Objective

Transform Art Archive — originally a navigable visual catalog — into a cultural discovery and learning environment mediated by generative Artificial Intelligence, without replacing the MVP's existing infrastructure.

### 3.2 Specific Objectives

1. Implement the **Insight Card**, an AI-generated narrative panel that displays historical contextualization of the artist and the work, and comparative analysis with artists and works of similar characteristics in terms of palette, technique, and style.
2. Implement an **on-demand persistence system** that stores AI-generated content in PostgreSQL on the first visit to a work, eliminating redundant calls to the AI API on subsequent accesses.
3. Implement **automatic Alt Text generation**, descriptive and educational, for artwork images via a multimodal LLM, integrated into the persistence pipeline.
4. Ensure **full screen reader support** through ARIA attributes and HTML semantics in the new components, making AI-generated content accessible to assistive technologies.
5. Produce **complete technical documentation** of the expanded system, including architecture, API contract, database schema, and prompt specification.
6. Conduct a **technical feasibility study** for a future implementation of vector search, RAG, and embeddings-based recommendation.

---

## 4. Stakeholders

| Stakeholder                          | Role                             | Interest in the Project                                                                    |
| ------------------------------------ | -------------------------------- | ------------------------------------------------------------------------------------------ |
| **Jeferson Patrick Dietrich Filho**  | Developer / Student              | Implement and deliver the product on time and with academic quality                        |
| **Prof. Alexandro Jose Baldassin**   | Advisor                          | Ensure academic alignment, technical rigor, and feasibility of the proposal                |
| **Pedro Henrique Potenza Fernandes** | External Member / MVP Author     | Technical reference on the original project's architecture decisions                       |
| **End User**                         | Platform visitor                 | Access rich cultural contextualization about artworks without needing specialized training |
| **User with Visual Impairment**      | Visitor who uses a screen reader | Consume the visual and narrative content of the works via assistive technologies           |
| **UNESP / Evaluation Committee**     | Academic institution             | Evaluate the technical quality, documentation, and impact of the delivered project         |

---

## 5. Project Scope

### 5.1 In Scope

The following features and deliverables are part of this expansion and will be implemented:

**Product Features:**

- **Multimodal Insight Card:** automatic LLM generation of two narrative blocks per work — historical contextualization (artist, period, movement) and comparative analysis (artists and works similar in palette, technique, and style).
- **On-Demand Persistence System:** verification of the existence of a prior analysis in the database before invoking the AI; permanent storage of the generated content in PostgreSQL on the first call.
- **AI-Generated Alt Text:** automatic, educational, and descriptive description of artwork images, persisted alongside the Insight Card content.
- **Screen Reader Support:** implementation of ARIA attributes and HTML semantics in the Insight Card and Alt Text components for compliance with accessibility guidelines.
- **Authentication migration:** transition from Firebase Auth to the new PostgreSQL database, maintaining functional parity.
- **Administration screen:** basic management panel for monitoring AI-generated content.

**Documentation and Academic Deliverables:**

- Complete set of specification documents (Spec-Driven Development), as planned in `/documentation/specs/`.
- Final technical report with qualitative analysis of the generated content.
- Technical feasibility study on embeddings, RAG, and vector search.
- Test plan and quality evaluation of the generated content.

### 5.2 Out of Scope

The following items are explicitly excluded from this expansion:

- **Vector search / RAG implementation**: will only be the subject of a technical feasibility study. No embeddings infrastructure will be deployed to production this semester.
- **Personalized recommendations based on user history**: outside the AI scope of this expansion.
- **Original MVP features**: the artwork grid with lazy loading, the filter system, the basic detail page, and the predominant color palette were delivered in the previous project and will not be rewritten — only extended.
- **Training or fine-tuning of models**: the project consumes existing LLM APIs (Azure OpenAI); no model will be trained or fine-tuned.
- **Moderation or manual curation of generated content**: the pipeline is automatic; systematic human review of the content is not planned for this phase.

---

## 6. Constraints

### 6.1 Technical Constraints

- **Harvard Art Museums API**: used under a non-commercial educational license. Request rate limits and the external service's availability are factors outside the project's control.
- **Azure OpenAI**: all content generation depends on the availability and quota limits of the Azure OpenAI service. Inference costs must be kept within the available educational budget.
- **Compatibility with existing infrastructure**: the Python back-end and the Next.js/TypeScript front-end must remain compatible with the original MVP's infrastructure throughout the expansion.
- **PostgreSQL as the sole database**: no additional database (e.g., a dedicated vector database) will be introduced in this phase.

### 6.2 Schedule Constraints

- The project follows the 1st Semester/2026 schedule, starting on 2026-03-14 and with final delivery between 2026-07-04 and 2026-07-10.
- Intermediate milestones defined in the Activity Plan (official plan delivery: week 6; UX refinement and QA: week 12; final delivery: week 17) are fixed and defined by the course.

### 6.3 Team Constraints

- The project is developed individually by a single student, without a dedicated technical support team.
- Advising occurs periodically and not continuously, which requires technical decision-making autonomy on the part of the developer.

---

## 7. Project Success Criteria

The project will be considered successful when all the criteria below are met:

1. **Functional Insight Card**: when accessing any artwork page, the Insight Card is displayed with the two narrative blocks (historical contextualization and comparative analysis), correctly generated by the AI.
2. **Verifiable persistence**: the second visit to a work does not invoke the AI API — the content is served directly from the PostgreSQL database.
3. **Generated and persisted Alt Text**: every work processed by the pipeline has an Alt Text stored in the database and rendered in the `alt` attribute of the corresponding image.
4. **Validated accessibility**: the Insight Card and Alt Text components pass an accessibility evaluation with a screen reader, with no critical ARIA errors.
5. **Complete documentation**: all 15 documents of the Spec-Driven Development plan are finalized in `/documentation/specs/`.
6. **Demonstrable prototype**: the expanded platform is accessible via a development environment or deployment and can be presented to the evaluation committee in working order.
7. **Delivered technical report**: the report documents architecture decisions, prompt engineering strategy, qualitative analysis of the generated content, and the embeddings/RAG feasibility study.

---

## 8. Assumptions

The following assumptions are taken as true for the planning and execution of the project:

1. **Availability of the Harvard Art Museums API**: the API will remain accessible with the necessary metadata (image, title, artist, date, technique, period) throughout the semester.
2. **Access to Azure OpenAI within the educational budget**: the multimodal model available via Azure OpenAI will support the volume of calls needed for development, testing, and demonstration without prohibitive cost.
3. **Stability of the MVP infrastructure**: the original project's Next.js/TypeScript front-end and Python back-end remain functional as an integration base, with no need for structural rewriting.
4. **Artwork images are accessible via public URL**: the images returned by the Harvard Art Museums API can be sent to the multimodal model for Alt Text generation and visual analysis.
5. **PostgreSQL as the target database**: the PostgreSQL instance will be available and configured for storing AI-generated content throughout the development period.
6. **Content generated in English is acceptable**: given that the Harvard Art Museums API returns metadata predominantly in English, the AI-generated content may be in English without compromising the project's proposal at this phase.

---

## 9. Specification Document Index

All documents follow the Spec-Driven Development approach: no functionality is implemented without a prior approved specification.

| #   | Document                                               | Objective                                                                                                                               | Status                             |
| --- | ------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| 01  | Vision / Scope Document                                | Defines the problem, product objective, stakeholders, and boundaries of what is in/out of scope. Foundation of everything that follows. | ✅ Done                            |
| 02  | Functional and Non-Functional Requirements             | Specifies what the system must do (functional) and with what quality (non-functional — performance, security, usability).               | ✅ Done                            |
| 03  | Use Cases (actors and features, Gherkin)               | Describes interactions between user and system in concrete, testable scenarios.                                                         | ✅ Done                            |
| 04  | System Architecture (components, deployment, sequence) | Shows how the system is technically structured: modules, infrastructure, call flow.                                                     | ✅ Done                            |
| 05  | Database (ERD, relational schema, data dictionary)     | Models how data is stored and related.                                                                                                  | ✅ Done                            |
| 06  | Persistence Flow Diagram                               | Specifically details the "check before generating" logic — the Insight Card's caching mechanism.                                        | ✅ Done                            |
| 07  | Interface Specification (API Contract)                 | Defines formal contracts for each endpoint: request, response, errors.                                                                  | ✅ Done                            |
| 08  | Navigation and Flow (navigability diagram)             | Maps the screens and transitions of the user experience.                                                                                | ✅ Done                            |
| 09  | AI Pipeline (Insight Card and Alt Text)                | Details the specific technical flow of AI content generation, from input to persisted output.                                           | ✅ Done                            |
| 10  | Card Design                                            | Visual wireframe/mockup of the Insight Card, including states (loading, generated, error).                                              | 🖼️ Ready — `.png` file to be added |
| 11  | Prompt Engineering Document                            | Documents the strategy, versioning, and evolution of the prompts used.                                                                  | ✅ Done                            |
| 12  | Test Plan (scope, acceptance criteria)                 | Defines what will be tested and how success is measured, before testing.                                                                | ⬜ Pending                         |
| 13  | Test Report (Alpha, Beta, results)                     | Records the actual results of the test rounds.                                                                                          | ⬜ Pending                         |
| 14  | Generated Content Quality Evaluation                   | Specific criteria and results for evaluating the quality of the AI output (historical accuracy, hallucination, coherence).              | ⬜ Pending                         |
| 15  | Risk Management Plan                                   | Lists technical and schedule risks, with probability, impact, and mitigation.                                                           | ⬜ Pending                         |
| 16  | Requirements Traceability Matrix                       | Connects each requirement to a use case, architecture component, and test.                                                              | ⬜ Pending                         |
| 17  | Development Journal                                    | Continuous record of the process, decisions, and obstacles throughout the semester.                                                     | ⬜ Pending                         |
| 18  | Final Technical Report                                 | Synthesis of architectural decisions, results, and qualitative analysis — the semester's final deliverable.                             | ⬜ Pending                         |
| 19  | Technical Feasibility Study (RAG/Embeddings)           | Feasibility document for future expansion with vector search and embeddings-based recommendation.                                       | ⬜ Pending                         |

> **Note on doc 10:** unlike the others, this document is an image (`.png`), not a Markdown file. The design has already been produced externally and is with a third party; all that remains is to bring the file into `documentation/specs/10-design-card.png`. For planning purposes (doc 99), it is considered ready — no phase depends on the creation of the design, only on the arrival of the file.
