"""Transforma a lista de imóveis no formato que o navegador baixa.

O PROBLEMA, MEDIDO
------------------
No arquivo do Rio de Janeiro — 5.995 imóveis, um terço do acervo nacional —
a lista de registros ocupava 7,47 MB. Onde:

* **4,00 MB (54%) eram os nomes dos campos**, 56 deles repetidos em cada um
  dos 5.995 registros. ``"desconto_anunciado":`` escrito 5.995 vezes.
* 0,97 MB (13%) era o campo ``veredito``, que é a mesma frase com três
  números trocados (resolvido em ``parecer.MOLDES``, não aqui).
* vários campos tinham um único valor distinto no estado inteiro —
  ``situacao``, ``ocupacao_fonte``, ``conferido_em`` — e mesmo assim eram
  gravados por extenso linha a linha.

A SOLUÇÃO
---------
Duas transformações, nenhuma delas perde informação:

1. **Colunar.** Os nomes dos campos aparecem uma vez, em ``campos``, e cada
   imóvel vira uma lista de valores na mesma ordem. Mata os 54%.
2. **Dicionário.** Campo de texto que repete muito (``cidade`` repete 139
   vezes no RJ, ``modalidade`` 1.499, ``situacao`` 5.995) guarda os valores
   distintos uma vez em ``dicionarios[campo]`` e a linha guarda o índice.

A página desfaz isso em dez linhas de JavaScript e volta a ter a mesma lista
de objetos de antes. O formato é escolhido por medição, não por gosto: sem
ele o navegador de celular recebe 8 MB de texto para interpretar só para
mostrar o Rio de Janeiro.

POR QUE NÃO SÓ CONFIAR NO GZIP
------------------------------
O gzip do GitHub Pages já derruba o RJ de 8 MB para 580 KB, porque nome de
campo repetido comprime quase perfeitamente. Mas o gzip resolve a
*transferência*, não o que vem depois: o navegador ainda descomprime 8 MB,
interpreta 8 MB de JSON e monta 5.995 objetos de 56 campos. É aí que celular
antigo engasga. Compactar antes resolve os dois.
"""

from __future__ import annotations

# Campos de texto que viram dicionário. Critério: muita repetição medida no
# acervo real. ``endereco`` e ``veredito`` NÃO entram — são praticamente
# únicos por imóvel (1,0x e 1,5x de repetição no RJ), e dicionário de valores
# únicos só aumenta o arquivo.
CAMPOS_DICIONARIO = (
    "cidade", "bairro", "tipo", "modalidade", "praca", "pagamento",
    "ocupacao", "ocupacao_fonte", "ocupacao_trecho", "nivel_pares",
    "conferido_em", "visto_em",
)

# Campos que a página calcula sozinha e que por isso não viajam.
# Cada um custava entre 0,13 e 0,50 MB no arquivo do Rio.
#
#   mercado_liquido      -> praca != "interior"
#   ocupado              -> ocupacao == "ocupado"
#   ocupacao_desconhecida-> ocupacao == "nao_informada"
#   situacao             -> rótulo de ocupacao, que já vem no índice
#   tem_catalogo_rm      -> é igual para o estado inteiro, vai no resumo
#   regiao_metropolitana -> depende só de (UF, cidade), vai na lista de
#                           cidades do resumo do estado
#   veredito             -> montado a partir de parecer.MOLDES
DERIVAVEIS = (
    "mercado_liquido", "ocupado", "ocupacao_desconhecida", "situacao",
    "tem_catalogo_rm", "regiao_metropolitana", "veredito",
)


def compactar(imoveis: list[dict]) -> dict:
    """Devolve ``{"campos": [...], "dicionarios": {...}, "linhas": [[...]]}``.

    A ordem dos campos é a do primeiro imóvel, e todos os imóveis têm de ter
    os mesmos campos — o gerador monta todos pelo mesmo caminho, então isso
    vale. Campo ausente num registro entra como ``None``, para o formato não
    desalinhar silenciosamente.
    """
    if not imoveis:
        return {"campos": [], "dicionarios": {}, "linhas": []}

    campos = [c for c in imoveis[0] if c not in DERIVAVEIS]

    dicionarios: dict[str, list] = {}
    indices: dict[str, dict] = {}
    for campo in CAMPOS_DICIONARIO:
        if campo in campos:
            dicionarios[campo] = []
            indices[campo] = {}

    linhas = []
    for imovel in imoveis:
        linha = []
        for campo in campos:
            valor = imovel.get(campo)
            if campo in indices:
                chave = "" if valor is None else str(valor)
                posicao = indices[campo].get(chave)
                if posicao is None:
                    posicao = len(dicionarios[campo])
                    dicionarios[campo].append(chave)
                    indices[campo][chave] = posicao
                linha.append(posicao)
            else:
                linha.append(valor)
        linhas.append(linha)

    return {"campos": campos, "dicionarios": dicionarios, "linhas": linhas}


def descompactar(bloco: dict) -> list[dict]:
    """O inverso, em Python. Existe para o teste poder provar a ida e volta.

    A página faz o mesmo em JavaScript. Se esta função e a da página
    discordarem, o teste de ida e volta aqui não pega — por isso o teste da
    página roda com navegador de verdade, contra este mesmo arquivo.
    """
    campos = bloco["campos"]
    dicionarios = bloco.get("dicionarios") or {}
    saida = []
    for linha in bloco["linhas"]:
        imovel = {}
        for posicao, campo in enumerate(campos):
            valor = linha[posicao]
            dic = dicionarios.get(campo)
            imovel[campo] = dic[valor] if dic is not None else valor
        saida.append(imovel)
    return saida
