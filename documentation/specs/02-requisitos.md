# Requisitos Funcionais e Não Funcionais — Art Archive AI

**Versão:** 1.0  
**Data:** 2026-07-02  
**Status:** Em revisão  
**Documento base:** [01 — Visão e Escopo](./01-visao-escopo.md)

---

## Convenções

- **RF-XXX** — Requisito Funcional
- **RNF-XXX** — Requisito Não Funcional
- **US-XXX** — User Story
- Cada RF possui um ou mais cenários Gherkin que serão referenciados no Plano de Testes (doc 12)
- Prioridade: **Alta** (MVP obrigatório) · **Média** (importante, mas não bloqueia entrega) · **Baixa** (desejável)

---

## User Stories

User stories descrevem o que os usuários precisam realizar, sem detalhar implementação. Cada US é rastreável a um ou mais RFs.

---

### Bloco de User Stories: Visitante sem Formação Especializada

**US-001**  
Como **visitante da plataforma sem formação em história da arte**,  
quero **ler uma contextualização histórica sobre a obra e o artista ao abrir a página de uma obra**,  
para que **eu compreenda o período, o movimento artístico e as influências culturais sem precisar buscar essa informação em outra fonte**.

> Rastreabilidade: RF-001, RF-002, RF-003, RF-004

---

**US-002**  
Como **visitante da plataforma sem formação em história da arte**,  
quero **ver referências a outros artistas e obras com estilo, paleta ou técnica semelhantes à obra que estou vendo**,  
para que **eu possa expandir meu repertório artístico a partir de uma obra que já me interessa**.

> Rastreabilidade: RF-001, RF-003, RF-004

---

**US-003**  
Como **visitante recorrente da plataforma**,  
quero **que a contextualização de uma obra que já acessei carregue instantaneamente**,  
para que **minha experiência de navegação não seja prejudicada por esperas repetidas**.

> Rastreabilidade: RF-012, RF-013, RF-014

---

### Bloco de User Stories: Usuário com Deficiência Visual

**US-004**  
Como **usuário com deficiência visual que depende de leitor de tela**,  
quero **ouvir uma descrição detalhada da imagem da obra ao navegar pela página de detalhe**,  
para que **eu possa compreender o conteúdo visual da obra sem depender de outro usuário ou de outra plataforma**.

> Rastreabilidade: RF-007, RF-008, RF-009

---

**US-005**  
Como **usuário com deficiência visual que depende de leitor de tela**,  
quero **que o painel de contextualização (Insight Card) seja navegável por teclado e anunciado corretamente pelo leitor de tela**,  
para que **eu acesse o mesmo conteúdo educativo que qualquer outro visitante, sem barreiras**.

> Rastreabilidade: RF-010, RF-011, RF-012

---

**US-006**  
Como **usuário com deficiência visual que depende de leitor de tela**,  
quero **ser informado quando o conteúdo do Insight Card ainda está sendo gerado ou quando ocorreu um erro**,  
para que **eu saiba o estado atual da página sem precisar navegar por todo o conteúdo para descobrir**.

> Rastreabilidade: RF-011, RF-012

---

## Bloco 1 — Insight Card: Geração de Texto via LLM Multimodal

O Insight Card é o painel narrativo exibido na página de detalhe de cada obra. Ele é composto por dois blocos de texto gerados por IA: contextualização histórica e análise comparativa.

---

**RF-001 — Disparo da geração do Insight Card**  
**Prioridade:** Alta

O sistema deve verificar, ao carregar a página de detalhe de uma obra, se o conteúdo do Insight Card já existe no banco de dados para aquela obra.

- Se existir: exibir o conteúdo armazenado (fluxo de persistência — ver RF-013).
- Se não existir: disparar a geração via LLM multimodal e exibir estado de carregamento.

**Cenário 1 — Conteúdo inexistente no banco**

```gherkin
Dado que o usuário acessa a página de detalhe de uma obra
E o Insight Card desta obra NÃO está armazenado no banco de dados
Quando a página termina de carregar
Então o sistema exibe o estado de carregamento do Insight Card
E dispara uma requisição ao back-end para gerar o conteúdo via LLM
```

