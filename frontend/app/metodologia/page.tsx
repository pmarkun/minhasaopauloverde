export default function MetodologiaPage() {
  return (
    <main className="methodPage">
      <article className="methodArticle">
        <p className="eyebrow">Metodologia</p>
        <h1>Como calculamos o Minha Sao Paulo Verde</h1>

        <section>
          <h2>Regra 3-30-300</h2>
          <p>
            O Minha Sao Paulo Verde olha para tres sinais simples do verde perto de casa: se voce ve
            pelo menos 3 arvores da janela, quanto do entorno tem cobertura vegetal e se existe uma
            praca ou area verde publica a uma distancia curta.
          </p>
        </section>

        <section>
          <h2>3 arvores visiveis</h2>
          <p>
            Nesta primeira versao, esta parte vem da sua resposta. A pergunta e direta porque ninguem
            conhece melhor a vista da sua janela do que voce.
          </p>
        </section>

        <section>
          <h2>30% de cobertura verde</h2>
          <p>
            Calculamos a porcentagem de verde dentro de um raio de 300 m usando dados abertos do
            GeoSampa. No mapa, mostramos so as manchas que ficam no entorno da casa informada, para o
            resultado ficar facil de ler e compartilhar.
          </p>
        </section>

        <section>
          <h2>300 m ate area verde publica</h2>
          <p>
            Usamos pracas e largos do GeoSampa como referencia de areas verdes publicas. A distancia
            exibida ainda e uma estimativa, entao o caminho real pode variar conforme entradas,
            calcadas, travessias e barreiras urbanas.
          </p>
        </section>

        <section>
          <h2>Fontes atuais</h2>
          <ul>
            <li>GeoSampa: cobertura vegetal.</li>
            <li>GeoSampa: arborizacao viaria.</li>
            <li>GeoSampa: pracas e largos.</li>
            <li>Resposta da pessoa: arvores visiveis da janela.</li>
          </ul>
        </section>

        <section>
          <h2>Limitações</h2>
          <p>
            Esta versao foi pensada para Sao Paulo capital, porque depende de bases do GeoSampa. O
            resultado e um retrato comunicavel do entorno, nao um laudo tecnico. Nas proximas versoes, a
            distancia podera usar roteamento real por ruas e calcadas.
          </p>
        </section>

        <a className="backLink" href="/">Voltar ao Minha Sao Paulo Verde</a>
      </article>
    </main>
  );
}
