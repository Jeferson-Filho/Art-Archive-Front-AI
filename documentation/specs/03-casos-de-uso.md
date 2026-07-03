# Casos de Uso — Art Archive AI

**Versão:** 1.0
**Data:** 2026-07-03
**Status:** Em revisão
**Documentos base:** [01 — Visão e Escopo](./01-visao-escopo.md), [02 — Requisitos](./02-requisitos.md)

---

## Sobre este documento

Este documento centraliza as **User Stories** e os **Casos de Uso** do projeto. Ele complementa o documento 02 (Requisitos) da seguinte forma:

- **Doc 02** especifica requisitos atômicos (RF/RNF) com cenários Gherkin de validação unitária — cada um testa uma única regra de negócio.
- **Doc 03 (este documento)** descreve fluxos completos de interação entre atores e sistema, do início ao fim, agrupando múltiplos RFs em um único caso de uso testável de ponta a ponta (nível de integração).

As User Stories anteriormente descritas no documento 02 foram movidas para cá e passam a ser mantidas exclusivamente neste documento.

---

## Convenções

- **UC-XX** — Caso de Uso
- **US-XXX** — User Story
- Cada Caso de Uso possui: Ator Principal, Atores Secundários, Pré-condições, Fluxo Principal, Fluxos Alternativos/Exceção, Pós-condições e Critério de Aceite em Gherkin
- Cada Caso de Uso referencia os RF/RNF do documento 02 que ele cobre

---

## 1. Atores

| Ator                               | Tipo            | Descrição                                                                                                         |
| ---------------------------------- | --------------- | ----------------------------------------------------------------------------------------------------------------- |
| **Visitante**                      | Humano          | Qualquer pessoa que acessa a plataforma para explorar obras de arte, sem necessidade de formação especializada    |
| **Usuário com Deficiência Visual** | Humano          | Visitante que depende de tecnologia assistiva (leitor de tela) para consumir o conteúdo da plataforma             |
| **Usuário Autenticado**            | Humano          | Visitante com conta na plataforma, relevante especificamente para os fluxos de autenticação                       |
| **Sistema Art Archive (Back-end)** | Sistema interno | Orquestra a verificação, geração e persistência do conteúdo de IA                                                 |
| **LLM Multimodal (Azure OpenAI)**  | Sistema externo | Gera o texto de contextualização histórica, análise comparativa e Alt Text a partir da imagem e metadados da obra |
| **Harvard Art Museums API**        | Sistema externo | Fonte dos metadados e imagens das obras (integração herdada do MVP)                                               |
| **PostgreSQL (Banco de Dados)**    | Infraestrutura  | Armazena e serve o conteúdo gerado e os dados de usuário                                                          |
| **Tecnologia Assistiva**           | Sistema externo | Leitor de tela (NVDA, VoiceOver, JAWS) utilizado pelo Usuário com Deficiência Visual para interpretar a página    |

---

## 2. User Stories

---

### Bloco: Visitante sem Formação Especializada

**US-001**
Como **visitante da plataforma sem formação em história da arte**,
quero **ler uma contextualização histórica sobre a obra e o artista ao abrir a página de uma obra**,
para que **eu compreenda o período, o movimento artístico e as influências culturais sem precisar buscar essa informação em outra fonte**.

> Rastreabilidade: RF-001, RF-002, RF-003, RF-004 · Caso de Uso: UC-01

---

**US-002**
Como **visitante da plataforma sem formação em história da arte**,
quero **ver referências a outros artistas e obras com estilo, paleta ou técnica semelhantes à obra que estou vendo**,
para que **eu possa expandir meu repertório artístico a partir de uma obra que já me interessa**.

> Rastreabilidade: RF-001, RF-003, RF-004 · Caso de Uso: UC-01

---

**US-003**
Como **visitante recorrente da plataforma**,
quero **que a contextualização de uma obra que já acessei carregue instantaneamente**,
para que **minha experiência de navegação não seja prejudicada por esperas repetidas**.

