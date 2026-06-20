# TreeCheck / 3-30-300 Brasil

Plataforma publica para avaliar acesso a infraestrutura verde urbana usando a regra 3-30-300:

- **3** arvores visiveis da residencia
- **30%** de cobertura arborea no entorno
- **300 m** de distancia caminhavel ate uma area verde publica acessivel

O MVP combina diagnostico individual, mapa interativo e indicadores agregados de desigualdade verde por bairro, distrito e municipio.

## Objetivo

Criar uma linguagem simples e verificavel para discutir justica climatica, saude urbana e desigualdade territorial no Brasil.

O produto deve responder duas perguntas:

1. Uma pessoa tem acesso minimo a natureza perto de casa?
2. Quais regioes da cidade tem menos acesso a infraestrutura verde?

## MVP

### Entrada do usuario

O usuario informa:

- Endereco
- Ou localizacao GPS

Pergunta manual obrigatoria:

> Da principal janela da sua residencia voce consegue ver pelo menos 3 arvores?

Opcoes:

- Sim
- Nao
- Nao sei

Entrada opcional:

- Upload de foto da janela

### Saida individual

Exemplo de resultado:

- 3 arvores visiveis: atendido
- Cobertura arborea local: 24%, abaixo da meta
- Parque mais proximo: 180 m, atendido

Resultado:

```text
2/3 criterios atendidos
```

### Mapa

O mapa deve exibir:

- Localizacao do usuario
- Parques e areas verdes proximas
- Cobertura arborea
- Arvores mapeadas, quando disponiveis
- Buffer de 300 m

### Recomendacoes

Exemplos:

- Faltam 6 pontos percentuais para atingir 30% de cobertura arborea.
- O parque mais proximo esta a 480 m.
- Uma nova entrada neste parque reduziria a distancia caminhavel para 230 m.

## Criterios

### Criterio 3: arvores visiveis

#### Primeira versao

Autodeclarado pelo usuario.

Justificativa:

- Barato de implementar
- Rapido de validar
- Evita modelagem 3D complexa no MVP
- Mantem aderencia ao conceito original da regra 3-30-300

#### Segunda versao

Analise de foto da janela.

Pipeline previsto:

- YOLOv11
- GroundingDINO
- Segment Anything

Saidas esperadas:

- 0 arvores
- 1-2 arvores
- 3+ arvores

### Criterio 30: cobertura arborea

Percentual de cobertura arborea em buffer ao redor da residencia.

Raios iniciais:

- 100 m
- 300 m

Ambos devem ser exibidos para o usuario. O valor de 300 m pode ser usado como criterio principal, enquanto 100 m ajuda a explicar a experiencia imediata do entorno.

### Criterio 300: distancia ate area verde publica

Distancia caminhavel ate area verde publica acessivel.

Importante:

- Nao usar distancia em linha reta como criterio final.
- Calcular distancia por rede viaria.
- Considerar entradas de parques quando o dado estiver disponivel.

## Dados

O MVP atual usa um dataset local pequeno de amostra para Sao Paulo, versionado no backend. Ele permite validar o fluxo completo sem depender de downloads externos:

- enderecos conhecidos para geocodificacao local
- areas verdes publicas de exemplo
- manchas de cobertura arborea de exemplo
- pontos de arvores de exemplo
- distancia caminhavel estimada por fator sobre distancia direta

As proximas etapas substituem esse dataset por ingestao OSM, MapBiomas e GeoSampa.

### Nacional

#### MapBiomas

Uso:

- Cobertura vegetal urbana
- Calculo do criterio 30
- Indicadores municipais

Produtos relevantes:

- Vegetacao urbana
- Cobertura vegetal
- Uso e cobertura da terra

Formatos esperados:

- GeoTIFF
- Tiles
- Google Earth Engine

