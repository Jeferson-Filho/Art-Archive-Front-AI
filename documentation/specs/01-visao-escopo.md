# Documento de Visão e Escopo — Art Archive AI

**Versão:** 1.0  
**Data:** 2026-06-23  
**Status:** Aprovado

---

## 1. Identificação do Projeto

| Campo                     | Valor                                                                              |
| ------------------------- | ---------------------------------------------------------------------------------- |
| **Nome do Projeto**       | Art Archive: Expansão com IA Generativa para Contextualização e Comparação de Arte |
| **Instituição**           | UNESP — Universidade Estadual Paulista, Campus Rio Claro                           |
| **Curso**                 | Bacharelado em Ciências da Computação                                              |
| **Disciplina**            | Projetos em Computação I — 1º Semestre/2026                                        |
| **Orientador**            | Prof. Alexandro Jose Baldassin (DEMAC)                                             |
| **Aluno / Desenvolvedor** | Jeferson Patrick Dietrich Filho (RA 221154231)                                     |
| **Membro Externo**        | Pedro Henrique Potenza Fernandes (autor do MVP original)                           |
| **Repositório Front-end** | `Art-Archive-Front-AI`                                                             |
| **Período de Execução**   | 14/03/2026 — 10/07/2026                                                            |

---

## 2. Problema

O acesso qualificado à história da arte permanece concentrado em contextos privilegiados: museus físicos com mediação especializada, cursos de formação acadêmica ou guias profissionais. Fora desses ambientes, a maioria das plataformas digitais de arte — incluindo a versão MVP do Art Archive — oferece ao usuário apenas metadados básicos de uma obra: título, autor, data e dimensões.

Essa abordagem é insuficiente para criar uma experiência cultural significativa. O usuário que acessa uma obra isolada não recebe:

- **Contextualização histórica**: o período, o movimento artístico e as influências que moldaram a obra e seu autor.
- **Análise comparativa**: referências a outros artistas e obras com paleta, técnica ou estilo semelhantes.
- **Acessibilidade descritiva**: descrição adequada da imagem para usuários que dependem de leitores de tela.

O resultado é uma barreira de acesso ao conhecimento cultural que afeta desproporcionalmente usuários sem formação especializada, fora de centros urbanos, ou com deficiência visual — exatamente o público que uma plataforma digital deveria prioritariamente alcançar.

---

## 3. Objetivo do Produto

### 3.1 Objetivo Geral

Transformar o Art Archive — originalmente um catálogo visual navegável — em um ambiente de descoberta e aprendizado cultural mediado por Inteligência Artificial generativa, sem substituir a infraestrutura existente do MVP.

### 3.2 Objetivos Específicos

1. Implementar o **Insight Card**, um painel narrativo gerado por IA que exibe contextualização histórica do artista e da obra, e análise comparativa com artistas e obras de características semelhantes em termos de paleta, técnica e estilo.
2. Implementar um **sistema de persistência sob demanda** que armazena o conteúdo gerado no PostgreSQL na primeira visita a uma obra, eliminando chamadas redundantes à API de IA em acessos subsequentes.
3. Implementar **geração automática de Alt Text** descritivo e educativo para imagens das obras via LLM multimodal, integrado ao pipeline de persistência.
4. Garantir **suporte completo a leitores de tela** por meio de atributos ARIA e semântica HTML nos novos componentes, tornando o conteúdo gerado pela IA acessível a tecnologias assistivas.
5. Produzir **documentação técnica completa** do sistema expandido, incluindo arquitetura, contrato de API, esquema de banco de dados e especificação de prompts.
6. Conduzir um **estudo de viabilidade técnica** para futura implementação de busca vetorial, RAG e recomendação baseada em embeddings.

---

## 4. Stakeholders

| Stakeholder                          | Papel                            | Interesse no Projeto                                                                                |
| ------------------------------------ | -------------------------------- | --------------------------------------------------------------------------------------------------- |
| **Jeferson Patrick Dietrich Filho**  | Desenvolvedor / Aluno            | Implementar e entregar o produto dentro do prazo e com qualidade acadêmica                          |
| **Prof. Alexandro Jose Baldassin**   | Orientador                       | Garantir alinhamento acadêmico, rigor técnico e viabilidade da proposta                             |
| **Pedro Henrique Potenza Fernandes** | Membro Externo / Autor do MVP    | Referência técnica sobre decisões de arquitetura do projeto original                                |
| **Usuário Final**                    | Visitante da plataforma          | Acessar contextualização cultural rica sobre obras de arte sem necessitar de formação especializada |
| **Usuário com Deficiência Visual**   | Visitante que usa leitor de tela | Consumir o conteúdo visual e narrativo das obras via tecnologias assistivas                         |
| **UNESP / Banca Avaliadora**         | Instituição acadêmica            | Avaliar a qualidade técnica, documentação e impacto do projeto entregue                             |

---

## 5. Escopo do Projeto

### 5.1 Dentro do Escopo

As seguintes funcionalidades e entregas fazem parte desta expansão e serão implementadas:

**Funcionalidades de Produto:**