> Rastreabilidade: RF-001, RF-016, RF-017, RF-018 · Caso de Uso: UC-02

---

### Bloco: Usuário com Deficiência Visual

**US-004**
Como **usuário com deficiência visual que depende de leitor de tela**,
quero **ouvir uma descrição detalhada da imagem da obra ao navegar pela página de detalhe**,
para que **eu possa compreender o conteúdo visual da obra sem depender de outro usuário ou de outra plataforma**.

> Rastreabilidade: RF-007, RF-008, RF-009 · Caso de Uso: UC-04

---

**US-005**
Como **usuário com deficiência visual que depende de leitor de tela**,
quero **que o painel de contextualização (Insight Card) seja navegável por teclado e anunciado corretamente pelo leitor de tela**,
para que **eu acesse o mesmo conteúdo educativo que qualquer outro visitante, sem barreiras**.

> Rastreabilidade: RF-010, RF-011, RF-012 · Caso de Uso: UC-05

---

**US-006**
Como **usuário com deficiência visual que depende de leitor de tela**,
quero **ser informado quando o conteúdo do Insight Card ainda está sendo gerado ou quando ocorreu um erro**,
para que **eu saiba o estado atual da página sem precisar navegar por todo o conteúdo para descobrir**.

> Rastreabilidade: RF-011, RF-019 · Caso de Uso: UC-03, UC-05

---

### Bloco: Usuário Autenticado

**US-007** _(removida — 2026-07-03)_

Descrevia originalmente a continuidade de acesso para usuários que já possuíam conta no Firebase antes da expansão. Não se aplica mais: o PostgreSQL é criado do zero e nenhum dado do Firebase é migrado — não existem "usuários que já possuíam conta" a preservar. Usuários que utilizavam o Firebase precisarão criar uma nova conta no sistema, coberto pelo fluxo padrão de cadastro (RF-014).

> Rastreabilidade: RF-013, RF-014 · Caso de Uso: UC-06

---

## 3. Casos de Uso Detalhados

---

### UC-01 — Visualizar Insight Card na Primeira Visita a uma Obra

| Campo                  | Detalhe                                                                                                      |
| ---------------------- | ------------------------------------------------------------------------------------------------------------ |
| **Ator Principal**     | Visitante                                                                                                    |
| **Atores Secundários** | Sistema Art Archive, LLM Multimodal, PostgreSQL                                                              |
| **Pré-condições**      | O visitante está na página de detalhe de uma obra; o Insight Card desta obra não existe no banco de dados    |
| **Pós-condições**      | O Insight Card é exibido ao visitante; o conteúdo gerado é persistido no banco de dados para visitas futuras |

**Fluxo Principal**

1. O visitante acessa a página de detalhe de uma obra.
2. O sistema verifica no banco de dados se o Insight Card já existe para essa obra.
3. O sistema constata que o conteúdo não existe.
4. O sistema exibe o estado de carregamento na área do Insight Card.
5. O sistema envia a imagem e os metadados da obra ao LLM Multimodal.
6. O LLM retorna a contextualização histórica, a análise comparativa e o Alt Text.
7. O sistema persiste o conteúdo gerado no banco de dados.
8. O sistema retorna o conteúdo ao front-end.
9. O front-end substitui o estado de carregamento pelo conteúdo completo do Insight Card.

**Fluxos Alternativos / Exceção**

- **6a.** O LLM falha ou excede o tempo limite → segue para **UC-03**.
- **7a.** A persistência no banco falha → o conteúdo é retornado ao visitante mesmo assim; o erro é registrado em log, sem impacto visível ao usuário.

**Critério de Aceite**

```gherkin
Funcionalidade: Geração e exibição do Insight Card na primeira visita

  Cenário: Visitante acessa obra sem Insight Card persistido
    Dado que o visitante acessa a página de detalhe de uma obra
    E o Insight Card desta obra não existe no banco de dados
    Quando a página termina de carregar
    Então o sistema exibe o estado de carregamento
    E dispara a geração via LLM multimodal
    E, ao concluir com sucesso, persiste o conteúdo no banco de dados
    E exibe o Insight Card completo, com contextualização histórica e análise comparativa
```

