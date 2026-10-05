"""Coletor da lista oficial de imóveis da Caixa Econômica Federal.

A Caixa publica, por estado, a lista completa dos imóveis que ela retomou e
está vendendo — leilão, venda direta e licitação:

    https://venda-imoveis.caixa.gov.br/sistema/download-lista.asp
    https://venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_PE.csv

É o arquivo que resolve o problema de "anúncio real sem raspar portal": vem
da fonte, é feito para ser baixado, e traz preço de venda, **avaliação da
própria Caixa** e desconto declarado. A avaliação é uma segunda opinião
independente para cruzar com a estimativa por comparáveis do ITBI.

O que o arquivo tem de chato
----------------------------
* separador ``;`` e codificação **latin-1**;
* uma ou duas linhas de título antes do cabeçalho de verdade;
* números em formato brasileiro (``612000,00``);
* tipologia, área, quartos, vagas e situação de ocupação **todos enfiados num
  campo de texto livre** chamado "Descrição".

Por isso o parser procura o cabeçalho em vez de assumir a linha, tenta três
codificações e extrai a descrição por expressão regular. Se o formato mudar,
a mensagem de erro diz quais colunas vieram no arquivo.

⚠️ Imóvel de leilão não é imóvel comum. Veja `AVISOS_CAIXA` no fim do módulo:
ocupação, débitos e condições de pagamento mudam a conta e **não estão no
desconto anunciado**.
"""

from __future__ import annotations

import re
import unicodedata
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

from analise.tipos import normalizar_tipo

URL_LISTA = "https://venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_{uf}.csv"

# O arquivo nacional. Conferido: o download de "todos os estados" entrega
# Lista_imoveis_geral.csv, e ele é byte a byte o mesmo que a soma dos 27
# arquivos estaduais — 18.266 imóveis em 30/09/2026, 6,6 MB. Então o robô
# baixa UM arquivo, não 27.
URL_NACIONAL = URL_LISTA.format(uf="geral")

# Aceito como pedido de "Brasil inteiro" em qualquer lugar que receba UF.
APELIDOS_NACIONAIS = ("BR", "BRASIL", "GERAL", "TODOS", "NACIONAL")

CODIFICACOES = ("latin-1", "utf-8-sig", "cp1252")

CORTESIA = ("radar-imoveis-br/1.0 (projeto independente, lista publica da "
            "Caixa; github.com/jleoandrade/radar-imoveis-br)")

# nome padronizado -> nomes aceitos no cabeçalho (sem acento, minúsculo)
COLUNAS = {
    "id_externo": ["n_do_imovel", "no_do_imovel", "numero_do_imovel",
                   "n_imovel", "imovel"],
    "uf": ["uf", "estado"],
    "cidade": ["cidade", "municipio"],
    "bairro": ["bairro"],
    "endereco": ["endereco", "logradouro"],
    "preco": ["preco", "preco_de_venda", "valor"],
    "avaliacao": ["valor_de_avaliacao", "avaliacao", "valor_avaliacao"],
    "desconto": ["desconto", "desconto_"],
    "descricao": ["descricao", "descricao_do_imovel"],
    "modalidade": ["modalidade_de_venda", "modalidade"],
    # coluna Sim/Não do arquivo real: diz se a Caixa aceita financiar.
    # É muito melhor que adivinhar pela modalidade — e na lista de PE de
    # 09/2026, 1.017 dos 1.060 imóveis eram "Não".
    "financiamento": ["financiamento", "aceita_financiamento"],
    "url": ["link_de_acesso", "link", "url"],
}

# ------------------------------------------------- leitura da descrição
RE_AREA_PRIVATIVA = re.compile(
    r"([\d.,]+)\s*(?:m2|m²)?\s*de\s+área\s+(?:privativa|útil|construída)",
    re.IGNORECASE,
)
RE_AREA_TERRENO = re.compile(
    r"([\d.,]+)\s*(?:m2|m²)?\s*de\s+área\s+(?:do\s+)?terreno", re.IGNORECASE
)
RE_AREA_TOTAL = re.compile(
    r"([\d.,]+)\s*(?:m2|m²)?\s*de\s+área\s+total", re.IGNORECASE
)
RE_QUARTOS = re.compile(r"(\d+)\s*(?:qto|quarto|dorm)", re.IGNORECASE)
RE_VAGAS = re.compile(r"(\d+)\s*(?:vaga|garagem)", re.IGNORECASE)