- **Insight Card Multimodal:** geração automática via LLM de dois blocos narrativos por obra — contextualização histórica (artista, período, movimento) e análise comparativa (artistas e obras semelhantes por paleta, técnica e estilo).
- **Sistema de Persistência sob Demanda:** verificação da existência de análise prévia no banco de dados antes de invocar a IA; armazenamento permanente do conteúdo gerado no PostgreSQL na primeira chamada.
- **Geração de Alt Text via IA:** descrição automática educativa e descritiva das imagens das obras, persistida junto ao conteúdo do Insight Card.
- **Suporte a Leitores de Tela:** implementação de atributos ARIA e semântica HTML nos componentes do Insight Card e Alt Text para conformidade com diretrizes de acessibilidade.
- **Migração de autenticação:** transição do Firebase Auth para o novo banco de dados PostgreSQL, mantendo paridade funcional.
- **Tela de administração:** painel básico de gestão para monitoramento do conteúdo gerado pela IA.

**Documentação e Entregáveis Acadêmicos:**

- Conjunto completo de documentos de especificação (Spec-Driven Development), conforme planejado em `/documentation/specs/`.
- Relatório técnico final com análise qualitativa do conteúdo gerado.
- Estudo de viabilidade técnica sobre embeddings, RAG e busca vetorial.
- Plano de testes e avaliação de qualidade do conteúdo gerado.

### 5.2 Fora do Escopo

Os seguintes itens estão explicitamente excluídos desta expansão:

- **Implementação de busca vetorial / RAG**: será apenas objeto de estudo de viabilidade técnica. Nenhuma infraestrutura de embeddings será implantada em produção neste semestre.
- **Recomendações personalizadas baseadas em histórico do usuário**: fora do escopo de IA desta expansão.
- **Funcionalidades do MVP original**: grade de obras com lazy loading, sistema de filtros, página de detalhe básica e paleta de cores predominante foram entregues no projeto anterior e não serão reescritas — apenas estendidas.
- **Treinamento ou fine-tuning de modelos**: o projeto consome APIs de LLM existentes (Azure OpenAI); nenhum modelo será treinado ou ajustado.
- **Moderação ou curadoria manual do conteúdo gerado**: o pipeline é automático; revisão humana sistemática do conteúdo não está prevista nesta fase.

---

## 6. Restrições

### 6.1 Restrições Técnicas

- **Harvard Art Museums API**: utilizada sob licença não-comercial educacional. Limites de taxa de requisições e disponibilidade do serviço externo são fatores fora do controle do projeto.
- **Azure OpenAI**: toda geração de conteúdo depende da disponibilidade e dos limites de cota do serviço Azure OpenAI. Custos de inferência devem ser mantidos dentro do orçamento educacional disponível.
- **Compatibilidade com infraestrutura existente**: o back-end em Python e o front-end em Next.js/TypeScript devem permanecer compatíveis com a infraestrutura do MVP original durante toda a expansão.
- **PostgreSQL como único banco de dados**: nenhum banco de dados adicional (ex: banco vetorial dedicado) será introduzido nesta fase.

### 6.2 Restrições de Prazo

- O projeto segue o cronograma do 1º Semestre/2026, com início em 14/03/2026 e entrega final entre 04/07/2026 e 10/07/2026.
- Marcos intermediários definidos no Plano de Atividades (entrega do plano oficial: semana 6; refinamento UX e QA: semana 12; entrega final: semana 17) são fixos e definidos pela disciplina.

### 6.3 Restrições de Equipe

- O projeto é desenvolvido individualmente por um único aluno, sem equipe de suporte técnico dedicada.
- A orientação ocorre de forma periódica e não contínua, o que exige autonomia de decisão técnica por parte do desenvolvedor.

---

## 7. Critérios de Sucesso do Projeto

O projeto será considerado bem-sucedido quando todos os critérios abaixo forem atendidos:

1. **Insight Card funcional**: ao acessar qualquer página de obra, o Insight Card é exibido com os dois blocos narrativos (contextualização histórica e análise comparativa), gerados corretamente pela IA.
2. **Persistência verificável**: a segunda visita a uma obra não invoca a API de IA — o conteúdo é servido diretamente do banco de dados PostgreSQL.
3. **Alt Text gerado e persistido**: toda obra processada pelo pipeline possui Alt Text armazenado no banco e renderizado no atributo `alt` da imagem correspondente.
4. **Acessibilidade validada**: os componentes do Insight Card e Alt Text passam por avaliação de acessibilidade com leitor de tela, sem erros críticos de ARIA.
5. **Documentação completa**: todos os 15 documentos do plano de Spec-Driven Development estão finalizados em `/documentation/specs/`.
6. **Protótipo demonstrável**: a plataforma expandida é acessível via ambiente de desenvolvimento ou deploy e pode ser apresentada à banca avaliadora em funcionamento.
7. **Relatório técnico entregue**: o relatório documenta decisões de arquitetura, estratégia de prompt engineering, análise qualitativa do conteúdo gerado e estudo de viabilidade de embeddings/RAG.

---

## 8. Premissas