**Requisitos relacionados:** RF-001, RF-002, RF-003, RF-004, RF-005, RF-009, RF-016, RF-017

---

### UC-02 — Visualizar Insight Card já Persistido (Cache)

| Campo                  | Detalhe                                                               |
| ---------------------- | --------------------------------------------------------------------- |
| **Ator Principal**     | Visitante                                                             |
| **Atores Secundários** | Sistema Art Archive, PostgreSQL                                       |
| **Pré-condições**      | O Insight Card da obra já está persistido no banco de dados           |
| **Pós-condições**      | O conteúdo é exibido rapidamente; nenhuma chamada é feita à API de IA |

**Fluxo Principal**

1. O visitante acessa a página de detalhe de uma obra.
2. O sistema verifica no banco de dados e encontra o conteúdo já persistido.
3. O sistema retorna o conteúdo diretamente ao front-end, sem acionar o LLM.
4. O front-end exibe o Insight Card imediatamente.

**Fluxos Alternativos / Exceção**

- Nenhum fluxo alternativo identificado — este é o caminho feliz do mecanismo de cache.

**Critério de Aceite**

```gherkin
Funcionalidade: Exibição do Insight Card a partir do cache

  Cenário: Visitante acessa obra com Insight Card já persistido
    Dado que o Insight Card de uma obra já está armazenado no banco de dados
    Quando qualquer visitante acessa a página de detalhe dessa obra
    Então o sistema retorna o conteúdo do banco de dados
    E nenhuma requisição é feita à API de IA
    E o tempo de resposta do back-end é de no máximo 500ms (RNF-001)
```

**Requisitos relacionados:** RF-001, RF-016, RF-018, RNF-001

---

### UC-03 — Tratar Falha na Geração do Insight Card

| Campo                  | Detalhe                                                                                                    |
| ---------------------- | ---------------------------------------------------------------------------------------------------------- |
| **Ator Principal**     | Visitante                                                                                                  |
| **Atores Secundários** | Sistema Art Archive, LLM Multimodal, Tecnologia Assistiva                                                  |
| **Pré-condições**      | O Insight Card da obra não está persistido; a geração via LLM falha (erro, timeout ou resposta malformada) |
| **Pós-condições**      | Nenhum conteúdo é persistido; o visitante é informado do erro; o restante da página permanece funcional    |

**Fluxo Principal**

1. O visitante acessa a página de detalhe de uma obra sem Insight Card persistido.
2. O sistema dispara a geração via LLM.
3. O LLM falha ou excede o tempo limite configurado.
4. O sistema retorna uma resposta de erro ao front-end.
5. O front-end exibe uma mensagem de erro apenas na área do Insight Card.
6. Título, imagem e metadados da obra permanecem visíveis e funcionais.

**Fluxos Alternativos / Exceção**

- **6a.** Se o visitante utiliza leitor de tela, a mensagem de erro é anunciada automaticamente via `aria-live`, sem exigir navegação manual até o componente (ver **UC-05**).

**Critério de Aceite**

```gherkin
Funcionalidade: Tratamento de falha na geração do Insight Card

  Cenário: Falha na geração por timeout da API de IA
    Dado que o visitante acessa a página de detalhe de uma obra sem conteúdo persistido
    E a requisição ao LLM excede o tempo limite configurado
    Quando o timeout é atingido
    Então o front-end exibe uma mensagem de erro apenas na área do Insight Card
    E título, imagem e metadados da obra permanecem visíveis e funcionais
    E nenhum conteúdo é persistido no banco de dados
```

**Requisitos relacionados:** RF-006, RF-011, RF-017, RF-019

---

### UC-04 — Consumir Alt Text da Imagem da Obra

