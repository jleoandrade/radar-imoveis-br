"""Catálogo geográfico do Brasil usado pelo radar.

Quatro coisas:

* ``CAPITAIS`` — a capital de cada uma das 27 unidades da federação. É fato
  verificável e não muda, então é a divisão principal do radar: capital
  concentra liquidez, interior não.
* ``REGIOES_METROPOLITANAS`` — catálogo **parcial**, carregado de
  ``dados/regioes_metropolitanas.json``. Região metropolitana é definida por
  **lei estadual**, muda de composição com frequência e não tem fonte aberta
  confiável que este projeto consiga consultar sozinho. Então o catálogo só
  traz os estados cuja lista alguém conferiu na lei, cada um com o campo
  ``fonte`` dizendo onde foi conferido. Estado sem catálogo não ganha palpite:
  cai em capital/interior e o texto do parecer muda junto.
* ``BAIRROS`` — os 93 bairros do Recife com a RPA de cada um, para reconhecer
  o bairro que a Caixa escreve em caixa alta e sem acento (``VARZEA`` ->
  ``Várzea``). Não existe catálogo equivalente para as outras 1.067 cidades
  da lista; nelas o bairro fica como a Caixa escreveu.
* ``NOMES_RPA`` — o nome usual de cada RPA do Recife.

⚠️ **Toda chave aqui é (UF, cidade), nunca só a cidade.** Medido na lista
nacional de 30/09/2026: 16 nomes de cidade aparecem em mais de um estado,
cobrindo 535 imóveis. Entre eles **Paulista**, que é PB e é PE — e Paulista/PE
está na Região Metropolitana do Recife enquanto Paulista/PB é interior.
Casar por nome marcaria uma como a outra, e o erro não apareceria em lugar
nenhum: a nota sairia 0,05 mais alta e a ressalva de mercado raso não sairia.
O mesmo vale para Santa Rita (MA e PB, 205 imóveis) e São Gonçalo do Amarante
(CE e RN, 99).
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path

# ----------------------------------------------------------------- capitais
# As 27 capitais. Fato estável, conferível em qualquer fonte oficial.
CAPITAIS = {
    "AC": "Rio Branco",
    "AL": "Maceió",
    "AM": "Manaus",
    "AP": "Macapá",
    "BA": "Salvador",
    "CE": "Fortaleza",
    "DF": "Brasília",
    "ES": "Vitória",
    "GO": "Goiânia",
    "MA": "São Luís",
    "MG": "Belo Horizonte",
    "MS": "Campo Grande",
    "MT": "Cuiabá",
    "PA": "Belém",
    "PB": "João Pessoa",
    "PE": "Recife",
    "PI": "Teresina",
    "PR": "Curitiba",
    "RJ": "Rio de Janeiro",
    "RN": "Natal",
    "RO": "Porto Velho",
    "RR": "Boa Vista",
    "RS": "Porto Alegre",
    "SC": "Florianópolis",
    "SE": "Aracaju",
    "SP": "São Paulo",
    "TO": "Palmas",
}

NOMES_UF = {
    "AC": "Acre", "AL": "Alagoas", "AM": "Amazonas", "AP": "Amapá",
    "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal",
    "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão",
    "MG": "Minas Gerais", "MS": "Mato Grosso do Sul", "MT": "Mato Grosso",
    "PA": "Pará", "PB": "Paraíba", "PE": "Pernambuco", "PI": "Piauí",
    "PR": "Paraná", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
    "RO": "Rondônia", "RR": "Roraima", "RS": "Rio Grande do Sul",
    "SC": "Santa Catarina", "SE": "Sergipe", "SP": "São Paulo",
    "TO": "Tocantins",
}

REGIOES = {
    "Norte": ("AC", "AM", "AP", "PA", "RO", "RR", "TO"),
    "Nordeste": ("AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"),
    "Centro-Oeste": ("DF", "GO", "MS", "MT"),
    "Sudeste": ("ES", "MG", "RJ", "SP"),
    "Sul": ("PR", "RS", "SC"),
}

REGIAO_DA_UF = {uf: nome for nome, ufs in REGIOES.items() for uf in ufs}


# ------------------------------------------------- regiões metropolitanas
CATALOGO_RM = Path(__file__).resolve().parents[1] / "dados" / \
    "regioes_metropolitanas.json"


def _carregar_rm() -> dict[str, tuple[dict, ...]]:
    """Lê o catálogo parcial de regiões metropolitanas.

    Devolve ``{UF: (região, região, ...)}`` porque um estado pode ter mais de
    uma: São Paulo tem seis na lista da Caixa, e Goiás tem duas que são
    mercados completamente diferentes — a de Goiânia e o Entorno do DF, que
    responde por 2.233 dos 2.649 imóveis do estado.

    Falta de arquivo não é erro: o radar funciona sem catálogo nenhum, só
    perde a camada intermediária entre capital e interior. Chave que começa
    com ``_`` é comentário do arquivo e é ignorada.
    """
    if not CATALOGO_RM.exists():
        return {}
    try:
        bruto = json.loads(CATALOGO_RM.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}

    saida: dict[str, tuple[dict, ...]] = {}
    for uf, entradas in bruto.items():
        if uf.startswith("_") or not isinstance(entradas, list):
            continue
        regioes = []
        for dados in entradas:
            municipios = (dados or {}).get("municipios") or []
            if not municipios:
                continue
            regioes.append({
                "nome": dados.get("nome") or f"Região Metropolitana ({uf})",
                "municipios": tuple(municipios),
                "fonte": dados.get("fonte", ""),
                "conferido": bool(dados.get("conferido")),
            })
        if regioes:
            saida[uf.strip().upper()] = tuple(regioes)
    return saida


REGIOES_METROPOLITANAS = _carregar_rm()


# ----------------------------------------------------------------- bairros
BAIRROS = [
    # ------------------------------------------------ RPA 1 - Centro
    ("Recife",                1, "medio_alto"),
    ("Santo Amaro",           1, "medio"),
    ("Boa Vista",             1, "medio"),
    ("Cabanga",               1, "medio"),
    ("Ilha do Leite",         1, "medio_alto"),
    ("Paissandu",             1, "medio"),
    ("Santo Antônio",         1, "medio"),
    ("São José",              1, "popular"),
    ("Coelhos",               1, "popular"),
    ("Soledade",              1, "medio"),
    ("Ilha Joana Bezerra",    1, "popular"),

    # ------------------------------------------------ RPA 2 - Norte
    ("Arruda",                2, "medio"),
    ("Campina do Barreto",    2, "popular"),
    ("Campo Grande",          2, "medio"),
    ("Encruzilhada",          2, "medio_alto"),
    ("Hipódromo",             2, "medio"),
    ("Peixinhos",             2, "popular"),
    ("Ponto de Parada",       2, "popular"),
    ("Rosarinho",             2, "medio_alto"),
    ("Torreão",               2, "medio"),
    ("Água Fria",             2, "popular"),
    ("Alto Santa Terezinha",  2, "popular"),
    ("Bomba do Hemetério",    2, "popular"),
    ("Cajueiro",              2, "popular"),
    ("Fundão",                2, "popular"),
    ("Linha do Tiro",         2, "popular"),
    ("Porto da Madeira",      2, "popular"),

    # ------------------------------------------------ RPA 3 - Noroeste
    ("Aflitos",               3, "alto_padrao"),
    ("Alto do Mandu",         3, "popular"),
    ("Alto José Bonifácio",   3, "popular"),
    ("Alto José do Pinho",    3, "popular"),
    ("Apipucos",              3, "medio_alto"),
    ("Brejo da Guabiraba",    3, "popular"),
    ("Brejo de Beberibe",     3, "popular"),
    ("Casa Amarela",          3, "medio"),
    ("Casa Forte",            3, "alto_padrao"),
    ("Córrego do Jenipapo",   3, "popular"),
    ("Derby",                 3, "alto_padrao"),
    ("Dois Irmãos",           3, "medio"),
    ("Jaqueira",              3, "alto_padrao"),
    ("Macaxeira",             3, "popular"),
    ("Mangabeira",            3, "popular"),
    ("Monteiro",              3, "medio_alto"),
    ("Nova Descoberta",       3, "popular"),
    ("Parnamirim",            3, "alto_padrao"),
    ("Passarinho",            3, "popular"),
    ("Pau-Ferro",             3, "popular"),
    ("Poço da Panela",        3, "medio_alto"),
    ("Santana",               3, "medio_alto"),
    ("Sítio dos Pintos",      3, "popular"),
    ("Tamarineira",           3, "medio_alto"),
    ("Vasco da Gama",         3, "popular"),
    ("Graças",                3, "alto_padrao"),
    ("Espinheiro",            3, "alto_padrao"),
    ("Guabiraba",             3, "popular"),
    ("Morro da Conceição",    3, "popular"),

    # ------------------------------------------------ RPA 4 - Oeste
    ("Cordeiro",              4, "medio"),
    ("Engenho do Meio",       4, "medio"),
    ("Ilha do Retiro",        4, "medio_alto"),
    ("Iputinga",              4, "popular"),
    ("Madalena",              4, "alto_padrao"),
    ("Prado",                 4, "medio"),
    ("Torre",                 4, "medio_alto"),
    ("Torrões",               4, "popular"),
    ("Zumbi",                 4, "medio"),
    ("Caxangá",               4, "medio"),
    ("Cidade Universitária",  4, "medio"),
    ("Várzea",                4, "medio"),

    # ------------------------------------------------ RPA 5 - Sudoeste
    ("Afogados",              5, "medio"),
    ("Areias",                5, "popular"),
    ("Barro",                 5, "popular"),
    ("Bongi",                 5, "popular"),
    ("Caçote",                5, "popular"),
    ("Coqueiral",             5, "popular"),
    ("Curado",                5, "popular"),
    ("Estância",              5, "medio"),
    ("Jardim São Paulo",      5, "medio"),
    ("Jiquiá",                5, "medio"),
    ("Mangueira",             5, "popular"),
    ("Mustardinha",           5, "popular"),
    ("San Martin",            5, "popular"),
    ("Sancho",                5, "popular"),
    ("Tejipió",               5, "popular"),
    ("Totó",                  5, "popular"),

    # ------------------------------------------------ RPA 6 - Sul
    ("Boa Viagem",            6, "alto_padrao"),
    ("Brasília Teimosa",      6, "popular"),
    ("Cohab",                 6, "popular"),
    ("Ibura",                 6, "popular"),
    ("Imbiribeira",           6, "medio"),
    ("Ipsep",                 6, "medio"),
    ("Jordão",                6, "popular"),
    ("Pina",                  6, "alto_padrao"),
]

NOMES_RPA = {
    1: "RPA 1 - Centro",
    2: "RPA 2 - Norte",
    3: "RPA 3 - Noroeste",
    4: "RPA 4 - Oeste",
    5: "RPA 5 - Sudoeste",
    6: "RPA 6 - Sul",
}


# ------------------------------------------------------------- utilidades
def sem_acento(texto: str) -> str:
    """'VARZEA' e 'Várzea' viram a mesma chave de busca."""
    texto = unicodedata.normalize("NFKD", str(texto))
    limpo = "".join(c for c in texto if not unicodedata.combining(c))
    return limpo.lower().strip()


_CAPITAIS = {uf: sem_acento(c) for uf, c in CAPITAIS.items()}

# (UF, cidade sem acento) -> nome da região. Dicionário plano de propósito:
# a chave TEM de carregar a UF, senão Paulista/PB entra na RMR.
_RM: dict[tuple[str, str], str] = {}
for _uf, _regioes in REGIOES_METROPOLITANAS.items():
    for _r in _regioes:
        for _m in _r["municipios"]:
            _RM.setdefault((_uf, sem_acento(_m)), _r["nome"])

_BAIRROS = {sem_acento(nome): (nome, rpa) for nome, rpa, *_ in BAIRROS}

# as três camadas de mercado, da mais líquida para a mais rasa
CAPITAL = "capital"
METROPOLITANA = "metropolitana"
INTERIOR = "interior"

NOMES_PRACA = {
    CAPITAL: "Capital",
    METROPOLITANA: "Região metropolitana",
    INTERIOR: "Interior",
}


def eh_capital(uf: str, cidade: str) -> bool:
    """O Distrito Federal é um caso à parte.

    A Caixa lista as regiões administrativas de Brasília — Ceilândia,
    Samambaia, Taguatinga — na coluna de cidade. Juridicamente o DF é um
    município só, então tudo que é DF é capital.
    """
    uf = str(uf).strip().upper()
    if uf == "DF":
        return True
    return _CAPITAIS.get(uf) == sem_acento(cidade)


def tem_catalogo_rm(uf: str) -> bool:
    """Este estado tem alguma lista de região metropolitana no catálogo?"""
    return str(uf).strip().upper() in REGIOES_METROPOLITANAS


def regiao_metropolitana(uf: str, cidade: str) -> str:
    """O nome da região metropolitana desta cidade, ou "" se não houver."""
    return _RM.get((str(uf).strip().upper(), sem_acento(cidade)), "")


def praca(uf: str, cidade: str) -> str:
    """Em que camada de mercado está o imóvel: capital, RM ou interior.

    Estado sem catálogo de RM nunca devolve ``metropolitana`` — devolve
    ``interior``, que é o que se pode afirmar com o que se tem. Quem precisa
    distinguir "é interior" de "não sabemos" pergunta a ``tem_catalogo_rm``.
    """
    uf = str(uf).strip().upper()
    if eh_capital(uf, cidade):
        return CAPITAL
    if regiao_metropolitana(uf, cidade):
        return METROPOLITANA
    return INTERIOR


def mercado_liquido(uf: str, cidade: str) -> bool:
    """Capital ou região metropolitana.

    É o sucessor do antigo ``na_rmr``: a pergunta é a mesma — tem comprador
    quando você quiser sair? — só que agora vale para os 27 estados.
    """
    return praca(uf, cidade) in (CAPITAL, METROPOLITANA)


def fonte_da_rm(uf: str, cidade: str) -> tuple[str, bool]:
    """(texto da fonte, conferido na lei?) da região desta cidade."""
    nome = regiao_metropolitana(uf, cidade)
    if not nome:
        return "", False
    for r in REGIOES_METROPOLITANAS.get(str(uf).strip().upper(), ()):
        if r["nome"] == nome:
            return r["fonte"], r["conferido"]
    return "", False


def reconhecer_bairro(uf: str, cidade: str, bairro: str) -> tuple[str, int]:
    """Devolve (nome com acento, RPA). RPA 0 = fora do catálogo do Recife.

    Recebe a UF porque existe Recife só em PE, mas o nome de cidade não é
    único no Brasil e a assinatura tem de forçar quem chama a dizer o estado.
    """
    if str(uf).strip().upper() != "PE" or sem_acento(cidade) != "recife":
        return str(bairro).strip().title(), 0

    chave = sem_acento(bairro)
    achado = _BAIRROS.get(chave)
    if achado is None:
        # "Boa Viagem (Setor A)" e variações com sufixo
        for alvo, valor in _BAIRROS.items():
            if chave.startswith(alvo) or alvo.startswith(chave):
                achado = valor
                break
    if achado is None:
        return str(bairro).strip().title(), 0
    return achado
