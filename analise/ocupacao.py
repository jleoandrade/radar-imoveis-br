"""Situação de ocupação do imóvel e o que fazer quando ele está ocupado.

POR QUE ESTE ARQUIVO EXISTE
---------------------------
O arquivo que a Caixa publica para download **não diz se o imóvel está
ocupado**. Conferido na lista de PE de 30/09/2026: zero menções a "ocupado",
"desocupado", "inquilino" ou "posseiro" em 1.060 registros.

E ocupação é o item mais caro da conta depois da reforma. Tratar "não sei"
como "vazio" é assumir o melhor cenário justamente onde o erro dói mais — é
o que faz toda lista de leilão parecer barata no papel.

A informação existe, mas num lugar diferente: a **página de cada imóvel** no
site da Caixa, que costuma trazer uma frase como "Imóvel ocupado" ou
"Imóvel desocupado". Este módulo lê essa frase (``ler_pagina``) e guarda o
trecho original junto com a conclusão, para quem usa o site poder conferir
se a leitura foi honesta.

CUIDADO COM O FALSO POSITIVO
----------------------------
A página tem texto padrão que menciona ocupação sem afirmar nada:

    "a desocupação do imóvel, caso ocupado, correrá por conta do comprador"

Um ``if "ocupado" in texto`` marcaria esse imóvel como ocupado. Por isso
aqui só vale frase **afirmativa**: frases com "caso", "se", "eventual",
"quando" e parentes são descartadas antes da decisão.
"""

from __future__ import annotations

import html
import re
import unicodedata

OCUPADO = "ocupado"
DESOCUPADO = "desocupado"
NAO_INFORMADA = "nao_informada"

# --------------------------------------------------- o imóvel ainda existe?
# A lista da Caixa é uma fotografia do dia em que foi gerada. Entre a
# geração e agora, imóvel é arrematado, leilão encerra, edital é suspenso —
# e a página responde "Nenhum imóvel encontrado para o filtro selecionado".
#
# A regra é de TRÊS estados, e isso é proposital: só sai da lista quem a
# página NEGOU existir. Erro de rede, lentidão ou página estranha devolvem
# INDEFINIDO e não tiram ninguém do site. Apagar imóvel bom por causa de um
# soluço de rede seria muito pior do que mostrar um que acabou de sair.
VIVO = "vivo"
MORTO = "morto"
INDEFINIDO = "indefinido"

RE_SEM_IMOVEL = re.compile(
    r"nenhum\s+imovel\s+encontrado"
    r"|imovel\s+nao\s+(?:encontrado|localizado|disponivel)"
    r"|nao\s+foi\s+possivel\s+localizar\s+o\s+imovel",
    re.IGNORECASE,
)

# Marcas de uma página de imóvel de verdade. Exigir DUAS evita confundir
# uma página de erro que por acaso tenha uma delas no menu.
MARCAS_DE_VIDA = (
    re.compile(r"valor\s+de\s+avaliacao", re.I),
    re.compile(r"numero\s+do\s+imovel", re.I),
    re.compile(r"tipo\s+de\s+imovel", re.I),
    re.compile(r"area\s+(?:privativa|total|do\s+terreno)", re.I),
    re.compile(r"baixar\s+(?:o\s+)?edital", re.I),
    re.compile(r"de\s+seu\s+lance|sou\s+o\s+ex\s*-?\s*mutuario", re.I),
    re.compile(r"valor\s+minimo\s+de\s+venda", re.I),
)

ROTULOS = {
    OCUPADO: "Ocupado",
    DESOCUPADO: "Desocupado",
    NAO_INFORMADA: "Ocupação não informada",
}

# Frases condicionais: se a sentença tem uma destas, ela está falando de uma
# hipótese, não do imóvel. "caso ocupado", "se estiver ocupado", "eventual
# desocupação" — nenhuma afirma coisa alguma sobre este imóvel.
RE_CONDICIONAL = re.compile(
    r"\b(caso|se\s+(?:o|a|est|houver)|eventual|eventualmente|quando|"
    r"porventura|acaso|na\s+hipotese|havendo|se\s+necessario)\b",
    re.IGNORECASE,
)

# Em ordem de confiança. A primeira que casar decide.
PADROES = (
    # campo rotulado: "Situação: OCUPADO", "Situação do imóvel - desocupado"
    re.compile(r"situacao(?:\s+do\s+imovel)?\s*[:\-–]\s*(des)?ocupad", re.I),
    # afirmação direta: "Imóvel ocupado", "o imóvel encontra-se desocupado"
    re.compile(r"imovel\s+(?:se\s+)?(?:encontra[\-\s]se\s+|esta\s+|"
               r"atualmente\s+)?(des)?ocupad", re.I),
    # inversão: "ocupado o imóvel" / "desocupado o imóvel"
    re.compile(r"\b(des)?ocupado\s+o\s+imovel", re.I),
    # último recurso: a palavra solta, já sem condicional na frase
    re.compile(r"(?<!des)\b(ocupad[oa])\b|\b(desocupad[oa])\b", re.I),
)

