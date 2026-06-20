# Plano de Implementacao

Este plano desdobra o TreeCheck / 3-30-300 Brasil em etapas sequenciais. A ordem prioriza aprendizado rapido, validacao do produto, baixo custo inicial e evolucao progressiva para analises espaciais mais robustas.

## 1. Fundacao do projeto

### 1.1. Definir escopo do MVP

Objetivo:

- Congelar a primeira versao funcional em torno de score individual e mapa simples.

Entregas:

- Definicao dos criterios que entram no MVP
- Definicao do territorio piloto
- Definicao das fontes de dados da primeira versao
- Definicao do que sera mockado, estimado ou calculado de fato

Decisoes iniciais recomendadas:

- Usar criterio 3 autodeclarado
- Usar cobertura arborea por buffer de 100 m e 300 m
- Usar distancia caminhavel ate areas verdes do OpenStreetMap
- Comecar por Sao Paulo ou por um municipio piloto antes de expandir para o Brasil

### 1.2. Criar estrutura tecnica inicial

Objetivo:

- Separar frontend, backend, dados e documentacao desde o inicio.

Estrutura sugerida:

```text
.
├── README.md
├── PLAN.md
├── frontend/
├── backend/
├── data/
├── notebooks/
└── infra/
```

Entregas:

- Projeto Next.js em `frontend/`
- Projeto FastAPI em `backend/`
- Configuracao Nix para ambiente local
- Scripts de desenvolvimento
- Configuracao basica de lint, teste e formatacao

### 1.3. Definir contratos de API

Objetivo:

- Permitir que frontend e backend evoluam em paralelo.

Entregas:

- Especificacao do endpoint `GET /score`
- Especificacao de respostas de erro
- Modelo de resposta do score individual
- Modelo de recomendacoes
- Modelo GeoJSON para camadas do mapa

Primeiro contrato:

```http
GET /score?lat=-23.55&lng=-46.63&trees_visible=true
```

Resposta esperada:

```json
{
  "location": {
    "lat": -23.55,
    "lng": -46.63
  },
  "criteria": {
    "trees_visible": {
      "status": "passed",
      "value": true,
      "source": "self_reported"
    },
    "canopy": {
      "status": "warning",
      "canopy_100m": 22.4,
      "canopy_300m": 18.1,
      "target": 30
    },
    "park_access": {
      "status": "passed",
      "distance_m": 184,
      "target_m": 300
    }
  },
  "score": {
    "passed": 2,
    "total": 3
  },
  "recommendations": []
}
```

## 2. Prototipo navegavel sem dados reais

### 2.1. Construir tela principal

Objetivo:

- Validar o fluxo do usuario antes de investir em processamento espacial.

Entregas:

- Campo de endereco
- Botao para usar GPS
- Pergunta do criterio 3
- Botao para calcular score
- Area de resultado
- Mapa inicial

Fluxo:

1. Usuario informa endereco ou GPS.
2. Usuario responde se ve pelo menos 3 arvores.
3. Frontend chama o backend.
4. Backend retorna dados mockados.
5. Frontend exibe score e mapa.

### 2.2. Implementar backend mockado

Objetivo:

- Estabilizar o contrato de API.

Entregas:

- Endpoint `GET /health`
- Endpoint `GET /score`
- Dados simulados coerentes
- Testes unitarios basicos do calculo de score

Regras mockadas:

- `trees_visible=true` soma 1 ponto
- `canopy_300m >= 30` soma 1 ponto
- `park_distance <= 300` soma 1 ponto

### 2.3. Implementar mapa basico

Objetivo:

- Criar a experiencia visual minima do produto.

Entregas:

- MapLibre GL no frontend
- Marcador da localizacao do usuario
- Buffer visual de 300 m
- Pontos ou poligonos mockados de areas verdes
- Camada mockada de cobertura arborea

## 3. Geocodificacao e localizacao

### 3.1. Entrada por GPS

Objetivo:

- Permitir uso sem endereco digitado.

Entregas:

- Integracao com Geolocation API do navegador
- Tratamento de permissao negada
- Tratamento de erro de precisao/localizacao indisponivel
- Estado de carregamento

### 3.2. Entrada por endereco

Objetivo:

- Converter endereco em coordenadas.

Opcoes:

- Nominatim/OpenStreetMap para prototipo
- Provedor pago ou cacheado em producao, se necessario

Entregas:

- Campo de busca
- Lista de sugestoes ou resultado unico
- Normalizacao de endereco
- Armazenamento apenas das coordenadas necessarias ao calculo, salvo consentimento explicito

### 3.3. Validacao de territorio

Objetivo:

- Evitar resposta falsa para regioes sem dados.