**Cenário 2 — Conteúdo já existente no banco**

```gherkin
Dado que o usuário acessa a página de detalhe de uma obra
E o Insight Card desta obra JÁ está armazenado no banco de dados
Quando a página termina de carregar
Então o sistema exibe o conteúdo do Insight Card diretamente
E nenhuma requisição é feita à API de IA
```

---

**RF-002 — Geração do bloco de contextualização histórica**  
**Prioridade:** Alta

O LLM deve gerar, para cada obra, um bloco de texto narrativo com contextualização histórica contendo: período histórico, movimento artístico, biografia relevante do artista e influências culturais da obra. A geração deve utilizar a imagem da obra e seus metadados (título, artista, data, técnica, classificação) como entrada.

**Cenário 1 — Geração bem-sucedida**

```gherkin
Dado que o back-end recebe uma requisição de geração para uma obra com imagem e metadados válidos
Quando o LLM processa a requisição
Então o back-end retorna um bloco de texto com contextualização histórica não vazio
E o texto menciona pelo menos o período histórico e o movimento artístico da obra
```

**Cenário 2 — Metadados incompletos**

```gherkin
Dado que o back-end recebe uma requisição de geração para uma obra sem data ou técnica nos metadados
Quando o LLM processa a requisição com os metadados disponíveis
Então o back-end retorna um bloco de contextualização histórica baseado nos dados presentes
E não retorna erro por ausência de campos opcionais
```

---

**RF-003 — Geração do bloco de análise comparativa**  
**Prioridade:** Alta

O LLM deve gerar, para cada obra, um bloco de texto com análise comparativa contendo referências a pelo menos dois outros artistas ou obras com características semelhantes em termos de paleta, técnica ou estilo.

**Cenário 1 — Geração bem-sucedida**

```gherkin
Dado que o back-end recebe uma requisição de geração para uma obra com imagem e metadados válidos
Quando o LLM processa a requisição
Então o back-end retorna um bloco de texto de análise comparativa não vazio
E o texto referencia pelo menos dois artistas ou obras distintos
```

---

**RF-004 — Exibição do Insight Card na página de detalhe**  
**Prioridade:** Alta

O front-end deve exibir o Insight Card na página de detalhe da obra, apresentando os dois blocos (contextualização histórica e análise comparativa) como seções distintas com títulos visíveis.

**Cenário 1 — Exibição após geração**

```gherkin
Dado que o back-end retornou o conteúdo do Insight Card com sucesso
Quando o front-end recebe a resposta
Então o Insight Card é exibido na página de detalhe
E a seção de contextualização histórica está visível com seu título
E a seção de análise comparativa está visível com seu título
```

---

**RF-005 — Estado de carregamento do Insight Card**  
**Prioridade:** Alta

Enquanto o conteúdo do Insight Card está sendo gerado, o front-end deve exibir um estado de carregamento visível no espaço reservado ao card, indicando que o processo está em andamento.

**Cenário 1 — Loading visível**

```gherkin
Dado que o usuário acessa a página de detalhe de uma obra sem Insight Card persistido
Quando a geração é disparada
Então o front-end exibe um indicador de carregamento na área do Insight Card
E o restante da página (título, imagem, metadados básicos) permanece visível e utilizável
```

---

**RF-006 — Estado de erro do Insight Card**  
**Prioridade:** Alta

Se a geração do Insight Card falhar (timeout, erro da API de IA, dados insuficientes), o front-end deve exibir uma mensagem de erro no espaço do card, sem travar ou ocultar o restante da página.

**Cenário 1 — Falha na geração**

```gherkin
Dado que o usuário acessa a página de detalhe de uma obra sem Insight Card persistido
E a requisição de geração ao back-end retorna erro
Quando o front-end recebe a resposta de erro
Então o front-end exibe uma mensagem de erro na área do Insight Card
E a mensagem informa que o conteúdo não pôde ser carregado
E o restante da página continua funcional
```

---

## Bloco 2 — Alt Text: Geração de Texto Alternativo via IA

O Alt Text é uma descrição textual da imagem da obra, gerada pelo LLM multimodal. Ele é armazenado no banco junto ao Insight Card e aplicado ao atributo `alt` da imagem.