| Campo                  | Detalhe                                                                                           |
| ---------------------- | ------------------------------------------------------------------------------------------------- |
| **Ator Principal**     | Usuário com Deficiência Visual (beneficia também qualquer visitante como reforço de robustez/SEO) |
| **Atores Secundários** | Sistema Art Archive, LLM Multimodal, Tecnologia Assistiva                                         |
| **Pré-condições**      | O visitante acessa a página de detalhe de uma obra                                                |
| **Pós-condições**      | A imagem da obra sempre possui um atributo `alt` não vazio                                        |

**Fluxo Principal**

1. O usuário (ou sua tecnologia assistiva) acessa a página de detalhe de uma obra.
2. O sistema verifica se o Alt Text da obra já foi gerado.
3. Caso exista: o sistema aplica o Alt Text gerado pela IA ao atributo `alt` da imagem.
4. A tecnologia assistiva lê o conteúdo do atributo `alt` ao focar na imagem.

**Fluxos Alternativos / Exceção**

- **3a.** Caso o Alt Text ainda não tenha sido gerado (obra nunca processada): o sistema aplica um texto descritivo genérico como fallback (ex.: "Imagem da obra [título]").
- **3b.** Caso a imagem da obra seja inacessível durante a geração (URL inválida ou erro de rede): atualmente nenhum Alt Text é persistido para a obra (RF-007, cenário 2). **Pendência identificada:** definir um texto padrão de aviso ("Descrição não disponível para esta obra") para este cenário, em vez de deixar a obra sem qualquer Alt Text armazenado — ver nota de revisão ao final deste documento.

**Critério de Aceite**

```gherkin
Funcionalidade: Aplicação do Alt Text na imagem da obra

  Cenário: Alt Text disponível
    Dado que a obra possui Alt Text armazenado no banco de dados
    Quando o front-end renderiza a imagem da obra
    Então o atributo alt da tag img contém o texto gerado pela IA

  Cenário: Alt Text ainda não gerado
    Dado que a obra ainda não possui Alt Text armazenado no banco de dados
    Quando o front-end renderiza a imagem da obra
    Então o atributo alt contém um texto descritivo genérico com o título da obra
```

**Requisitos relacionados:** RF-007, RF-008, RF-009

---

### UC-05 — Navegar no Insight Card via Leitor de Tela

| Campo                  | Detalhe                                                                                                            |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------ |
| **Ator Principal**     | Usuário com Deficiência Visual                                                                                     |
| **Atores Secundários** | Sistema Art Archive (front-end), Tecnologia Assistiva                                                              |
| **Pré-condições**      | O Insight Card está em algum dos estados possíveis: carregando, gerado ou com erro                                 |
| **Pós-condições**      | O usuário com deficiência visual acessa o mesmo conteúdo e os mesmos estados que um usuário vidente, sem barreiras |

**Fluxo Principal**

1. O usuário navega até a região do Insight Card utilizando a tecla Tab.
2. A tecnologia assistiva anuncia a região como "Insight Card" (ou equivalente).
3. O usuário navega entre as subseções (contextualização histórica, análise comparativa) usando Tab/Shift+Tab.
4. A tecnologia assistiva anuncia cada subseção ao ser alcançada.

**Fluxos Alternativos / Exceção**

- **1a.** Se o conteúdo ainda está sendo gerado ou falhou, a tecnologia assistiva anuncia automaticamente o estado (carregando/erro) via `aria-live="polite"`, sem que o usuário precise mover o foco até o componente.

**Critério de Aceite**

```gherkin
Funcionalidade: Navegação acessível no Insight Card

  Cenário: Navegação por teclado e anúncio de seções
    Dado que o Insight Card foi gerado e exibido na página de detalhe de uma obra
    Quando o usuário navega até o componente usando a tecla Tab
    Então a tecnologia assistiva anuncia a região como "Insight Card"
    E anuncia cada subseção ao ser alcançada via Tab

  Cenário: Anúncio automático de estado transitório
    Dado que o usuário com leitor de tela acessa uma obra sem Insight Card persistido
    Quando o estado de carregamento ou de erro é exibido
    Então a tecnologia assistiva anuncia automaticamente o estado, sem exigir navegação manual até o componente
```

