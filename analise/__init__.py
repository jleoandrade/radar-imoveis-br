"""Núcleo de análise do Radar de Imóveis Brasil.

Cada módulo com uma responsabilidade, e nenhum deles depende de interface
gráfica: o pacote roda num GitHub Actions em poucos segundos, com pandas
e requests e mais nada.

* ``caixa``      — lê a lista oficial da Caixa (CSV latin-1, com um campo
                   de texto livre que carrega metade da informação) e
                   devolve uma tabela limpa. Aceita o arquivo nacional e
                   o de um estado só.
* ``tipos``      — normaliza a tipologia, que a Caixa escreve de várias
                   formas, em cinco categorias.
* ``geografia``  — as 27 capitais, o catálogo de regiões metropolitanas e
                   os bairros do Recife. Separa capital, região
                   metropolitana e interior.
* ``custos``     — o que o imóvel custa além do preço: ITBI, cartório,
                   leiloeiro, reforma, provisão de desocupação.
* ``ocupacao``   — lê na página da Caixa se o imóvel existe e se está
                   ocupado, e guarda o roteiro de desocupação.
* ``parecer``    — desconto real, nota, classe, ressalvas e os moldes do
                   texto que a página desenha.
* ``compactar``  — encolhe o arquivo de cada estado para caber no celular.

⚠️ Uma regra atravessa o pacote inteiro: **nome de cidade não identifica
uma cidade no Brasil**. Dezesseis nomes aparecem em mais de um estado na
lista da Caixa. Toda chave de geografia, de pares e de lote carrega a UF.
"""