# Quebra em sentenças sem depender de pontuação perfeita: a página da Caixa
# mistura ponto, ponto-e-vírgula e quebra de linha.
RE_SENTENCA = re.compile(r"[^.;\n|]+")

# Tira marcação e script de uma página inteira, deixando só o texto corrido.
RE_SCRIPT = re.compile(r"<(script|style)\b.*?</\1>", re.IGNORECASE | re.DOTALL)
RE_TAG = re.compile(r"<[^>]+>")
RE_ESPACO = re.compile(r"[ \t\r\f\v ]+")


def _sem_acento(texto: str) -> str:
    plano = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in plano if not unicodedata.combining(c))


def texto_da_pagina(pagina: str) -> str:
    """Transforma o HTML da página do imóvel em texto corrido.

    O parâmetro NÃO se chama "html": esse nome é do módulo da biblioteca
    padrão usado logo abaixo, e sombreá-lo quebra o unescape.
    """
    limpo = RE_SCRIPT.sub(" ", pagina)
    limpo = re.sub(r"<br\s*/?>|</(p|div|td|tr|li|h\d)>", "\n", limpo,
                   flags=re.IGNORECASE)
    limpo = RE_TAG.sub(" ", limpo)
    # IMPORTANTE decodificar as entidades ANTES de quebrar em frases: o
    # ponto-e-vírgula que fecha "&oacute;" é separador de frase aqui, e
    # partiria "Imóvel ocupado" no meio da palavra.
    limpo = html.unescape(limpo)
    limpo = RE_ESPACO.sub(" ", limpo)
    return re.sub(r"\n{2,}", "\n", limpo).strip()


def ler_texto(texto: str) -> dict:
    """Decide a situação de ocupação a partir do texto da página.

    Devolve ``situacao`` (uma das três constantes) e ``trecho``: a frase
    original que embasou a decisão, ou "" quando nada foi afirmado. O trecho
    vai para a tela de propósito — se a leitura errar, quem olha percebe.
    """
    if not texto:
        return {"situacao": NAO_INFORMADA, "trecho": ""}

    for sentenca in RE_SENTENCA.findall(texto):
        frase = sentenca.strip()
        if len(frase) < 4 or len(frase) > 400:
            continue
        plano = _sem_acento(frase)
        if "ocupad" not in plano.lower():
            continue
        if RE_CONDICIONAL.search(plano):
            continue  # fala de hipótese, não deste imóvel

        for padrao in PADROES:
            achado = padrao.search(plano)
            if not achado:
                continue
            # o grupo "des" (ou o grupo 2 do último padrão) decide o sinal
            grupos = [g for g in achado.groups() if g]
            negado = any(g.lower().startswith("des") for g in grupos)
            return {
                "situacao": DESOCUPADO if negado else OCUPADO,
                "trecho": _encurtar(frase),
            }

    return {"situacao": NAO_INFORMADA, "trecho": ""}


def existencia(texto: str) -> str:
    """O imóvel ainda está no site da Caixa?

    VIVO      a página tem pelo menos duas marcas de ficha de imóvel
    MORTO     a página NEGA, com todas as letras, que o imóvel exista
    INDEFINIDO qualquer outra coisa — e aí não se mexe em nada

    A negação vem primeiro de propósito: a página de "não encontrado"
    carrega o menu inteiro do site da Caixa e pode conter, no rodapé ou
    numa aba, palavras que parecem marca de vida.
    """
    if not texto:
        return INDEFINIDO
    plano = _sem_acento(texto)
    if RE_SEM_IMOVEL.search(plano):
        return MORTO
    if sum(1 for m in MARCAS_DE_VIDA if m.search(plano)) >= 2:
        return VIVO
    return INDEFINIDO


def amostra(texto: str, limite: int = 200) -> str:
    """O que a página diz perto de 'ocupa', quando nada foi concluído.

    Existe para responder a uma dúvida que só os dados reais resolvem:
    quando a leitura não conclui nada, é porque a página da Caixa não
    informa mesmo, ou porque ela informa de um jeito que os padrões
    daqui não pegam? Guardar o trecho original transforma a dúvida numa
    pergunta respondível na execução seguinte, sem ninguém precisar
    abrir 300 páginas na mão.
    """
    if not texto:
        return ""
    plano = _sem_acento(texto)
    achado = re.search(r"ocupa", plano, re.IGNORECASE)
    if not achado:
        return ""
    ini = max(0, achado.start() - 90)
    pedaco = texto[ini:achado.start() + 110]
    return re.sub(r"\s+", " ", pedaco).strip()[:limite]


def ler_pagina(pagina: str) -> dict:
    """Uma visita, duas respostas: se existe e se está ocupado.

    Vale a pena ler juntas porque é a MESMA requisição. Um verificador
    separado dobraria o tráfego no site da Caixa sem necessidade.
    """
    texto = texto_da_pagina(pagina)
    vida = existencia(texto)
    # Imóvel que não existe mais não tem ocupação para ler: insistir só
    # produziria leitura feita no texto da página de erro.
    if vida == MORTO:
        return {"situacao": NAO_INFORMADA, "trecho": "", "existe": MORTO,
                "amostra": ""}
    achado = {**ler_texto(texto), "existe": vida}
    achado["amostra"] = ("" if achado["situacao"] != NAO_INFORMADA
                         else amostra(texto))
    return achado