**Requisitos relacionados:** RF-010, RF-011, RF-012

---

### UC-06 — Autenticar-se na Plataforma

| Campo                  | Detalhe                                                                                        |
| ---------------------- | ---------------------------------------------------------------------------------------------- |
| **Ator Principal**     | Usuário Autenticado                                                                            |
| **Atores Secundários** | Sistema Art Archive, PostgreSQL                                                                |
| **Pré-condições**      | O usuário possui conta criada no PostgreSQL (via cadastro — não há dados herdados do Firebase) |
| **Pós-condições**      | O usuário está autenticado com uma sessão válida                                               |

**Fluxo Principal**

1. O usuário acessa a tela de login.
2. O usuário informa suas credenciais.
3. O sistema autentica o usuário consultando o PostgreSQL.
4. O sistema cria uma sessão válida.
5. O usuário é redirecionado para a área autenticada da plataforma.

**Fluxos Alternativos / Exceção**

- **3a.** Credenciais inválidas: o sistema informa o erro de autenticação, mantendo o comportamento equivalente ao oferecido pelo MVP (paridade funcional, RF-014).

**Critério de Aceite**

```gherkin
Funcionalidade: Autenticação via PostgreSQL

  Cenário: Login bem-sucedido
    Dado que o usuário possui conta criada no PostgreSQL
    Quando o usuário realiza login com suas credenciais
    Então o sistema autentica o usuário via PostgreSQL
    E uma sessão válida é criada
    E o usuário é redirecionado para a área autenticada
```

**Requisitos relacionados:** RF-013, RF-014

---

### UC-07 — _(Removido)_

Descrevia originalmente a migração de dados de usuário do Firebase para o PostgreSQL, executada por um script de migração. **Não se aplica mais** (decisão de 2026-07-03): o banco de dados PostgreSQL é criado do zero e nenhum dado do Firebase é migrado ou preservado. O Firebase é descontinuado integralmente, sem etapa de transição de dados. Este identificador é mantido como removido, sem reaproveitamento, por rastreabilidade histórica — ver doc 00 (§7).

---

## 4. Matriz de Rastreabilidade Resumida

| Caso de Uso | User Stories        | Requisitos Funcionais                                          |
| ----------- | ------------------- | -------------------------------------------------------------- |
| UC-01       | US-001, US-002      | RF-001, RF-002, RF-003, RF-004, RF-005, RF-009, RF-016, RF-017 |
| UC-02       | US-003              | RF-001, RF-016, RF-018                                         |
| UC-03       | US-006              | RF-006, RF-011, RF-017, RF-019                                 |
| UC-04       | US-004              | RF-007, RF-008, RF-009                                         |
| UC-05       | US-005, US-006      | RF-010, RF-011, RF-012                                         |
| UC-06       | US-007 _(removida)_ | RF-013, RF-014                                                 |
| UC-07       | _(removido)_        | _(removido — RF-015)_                                          |

> A matriz completa, conectando requisitos a componentes de arquitetura e casos de teste, será formalizada no documento 16 — Matriz de Rastreabilidade.

---

## 5. Nota de Revisão Pendente

Durante a elaboração deste documento, foi identificada uma lacuna no **RF-007, cenário 2** (doc 02): atualmente, quando a imagem de uma obra está inacessível, nenhum Alt Text é persistido, e o usuário com leitor de tela não recebe nenhuma indicação sobre a ausência dessa descrição. A recomendação é que o sistema gere e persista um texto padrão de aviso (ex.: "Descrição não disponível para esta obra") nesse cenário, em vez de omitir o Alt Text por completo.

Esta alteração ainda não foi aplicada ao documento 02 — depende de confirmação do autor do projeto antes de ser incorporada como alteração formal ao RF-007.