Entregas:

- Checagem se a coordenada esta dentro da area coberta pelo MVP
- Mensagem clara para localizacoes fora da cobertura
- Metadado `coverage_area` na API

## 4. Criterio 3: autodeclaracao

### 4.1. Modelar resposta do usuario

Objetivo:

- Registrar a resposta de forma simples e auditavel.

Valores:

- `yes`
- `no`
- `unknown`

Mapeamento inicial:

- `yes`: criterio atendido
- `no`: criterio nao atendido
- `unknown`: criterio indeterminado e nao soma ponto

Entregas:

- Componente de pergunta no frontend
- Campo correspondente na API
- Testes das regras de score

### 4.2. Preparar consentimento para uso agregado

Objetivo:

- Permitir indicadores sem expor informacao sensivel.

Entregas:

- Texto curto de consentimento
- Opcao de nao enviar resposta para indicadores agregados
- Estrategia para anonimizar ou agregar respostas

## 5. Criterio 30: cobertura arborea

### 5.1. Escolher fonte inicial

Objetivo:

- Definir a primeira fonte operacional de cobertura vegetal.

Opcoes:

- MapBiomas para cobertura nacional
- GeoSampa para piloto em Sao Paulo

Decisao recomendada:

- Usar GeoSampa se o piloto for Sao Paulo.
- Usar MapBiomas se a prioridade for cobertura nacional desde o inicio.

### 5.2. Ingerir dados raster ou vetoriais

Objetivo:

- Colocar dados de cobertura no formato adequado para consulta.

Entregas:

- Script de download ou instrucao manual de obtencao
- Pasta `data/raw/`
- Pasta `data/processed/`
- Metadados da fonte
- CRS padronizado

Cuidados:

- Registrar data da fonte
- Registrar licenca
- Evitar commitar arquivos grandes no Git

### 5.3. Calcular cobertura por buffer

Objetivo:

- Calcular percentual de cobertura arborea no entorno da coordenada.

Etapas:

1. Receber `lat` e `lng`.
2. Projetar coordenada para CRS metrico adequado.
3. Gerar buffers de 100 m e 300 m.
4. Intersectar buffer com cobertura arborea.
5. Calcular area coberta.
6. Dividir pela area total do buffer.
7. Retornar percentuais.

Entregas:

- Funcao `calculate_canopy(lat, lng, radius_m)`
- Testes com geometrias pequenas e conhecidas
- Endpoint retornando `canopy_100m` e `canopy_300m`

### 5.4. Otimizar consultas

Objetivo:

- Tornar o calculo viavel para uso publico.

Estrategias:

- Preprocessar tiles
- Usar PostGIS com indices espaciais
- Cachear resultados por celula de grade
- Precalcular indicadores por setor censitario, bairro ou quadricula

## 6. Criterio 300: acesso caminhavel a areas verdes

### 6.1. Ingerir areas verdes do OpenStreetMap

Objetivo:

- Montar camada inicial de areas verdes publicas.

Tags iniciais:

- `leisure=park`
- `leisure=garden`
- `leisure=recreation_ground`
- `leisure=nature_reserve`

Entregas:

- Consulta Overpass documentada
- Script de ingestao
- Normalizacao para tabela `green_areas`
- Filtro inicial de geometrias invalidas

### 6.2. Definir acessibilidade publica

Objetivo:

- Evitar considerar areas verdes privadas ou inacessiveis.

Regras iniciais:

- Incluir `access=yes`, `access=permissive` ou sem tag de restricao
- Excluir `access=private`
- Marcar casos incertos para revisao

Entregas:

- Campo `access_status`
- Campo `source_tags`
- Testes de classificacao por tags

### 6.3. Ingerir rede viaria caminhavel

Objetivo:

- Calcular distancia por deslocamento real, nao em linha reta.

Fontes:

- OpenStreetMap

Regras iniciais:

- Incluir ruas caminhaveis, calcadas e caminhos
- Excluir vias inacessiveis a pedestres
- Considerar travessias quando disponiveis

Entregas:

- Tabela de segmentos caminhaveis
- Indices espaciais
- Validacao visual em mapa

### 6.4. Calcular distancia ate area verde

Objetivo:

- Retornar a menor distancia caminhavel ate area verde publica.

Etapas:

1. Receber coordenada do usuario.
2. Conectar ponto a rede caminhavel mais proxima.
3. Identificar areas verdes candidatas proximas.
4. Usar entradas do parque quando existirem.
5. Calcular menor caminho na rede.
6. Retornar distancia em metros e area verde correspondente.

Entregas:

- Funcao `calculate_park_distance(lat, lng)`
- Resultado com distancia e identificador da area verde
- Testes com rede pequena artificial
- Fallback claramente marcado quando houver apenas distancia em linha reta

## 7. Banco de dados espacial

### 7.1. Configurar PostGIS

Objetivo:

- Centralizar dados espaciais e consultas geograficas.

Entregas:

- Banco local Postgres + PostGIS
- Scripts de migracao
- Tabelas iniciais
- Indices GiST

Tabelas candidatas:

- `green_areas`
- `tree_points`
- `canopy_polygons`
- `walking_network_edges`
- `admin_boundaries`
- `score_events`

### 7.2. Criar camada de limites administrativos

Objetivo:

- Suportar indicadores agregados.

Entregas:

- Bairros
- Distritos
- Municipios
- Subprefeituras, quando aplicavel
- Relacao entre ponto do usuario e territorio

## 8. Recomendacoes

### 8.1. Regras simples de recomendacao

Objetivo:

- Transformar diagnostico em orientacao compreensivel.

Regras iniciais:

- Se cobertura menor que 30%, informar diferenca em pontos percentuais.
- Se parque esta a mais de 300 m, informar distancia excedente.
- Se criterio 3 for negativo, sugerir arborizacao de rua, patio ou fachada verde como pauta local.

Entregas:

- Gerador de recomendacoes no backend
- Textos curtos no frontend
- Testes de regras

### 8.2. Recomendacao por nova entrada de parque

Objetivo:

- Avaliar impacto de acessos adicionais a areas verdes existentes.

Etapas:

1. Identificar parque proximo em linha reta.
2. Comparar distancia caminhavel atual.
3. Simular ponto de entrada mais proximo da residencia.
4. Recalcular distancia caminhavel.
5. Retornar diferenca estimada.

Entregas:

- Prototipo analitico
- Marcacao clara de que se trata de simulacao
- Camada visual de entrada sugerida

## 9. Indicadores agregados

### 9.1. Definir unidade territorial

Objetivo:

- Escolher como os resultados publicos serao comparados.

Opcoes:

- Bairro
- Distrito
- Municipio
- Setor censitario
- Grade regular

Decisao recomendada:

- Usar distrito ou municipio no inicio.
- Evoluir para setor censitario ou grade quando houver mais robustez estatistica.

### 9.2. Gerar indicadores por territorio

Objetivo:

- Medir desigualdade verde de forma agregada.

Indicadores:

- Cobertura arborea media
- Distancia media ate area verde
- Percentual estimado de moradores atendidos pelo criterio 30
- Percentual estimado de moradores atendidos pelo criterio 300
- Percentual autodeclarado do criterio 3, quando houver amostra suficiente

Entregas:

- Job de agregacao
- Tabela `territory_indicators`
- Endpoint de consulta
- Mapa coropletico

### 9.3. Incorporar dados socioeconomicos

Objetivo:

- Criar indice de desigualdade verde.

Fontes candidatas:

- IBGE
- Censo
- Dados municipais abertos

Metricas:

- Renda
- Raca/cor
- Densidade populacional
- Idade ou vulnerabilidade climatica, quando disponivel

Cuidados:

- Trabalhar apenas com dados agregados
- Evitar inferencias individuais sensiveis
- Documentar limitacoes

## 10. Experiencia de usuario

### 10.1. Resultado individual

Objetivo:

- Mostrar o diagnostico de forma simples.

Componentes:

- Placar `0/3`, `1/3`, `2/3` ou `3/3`
- Status de cada criterio
- Valores numericos
- Recomendacoes
- Link para compartilhar resultado agregado sem expor endereco exato

### 10.2. Mapa publico

Objetivo:

- Comunicar desigualdade territorial.

Camadas:

- Cobertura arborea
- Areas verdes
- Distancia ate areas verdes
- Indicador por bairro/distrito/municipio
- Arvores mapeadas, quando houver

Controles:

- Liga/desliga camadas
- Busca de endereco
- Selecionar territorio
- Legenda

## 11. Privacidade e governanca

### 11.1. Minimizar dados pessoais

Objetivo:

- Reduzir risco desde o MVP.

Regras:

- Nao armazenar endereco completo por padrao.
- Armazenar coordenada aproximada apenas com consentimento.
- Agregar respostas antes de publicar mapas.
- Nunca exibir pontos individuais publicamente.

Entregas:

- Politica curta de privacidade
- Modelo de consentimento
- Parametro para arredondamento ou agregacao espacial

### 11.2. Documentar incertezas

Objetivo:

- Evitar falsa precisao.

Entregas:

- Metadados por fonte
- Aviso sobre resolucao espacial
- Aviso sobre qualidade de dados OSM
- Diferenciacao entre dado calculado, autodeclarado e estimado