def _encurtar(frase: str, limite: int = 220) -> str:
    frase = re.sub(r"\s+", " ", frase).strip(" -–—:;")
    return frase if len(frase) <= limite else frase[:limite - 1].rstrip() + "…"


# ---------------------------------------------------------------- roteiro
# O que o comprador precisa saber, por situação. Vai inteiro para o
# resumo.json e a página só renderiza — a regra fica aqui, num lugar só.

_ACORDO = {
    "titulo": "1. Tente o acordo antes de pensar em processo",
    "passos": [
        "Quem está dentro quase sempre é o antigo dono, que perdeu o imóvel "
        "para o banco. Vale procurar antes de qualquer medida judicial.",
        "Negocia-se uma verba de desocupação e um prazo, com termo assinado "
        "— de preferência homologado em juízo, para virar título executivo.",
        "Prazo típico: de algumas semanas a três meses.",
        "Compensa porque, enquanto o processo corre, você paga IPTU e "
        "condomínio de um imóvel que não pode usar nem alugar.",
    ],
}

_JUDICIAL = {
    "titulo": "2. Se não houver acordo, o caminho é judicial",
    "passos": [
        "Quando a Caixa retomou por ALIENAÇÃO FIDUCIÁRIA (o padrão dos "
        "financiamentos mais recentes), o art. 30 da Lei 9.514/97 garante a "
        "quem comprou no leilão a reintegração na posse CONCEDIDA "
        "LIMINARMENTE, com 60 dias para desocupação, bastando comprovar a "
        "consolidação da propriedade.",
        "Desde a Lei 14.711/2023, discussão sobre o contrato ou sobre o "
        "procedimento do leilão não trava mais a reintegração: segue e, se "
        "o ocupante tiver razão, resolve-se em perdas e danos.",
        "Quando a retomada veio de EXECUÇÃO HIPOTECÁRIA ou adjudicação "
        "(contratos antigos), não existe essa liminar automática: é ação de "
        "imissão na posse pelo rito comum, bem mais lenta.",
        "Na prática, mesmo com liminar, conte de 3 a 8 meses entre "
        "protocolar e a chave na mão. Sem liminar, de um a dois anos.",
    ],
}

_TRAVAS = {
    "titulo": "3. O que pode travar — confira antes de dar lance",
    "passos": [
        "Locação averbada na matrícula pode ser oponível ao comprador. "
        "Peça a matrícula atualizada e leia.",
        "Ocupante idoso, com criança pequena ou com problema de saúde: o "
        "juiz costuma alargar prazos.",
        "Débitos de condomínio e IPTU: no acervo da Caixa é comum o "
        "comprador assumir. O edital diz de quem é.",
        "O edital manda. Ele define responsabilidade pela desocupação, "
        "pelos débitos e o estado em que o imóvel é vendido.",
    ],
}

ROTEIRO = {
    OCUPADO: {
        "situacao": "Imóvel ocupado",
        "resumo": "A desocupação corre por sua conta, em dinheiro e em "
                  "tempo. É o custo que mais some das planilhas.",
        "blocos": [_ACORDO, _JUDICIAL, _TRAVAS],
    },
    DESOCUPADO: {
        "situacao": "Imóvel desocupado",
        "resumo": "Sem provisão de desocupação na conta. Ainda assim, "
                  "confirme com os próprios olhos antes de dar lance.",
        "blocos": [
            {
                "titulo": "Confirme, não confie",
                "passos": [
                    "A informação é do momento em que a página foi lida. "
                    "Imóvel vazio é alvo de invasão justamente por estar "
                    "vazio.",
                    "Vá até o endereço, ou peça a alguém de confiança. "
                    "Pergunte no condomínio ou na vizinhança.",
                    "Reserve algo para fechadura, limpeza, religação de "
                    "água e luz, e para o que a foto não mostra.",
                ],
            },
            _TRAVAS,
        ],
    },
    NAO_INFORMADA: {
        "situacao": "Ocupação não informada",
        "resumo": "O arquivo que a Caixa publica não traz ocupação, e a "
                  "página deste imóvel também não afirmou nada. Por "
                  "precaução, trata-se como se pudesse estar ocupado.",
        "blocos": [
            {
                "titulo": "Onde descobrir",
                "passos": [
                    "O edital do imóvel, no site da Caixa, é o documento "
                    "que responde. Baixe e leia antes de qualquer lance.",
                    "A matrícula atualizada mostra de onde veio a "
                    "propriedade e se há locação averbada.",
                    "Visita ao endereço resolve em dez minutos o que "
                    "nenhuma planilha resolve.",
                ],
            },
            _ACORDO,
            _JUDICIAL,
            _TRAVAS,
        ],
    },
}

AVISO_JURIDICO = (
    "Isto é orientação geral, não consultoria jurídica. Prazos, custos e "
    "estratégia mudam conforme o caso, a vara e quem está no imóvel. "
    "Consulte um advogado antes de dar lance em imóvel ocupado."
)