# "ocupado" aparece como situação; cuidado para não casar com "desocupado"
RE_DESOCUPADO = re.compile(r"\bdesocupad", re.IGNORECASE)
RE_OCUPADO = re.compile(r"(?<!des)\bocupad", re.IGNORECASE)
RE_REFORMA = re.compile(r"necessita\s+reforma|em\s+ru[ií]nas|demoli",
                        re.IGNORECASE)

MODALIDADES_A_VISTA = ("leilão", "leilao", "licitação", "licitacao")


def _sem_acento(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in texto if not unicodedata.combining(c))


def _normalizar_coluna(texto: str) -> str:
    limpo = _sem_acento(texto).strip().lower()
    limpo = re.sub(r"[^a-z0-9]+", "_", limpo)
    return limpo.strip("_")


def _numero_br(texto) -> float:
    """'612.000,00' ou '612000,00' -> 612000.0"""
    if texto is None or (isinstance(texto, float) and pd.isna(texto)):
        return 0.0
    if isinstance(texto, (int, float)):
        return float(texto)
    limpo = "".join(c for c in str(texto) if c in "0123456789.,")
    if not limpo:
        return 0.0
    if "," in limpo:
        limpo = limpo.replace(".", "").replace(",", ".")
    elif limpo.count(".") > 1:
        limpo = limpo.replace(".", "")
    try:
        return float(limpo)
    except ValueError:
        return 0.0


def ler_descricao(texto: str) -> dict:
    """Extrai do texto livre o que o resto do sistema precisa em coluna."""
    texto = str(texto or "")

    def primeiro(padrao):
        achado = padrao.search(texto)
        return _numero_br(achado.group(1)) if achado else 0.0

    area_privativa = primeiro(RE_AREA_PRIVATIVA)
    area_terreno = primeiro(RE_AREA_TERRENO)
    area_total = primeiro(RE_AREA_TOTAL)

    # o tipo é a primeira palavra da descrição ("Apartamento, 92,00 de ...")
    primeiro_campo = texto.split(",")[0].strip()
    tipo = normalizar_tipo(primeiro_campo)

    # terreno não tem área privativa; use a do terreno como área de referência
    area = area_privativa or area_total
    if tipo == "Terreno" or not area:
        area = area or area_terreno

    # ATENÇÃO: na lista real a Caixa NÃO informa ocupação nenhuma. Conferido
    # na lista de PE de 30/09/2026: zero ocorrências de "ocupado",
    # "desocupado", "inquilino" ou "posseiro" em 1.060 registros. A situação
    # de ocupação só aparece na página de cada imóvel e no edital.
    # Os padrões ficam porque alguns estados e algumas safras do arquivo
    # trazem a informação — quando não vem, 'situacao_informada' diz
    # "não informada" e quem consome DEVE tratar isso como desconhecido, não
    # como desocupado. Assumir desocupado é o erro que torna todo imóvel de
    # leilão barato no papel.
    desocupado = bool(RE_DESOCUPADO.search(texto))
    ocupado = bool(RE_OCUPADO.search(texto)) and not desocupado

    return {
        "tipo_imovel": tipo,
        "area_m2": area,
        # as três áreas separadas: a Caixa informa "área total",
        # "área privativa" e "área do terreno" e elas dizem coisas
        # diferentes. Num apartamento a total costuma incluir a área comum;
        # numa casa, a privativa é o construído e a do terreno é o lote.
        "area_privativa": area_privativa,
        "area_total": area_total,
        "area_terreno": area_terreno,
        "quartos": int(primeiro(RE_QUARTOS)),
        "vagas": int(primeiro(RE_VAGAS)),
        "ocupado": ocupado,
        "ocupacao_desconhecida": not (ocupado or desocupado),
        "situacao_informada": (
            "ocupado" if ocupado else "desocupado" if desocupado
            else "não informada"
        ),
        "precisa_reforma": bool(RE_REFORMA.search(texto)),
    }