---

**RF-007 — Geração do Alt Text via LLM**  
**Prioridade:** Alta

O LLM deve gerar, para cada obra, um texto alternativo descritivo e educativo que descreva o conteúdo visual da imagem (elementos representados, composição, cores predominantes, técnica perceptível) de forma adequada para tecnologias assistivas.

**Cenário 1 — Geração bem-sucedida**

```gherkin
Dado que o back-end recebe uma requisição de geração para uma obra com imagem válida
Quando o LLM processa a imagem
Então o back-end retorna um texto de Alt Text não vazio
E o texto descreve elementos visuais da imagem (figuras, cores, composição ou técnica)
E o texto tem entre 50 e 300 caracteres
```

TODO Jeff - Caso não exista a imagem, ou dê erro para gerar o alt text, deve ser gerado um texto padrão que avise ao usuáio que não há alt text para essa obra
**Cenário 2 — Imagem inacessível**

```gherkin
Dado que o back-end recebe uma requisição de geração para uma obra cuja URL de imagem retorna erro
Quando o sistema tenta acessar a imagem
Então o back-end retorna um erro indicando que a imagem não pôde ser processada
E nenhum Alt Text é persistido para essa obra
```

---

**RF-008 — Aplicação do Alt Text na imagem da obra**  
**Prioridade:** Alta

O front-end deve aplicar o Alt Text gerado ao atributo `alt` do elemento `<img>` da obra na página de detalhe. O atributo deve ser preenchido com o conteúdo do banco de dados quando disponível.

**Cenário 1 — Alt Text disponível**

```gherkin
Dado que a obra possui Alt Text armazenado no banco de dados
Quando o front-end renderiza a imagem da obra
Então o atributo alt da tag img contém o texto gerado pela IA
E o atributo alt não está vazio nem ausente
```

**Cenário 2 — Alt Text ainda não gerado**

```gherkin
Dado que a obra ainda não possui Alt Text armazenado no banco de dados
Quando o front-end renderiza a imagem da obra
Então o atributo alt contém um texto descritivo genérico (ex: "Imagem da obra [título]")
E o atributo alt não está vazio nem ausente
```

---

**RF-009 — Persistência do Alt Text junto ao Insight Card**  
**Prioridade:** Alta

O Alt Text deve ser gerado e persistido no banco de dados na mesma operação que o Insight Card, dentro do mesmo fluxo de pipeline. Não deve existir uma chamada separada ao LLM exclusivamente para o Alt Text.

**Cenário 1 — Persistência conjunta**

```gherkin
Dado que o pipeline de geração é disparado para uma obra sem conteúdo persistido
Quando o LLM retorna a resposta completa
Então o banco de dados registra o Alt Text, a contextualização histórica e a análise comparativa na mesma transação
E a obra é marcada como processada
```

---

## Bloco 3 — Suporte a Leitores de Tela (ARIA)

Este bloco cobre os requisitos de acessibilidade aplicados aos novos componentes introduzidos pela expansão. Os requisitos do MVP original não são alterados.

---

**RF-010 — ARIA labels no Insight Card**  
**Prioridade:** Alta

O componente Insight Card deve possuir `aria-label` ou `aria-labelledby` na região que o contém, identificando-o como "Insight Card" para leitores de tela. As duas seções internas (contextualização histórica e análise comparativa) devem ser identificadas individualmente com `aria-label`.

**Cenário 1 — Atributos ARIA presentes**

```gherkin
Dado que o Insight Card foi gerado e exibido na página de detalhe de uma obra
Quando um leitor de tela navega até o componente
Então o leitor de tela anuncia a região como "Insight Card" ou equivalente
E anuncia as subseções como "Contextualização histórica" e "Análise comparativa" ao entrar em cada uma
```

---

**RF-011 — ARIA live region para estado de carregamento e erro**  
**Prioridade:** Alta

O estado de carregamento e o estado de erro do Insight Card devem ser anunciados automaticamente por leitores de tela sem que o usuário precise navegar até o elemento. Isso deve ser implementado por meio de um elemento com `aria-live="polite"`.

