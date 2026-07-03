# Guia de Desenvolvimento — Art Archive AI

**Versão:** 1.0
**Data:** 2026-07-02
**Status:** Documento vivo — atualizado continuamente durante o desenvolvimento
**Documentos base:** [01 — Visão e Escopo](./01-visao-escopo.md), [02 — Requisitos](./02-requisitos.md)

---

## Como usar este documento

Este documento não é uma especificação de funcionalidade — é um guia operacional para orientar a ordem de implementação. Ele traduz os requisitos (doc 02) em um plano de execução prático, organizado para que nenhuma etapa fique bloqueada esperando um artefato, documento ou infraestrutura que ainda não existe.

Cada item do checklist referencia, quando aplicável, o RF/RNF que ele implementa (doc 02) e o documento de especificação do qual depende (doc 03–19). Itens sem especificação prévia não devem ser iniciados — a especificação correspondente deve ser escrita primeiro.

Este documento será revisado conforme os documentos 03 a 19 forem criados. Atualizações estruturais (mudança de fases, novos blocos) serão propostas ao usuário antes de serem aplicadas.

---

## 1. Blocos de Funcionalidade

| Bloco | Nome                                                   | RFs/RNFs Relacionados                            |
| ----- | ------------------------------------------------------ | ------------------------------------------------ |
| **0** | Infraestrutura Base                                    | RNF-005                                          |
| **1** | Banco de Dados e Persistência sob Demanda              | RF-016, RF-017, RF-018, RF-019, RNF-001, RNF-003 |
| **2** | Pipeline de IA (Insight Card + Alt Text)               | RF-002, RF-003, RF-007, RF-009, RNF-002, RNF-006 |
| **3** | Contrato de API                                        | RF-001, RNF-001                                  |
| **4** | Frontend: Insight Card e Alt Text                      | RF-004, RF-005, RF-006, RF-008                   |
| **5** | Acessibilidade (ARIA)                                  | RF-010, RF-011, RF-012, RNF-004                  |
| **6** | Autenticação sobre PostgreSQL (Firebase Descontinuado) | RF-013, RF-014                                   |
| **7** | Painel Administrativo                                  | — (fora dos RFs formais, suporte operacional)    |
| **8** | Testes e Qualidade                                     | Todos os RFs/RNFs                                |
| **9** | Documentação Contínua e Encerramento                   | —                                                |

---

## 2. Dependências entre Blocos

| Bloco                             | Depende de                     | Pode rodar em paralelo com |
| --------------------------------- | ------------------------------ | -------------------------- |
| 0 — Infraestrutura                | —                              | —                          |
| 1 — Banco de Dados e Persistência | 0                              | 6 (schemas independentes)  |
| 2 — Pipeline de IA                | 0                              | 1, 6                       |
| 3 — Contrato de API               | 1, 2                           | —                          |
| 4 — Frontend Insight Card         | 3                              | —                          |
| 5 — Acessibilidade                | 4                              | —                          |
| 6 — Autenticação sobre PostgreSQL | 0, 1 (schema de usuários)      | 1 (conteúdo IA), 2         |
| 7 — Painel Administrativo         | 1, 3                           | —                          |
| 8 — Testes e Qualidade            | 4, 5, 6 (parcial, incremental) | —                          |
| 9 — Documentação Contínua         | — (contínuo desde o início)    | Todos                      |

**Insight-chave:** o pipeline de IA (Bloco 2) é testável isoladamente via script, sem depender de endpoint HTTP ou frontend prontos. Isso permite validar a qualidade da geração antes de qualquer camada de API ou UI existir.

---

## 3. Ordem de Execução Recomendada

```
Fase 1  → Infraestrutura Base                         (Bloco 0)
Fase 2  → Schemas de Banco de Dados                    (Bloco 1, parte DB)
Fase 3  → Pipeline de IA isolado (script/CLI)          (Bloco 2)
Fase 4  → Persistência sob Demanda (integração)        (Bloco 1, integração)
Fase 5  → Contrato de API                              (Bloco 3)
Fase 6  → Frontend: Insight Card + Alt Text            (Bloco 4)
Fase 7  → Acessibilidade (ARIA)                        (Bloco 5)
Fase 8  → Autenticação sobre PostgreSQL  [paralelizável desde a Fase 1]  (Bloco 6)
Fase 9  → Painel Administrativo                        (Bloco 7)
Fase 10 → Testes e Qualidade                           (Bloco 8)
Fase 11 → Encerramento e Documentação Final            (Bloco 9, contínuo)
```

A Fase 8 (autenticação sobre PostgreSQL) não depende de nenhum artefato do pipeline de IA — ela compartilha apenas a infraestrutura de banco de dados (Fase 1/2). Pode ser desenvolvida em paralelo às Fases 3–7 sem risco de bloqueio.

---

## 4. Checklist Detalhado

### Fase 0 — Especificações Pendentes (pré-requisito documental)

Nenhuma fase de implementação abaixo deve começar antes da especificação correspondente existir e estar aprovada.