def _achar_coluna(disponiveis: list[str], candidatos: list[str]) -> str | None:
    for candidato in candidatos:
        if candidato in disponiveis:
            return candidato
    for coluna in disponiveis:
        if any(candidato in coluna for candidato in candidatos):
            return coluna
    return None


def _decodificar(bruto: bytes) -> str:
    for codificacao in CODIFICACOES:
        try:
            return bruto.decode(codificacao)
        except UnicodeDecodeError:
            continue
    return bruto.decode("latin-1", errors="replace")


RE_DATA_GERACAO = re.compile(r"(\d{2}/\d{2}/\d{4})")


def _data_de_geracao(texto: str) -> str | None:
    """Pesca a data da linha de título: 'Data de geração:;30/09/2026'."""
    for linha in texto.splitlines()[:5]:
        if "gera" in _sem_acento(linha).lower():
            achado = RE_DATA_GERACAO.search(linha)
            if achado:
                return achado.group(1)
    return None


def _linha_do_cabecalho(texto: str) -> int:
    """Acha a linha do cabeçalho de verdade, pulando o título do arquivo."""
    for indice, linha in enumerate(texto.splitlines()[:30]):
        normalizada = _sem_acento(linha).lower()
        if ";" in linha and "cidade" in normalizada and "bairro" in normalizada:
            return indice
    return 0