**Cenário 1 — Anúncio de carregamento**

```gherkin
Dado que o usuário com leitor de tela acessa a página de detalhe de uma obra
E o Insight Card ainda está sendo gerado
Quando o estado de carregamento é exibido
Então o leitor de tela anuncia automaticamente que o conteúdo está sendo carregado
Sem que o usuário precise mover o foco para a área do card
```

**Cenário 2 — Anúncio de erro**

```gherkin
Dado que o usuário com leitor de tela acessa a página de detalhe de uma obra
E a geração do Insight Card falha
Quando o estado de erro é exibido
Então o leitor de tela anuncia automaticamente a mensagem de erro
```

---

**RF-012 — Navegação por teclado no Insight Card**  
**Prioridade:** Alta

O Insight Card deve ser completamente navegável via teclado. O usuário deve conseguir alcançar o componente e navegar entre suas seções usando Tab e as teclas de navegação sem depender de mouse.

**Cenário 1 — Navegação por Tab**

```gherkin
Dado que o usuário está na página de detalhe de uma obra com Insight Card exibido
Quando o usuário navega com a tecla Tab
Então o foco alcança o Insight Card
E o usuário consegue navegar entre os elementos interativos do card usando Tab e Shift+Tab
E nenhum elemento focável fica inacessível via teclado
```

---

## Bloco 4 — Autenticação sobre PostgreSQL (Firebase Descontinuado)

> **Nota de Alteração (2026-07-03):** este bloco descrevia originalmente uma _migração_ de dados do Firebase para o PostgreSQL. Foi decidido que o banco de dados PostgreSQL será criado **do zero** — nenhum dado do Firebase (usuários, sessões, preferências) é migrado ou preservado. O Firebase Auth é descontinuado e seus dados descartados integralmente. Os requisitos abaixo foram revisados para refletir essa decisão. RF-015, que tratava exclusivamente da preservação de dados migrados, foi removido — ver nota ao final do bloco.

Este bloco cobre os requisitos do sistema de autenticação novo, construído sobre o banco de dados PostgreSQL centralizado, substituindo integralmente o Firebase Auth e o Google OAuth integrado a ele no MVP original.

---

**RF-013 — Autenticação de usuário via PostgreSQL**  
**Prioridade:** Alta

O sistema deve autenticar usuários utilizando o banco de dados PostgreSQL como única fonte de verdade para sessões e dados de usuário. Nenhuma operação de login ou verificação de sessão depende do Firebase Auth.

**Cenário 1 — Login bem-sucedido**

```gherkin
Dado que o usuário possui conta criada no PostgreSQL
Quando o usuário realiza login com suas credenciais
Então o sistema autentica o usuário via PostgreSQL
E uma sessão válida é criada
E o usuário é redirecionado para a página inicial autenticada
```

---

**RF-014 — Paridade funcional de autenticação com o MVP original**  
**Prioridade:** Alta

O novo sistema de autenticação deve oferecer as mesmas funcionalidades disponíveis no MVP original (login, logout, recuperação de senha, persistência de sessão), implementadas do zero sobre o PostgreSQL. Não há continuidade de dados com o Firebase — usuários que existiam no Firebase precisam criar uma nova conta no sistema.

**Cenário 1 — Funcionalidades de autenticação disponíveis**

```gherkin
Dado que o Firebase Auth foi descontinuado e seus dados descartados
Quando um usuário cria uma nova conta no sistema
Então ele consegue fazer login, fazer logout, recuperar a senha e ter sua sessão persistida
E nenhuma dessas funcionalidades depende de dados que existiam no Firebase
```

---

**RF-015 — _(Removido)_**

Tratava da preservação de dados de usuário durante a migração do Firebase. Não se aplica mais: o banco de dados PostgreSQL é criado do zero e nenhum dado do Firebase é migrado. Referências a este identificador em outros documentos (doc 03 UC-07, doc 05, doc 07, doc 99) foram marcadas como removidas ou ajustadas — ver Registro de Pendências no doc 00 (§7) para o histórico da decisão.

---

## Bloco 5 — Sistema de Persistência sob Demanda