As seguintes suposições são assumidas como verdadeiras para o planejamento e execução do projeto:

1. **Disponibilidade da Harvard Art Museums API**: a API permanecerá acessível e com os metadados necessários (imagem, título, artista, data, técnica, período) durante todo o semestre.
2. **Acesso ao Azure OpenAI dentro do orçamento educacional**: o modelo multimodal disponível via Azure OpenAI suportará o volume de chamadas necessário para desenvolvimento, testes e demonstração sem custo proibitivo.
3. **Estabilidade da infraestrutura do MVP**: o front-end em Next.js/TypeScript e o back-end em Python do projeto original permanecem funcionais como base de integração, sem necessidade de reescrita estrutural.
4. **Imagens das obras são acessíveis via URL pública**: as imagens retornadas pela Harvard Art Museums API podem ser enviadas ao modelo multimodal para geração de Alt Text e análise visual.
5. **PostgreSQL como banco de dados de destino**: a instância PostgreSQL estará disponível e configurada para o armazenamento do conteúdo gerado pela IA durante todo o período de desenvolvimento.
6. **Conteúdo gerado em inglês é aceitável**: dado que a Harvard Art Museums API retorna metadados predominantemente em inglês, o conteúdo gerado pela IA poderá ser em inglês sem comprometer a proposta do projeto nesta fase.

---

## 9. Índice de Documentos de Especificação

Todos os documentos seguem a abordagem Spec-Driven Development: nenhuma funcionalidade é implementada sem especificação prévia aprovada.

| #   | Documento                                                     | Objetivo                                                                                                                       | Status       |
| --- | ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | ------------ |
| 01  | Documento de Visão / Escopo                                   | Define o problema, objetivo do produto, stakeholders e limites do que está dentro/fora do escopo. Base de tudo que vem depois. | ✅ Concluído |
| 02  | Requisitos Funcionais e Não Funcionais                        | Especifica o que o sistema deve fazer (funcional) e com que qualidade (não funcional — performance, segurança, usabilidade).   | ⬜ Pendente  |
| 03  | Casos de Uso (atores e funcionalidades, Gherkin)              | Descreve interações entre usuário e sistema em cenários concretos e testáveis.                                                 | ⬜ Pendente  |
| 04  | Arquitetura do Sistema (componentes, implantação, sequência)  | Mostra como o sistema é estruturado tecnicamente: módulos, infraestrutura, fluxo de chamadas.                                  | ⬜ Pendente  |
| 05  | Banco de Dados (DER, esquema relacional, dicionário de dados) | Modela como os dados são armazenados e relacionados.                                                                           | ⬜ Pendente  |
| 06  | Diagrama de Fluxo de Persistência                             | Detalha especificamente a lógica de "verificar antes de gerar" — o mecanismo de cache do Insight Card.                         | ⬜ Pendente  |
| 07  | Especificação de Interface (API Contract)                     | Define contratos formais de cada endpoint: request, response, erros.                                                           | ⬜ Pendente  |
| 08  | Navegação e Fluxo (diagrama de navegabilidade)                | Mapeia as telas e transições da experiência do usuário.                                                                        | ⬜ Pendente  |
| 09  | Pipeline de IA (Insight Card e Alt Text)                      | Detalha o fluxo técnico específico de geração de conteúdo por IA, do input ao output persistido.                               | ⬜ Pendente  |
| 10  | Design do Card                                                | Wireframe/mockup visual do Insight Card, incluindo estados (loading, gerado, erro).                                            | ⬜ Pendente  |
| 11  | Documento de Prompt Engineering                               | Documenta a estratégia, versionamento e evolução dos prompts usados.                                                           | ⬜ Pendente  |
| 12  | Plano de Testes (escopo, critérios de aceite)                 | Define o que será testado e como o sucesso é medido, antes de testar.                                                          | ⬜ Pendente  |
| 13  | Relatório de Testes (Alfa, Beta, resultados)                  | Registra os resultados reais das rodadas de teste.                                                                             | ⬜ Pendente  |
| 14  | Avaliação de Qualidade do Conteúdo Gerado                     | Critérios e resultados específicos para avaliar a qualidade do output de IA (precisão histórica, alucinação, coerência).       | ⬜ Pendente  |
| 15  | Plano de Gerenciamento de Riscos                              | Lista riscos técnicos e de cronograma, com probabilidade, impacto e mitigação.                                                 | ⬜ Pendente  |
| 16  | Matriz de Rastreabilidade de Requisitos                       | Conecta cada requisito a um caso de uso, componente de arquitetura e teste.                                                    | ⬜ Pendente  |
| 17  | Diário de Desenvolvimento                                     | Registro contínuo do processo, decisões e obstáculos ao longo do semestre.                                                     | ⬜ Pendente  |
| 18  | Relatório Técnico Final                                       | Síntese de decisões arquiteturais, resultados e análise qualitativa — entregável final do semestre.                            | ⬜ Pendente  |
| 19  | Estudo de Viabilidade Técnica (RAG/Embeddings)                | Documento de viabilidade para expansão futura com busca vetorial e recomendação baseada em embeddings.                         | ⬜ Pendente  |