class ListaCaixa:
    """Lê a lista de imóveis da Caixa de uma URL, de um arquivo ou de bytes."""

    nome = "caixa"

    def __init__(self, origem: str | Path = "BR", cidade: str | None = None,
                 timeout: int = 300):
        self.origem = str(origem)
        self.cidade = cidade
        self.timeout = timeout
        # a linha de título do arquivo traz "Data de geração:;30/09/2026".
        # Vale mostrar na página: o acervo muda toda semana, e o usuário
        # precisa saber de que dia é o dado que está vendo.
        self.data_da_lista: str | None = None

    # ------------------------------------------------------------ leitura
    def _bruto(self) -> bytes:
        caminho = Path(self.origem)
        if caminho.exists():
            return caminho.read_bytes()

        if self.origem.lower().startswith("http"):
            url = self.origem
        else:
            uf = self.origem.strip().upper()
            url = (URL_NACIONAL if uf in APELIDOS_NACIONAIS
                   else URL_LISTA.format(uf=uf))

        # User-Agent honesto: diz o que é e para onde reclamar. A lista é
        # pública e feita para download, então não há nada a disfarçar.
        resposta = requests.get(
            url, timeout=self.timeout,
            headers={"User-Agent": CORTESIA},
        )
        resposta.raise_for_status()
        return resposta.content

    def tabela(self) -> pd.DataFrame:
        """A lista crua, só com as colunas padronizadas."""
        texto = _decodificar(self._bruto())
        pular = _linha_do_cabecalho(texto)
        self.data_da_lista = _data_de_geracao(texto)

        bruto = pd.read_csv(
            StringIO(texto), sep=";", skiprows=pular, dtype=str,
            engine="python", on_bad_lines="skip",
        )
        bruto.columns = [_normalizar_coluna(c) for c in bruto.columns]

        mapa = {
            padrao: _achar_coluna(list(bruto.columns), candidatos)
            for padrao, candidatos in COLUNAS.items()
        }
        faltando = [k for k in ("cidade", "bairro", "preco", "descricao")
                    if mapa[k] is None]
        if faltando:
            raise ValueError(
                "A lista da Caixa veio num formato que não reconheço. "
                f"Faltam as colunas {faltando}. "
                f"O arquivo trouxe: {list(bruto.columns)}. "
                "Ajuste o dicionário COLUNAS em coletores/caixa.py."
            )

        usadas = {origem: padrao for padrao, origem in mapa.items()
                  if origem is not None}
        tabela = bruto.rename(columns=usadas)[list(usadas.values())].copy()

        for coluna in ("preco", "avaliacao", "desconto"):
            if coluna in tabela:
                tabela[coluna] = tabela[coluna].map(_numero_br)

        detalhes = tabela["descricao"].map(ler_descricao).apply(pd.Series)
        tabela = pd.concat([tabela, detalhes], axis=1)

        tabela["cidade"] = tabela["cidade"].astype(str).str.strip().str.title()
        tabela["bairro"] = tabela["bairro"].astype(str).str.strip().str.title()
        # A UF vira a chave de tudo no arquivo nacional, então é normalizada
        # aqui, uma vez, e não em cada lugar que precisar dela.
        if "uf" in tabela:
            tabela["uf"] = tabela["uf"].astype(str).str.strip().str.upper()
        else:
            tabela["uf"] = str(self.origem).strip().upper()[:2]
        tabela["modalidade"] = (
            tabela["modalidade"].astype(str).str.strip()
            if "modalidade" in tabela else "não informada"
        )
        # leilão/licitação é o que cobra comissão de leiloeiro — não é a
        # mesma pergunta de "aceita financiamento"
        tabela["leilao"] = tabela["modalidade"].str.lower().apply(
            lambda m: any(p in m for p in MODALIDADES_A_VISTA)
        )
        if "financiamento" in tabela:
            tabela["aceita_financiamento"] = (
                tabela["financiamento"].astype(str).str.strip().str.lower()
                .eq("sim")
            )
        else:
            tabela["aceita_financiamento"] = ~tabela["leilao"]
        tabela["pagamento_a_vista"] = ~tabela["aceita_financiamento"]

        # preço acima da avaliação do próprio banco: em Leilão SFI o "preço"
        # é o saldo da dívida, não um desconto. Não é oportunidade, é lance
        # mínimo acima do valor do imóvel.
        tabela["preco_acima_da_avaliacao"] = (
            tabela["avaliacao"].gt(0) & tabela["preco"].gt(tabela["avaliacao"])
        )

        if self.cidade:
            alvo = _sem_acento(self.cidade).lower()
            tabela = tabela[
                tabela["cidade"].map(lambda c: _sem_acento(c).lower()) == alvo
            ]

        return tabela.reset_index(drop=True)


# ------------------------------------------------------------- avisos
AVISOS_CAIXA = [
    ("Ocupação",
     "Imóvel ocupado é vendido com o ocupante dentro. A desocupação é por "
     "conta do comprador: ação judicial, tempo (meses a anos) e custo de "
     "advogado. Boa parte do desconto da Caixa é exatamente o preço desse "
     "risco."),
    ("Estado de conservação",
     "A venda é no estado em que o imóvel se encontra, e em geral sem visita "
     "interna. Reserve orçamento de reforma às cegas — some esse valor no "
     "campo de reforma antes de comparar preços."),
    ("Débitos anteriores",
     "Condomínio e IPTU atrasados podem ficar com o comprador, dependendo do "
     "edital. Leia a cláusula de débitos ANTES de dar lance; em condomínio "
     "com cota alta, a dívida acumulada engole o desconto."),
    ("Condições de pagamento",
     "Leilão e licitação costumam exigir pagamento à vista em prazo curto. "
     "Venda direta às vezes aceita financiamento e FGTS. Desconto que exige "
     "a vista é um ativo diferente de desconto financiável."),
    ("Comissão do leiloeiro",
     "Em leilão há comissão do leiloeiro, normalmente 5% sobre o valor da "
     "arrematação, somada ao preço — e ela não entra no desconto anunciado."),
    ("Avaliação da Caixa",
     "O 'valor de avaliação' é a referência do banco, não necessariamente o "
     "preço de mercado. Por isso cruzamos com o ITBI: quando as duas fontes "
     "concordam, o sinal é muito mais forte."),
]