- [x] Doc 03 — Casos de Uso (Gherkin)
- [x] Doc 04 — Arquitetura do Sistema
- [x] Doc 05 — Banco de Dados (DER, esquema, dicionário)
- [x] Doc 06 — Diagrama de Fluxo de Persistência
- [x] Doc 07 — Especificação de Interface (API Contract)
- [x] Doc 08 — Navegação e Fluxo
- [x] Doc 09 — Pipeline de IA
- [x] Doc 10 — Design do Card _(conteúdo pronto; arquivo `.png` ainda a ser incluído em `documentation/specs/` — não bloqueia as Fases 1–5, 7–9; bloqueia apenas o início efetivo da Fase 6)_
- [x] Doc 11 — Prompt Engineering

> Docs 12–19 (testes, qualidade, riscos, rastreabilidade, diário, relatório final, estudo de viabilidade) não bloqueiam o início da implementação e podem ser escritos próximos às fases correspondentes (ver Fases 10–11).

---

### Fase 1 — Infraestrutura Base

**Bloco 0** · Depende de: doc 04 (decisões de infraestrutura)

- [ ] Provisionar instância PostgreSQL (ambiente local de desenvolvimento)
- [ ] Criar recurso Azure OpenAI e obter chave/endpoint do modelo multimodal
- [ ] Configurar variáveis de ambiente (.env) no back-end e front-end, sem commit de segredos (RNF-005)
- [ ] Validar conectividade com PostgreSQL via script de teste simples
- [ ] Validar chamada de teste ao Azure OpenAI (uma imagem fixa + prompt fixo, sem lógica de negócio)
- [ ] Confirmar validade da chave da Harvard Art Museums API (já existente do MVP)

---

### Fase 2 — Schemas de Banco de Dados

**Bloco 1 (parte DB)** · Depende de: doc 05 (Banco de Dados)

- [ ] Modelar tabela de conteúdo de IA por obra (contextualização histórica, análise comparativa, alt text, versão do prompt, timestamps)
- [ ] Modelar tabela de usuários para o novo sistema de autenticação, criada do zero (independente da tabela acima — pode ser feita na mesma fase, sem ordem entre elas)
- [ ] Criar migrations (ex: Alembic) para ambas as tabelas
- [ ] Aplicar migrations no ambiente de desenvolvimento
- [ ] Popular seed de teste com 2–3 obras fictícias para validar o schema
- [ ] Resolver as pendências do doc 07 (§8) antes de finalizar o schema: adicionar `is_admin` a `users` (necessário para a Fase 9) e criar a tabela `password_reset_tokens` (necessária para a Fase 8)

---

### Fase 3 — Pipeline de IA Isolado

**Bloco 2** · Depende de: doc 09 (Pipeline de IA — concluído), doc 11 (Prompt Engineering — concluído, prompt `v1` definido)

Desenvolvido e testado via script/CLI, sem depender de endpoint HTTP ou frontend.

- [ ] Implementar verificação proativa de acessibilidade da imagem antes de qualquer chamada ao LLM (doc 09, §4 — `ImageUnavailableError`)
- [ ] Implementar montagem do prompt (mensagem de sistema + mensagem de usuário) usando o texto do prompt `v1` (doc 11, §3) a partir dos metadados selecionados em `ArtworkMetadata` (doc 09, §3 e §5)
- [ ] Implementar chamada ao Azure OpenAI com saída estruturada (JSON Schema, doc 11 §3.3) para os 3 campos simultâneos (doc 09, §5 e §6 — RF-002, RF-003, RF-007, RF-009)
- [ ] Implementar validação de completude da resposta (`is_complete()`), incluindo o intervalo de 50–300 caracteres do Alt Text (doc 09, §7 — RF-007)
- [ ] Testar pipeline com 3–5 obras reais da Harvard API, validar qualidade manualmente
- [ ] Confirmar que nenhuma tentativa automática de retry é implementada (doc 09, §8, decisão 3) e que o timeout total respeita os 60s da RNF-002

---

### Fase 4 — Persistência sob Demanda (Integração)

**Bloco 1 (integração)** · Depende de: Fase 2 + Fase 3 concluídas; doc 06 (Fluxo de Persistência)

- [ ] Implementar função de busca de conteúdo por ID de obra no banco
- [ ] Implementar lógica de verificação: existe → retorna do banco; não existe → aciona pipeline (Fase 3) e persiste (RF-016, RF-017, RF-018)
- [ ] Tratar falha de persistência sem quebrar a resposta ao usuário (RF-017, cenário 2)
- [ ] Testar fluxo completo via script: primeira chamada gera e persiste; segunda chamada não invoca a IA

---

### Fase 5 — Contrato de API

**Bloco 3** · Depende de: Fase 4 concluída; doc 07 (API Contract)

- [ ] Implementar endpoint de busca/geração de Insight Card por obra (aciona a lógica da Fase 4)
- [ ] Definir formato de resposta (contextualização, comparativa, alt_text, status)
- [ ] Implementar tratamento de erros HTTP (timeout do LLM, obra inexistente — RF-019)
- [ ] Testar endpoint via cURL/Postman com obras reais