Referencia: [MapBiomas Brasil](https://brasil.mapbiomas.org/)

#### OpenStreetMap

Uso:

- Areas verdes publicas
- Parques, pracas, jardins e reservas
- Rede viaria para calculo de distancia caminhavel

Tags iniciais:

```text
leisure=park
leisure=garden
leisure=recreation_ground
leisure=nature_reserve
```

Referencia: [OpenStreetMap Overpass API](https://overpass-api.de/)

### Sao Paulo

#### GeoSampa: Arborizacao Viaria

Uso:

- Arvores individuais no sistema viario
- Contagem de arvores proximas
- Heatmaps
- Densidade arborea

Referencia: [GeoSampa Metadados - Arborizacao Viaria](https://metadados.geosampa.prefeitura.sp.gov.br/)

#### GeoSampa: Cobertura Vegetal

Uso:

- Calculo preciso do criterio 30
- Indicadores por distrito
- Comparacao com dados nacionais do MapBiomas

Referencia: [GeoSampa](https://geosampa.prefeitura.sp.gov.br/)

## Indicadores agregados

### Por bairro, distrito e municipio

Exibir:

- Percentual da populacao que atende ao criterio 3
- Percentual da populacao que atende ao criterio 30
- Percentual da populacao que atende ao criterio 300
- Score medio 3-30-300
- Distribuicao dos scores individuais

### Indice de Desigualdade Verde

Metricas candidatas:

- Cobertura arborea media
- Distancia media caminhavel ate areas verdes
- Proporcao da populacao sem acesso a areas verdes em ate 300 m
- Distribuicao por renda
- Distribuicao por raca/cor, quando houver dados publicos adequados
- Ranking por distrito, subprefeitura, bairro ou municipio

## Arquitetura

### Frontend

- React
- Next.js
- MapLibre GL

Responsabilidades:

- Captura de endereco ou GPS
- Pergunta autodeclarada do criterio 3
- Exibicao do score
- Mapa interativo
- Camadas de cobertura arborea, parques, arvores e buffers
- Visualizacao de indicadores agregados

### Backend

- FastAPI
- PostGIS

Responsabilidades:

- Geocodificacao ou recebimento de coordenadas
- Calculo dos criterios 30 e 300
- Consulta a camadas espaciais
- Exposicao da API publica
- Persistencia de respostas autodeclaradas, quando houver consentimento

### Processamento espacial

- GeoPandas
- Shapely
- Rasterio

Responsabilidades:

- Ingestao e normalizacao de dados geoespaciais
- Processamento de rasters de cobertura vegetal
- Geracao de buffers
- Intersecoes espaciais
- Agregacoes territoriais

### Hospedagem

Opcoes:

- Railway
- Fly.io
- VPS simples

Por padrao, o desenvolvimento deve rodar localmente.

## Como rodar localmente

Entre no shell de desenvolvimento:

```bash
nix develop
```

Instale as dependencias do frontend:

```bash
cd frontend
npm install
```

Suba o backend:

```bash
python -m uvicorn treecheck_api.main:app --app-dir backend/src --reload
```

Em outro terminal, suba o frontend:

```bash
cd frontend
npm run dev
```

URLs locais:

- Frontend: `http://127.0.0.1:3000`
- Backend: `http://127.0.0.1:8000`
- Healthcheck: `http://127.0.0.1:8000/health`

Geocodificacao:

- O endpoint `/geocode` consulta Nominatim/OpenStreetMap para enderecos reais.
- Se a consulta externa falhar, usa apenas os enderecos locais conhecidos como fallback.
- O backend nao inventa coordenadas para enderecos desconhecidos; nesses casos retorna `404`.

Tambem e possivel executar comandos sem entrar no shell:

```bash
nix develop --command pytest backend/tests
nix develop --command npm run build --prefix frontend
```

Para baixar areas verdes do OpenStreetMap via Overpass para o recorte piloto:

```bash
nix develop --command python tools/fetch_osm_green_areas.py
```

Isso gera `data/processed/green_areas.json`. Quando esse arquivo existe, o backend usa esses dados no criterio 300 e no mapa; caso contrario, usa o dataset local de amostra.

Para baixar arvores individuais e uma camada proxy de cobertura arborea do OSM:

```bash
nix develop --command python tools/fetch_osm_tree_layers.py
```

Isso gera `data/processed/tree_points.json` e `data/processed/canopy_patches.json`. A camada de cobertura OSM e apenas um proxy para o MVP; MapBiomas/GeoSampa continuam sendo as fontes alvo para producao.

Para usar GeoSampa em Sao Paulo, exporte as camadas como GeoJSON pelo portal ou use uma URL GeoJSON acessivel:

```bash
nix develop --command python tools/import_geosampa_canopy.py caminho/para/cobertura_vegetal.geojson
nix develop --command python tools/import_geosampa_trees.py caminho/para/arborizacao_viaria.geojson
```

Os importadores tambem aceitam os ZIPs de Shapefile baixados do GeoSampa:

```bash
nix develop --command python tools/import_geosampa_canopy.py data/raw/SIRGAS_SHP_VEGETACAO_SIGNIFICATIVA.zip
nix develop --command python tools/import_geosampa_trees.py data/raw/SIRGAS_SHP_arvore.zip
nix develop --command python tools/import_geosampa_green_areas.py data/raw/GEOSAMPA_v_praca_largo.zip
```

Esses comandos substituem:

- `data/processed/treecheck.sqlite`, banco operacional com cobertura vegetal, pracas/largos, arvores e indices RTree
- `data/processed/canopy_patches.json`, com fonte `geosampa_cobertura_vegetal`
- `data/processed/tree_points.json`, com fonte `geosampa_arborizacao_viaria`
- `data/processed/green_areas.json`, com fonte `geosampa_praca_largo`

Depois disso, o `/score` passa a reportar a fonte GeoSampa no campo `source`.

Quando `treecheck.sqlite` existe, o backend usa esse banco unico para calcular cobertura, encontrar pracas/largos, buscar arvores proximas e desenhar as camadas no mapa. Os JSONs ficam como fallback leve para ambientes sem SQLite processado.

Por padrao, os importadores filtram o recorte piloto Paulista/Ibirapuera/Centro. Para processar Sao Paulo inteira, use `--all`:

```bash
nix develop --command python tools/import_geosampa_canopy.py data/raw/SIRGAS_SHP_VEGETACAO_SIGNIFICATIVA.zip --all
nix develop --command python tools/import_geosampa_trees.py data/raw/SIRGAS_SHP_arvore.zip --all
nix develop --command python tools/import_geosampa_green_areas.py data/raw/GEOSAMPA_v_praca_largo.zip --all
```

## API inicial

Endpoint:

```http
GET /score?lat=-23.55&lng=-46.63
```

Resposta exemplo:

```json
{
  "trees_visible": true,
  "canopy_100m": 22.4,
  "canopy_300m": 18.1,
  "park_distance": 184,
  "score": 2
}
```

Campos previstos:

- `trees_visible`: resposta autodeclarada do usuario, quando informada
- `canopy_100m`: cobertura arborea estimada no buffer de 100 m
- `canopy_300m`: cobertura arborea estimada no buffer de 300 m
- `park_distance`: distancia caminhavel ate area verde publica acessivel
- `score`: quantidade de criterios atendidos

## Fases

### Fase 1: MVP nacional

- Questionario
- Localizacao por endereco ou GPS
- Areas verdes do OpenStreetMap
- Cobertura vegetal do MapBiomas
- Score individual
- Mapa basico

### Fase 2: Sao Paulo premium

- GeoSampa
- Arborizacao viaria
- Cobertura vegetal detalhada
- Indicadores por distrito
- Upload de foto da janela

### Fase 3: visao computacional

- Deteccao automatica de arvores em fotos
- Segmentacao de copas
- Classificacao em 0, 1-2 ou 3+ arvores
- Possivel integracao com imagens de rua

### Fase 4: visibilidade e simulacao

- Modelo 3D
- Visibilidade real de arvores
- Simulacoes de plantio
- Avaliacao de impacto de novas entradas em parques

## Hipotese estrategica

O score individual e util, mas o maior valor publico pode estar no mapa agregado:

> Quem tem acesso a natureza na cidade?

A regra 3-30-300 funciona como uma linguagem acessivel para transformar dados ambientais complexos em uma discussao publica sobre desigualdade urbana.
