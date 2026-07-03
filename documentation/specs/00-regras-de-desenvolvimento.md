# Regras de Desenvolvimento e Governança — Art Archive AI

**Versão:** 1.0
**Data:** 2026-07-03
**Status:** Aprovado
**Escopo:** Este documento rege todos os demais documentos em `/documentation/specs/` e todo o código produzido a partir deles. Em caso de dúvida sobre como proceder durante o desenvolvimento, este é o primeiro documento a ser consultado.

---

## 1. Objetivo

O Art Archive AI é desenvolvido seguindo **Spec-Driven Development (SDD)**: nenhuma funcionalidade é implementada sem uma especificação prévia e aprovada em `/documentation/specs/`. Este documento existe para tornar essa regra operacional — define o que não pode ser quebrado sob nenhuma circunstância, como o desenvolvimento deve se conduzir no dia a dia, e o que fazer quando a especificação não cobre um cenário encontrado durante a implementação.

Este documento não substitui os demais — ele é a camada de regras que se aplica _por cima_ de todos eles.

---

## 2. Regras Duras (Não Podem Ser Quebradas em Hipótese Alguma)

1. **Nenhuma funcionalidade é implementada sem uma especificação aprovada correspondente** em `/documentation/specs/`. Se o código precisa fazer algo que nenhum documento descreve, a implementação para e a especificação é escrita ou revisada primeiro — nunca o contrário.
2. **Nenhuma chave de API, segredo ou credencial é exposta no front-end ou commitada no repositório.** Toda chamada ao Azure OpenAI e à Harvard Art Museums API ocorre exclusivamente no backend (RNF-005, doc 04 §9 decisão 3).
3. **Nenhuma chamada à IA ou à Harvard API parte diretamente do front-end.** O front-end só conversa com o backend único do projeto (doc 04 §6).
4. **Nenhuma funcionalidade do MVP existente é removida, reescrita ou tem seu comportamento alterado sem validação de paridade explícita antes da remoção do código antigo** — aplica-se especialmente à substituição do Firebase Auth por autenticação sobre PostgreSQL (garantir que login, logout e recuperação de senha continuem funcionando, ainda que sobre uma base de usuários nova — RF-014) e à reescrita do proxy Harvard (doc 04 §11).
5. **_(Removida — 2026-07-03)_** Aplicava-se à migração de dados do Firebase para o PostgreSQL. Não se aplica mais: por decisão explícita do projeto, o PostgreSQL é criado do zero e todos os dados de usuário do Firebase são descartados sem migração (RF-015 e UC-07 removidos — ver doc 02 e doc 03). Este identificador é mantido como removido, sem reaproveitamento, por rastreabilidade histórica.
6. **Nenhuma alteração estrutural em um documento de especificação já existente é feita silenciosamente.** Mudanças de conteúdo (correção, esclarecimento) podem ser feitas diretamente; mudanças de estrutura, escopo ou decisão arquitetural são sinalizadas ao autor antes de aplicadas.
7. **Nenhuma pendência identificada durante o desenvolvimento é resolvida por suposição.** Ver Seção 4.
8. **Todo código que implementa um Requisito Funcional deve ser validado contra os cenários Gherkin daquele requisito (doc 02 e doc 03) antes de ser considerado concluído.**

---

## 3. Regras de Conduta de Desenvolvimento

1. **Seguir a ordem de fases do doc 99**, respeitando as dependências ali documentadas. Não iniciar uma fase cuja especificação de origem ainda não existe (doc 99, §4, Fase 0).
2. **Toda função, endpoint ou componente relevante deve referenciar o RF/RNF/UC que implementa** — em comentário, docstring ou na descrição do commit/PR. Isso mantém a rastreabilidade viva entre código e especificação, para além do doc 16.
3. **Não introduzir abstrações, configurações ou generalizações além do que a especificação atual exige.** Se um requisito descreve um caso único, o código implementa esse caso único — não uma solução genérica para casos hipotéticos futuros.
4. **Manter os documentos de especificação atualizados** conforme a implementação avança: status no índice do doc 01 (§9), checklist do doc 99, e qualquer decisão nova documentada no lugar apropriado.
5. **Preferir muitos commits pequenos e atômicos**, cada um implementando um RF/UC específico ou uma etapa clara de um documento técnico (doc 06, doc 09), facilitando reverter uma decisão isolada sem afetar o restante.
6. **Toda decisão técnica não prevista em nenhuma especificação, mas necessária para o código funcionar** (ex.: uma biblioteca específica, um padrão de tratamento de erro não coberto), deve ser registrada como uma decisão explícita no documento mais relacionado ao tema — nunca deixada apenas implícita no código.

---

## 4. Regras de Mitigação de Pendências

### 4.1 O que é uma pendência

Uma pendência é qualquer cenário, comportamento ou decisão que o código **precisa resolver para funcionar**, mas que **nenhum documento em `/documentation/specs/` define com clareza suficiente**. Já ocorreu diversas vezes durante a elaboração destes documentos (ver Seção 6) — é esperado que continue ocorrendo durante a implementação.