---

### Fase 6 — Frontend: Insight Card e Alt Text

**Bloco 4** · Depende de: Fase 5 concluída; doc 08 (Navegação), doc 10 (Design do Card — conteúdo pronto, aguardando inclusão do arquivo `.png` em `documentation/specs/`)

- [ ] Criar componente Insight Card (seções de contextualização e análise comparativa)
- [ ] Integrar componente ao endpoint da Fase 5
- [ ] Implementar estado de carregamento (RF-005)
- [ ] Implementar estado de erro (RF-006)
- [ ] Aplicar Alt Text gerado na tag `<img>` da obra, com fallback genérico se ausente (RF-008)

---

### Fase 7 — Acessibilidade (ARIA)

**Bloco 5** · Depende de: Fase 6 (componente já existente); doc 03 (casos de uso com leitor de tela)

- [ ] Adicionar `aria-label`/`aria-labelledby` nas seções do Insight Card (RF-010)
- [ ] Adicionar `aria-live="polite"` nos estados de loading/erro (RF-011)
- [ ] Validar navegação por teclado (Tab/Shift+Tab) no componente (RF-012)
- [ ] Testar manualmente com NVDA ou VoiceOver (RNF-004)

---

### Fase 8 — Autenticação sobre PostgreSQL (Firebase Descontinuado)

**Bloco 6** · Paralelizável desde a Fase 1 · Depende de: Fase 2 (schema de usuários); doc 04 (estratégia de autenticação)

> Banco de dados criado do zero — nenhum dado do Firebase é migrado (ver Nota de Alteração em doc 02, doc 04 e doc 05).

- [ ] Implementar endpoints de autenticação usando PostgreSQL (registro, login, logout, sessão, recuperação de senha — doc 07 §5)
- [ ] Remover integralmente o código, configuração e credenciais do Firebase (front-end e back-end), incluindo `.firebaseAdminSDK.json` — nenhum dado precisa ser preservado antes da remoção
- [ ] Validar paridade funcional de ponta a ponta (login, logout, recuperação de senha, persistência de sessão) com contas novas criadas no PostgreSQL (RF-014)

---

### Fase 9 — Painel Administrativo

**Bloco 7** · Depende de: Fase 4 (dados persistidos existentes), Fase 5 (endpoint disponível)

- [ ] Criar tela listando obras processadas pela IA (status, data de geração)
- [ ] Permitir visualizar o conteúdo gerado de uma obra específica
- [ ] _(Opcional, baixa prioridade)_ Permitir re-disparo manual da geração para uma obra

---

### Fase 10 — Testes e Qualidade

**Bloco 8** · Depende de: docs 12, 13, 14; funcionalidades das Fases 3–8 implementadas

- [ ] Escrever casos de teste a partir dos cenários Gherkin do doc 02
- [ ] Executar rodada de testes Alfa (funcional)
- [ ] Executar avaliação de qualidade do conteúdo gerado (precisão histórica, alucinação, coerência)
- [ ] Executar testes de acessibilidade formais
- [ ] Executar rodada de testes Beta (usabilidade)

---

### Fase 11 — Encerramento e Documentação Final

**Bloco 9** · Contínuo desde o início do desenvolvimento

- [ ] Manter o Diário de Desenvolvimento (doc 17) atualizado a cada marco relevante
- [ ] Atualizar a Matriz de Rastreabilidade (doc 16) conforme requisitos são implementados e testados
- [ ] Atualizar o Plano de Gerenciamento de Riscos (doc 15) conforme riscos se concretizam ou são mitigados
- [ ] Escrever o Estudo de Viabilidade Técnica — RAG/Embeddings (doc 19) — pode ocorrer a qualquer momento após a Fase 3, pois não bloqueia nem é bloqueado por nenhuma outra fase
- [ ] Consolidar o Relatório Técnico Final (doc 18) ao término do semestre

---

## 5. Regras de Não-Bloqueio

- O pipeline de IA (Fase 3) é validável via script isolado, sem esperar endpoint ou frontend prontos — permite detectar problemas de qualidade de prompt cedo.
- O schema de conteúdo de IA e o schema de usuários (Fase 2) são independentes entre si — não há ordem obrigatória entre eles.
- A implementação de autenticação (Fase 8) depende apenas da infraestrutura base (Fase 1) e do schema de usuários (Fase 2) — pode ser desenvolvida em paralelo ao pipeline de IA e ao frontend, pois não compartilha código com esses blocos.
- O estudo de viabilidade de RAG/Embeddings (doc 19) é isolado e pode ser produzido a qualquer momento sem impactar o cronograma de implementação.
- A documentação contínua (diário, riscos, rastreabilidade) roda em paralelo a todas as fases, evitando acúmulo de trabalho documental no fim do semestre.

---

## 6. Nota de Manutenção

Este documento deve ser revisado conforme os documentos 03 a 19 forem produzidos, já que cada um pode refinar ou alterar a ordem de execução aqui proposta. Qualquer atualização estrutural neste guia (mudança de fases, blocos ou dependências) será proposta ao usuário antes de ser aplicada.