Este bloco cobre a lógica central de cache inteligente: gerar o conteúdo de IA apenas na primeira visita a uma obra e servir do banco nas visitas seguintes.

---

**RF-016 — Verificação de existência antes da geração**  
**Prioridade:** Alta

Antes de qualquer chamada à API de IA, o back-end deve consultar o banco de dados para verificar se o conteúdo (Insight Card + Alt Text) da obra solicitada já foi gerado e persistido. A chamada à IA só ocorre se o conteúdo não existir.

**Cenário 1 — Conteúdo ausente, geração disparada**

```gherkin
Dado que o front-end solicita o Insight Card de uma obra ao back-end
E o banco de dados não possui registro de conteúdo para o ID dessa obra
Quando o back-end processa a requisição
Então o back-end dispara a chamada à API de IA
E aguarda a resposta para persistência
```

**Cenário 2 — Conteúdo presente, geração ignorada**

```gherkin
Dado que o front-end solicita o Insight Card de uma obra ao back-end
E o banco de dados já possui conteúdo persistido para o ID dessa obra
Quando o back-end processa a requisição
Então o back-end retorna o conteúdo armazenado
E nenhuma chamada à API de IA é realizada
```

---

**RF-017 — Persistência do conteúdo gerado após primeira geração**  
**Prioridade:** Alta

Após a geração bem-sucedida pelo LLM, o back-end deve persistir o conteúdo completo (contextualização histórica, análise comparativa, Alt Text) no banco de dados PostgreSQL antes de retornar a resposta ao front-end.

**Cenário 1 — Persistência bem-sucedida**

```gherkin
Dado que o LLM retornou o conteúdo completo para uma obra
Quando o back-end recebe a resposta do LLM
Então o back-end persiste os três campos (contextualização, comparativa, alt text) no banco de dados
E o registro é criado com o ID da obra como chave
E o back-end retorna o conteúdo ao front-end
```

**Cenário 2 — Falha na persistência**

```gherkin
Dado que o LLM retornou o conteúdo completo para uma obra
E o banco de dados retorna erro ao tentar salvar o registro
Quando o back-end tenta persistir o conteúdo
Então o back-end retorna o conteúdo gerado ao front-end mesmo sem persistência
E registra o erro de persistência em log
E não exibe mensagem de erro ao usuário final
```

---

**RF-018 — Servir conteúdo do banco em visitas subsequentes**  
**Prioridade:** Alta

Em qualquer visita a uma obra que já possua conteúdo persistido, o back-end deve retornar o conteúdo do banco de dados sem invocar a API de IA, independentemente de quantas vezes a obra tenha sido acessada anteriormente.

**Cenário 1 — Segunda visita**

```gherkin
Dado que a obra X foi acessada anteriormente e seu Insight Card está persistido no banco
Quando qualquer usuário acessa a página de detalhe da obra X
Então o Insight Card é retornado a partir do banco de dados
E o tempo de resposta é inferior ao tempo de uma geração nova (ver RNF-002)
```

---

**RF-019 — Tratamento de falha na geração sem prejudicar a página**  
**Prioridade:** Alta

Se a geração via LLM falhar por qualquer motivo (timeout, erro da API, resposta malformada), o sistema deve exibir uma mensagem de erro apenas no espaço do Insight Card. O restante da página de detalhe (imagem, metadados, títulos) deve permanecer acessível e funcional.

**Cenário 1 — Timeout da API de IA**

```gherkin
Dado que o usuário acessa a página de detalhe de uma obra sem conteúdo persistido
E a requisição à API de IA excede o tempo limite configurado
Quando o timeout é atingido
Então o back-end retorna uma resposta de erro para o front-end
E o front-end exibe mensagem de erro apenas na área do Insight Card
E título, imagem e metadados da obra permanecem visíveis e funcionais
```

---

## Requisitos Não Funcionais

---

**RNF-001 — Tempo de resposta para conteúdo já persistido**  
**Prioridade:** Alta

A resposta do back-end ao front-end quando o Insight Card já está no banco de dados deve ser entregue em no máximo **500ms** para 95% das requisições, medido do recebimento da requisição até o envio da resposta (excluindo latência de rede do cliente).

