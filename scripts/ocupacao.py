"""Descobre na página da Caixa se cada imóvel está ocupado, com cache.

    python scripts/ocupacao.py                 # a fila do dia, até 600
    python scripts/ocupacao.py --limite 50
    python scripts/ocupacao.py --uf PE         # só um estado

POR QUE PRECISA DISTO
---------------------
O arquivo que a Caixa publica para download não traz ocupação — conferido,
zero menções a ocupação nos 18.266 imóveis do arquivo nacional. A informação
está na página individual de cada imóvel, aquela mesma do botão "Página da
Caixa" no site.

Ocupação é o item mais caro da conta depois da reforma. Sem ela, o modelo
reserva uma provisão cega em todo imóvel; com ela, o imóvel comprovadamente
vazio sai da provisão e o ocupado entra com aviso na tela.

A ARITMÉTICA MUDOU AO VIRAR NACIONAL
------------------------------------
Em Pernambuco eram 1.060 páginas: a 300 por execução, o acervo inteiro ficava
lido em quatro dias e dava para reconferir tudo a cada sete. No Brasil são
18.266. Com a regra antiga:

* primeira passada: 18.266 / 900 por dia = **21 dias**;
* reconferir tudo a cada 7 dias exigiria 2.609 páginas por dia, contra as
  900 que cabem. **A regra de 7 dias para todo mundo é impossível.**

Então a fila passou a ser por MÉRITO, e o prazo de releitura passou a ser
dois. Destaque (nota >= 0,60, são 3.613) é reconferido a cada 7 dias; o resto
a cada 30. Em regime isso dá cerca de mil páginas por dia, e cabe nas 1.800
que três execuções permitem — sobra folga para a primeira passada andar.

O efeito prático: o que você olha fica conferido em dois ou três dias, não em
vinte e um. O imóvel de nota baixa demora mais, e demorar mais nele custa
pouco.

COMO SE COMPORTA
----------------
Lê uma página por vez, com pausa de pouco mais de um segundo e User-Agent que
identifica o projeto, e guarda o resultado em ``dados/ocupacao.json`` para
nunca pedir duas vezes o mesmo imóvel sem necessidade. São 600 páginas em
cerca de 18 minutos, ou seja menos de uma requisição por segundo.

Se a Caixa recusar, demorar ou mudar a página, o script PARA sem quebrar
nada: quem não foi lido continua como "não informada", que é exatamente o
que o site já mostrava antes. Nada regride.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import date
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from analise.ocupacao import (  # noqa: E402
    INDEFINIDO,
    MORTO,
    NAO_INFORMADA,
    VIVO,
    ler_pagina,
)

CACHE = RAIZ / "dados" / "ocupacao.json"
DADOS_UF = RAIZ / "site" / "dados" / "uf"
INDICE = RAIZ / "site" / "dados" / "indice.json"

PAGINA_CAIXA = ("https://venda-imoveis.caixa.gov.br/sistema/"
                "detalhe-imovel.asp?hdnimovel=")

LIMITE_PADRAO = 600   # ~18 min por execução, menos de 1 requisição/segundo
PAUSA = 1.2            # segundos entre páginas; nada de rajada
ESPERA_RESPOSTA = 20   # segundos até desistir de uma página
FALHAS_SEGUIDAS = 5    # tantas falhas em sequência e o script desiste

# De quantos em quantos dias vale reconferir um imóvel já lido. Ocupação
# quase não muda; existência muda toda hora. Por isso a releitura existe:
# sem ela, um imóvel lido hoje nunca mais seria conferido e continuaria
# no site depois de arrematado.
#
# São DOIS prazos porque com 18.266 imóveis um prazo só não fecha a conta:
# 7 dias para todos exigiria 2.609 páginas por dia e só cabem 1.800.
DIAS_RECONFERIR_DESTAQUE = 7
DIAS_RECONFERIR_RESTO = 30

# nota a partir da qual o imóvel é destaque. TEM DE BATER com NOTA_DESTAQUE
# de scripts/gerar_dados.py — é lida do índice quando ele existe, e esta
# constante é só o padrão para quando não existe.
NOTA_DESTAQUE = 0.60

AGENTE = (
    "radar-imoveis-br/1.0 (projeto pessoal de analise do acervo publico "
    "da Caixa; contato pelo GitHub)"
)
CABECALHOS = {
    "User-Agent": AGENTE,
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "pt-BR,pt;q=0.9",
}


def carregar_cache() -> dict:
    """Lê o cache já com as chaves limpas.

    As primeiras leituras foram gravadas com o número sujo da Caixa
    (" 8444411406630 "). O limpar aqui não é cosmético: sem ele, o
    escolher() não reconheceria essas páginas como já lidas e mandaria
    visitar de novo as mesmas 300 — seis minutos e trezentas requisições
    jogadas fora, todo dia.
    """
    if not CACHE.exists():
        return {}
    try:
        dados = json.loads(CACHE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(dados, dict):
        return {}

    limpo, sujas = {}, 0
    for chave, valor in dados.items():
        if str(chave).startswith("_"):
            limpo[chave] = valor       # metadados passam intactos
            continue
        k = str(chave).strip()
        sujas += k != chave
        anterior = limpo.get(k)
        if anterior and (anterior.get("lido_em") or "") >= (
                (valor or {}).get("lido_em") or ""):
            continue
        limpo[k] = valor
    if sujas:
        print(f"  {sujas} chaves antigas limpas (vinham com espaço)")
    return limpo


def gravar_cache(cache: dict) -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=0),
                     encoding="utf-8")


def consultar(sessao: requests.Session, url: str) -> dict:
    """Lê a página do imóvel e devolve situação + trecho que a embasou."""
    resposta = sessao.get(url, headers=CABECALHOS, timeout=ESPERA_RESPOSTA)
    resposta.raise_for_status()
    # a página da Caixa é latin-1; o requests às vezes adivinha errado
    if not resposta.encoding or resposta.encoding.lower() == "iso-8859-1":
        resposta.encoding = "latin-1"
    return ler_pagina(resposta.text)


def escolher(imoveis: list, cache: dict, limite: int, hoje: str,
             nota_destaque: float = NOTA_DESTAQUE) -> list:
    """Monta a fila da execução, em cinco camadas de prioridade.

    1. OS MARCADOS COMO FORA DO AR, sempre e todos. São poucos e a
       releitura é o que permite o imóvel RESSUSCITAR: leilão não
       arrematado volta para o acervo, e seria péssimo deixá-lo apagado
       para sempre por causa de uma leitura de ontem.
    2. DESTAQUE NUNCA LIDO, do melhor para o pior. É onde a informação nova
       vale mais, e é o que a pessoa de fato vai abrir.
    3. DESTAQUE VENCIDO (lido há 7 dias ou mais), do mais velho primeiro.
    4. O RESTO NUNCA LIDO, do melhor para o pior.
    5. O RESTO VENCIDO (lido há 30 dias ou mais).

    A ordem entre 3 e 4 é deliberada: destaque com leitura velha vem ANTES
    de imóvel de nota baixa nunca lido. Um destaque que já foi arrematado e
    continua na tela engana; um imóvel de nota 0,2 sem leitura só fica com a
    provisão cega de desocupação, que é o comportamento padrão e correto.

    Com 18.266 imóveis, é esta ordem — e não o tamanho da fila — que decide
    se o site está confiável no que importa.
    """
    dentro, vistos = [], set()

    def juntar(candidatos):
        for i in candidatos:
            if len(dentro) >= limite:
                return
            if i["id"] in vistos:
                continue
            vistos.add(i["id"])
            dentro.append(i)

    def lido_em(i):
        return (cache.get(i["id"]) or {}).get("lido_em", "")

    def vencido(i, prazo):
        return i["id"] in cache and _dias(lido_em(i), hoje) >= prazo

    destaque = [i for i in imoveis if (i.get("nota") or 0) >= nota_destaque]
    resto = [i for i in imoveis if (i.get("nota") or 0) < nota_destaque]

    # 1 — fora do ar: todos, sempre
    juntar([i for i in imoveis
            if (cache.get(i["id"]) or {}).get("existe") == MORTO])
    # 2 — destaque nunca lido
    juntar(sorted([i for i in destaque if i["id"] not in cache],
                  key=lambda i: -(i.get("nota") or 0)))
    # 3 — destaque vencido
    juntar(sorted([i for i in destaque
                   if vencido(i, DIAS_RECONFERIR_DESTAQUE)], key=lido_em))
    # 4 — o resto nunca lido
    juntar(sorted([i for i in resto if i["id"] not in cache],
                  key=lambda i: -(i.get("nota") or 0)))
    # 5 — o resto vencido
    juntar(sorted([i for i in resto
                   if vencido(i, DIAS_RECONFERIR_RESTO)], key=lido_em))
    return dentro


def _dias(de: str, ate: str) -> int:
    try:
        return (date.fromisoformat(ate) - date.fromisoformat(de)).days
    except (ValueError, TypeError):
        return 10**6      # data estranha conta como vencida há muito tempo


def carregar_imoveis(uf: str | None = None) -> tuple[list[dict], float]:
    """Junta os imóveis dos arquivos por estado e descompacta o necessário.

    Só três campos interessam aqui — id, nota e o rótulo para o relatório —
    então nem vale montar o objeto inteiro de 49 campos de 18 mil imóveis.
    """
    if not DADOS_UF.exists():
        raise SystemExit("Rode antes: python scripts/gerar_dados.py")

    nota_destaque = NOTA_DESTAQUE
    if INDICE.exists():
        try:
            nota_destaque = float(json.loads(
                INDICE.read_text(encoding="utf-8")).get(
                    "nota_destaque", NOTA_DESTAQUE))
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            pass

    arquivos = sorted(DADOS_UF.glob("*.json"))
    if uf:
        arquivos = [a for a in arquivos if a.stem == uf.strip().upper()]
        if not arquivos:
            raise SystemExit(f"Não há dados de {uf} em site/dados/uf/")

    imoveis = []
    for arquivo in arquivos:
        bloco = json.loads(arquivo.read_text(encoding="utf-8"))["imoveis"]
        campos = bloco["campos"]
        dicionarios = bloco.get("dicionarios") or {}
        pos = {c: n for n, c in enumerate(campos)}

        def valor(linha, campo, pos=pos, dicionarios=dicionarios):
            if campo not in pos:
                return None
            v = linha[pos[campo]]
            dic = dicionarios.get(campo)
            return dic[v] if dic is not None else v

        for linha in bloco["linhas"]:
            imoveis.append({
                "id": valor(linha, "id"),
                "nota": valor(linha, "nota") or 0,
                "uf": valor(linha, "uf") or arquivo.stem,
                "cidade": valor(linha, "cidade") or "",
                "bairro": valor(linha, "bairro") or "",
                "tipo": valor(linha, "tipo") or "",
                "preco": valor(linha, "preco") or 0,
                "link": PAGINA_CAIXA + str(valor(linha, "id") or ""),
            })
    return imoveis, nota_destaque


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limite", type=int, default=LIMITE_PADRAO,
                        help=f"páginas por execução (padrão {LIMITE_PADRAO})")
    parser.add_argument("--uf", default=None,
                        help="confere só um estado (ex.: PE)")
    argumentos = parser.parse_args()

    imoveis, nota_destaque = carregar_imoveis(argumentos.uf)
    cache = carregar_cache()
    hoje = date.today().isoformat()
    alvo = escolher(imoveis, cache, argumentos.limite, hoje, nota_destaque)

    lidos = sum(1 for k in cache if not str(k).startswith("_"))
    faltam = sum(1 for i in imoveis if i["id"] not in cache)
    destaques = sum(1 for i in imoveis if i["nota"] >= nota_destaque)
    falta_destaque = sum(1 for i in imoveis
                         if i["nota"] >= nota_destaque and i["id"] not in cache)
    print(f"{len(imoveis)} imóveis no acervo, {lidos} já lidos, "
          f"{faltam} sem leitura.")
    print(f"  destaques: {destaques}, dos quais {falta_destaque} sem leitura "
          f"— é a fila que importa")
    if faltam:
        dias = faltam / max(1, argumentos.limite * 3)
        print(f"  no ritmo de {argumentos.limite} x 3 por dia, a primeira "
              f"passada fecha em ~{dias:.0f} dias")
    if not alvo:
        print("Nada a fazer.")
        return
    print(f"Lendo {len(alvo)} páginas, uma a cada {PAUSA}s "
          f"(~{len(alvo) * PAUSA / 60:.0f} min).")

    sessao = requests.Session()
    contagem = {"ocupado": 0, "desocupado": 0, NAO_INFORMADA: 0}
    vida = {VIVO: 0, MORTO: 0, INDEFINIDO: 0}
    saiu, voltou, amostras = [], [], []
    seguidas = 0

    for n, imovel in enumerate(alvo, start=1):
        try:
            achado = consultar(sessao, imovel["link"])
            seguidas = 0
        except Exception as erro:  # noqa: BLE001
            seguidas += 1
            print(f"  ! {imovel['id']}: {type(erro).__name__}")
            if seguidas >= FALHAS_SEGUIDAS:
                print(f"\n! {FALHAS_SEGUIDAS} falhas seguidas. Parando por "
                      f"aqui — quem não foi lido fica como 'não informada', "
                      f"que é o que o site já mostrava. Nada se perde.")
                break
            time.sleep(PAUSA * 2)
            continue

        anterior = cache.get(imovel["id"]) or {}
        antes, agora = anterior.get("existe"), achado["existe"]

        # INDEFINIDO nunca sobrescreve uma resposta que já foi clara.
        # Página lenta, estranha ou meio carregada não pode apagar nem
        # ressuscitar imóvel nenhum.
        if agora == INDEFINIDO and antes in (VIVO, MORTO):
            agora = antes

        if antes != MORTO and agora == MORTO:
            saiu.append(imovel)
        elif antes == MORTO and agora == VIVO:
            voltou.append(imovel)

        cache[imovel["id"]] = {
            # ocupação lida de página morta não vale nada: guarda a antiga
            "situacao": (anterior.get("situacao", NAO_INFORMADA)
                         if agora == MORTO else achado["situacao"]),
            "trecho": (anterior.get("trecho", "")
                       if agora == MORTO else achado["trecho"]),
            "existe": agora,
            "lido_em": hoje,
        }
        contagem[achado["situacao"]] = contagem.get(achado["situacao"], 0) + 1
        vida[agora] = vida.get(agora, 0) + 1

        # guarda até 8 trechos DIFERENTES do que a página diz perto de
        # "ocupa" quando nada foi concluído. É o que vai dizer, na
        # próxima execução, se as páginas calam ou se os padrões erram.
        a = achado.get("amostra")
        if a and len(amostras) < 8 and a not in amostras:
            amostras.append(a)

        if n % 25 == 0 or n == len(alvo):
            print(f"  {n}/{len(alvo)} · {contagem['ocupado']} ocupados · "
                  f"{contagem['desocupado']} vazios · "
                  f"{vida[MORTO]} fora do ar")
            gravar_cache(cache)

        # jitter pequeno: ritmo exatamente constante é desnecessário e
        # parece mais com robô do que com gente lendo anúncio
        time.sleep(PAUSA + random.uniform(0, 0.4))

    if amostras:
        cache["_amostras"] = {"lido_em": hoje, "trechos": amostras}
    gravar_cache(cache)

    if amostras:
        print(f"\nO QUE AS PÁGINAS DIZEM PERTO DE \"OCUPA\" quando a leitura "
              f"não conclui ({len(amostras)} exemplos diferentes):")
        for a in amostras:
            print(f"   · {a}")
        print("   (se houver aí um padrão que os filtros não pegam, dá para "
              "ensiná-lo em analise/ocupacao.py)")

    total = sum(1 for k in cache if not str(k).startswith("_"))
    reais = [v for k, v in cache.items() if not str(k).startswith("_")]
    ocupados = sum(1 for v in reais if v.get("situacao") == "ocupado")
    vazios = sum(1 for v in reais if v.get("situacao") == "desocupado")
    mortos = sum(1 for v in reais if v.get("existe") == MORTO)
    print(f"\nCache: {total} imóveis · {ocupados} ocupados · "
          f"{vazios} desocupados · {total - ocupados - vazios} sem informação")
    print(f"       {mortos} marcados como fora do ar no site da Caixa")

    if saiu:
        print(f"\nSAÍRAM do site da Caixa nesta execução ({len(saiu)}):")
        for i in saiu[:12]:
            print(f"  {i['id']}  {i['tipo']} · {i['bairro']}, "
                  f"{i['cidade']}/{i['uf']}"
                  f"  R$ {i['preco']:,.0f}".replace(",", "."))
        if len(saiu) > 12:
            print(f"  ... e mais {len(saiu) - 12}")
    if voltou:
        print(f"\nVOLTARAM ao site da Caixa ({len(voltou)}):")
        for i in voltou[:12]:
            print(f"  {i['id']}  {i['tipo']} · {i['bairro']}, "
                  f"{i['cidade']}/{i['uf']}")

    print("\nRode scripts/gerar_dados.py de novo para a conta usar isto.")


if __name__ == "__main__":
    main()