### 4.2 Regra central

**Nada é criado ou decidido "no código" sem estar dentro das especificações.** Ao encontrar uma pendência:

1. **Pare** a implementação daquele trecho específico — não escreva um comportamento improvisado só para "fazer funcionar por enquanto".
2. **Registre a pendência** no documento mais relacionado ao tema, em uma seção clara (seguindo o padrão já usado nos docs 03 §5, 06 §7 e 07 §8): o que falta, por que é necessário, e uma sugestão de solução, se houver uma óbvia.
3. **Comunique a pendência ao autor** antes de prosseguir com a implementação daquele trecho — nunca apenas registre em silêncio e siga em frente com uma suposição própria.
4. **Aguarde a definição formal** (uma atualização do documento correspondente) antes de implementar o comportamento definitivo. Se um desbloqueio temporário for indispensável para não travar todo o desenvolvimento, ele deve ser explicitamente marcado no código como provisório e vinculado à pendência registrada.

### 4.3 O que isso evita

Esta regra existe para impedir o cenário mais comum de divergência entre código e documentação em projetos SDD: o desenvolvedor (ou um assistente de IA) encontra um caso não coberto, tenta ser prestativo, decide algo razoável sozinho, e a especificação nunca é atualizada — o código passa a ser a única fonte de verdade sobre aquele comportamento, quebrando o propósito de todo o processo de Spec-Driven Development.

---

## 5. Hierarquia e Resolução de Conflitos entre Documentos

Quando dois documentos parecerem se contradizer:

1. O documento **mais específico e mais próximo da implementação** (numeração mais alta) prevalece sobre um documento mais geral — ex.: o doc 09 (Pipeline de IA) prevalece sobre o doc 04 (Arquitetura) em detalhes de implementação do pipeline, desde que não contrarie uma decisão explícita do doc 04.
2. **Exceção:** nenhum documento pode contradizer o doc 01 (Visão e Escopo) sem que isso seja tratado como uma pendência de revisão do próprio doc 01, escalada ao autor — o doc 01 é a base de tudo (doc 01, §9).
3. Um conflito encontrado nunca é resolvido silenciosamente escolhendo um dos dois lados — ele é tratado como uma pendência (Seção 4).

---

## 6. Regras para Uso de Assistentes de IA no Desenvolvimento

Como este projeto é construído com apoio de assistentes de IA (ex.: Claude Code) tanto para documentação quanto para código, as regras deste documento se aplicam integralmente a esse uso:

1. Um assistente de IA **nunca implementa uma funcionalidade que não tenha especificação aprovada** — mesmo que a solicitação pareça simples ou óbvia.
2. Um assistente de IA que encontrar uma lacuna de especificação durante a geração de documentação ou código **deve reportá-la explicitamente ao autor**, seguindo o mesmo formato já estabelecido nos docs 03, 06, 07 e 09, em vez de preencher a lacuna por conta própria.
3. Alterações estruturais propostas por um assistente de IA a um documento já existente (ex.: mudar uma decisão de arquitetura, remover uma seção) **são sempre confirmadas com o autor antes de aplicadas**.

---

## 7. Registro de Pendências Conhecidas (Índice de Conveniência)

Lista de conveniência apontando para as pendências já identificadas durante a elaboração dos documentos até aqui. O conteúdo completo de cada uma vive no documento de origem — esta tabela existe apenas para não perdê-las de vista.

| Pendência                                              | Documento de Origem                    | Resumo                                                                                                                                                                                     |
| ------------------------------------------------------ | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Alt Text quando a imagem é inacessível                 | doc 03 (§5), doc 06 (§7), doc 09 (§10) | Hoje, se a imagem da obra não pode ser processada, nenhum Alt Text é persistido e o usuário não recebe nenhum aviso. Recomendação: gerar um texto padrão de aviso em vez de omitir o campo |
| Privilégio administrativo ausente no schema            | doc 07 (§8, item 1)                    | `users` não tem um campo para distinguir administradores de visitantes comuns, necessário para os endpoints `/admin/*`                                                                     |
| Armazenamento de token de redefinição de senha ausente | doc 07 (§8, item 2)                    | `POST /auth/password-reset/confirm` depende de uma tabela de tokens com expiração que ainda não existe no doc 05                                                                           |

> Esta tabela deve ser atualizada sempre que uma nova pendência for registrada em qualquer documento, e uma linha deve ser removida somente quando a pendência correspondente for formalmente resolvida no documento de origem.

---

## 8. Nota de Manutenção

Este documento é a constituição do processo de desenvolvimento deste projeto — suas regras devem ser estáveis. Alterações a ele (adição, remoção ou modificação de qualquer regra das Seções 2 a 6) exigem confirmação explícita do autor antes de serem aplicadas. A Seção 7 é a exceção: por ser um índice de conveniência, deve ser mantida atualizada continuamente conforme novas pendências surgem ou são resolvidas.