## 12. Testes e qualidade

### 12.1. Testes backend

Objetivo:

- Garantir consistencia dos calculos.

Testes:

- Calculo de score
- Regra do criterio 3
- Percentual de cobertura por geometria artificial
- Distancia em rede artificial
- Serializacao da API

### 12.2. Testes frontend

Objetivo:

- Garantir fluxo principal sem regressao.

Testes:

- Renderizacao da tela principal
- Estados de carregamento e erro
- Envio de resposta autodeclarada
- Exibicao correta do score
- Mapa carrega com marcador e buffer

### 12.3. Validacao espacial

Objetivo:

- Conferir se os resultados fazem sentido no territorio real.

Procedimento:

1. Escolher 10 pontos conhecidos.
2. Comparar cobertura calculada com inspecao visual.
3. Comparar distancia ate parques com rota manual.
4. Registrar divergencias.
5. Ajustar filtros e regras.

## 13. Deploy

### 13.1. Desenvolvimento local

Objetivo:

- Ter ambiente reproduzivel.

Entregas:

- `nix develop`
- Backend local
- Frontend local
- Banco PostGIS local ou containerizado
- Dados de amostra pequenos

### 13.2. Staging

Objetivo:

- Publicar versao de teste.

Opcoes:

- Railway
- Fly.io
- VPS simples

Entregas:

- Backend em staging
- Frontend em staging
- Banco de staging
- Variaveis de ambiente
- Dados piloto

### 13.3. Producao

Objetivo:

- Publicar versao publica com dados documentados.

Pre-requisitos:

- Politica de privacidade
- Monitoramento basico
- Backups do banco
- Logs sem dados sensiveis
- Limites de taxa para API publica

## 14. Evolucao futura

### 14.1. Foto da janela

Objetivo:

- Reduzir dependencia de autodeclaracao.

Etapas:

1. Upload opcional.
2. Armazenamento temporario.
3. Deteccao de arvores.
4. Segmentacao de copas.
5. Classificacao em 0, 1-2 ou 3+.
6. Exclusao ou anonimização da imagem conforme politica de privacidade.

### 14.2. Street View e imagens de rua

Objetivo:

- Automatizar estimativa visual sem depender do usuario.

Cuidados:

- Licenciamento das imagens
- Cobertura desigual
- Datas das imagens
- Privacidade

### 14.3. Modelo 3D e visibilidade real

Objetivo:

- Estimar se arvores sao realmente visiveis a partir da residencia.

Requisitos:

- Altura de edificacoes
- Modelo digital de superficie
- Posicao de janelas ou fachadas
- Altura e copa de arvores

### 14.4. Simulacoes de plantio

Objetivo:

- Transformar diagnostico em planejamento urbano.

Perguntas:

- Onde plantar arvores maximiza o numero de pessoas que atingem 30%?
- Quais novas entradas reduzem mais a distancia ate parques?
- Quais territorios tem maior deficit verde?

## 15. Sequencia recomendada de execucao

1. Criar estrutura do repositorio.
2. Criar backend FastAPI com `/health` e `/score` mockado.
3. Criar frontend Next.js com formulario, pergunta do criterio 3 e resultado.
4. Adicionar MapLibre com marcador e buffer mockado.
5. Implementar entrada por GPS.
6. Implementar geocodificacao por endereco.
7. Definir territorio piloto.
8. Ingerir areas verdes do OpenStreetMap.
9. Calcular distancia inicial ate parques, primeiro com fallback em linha reta marcado como estimativa.
10. Ingerir rede caminhavel e substituir por distancia em rede.
11. Ingerir cobertura vegetal.
12. Calcular cobertura em buffers de 100 m e 300 m.
13. Persistir eventos consentidos e agregados.
14. Criar indicadores por territorio.
15. Criar mapa publico de desigualdade verde.
16. Validar resultados com pontos reais.
17. Publicar staging.
18. Revisar privacidade, textos e fontes.
19. Publicar MVP.
20. Planejar fase de foto da janela e visao computacional.

## 16. Marco de MVP pronto

O MVP pode ser considerado pronto quando:

- O usuario consegue informar endereco ou GPS.
- O usuario responde ao criterio 3.
- O sistema retorna score 3-30-300.
- O mapa mostra localizacao, buffer e areas verdes.
- A cobertura arborea e calculada a partir de uma fonte documentada.
- A distancia ate area verde e calculada por rede ou marcada claramente como estimativa.
- O sistema exibe recomendacoes basicas.
- As limitacoes dos dados estao documentadas.
- Existe pelo menos um indicador agregado por territorio piloto.