**Como verificar:** teste de carga com K6 ou similar contra o endpoint de busca de Insight Card com dados pré-populados no banco.

---

**RNF-002 — Tempo máximo de geração (primeira visita)**  
**Prioridade:** Média

O tempo total de geração do Insight Card completo (do disparo da requisição ao LLM até a persistência no banco) não deve exceder **60 segundos**. O front-end deve exibir estado de carregamento durante todo esse período.

**Como verificar:** medição do tempo de ponta a ponta em ambiente de desenvolvimento com chamadas reais à API do Azure OpenAI.

---

**RNF-003 — Confiabilidade da persistência**  
**Prioridade:** Alta

Uma vez que o conteúdo de uma obra é gerado com sucesso e retornado ao front-end, ele deve estar disponível no banco de dados em todas as requisições subsequentes para aquela obra. Taxa de perda de dados após geração bem-sucedida: **0%**.

**Como verificar:** após cada geração bem-sucedida em testes, consultar diretamente o banco de dados para verificar a presença do registro.

---

**RNF-004 — Conformidade com WCAG 2.1 nível AA nos novos componentes**  
**Prioridade:** Alta

Os novos componentes introduzidos (Insight Card, estados de loading/erro, Alt Text) devem ser conformes com as diretrizes WCAG 2.1 nível AA. Especificamente: contraste mínimo de 4.5:1 para texto normal, navegação por teclado funcional, e anúncios corretos via leitores de tela.

**Como verificar:** avaliação com NVDA ou VoiceOver + axe DevTools durante testes de acessibilidade (doc 12).

---

**RNF-005 — Segurança das credenciais de API**  
**Prioridade:** Alta

As chaves de API do Azure OpenAI e da Harvard Art Museums API não devem ser expostas no código-fonte, em logs de aplicação ou em respostas HTTP retornadas ao front-end. Devem ser armazenadas exclusivamente em variáveis de ambiente do servidor.

**Como verificar:** revisão de código + busca por padrões de chave no repositório antes de qualquer commit.

---

**RNF-006 — Versionamento de prompts**  
**Prioridade:** Média

Os prompts utilizados para geração do Insight Card e do Alt Text devem ser versionados (ex: `v1`, `v2`) e o identificador da versão do prompt deve ser armazenado junto ao conteúdo gerado no banco de dados, permitindo rastrear qual versão produziu cada registro.

**Como verificar:** verificar, após geração, que o campo de versão do prompt está preenchido corretamente no registro do banco de dados.

---

**RNF-007 — Usabilidade do estado de carregamento**  
**Prioridade:** Média

O estado de carregamento do Insight Card deve comunicar ao usuário que o processo está em andamento. O indicador deve ser visível sem que o usuário precise rolar a página, assumindo uma tela com resolução mínima de 1024x768.

**Como verificar:** inspeção visual em resolução 1024x768 durante testes de usabilidade (doc 12).

---

**RNF-008 — Disponibilidade degradada sem IA**  
**Prioridade:** Média

Em caso de indisponibilidade total da API de IA, a plataforma deve permanecer funcional para todas as funcionalidades do MVP original (navegação, filtros, página de detalhe com metadados). Apenas o Insight Card fica indisponível, exibindo mensagem de erro.

**Como verificar:** simular falha da API de IA e verificar que as funcionalidades do MVP continuam operacionais.

---

## Rastreabilidade Rápida

| Requisito | User Stories Relacionadas |
| --------- | ------------------------- |
| RF-001    | US-001, US-002, US-003    |
| RF-002    | US-001                    |
| RF-003    | US-002                    |
| RF-004    | US-001, US-002            |
| RF-005    | US-001, US-006            |
| RF-006    | US-001, US-006            |
| RF-007    | US-004                    |
| RF-008    | US-004                    |
| RF-009    | US-004                    |
| RF-010    | US-005                    |
| RF-011    | US-005, US-006            |
| RF-012    | US-005                    |
| RF-013    | US-003                    |
| RF-014    | US-003                    |
| RF-015    | _(removido)_              |
| RF-016    | US-003                    |
| RF-017    | US-001, US-003            |
| RF-018    | US-003                    |
| RF-019    | US-001, US-006            |
