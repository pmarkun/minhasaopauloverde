export default function MetodologiaPage() {
  return (
    <main className="methodPage">
      <article className="methodArticle">
        <p className="eyebrow">Metodologia</p>
        <h1>Como calculamos o Minha São Paulo Verde</h1>

        <section>
          <h2>Regra 3-30-300</h2>
          <p>
            O Minha São Paulo Verde olha para três sinais simples do verde perto de casa: se você vê
            pelo menos 3 árvores da janela, quanto do entorno tem cobertura vegetal e se existe uma
            praça ou área verde pública a uma distância curta.
          </p>
        </section>

        <section>
          <h2>3 árvores visíveis</h2>
          <p>
            Nesta primeira versão, esta parte vem da sua resposta. A pergunta é direta porque ninguém
            conhece melhor a vista da sua janela do que você.
          </p>
        </section>

        <section>
          <h2>30% de cobertura verde</h2>
          <p>
            Calculamos a porcentagem de verde dentro de um raio de 300 m usando dados abertos do
            <a href="https://geosampa.prefeitura.sp.gov.br/" rel="noreferrer" target="_blank">GeoSampa</a>.
            No mapa, mostramos só as manchas que ficam no entorno da casa informada, para o resultado
            ficar fácil de ler e compartilhar.
          </p>
        </section>

        <section>
          <h2>300 m até área verde pública</h2>
          <p>
            Usamos praças e largos do
            <a href="https://geosampa.prefeitura.sp.gov.br/" rel="noreferrer" target="_blank"> GeoSampa</a>
            como referência de áreas verdes públicas. A distância exibida ainda é uma estimativa, então
            o caminho real pode variar conforme entradas, calçadas, travessias e barreiras urbanas.
          </p>
        </section>

        <section>
          <h2>Fontes atuais</h2>
          <ul>
            <li>
              <a href="https://geosampa.prefeitura.sp.gov.br/" rel="noreferrer" target="_blank">GeoSampa</a>:
              cobertura vegetal.
            </li>
            <li>
              <a href="https://metadados.geosampa.prefeitura.sp.gov.br/" rel="noreferrer" target="_blank">
                GeoSampa Metadados
              </a>:
              arborização viária.
            </li>
            <li>
              <a href="https://geosampa.prefeitura.sp.gov.br/" rel="noreferrer" target="_blank">GeoSampa</a>:
              praças e largos.
            </li>
            <li>Resposta da pessoa: árvores visíveis da janela.</li>
          </ul>
        </section>

        <section>
          <h2>Limitações</h2>
          <p>
            Esta versão foi pensada para São Paulo capital, porque depende de bases do GeoSampa. O
            resultado é um retrato comunicável do entorno, não um laudo técnico. Nas próximas versões, a
            distância poderá usar roteamento real por ruas e calçadas.
          </p>
        </section>

        <a className="backLink" href="/">Voltar ao Minha São Paulo Verde</a>
      </article>
    </main>
  );
}
