"""Confere se o que foi gerado faz sentido antes de publicar.

    python scripts/conferir.py

Existe por um motivo concreto: quando fui olhar o site de um projeto
parecido, ele estava no ar, bonito, e com "Nenhum imóvel encontrado". A
coleta tinha falhado em silêncio e o site continuou publicado, vazio.

Aqui a execução para antes de publicar se qualquer coisa estiver errada. A
falha aparece na aba Actions, em vermelho, e o site continua mostrando os
dados bons da véspera — que é o comportamento certo.

NO NACIONAL, A TRAVA PRECISOU DE MAIS DENTES
--------------------------------------------
Com um estado só, "veio pouca coisa" era a única falha possível. Com 27
arquivos, existem falhas novas que o total nacional esconde:

* um estado inteiro faltando — o total cai 3% e ninguém nota, mas quem mora
  lá vê uma lista vazia;
* o arquivo compactado desalinhado — linha com menos valores que campos, o
  que faria a página mostrar dado de um campo no lugar de outro;
* índice e arquivos de estado em desacordo, se um for gravado e o outro não.

Por isso a conferência percorre os 27 arquivos, e não só o total.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DADOS = RAIZ / "site" / "dados"
DADOS_UF = DADOS / "uf"

# Mínimos deliberadamente folgados: eles pegam "a coleta quebrou", não "o
# acervo encolheu um pouco". Medido em 30/09/2026: 18.266 imóveis, 27 UFs,
# 1.068 cidades. O piso nacional é um terço disso, porque acervo de leilão
# oscila de verdade e falha de robô é sempre catastrófica, não sutil.
MINIMO_IMOVEIS = 6_000
MINIMO_CIDADES = 200
MINIMO_UFS = 20

# O menor estado real tinha 3 imóveis (Amapá), então não dá para exigir
# volume por estado. O que dá para exigir é que o arquivo exista e abra.
MINIMO_POR_UF = 1


def conferir() -> list[str]:
    problemas = []

    for nome in ("indice.json", "feed.xml"):
        if not (DADOS / nome).exists():
            problemas.append(f"{nome} não foi gerado")
    if not DADOS_UF.exists():
        problemas.append("a pasta site/dados/uf/ não foi gerada")
    if problemas:
        return problemas

    indice = json.loads((DADOS / "indice.json").read_text(encoding="utf-8"))
    estados = indice.get("estados", [])

    if len(estados) < MINIMO_UFS:
        problemas.append(
            f"só {len(estados)} estados no índice (esperado ao menos "
            f"{MINIMO_UFS}) — o arquivo nacional provavelmente veio parcial"
        )

    total = 0
    cidades = set()
    sem_preco = sem_area = 0

    for estado in estados:
        uf = estado.get("uf", "?")
        arquivo = DADOS_UF / f"{uf}.json"
        if not arquivo.exists():
            # É ESTA a falha que o total nacional esconderia: o índice
            # anuncia o estado, o seletor o oferece, e o arquivo não existe.
            problemas.append(f"o índice lista {uf} mas {uf}.json não existe")
            continue

        try:
            dados = json.loads(arquivo.read_text(encoding="utf-8"))
        except json.JSONDecodeError as erro:
            problemas.append(f"{uf}.json está corrompido: {erro}")
            continue

        bloco = dados.get("imoveis") or {}
        campos = bloco.get("campos") or []
        linhas = bloco.get("linhas") or []

        if len(linhas) < MINIMO_POR_UF:
            problemas.append(f"{uf}.json veio sem nenhum imóvel")
            continue
        if len(linhas) != estado.get("total"):
            problemas.append(
                f"{uf}: o índice diz {estado.get('total')} imóveis e o "
                f"arquivo tem {len(linhas)}"
            )

        # Desalinhamento do formato compacto: uma linha com número de
        # valores diferente do número de campos faria a página ler o campo
        # errado SEM ERRO NENHUM — o pior tipo de defeito.
        tortas = sum(1 for linha in linhas if len(linha) != len(campos))
        if tortas:
            problemas.append(
                f"{uf}: {tortas} linhas com número de valores diferente dos "
                f"{len(campos)} campos — o arquivo compacto desalinhou"
            )

        pos = {c: n for n, c in enumerate(campos)}
        for obrigatorio in ("id", "uf", "cidade", "preco", "nota"):
            if obrigatorio not in pos:
                problemas.append(f"{uf}: falta o campo '{obrigatorio}'")

        if "cidade" in pos:
            dic = (bloco.get("dicionarios") or {}).get("cidade") or []
            for linha in linhas:
                if len(linha) == len(campos):
                    valor = linha[pos["cidade"]]
                    # (UF, cidade), não só o nome: 16 nomes se repetem
                    # entre estados e contar por nome subestima o total
                    # de municípios em 16 — o mesmo erro que o projeto
                    # inteiro existe para não cometer
                    cidades.add((uf, dic[valor] if dic else valor))
        if "preco" in pos:
            sem_preco += sum(1 for linha in linhas
                             if len(linha) == len(campos)
                             and not linha[pos["preco"]])
        if "area" in pos:
            sem_area += sum(1 for linha in linhas
                            if len(linha) == len(campos)
                            and not linha[pos["area"]])
        total += len(linhas)

    if total < MINIMO_IMOVEIS:
        problemas.append(
            f"só {total} imóveis somando os estados (esperado ao menos "
            f"{MINIMO_IMOVEIS}) — a lista da Caixa provavelmente mudou de "
            f"formato ou veio incompleta"
        )
    if total != indice.get("total"):
        problemas.append(
            f"o índice diz {indice.get('total')} imóveis e os arquivos "
            f"somam {total}"
        )
    if len(cidades) < MINIMO_CIDADES:
        problemas.append(
            f"só {len(cidades)} municípios distintos — suspeito de erro de "
            f"leitura das colunas"
        )
    if total and sem_preco > total * 0.05:
        problemas.append(
            f"{sem_preco} imóveis sem preço — a coluna de preço não foi "
            f"lida direito"
        )
    if total and sem_area > total * 0.30:
        problemas.append(
            f"{sem_area} imóveis sem área — a descrição mudou de formato e "
            f"as expressões regulares pararam de casar"
        )

    if not indice.get("data_da_lista") or indice["data_da_lista"] == "—":
        problemas.append("a data de geração da lista não foi encontrada")

    desconto = indice.get("desconto_real_mediano")
    if desconto is None or not (-1 < desconto < 1):
        problemas.append(f"desconto real mediano fora do esperado: {desconto}")

    # Os moldes do parecer agora viajam no índice e a página depende deles:
    # sem eles, todo imóvel apareceria sem o texto que explica a nota.
    for molde in ("desconto", "pares", "sem_pares", "vetado"):
        if not (indice.get("moldes") or {}).get(molde):
            problemas.append(f"falta o molde '{molde}' no índice")

    return problemas


def main() -> None:
    problemas = conferir()
    if problemas:
        print("FALHOU — o site NÃO será publicado:\n")
        for p in problemas:
            print(f"  - {p}")
        print("\nO site continua no ar com os dados da última execução boa.")
        sys.exit(1)

    indice = json.loads((DADOS / "indice.json").read_text(encoding="utf-8"))
    estados = indice.get("estados", [])
    maior = max(estados, key=lambda e: e["total"]) if estados else {}
    print(
        f"OK: {indice['total']} imóveis em {len(estados)} estados, "
        f"{indice['destaques']} destaques. "
        f"Maior: {maior.get('uf')} com {maior.get('total')}. "
        f"Lista da Caixa de {indice['data_da_lista']}."
    )


if __name__ == "__main__":
    main()
