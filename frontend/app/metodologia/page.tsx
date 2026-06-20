export default function MetodologiaPage() {
  return (
    <main className="methodPage">
      <article className="methodArticle">
        <p className="eyebrow">Metodologia</p>
        <h1>Como calculamos o TreeCheck</h1>

        <section>
          <h2>Regra 3-30-300</h2>
          <p>
            O TreeCheck resume o acesso a infraestrutura verde urbana em tres criterios: ver pelo menos
            3 arvores da janela principal, ter 30% de cobertura verde no entorno e estar a ate 300 m de
            uma area verde publica.
          </p>
        </section>

        <section>
          <h2>3 arvores visiveis</h2>
          <p>
            No MVP, este criterio e autodeclarado. A pessoa responde se ve pelo menos 3 arvores da
            principal janela da residencia.
          </p>
        </section>

        <section>
          <h2>30% de cobertura verde</h2>
          <p>
            Calculamos a cobertura no raio de 300 m usando dados processados do GeoSampa. A camada atual
            vem de vegetacao significativa e e convertida para manchas de cobertura usadas no calculo
            percentual.
          </p>
        </section>

        <section>
          <h2>300 m ate area verde publica</h2>
          <p>
            Usamos pracas e largos do GeoSampa como areas verdes publicas. A distancia exibida ainda e
            uma estimativa, calculada a partir da proximidade geografica com fator de caminhada. Ela nao
            substitui roteamento real por rede de calcadas e ruas.
          </p>
        </section>

        <section>
          <h2>Fontes atuais</h2>
          <ul>
            <li>GeoSampa: cobertura vegetal significativa.</li>
            <li>GeoSampa: arborizacao viaria.</li>
            <li>GeoSampa: pracas e largos.</li>
            <li>Resposta do usuario: arvores visiveis da janela.</li>
          </ul>
        </section>

        <section>
          <h2>Limitações</h2>
          <p>
            O MVP cobre melhor Sao Paulo capital, porque usa GeoSampa. A distancia ate area verde ainda
            e estimada. O resultado deve ser lido como diagnostico publico e comunicavel, nao como laudo
            tecnico individual.
          </p>
        </section>

        <a className="backLink" href="/">Voltar ao TreeCheck</a>
      </article>
    </main>
  );
}

