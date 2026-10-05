"""O parecer de cada imóvel: desconto real, nota, classe e ressalvas.

A lógica é deliberadamente simples e explicável. Cada imóvel responde três
perguntas, nesta ordem:

1. **Tem algum impedimento?** Preço acima da avaliação do próprio banco é
   veto — em Leilão SFI o preço é o saldo da dívida, não um desconto.
2. **Quanto sobra de desconto depois do custo real?** Preço mais reforma,
   provisão de desocupação e comissão, comparado com a avaliação da Caixa.
3. **Está fora da curva em relação aos pares?** R$/m² contra a mediana dos
   imóveis parecidos na própria lista. A referência desce uma escada —
   mesma cidade e tipologia, mesma cidade, mesma tipologia no estado, mesma
   tipologia no Brasil — e para no primeiro nível com pares suficientes. O
   peso na nota cai junto: comparar com a mediana nacional é evidência
   fraca, e o parecer diz qual nível usou.

A nota sai disso, de 0 a 1, e o rótulo diz em uma frase o porquê. Nada aqui
é avaliação de mercado: a referência é o laudo do banco, que é número
interno da Caixa. Avaliação de mercado exige transação registrada, e isso
só existe onde há dado de ITBI.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# pares mínimos na própria lista para a comparação de R$/m² valer
MINIMO_PARES = 5

# faixas de desconto real que definem a classe
FAIXA_ALTO = 0.45
FAIXA_MEDIO = 0.30
FAIXA_BAIXO = 0.15

# lote de unidades quase idênticas que já conta como "empreendimento em bloco"
LOTE_RELEVANTE = 5

CLASSES = {
    "vetado": ("Vetado", "bloqueio"),
    "alto": ("Desconto alto", "positivo"),
    "medio": ("Desconto médio", "neutro"),
    "baixo": ("Desconto baixo", "neutro"),
    "sem": ("Sem desconto", "atencao"),
    "indefinido": ("Sem referência", "atencao"),
}


@dataclass
class Parecer:
    classe: str
    nota: float
    rotulo: str
    cor: str
    desconto_real: float | None
    vs_pares: float | None
    nivel_pares: str = ""
    ressalvas: list[str] = field(default_factory=list)


def _faixa(desconto: float) -> tuple[str, float]:
    if desconto >= FAIXA_ALTO:
        return "alto", 0.80
    if desconto >= FAIXA_MEDIO:
        return "medio", 0.60
    if desconto >= FAIXA_BAIXO:
        return "baixo", 0.40
    return "sem", 0.20


def ressalvas_do_imovel(imovel: dict) -> list[str]:
    """O que o comprador precisa saber antes de olhar a nota.

    A ordem importa: o que invalida a leitura vem primeiro.
    """
    avisos = []

    if imovel["preco_acima_da_avaliacao"]:
        avisos.append(
            "Armadilha: o preço pedido está acima da avaliação da própria "
            "Caixa. Em Leilão SFI o preço é o saldo da dívida, não um "
            "desconto — aqui não há desconto nenhum."
        )
    if imovel["lote"] >= LOTE_RELEVANTE:
        avisos.append(
            f"{imovel['lote']} unidades quase idênticas nesta mesma lista: é "
            "empreendimento retomado em bloco, não escassez. Quem compra uma "
            "concorre com as outras na revenda."
        )
    if imovel["ocupacao_desconhecida"]:
        avisos.append(
            "A ocupação não consta no arquivo da Caixa nem foi afirmada na "
            "página do imóvel, então a provisão de desocupação é estimativa "
            "cega. O edital responde — leia antes de dar lance."
        )
    elif imovel["ocupado"]:
        avisos.append(
            "Imóvel ocupado: a desocupação corre por sua conta. Tente "
            "acordo antes de processo; veja o roteiro nos detalhes."
        )
    if imovel["reforma_declarada"]:
        avisos.append("A própria descrição da Caixa diz que necessita reforma.")
    if imovel["leilao"]:
        avisos.append(
            "Leilão ou licitação: há comissão de leiloeiro e o prazo de "
            "pagamento é curto."
        )
    if not imovel["aceita_financiamento"]:
        avisos.append("Não aceita financiamento — precisa do valor à vista.")
    if imovel["tipo"] == "Terreno":
        avisos.append(
            "Terreno: confira muro, posse, acesso e se há ocupação por "
            "terceiros, que não aparece em coluna nenhuma."
        )
    if not imovel["area"]:
        avisos.append("Área não informada na descrição: R$/m² indisponível.")
    if not imovel["mercado_liquido"]:
        if imovel.get("tem_catalogo_rm"):
            avisos.append(
                "Interior: fora da capital e fora da região metropolitana "
                "do estado. Mercado mais raso e revenda mais lenta — confira "
                "quem seria o comprador quando você quiser sair."
            )
        else:
            # Estado sem catálogo de RM: a única coisa afirmável é que não é
            # a capital. Dizer "fora da região metropolitana" seria afirmar
            # algo que este projeto não conferiu neste estado.
            avisos.append(
                "Fora da capital do estado. Este estado ainda não tem lista "
                "de região metropolitana conferida neste projeto, então não "
                "há como dizer se a cidade integra uma. Mercado possivelmente "
                "mais raso: confira quem seria o comprador na revenda."
            )

    return avisos


def avaliar(imovel: dict, custo_real: float,
            referencia_m2: float | None, pares: int,
            nivel: str = "cidade") -> Parecer:
    """Monta o parecer de um imóvel."""
    ressalvas = ressalvas_do_imovel(imovel)

    if imovel["preco_acima_da_avaliacao"]:
        return Parecer(
            classe="vetado", nota=0.0, cor="bloqueio",
            rotulo=MOLDES["vetado"],
            desconto_real=None, vs_pares=None, nivel_pares="",
            ressalvas=ressalvas,
        )

    avaliacao = imovel["avaliacao"]
    if not avaliacao:
        return Parecer(
            classe="indefinido", nota=0.0, cor="atencao",
            rotulo=MOLDES["sem_avaliacao"],
            desconto_real=None, vs_pares=None, nivel_pares="",
            ressalvas=ressalvas,
        )

    desconto = 1 - custo_real / avaliacao
    classe, nota = _faixa(desconto)

    partes = [MOLDES["desconto"].format(desconto=f"{desconto:.0%}")]

    vs_pares = None
    if referencia_m2 and imovel["area"]:
        preco_m2 = imovel["preco"] / imovel["area"]
        vs_pares = preco_m2 / referencia_m2 - 1
        partes.append(MOLDES["pares"].format(
            diferenca=f"{abs(vs_pares):.0%}",
            lado="abaixo" if vs_pares < 0 else "acima",
            pares=pares,
            nivel=DESCRICAO_NIVEL.get(nivel, ""),
        ))
        # Concordar com os pares reforça o sinal; discordar derruba. O peso
        # cai conforme a referência se afasta: mediana da mesma cidade é
        # evidência forte, mediana nacional da tipologia é evidência fraca —
        # Boa Viagem e o sertão não são o mesmo mercado, e tratar os dois
        # ajustes como iguais daria nota alta a qualquer imóvel de cidade
        # barata só por ser barato.
        peso = PESO_NIVEL.get(nivel, 0.0)
        if vs_pares <= -0.15:
            nota = min(1.0, nota + 0.10 * peso)
        elif vs_pares >= 0.15:
            nota = max(0.0, nota - 0.15 * peso)
    else:
        partes.append(MOLDES["sem_pares"])

    # cada ressalva de peso tira um pouco da nota: elas são risco, não enfeite
    if imovel["lote"] >= LOTE_RELEVANTE:
        nota = max(0.0, nota - 0.10)
    if not imovel["mercado_liquido"]:
        nota = max(0.0, nota - 0.05)

    return Parecer(
        classe=classe, nota=round(nota, 3), cor=CLASSES[classe][1],
        rotulo=". ".join(partes) + ".",
        desconto_real=round(desconto, 4),
        vs_pares=round(vs_pares, 4) if vs_pares is not None else None,
        nivel_pares=nivel if vs_pares is not None else "",
        ressalvas=ressalvas,
    )


def mediana(valores: list[float]) -> float:
    ordenado = sorted(valores)
    meio = len(ordenado) // 2
    if len(ordenado) % 2:
        return ordenado[meio]
    return (ordenado[meio - 1] + ordenado[meio]) / 2


def referencias_por_cidade(imoveis: list[dict]) -> dict:
    """Mediana de R$/m² na própria lista, em quatro níveis de agregação.

    As chaves são ``(UF, cidade, tipo)``, ``(UF, cidade, "*")``,
    ``(UF, "*", tipo)`` e ``("*", "*", tipo)``: cidade e tipologia primeiro,
    depois o estado, depois o Brasil. A busca desce por essa escada até achar
    pares suficientes — assim um apartamento em cidade de 2 imóveis ainda
    ganha comparação, só com uma referência mais larga e marcada como tal.

    ⚠️ **A UF faz parte da chave.** Nome de cidade não é único no Brasil: na
    lista de 30/09/2026 são 16 nomes repetidos entre estados, 535 imóveis.
    Agrupar Santa Rita/MA com Santa Rita/PB misturaria 205 imóveis de dois
    mercados sem nenhum aviso — a mediana sairia errada e ninguém veria.

    Não é preço de mercado: é o preço que a Caixa pede por imóvel parecido.
    Serve para achar quem está fora da curva dentro do próprio acervo.
    """
    baldes: dict[tuple[str, str, str], list[float]] = {}
    for i in imoveis:
        if not i["area"] or not i["preco"]:
            continue
        m2 = i["preco"] / i["area"]
        uf, cidade, tipo = i["uf"], i["cidade"], i["tipo"]
        baldes.setdefault((uf, cidade, tipo), []).append(m2)
        baldes.setdefault((uf, cidade, "*"), []).append(m2)
        baldes.setdefault((uf, "*", tipo), []).append(m2)
        baldes.setdefault(("*", "*", tipo), []).append(m2)

    return {chave: (mediana(v), len(v)) for chave, v in baldes.items()}


# o que cada nível de referência significa, para o texto do parecer
DESCRICAO_NIVEL = {
    "cidade": "da mesma cidade e tipologia",
    "cidade_geral": "da mesma cidade, de qualquer tipologia",
    "estado": "da mesma tipologia no estado",
    "brasil": "da mesma tipologia no Brasil",
}

# quanto a comparação com pares pode mexer na nota, por nível
PESO_NIVEL = {
    "cidade": 1.0,
    "cidade_geral": 0.6,
    "estado": 0.3,
    "brasil": 0.1,
}

# ---------------------------------------------------------------- moldes
# O TEXTO DO PARECER FICA AQUI, UMA VEZ SÓ — e a página recebe estes moldes
# pelo indice.json em vez de receber a frase montada em cada imóvel.
#
# Por que: medido no arquivo do Rio de Janeiro, o campo "veredito" ocupava
# 0,97 MB dos 7,47 MB do estado — 13%, o maior campo de todos. E são 3.977
# frases distintas em 5.995 imóveis porque só mudam três números: de 160
# caracteres, cerca de 145 são sempre os mesmos. Gravar a frase inteira em
# cada registro é guardar o mesmo texto quatro mil vezes.
#
# A regra continua sendo uma só, em Python: estes moldes são usados aqui
# para montar o parecer que vai no RSS, e são os MESMOS moldes que a página
# usa para desenhar. Ninguém reescreve a frase em JavaScript. Mudar a
# redação aqui muda nos dois lugares, porque é o mesmo texto viajando.
MOLDES = {
    "desconto": ("{desconto} abaixo da avaliação da Caixa já descontando "
                 "reforma, provisão de desocupação e comissão"),
    "pares": ("R$/m² {diferenca} {lado} dos {pares} pares {nivel} nesta "
              "lista"),
    "sem_pares": "sem pares suficientes nesta lista para comparar R$/m²",
    "vetado": "Preço acima da avaliação da própria Caixa",
    "sem_avaliacao": ("Sem avaliação da Caixa no arquivo — não há como medir "
                      "desconto"),
}


def referencia_do_imovel(imovel: dict, referencias: dict
                         ) -> tuple[float | None, int, str]:
    """A melhor referência interna disponível, e de que nível ela é.

    Devolve ``(mediana, pares, nivel)``. Desce a escada cidade -> estado ->
    Brasil e para no primeiro nível com pares suficientes.
    """
    uf, cidade, tipo = imovel["uf"], imovel["cidade"], imovel["tipo"]
    escada = (
        ("cidade",       (uf, cidade, tipo)),
        ("cidade_geral", (uf, cidade, "*")),
        ("estado",       (uf, "*", tipo)),
        ("brasil",       ("*", "*", tipo)),
    )
    for nivel, chave in escada:
        achado = referencias.get(chave)
        if not achado:
            continue
        med, total = achado
        pares = total - 1          # o próprio imóvel entra na mediana
        if pares >= MINIMO_PARES:
            return med, pares, nivel
    return None, 0, ""
