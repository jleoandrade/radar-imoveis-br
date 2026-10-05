"""Gera uma versão do site com os dados embutidos, para prévia offline.

    python scripts/gerar_previa.py           # recorte de PE
    python scripts/gerar_previa.py RJ PE GO  # os estados que você quiser

O site de verdade busca ``dados/indice.json`` e ``dados/uf/<UF>.json`` com
``fetch``, e isso só funciona servido por um servidor web. Para você poder
abrir o arquivo com dois cliques no Windows e ver como ficou, este script
embute um recorte dos dados direto no HTML, trocando a linha

    const DADOS_EMBUTIDOS = null;

por ``{ indice: {...}, uf: { PE: {...} } }``. Sai em ``previa/``, que não
vai para o site.

O recorte é por estado porque o site agora carrega um estado por vez: a
prévia tem de exercitar o mesmo caminho, inclusive a troca de estado, senão
ela testa um site que não existe.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from analise.compactar import compactar, descompactar  # noqa: E402

ORIGEM = RAIZ / "site"
DESTINO = RAIZ / "previa"
MARCADOR = "const DADOS_EMBUTIDOS = null;"

# quantos imóveis entram por estado. A lista inteira deixaria o arquivo
# grande demais para abrir confortável; 160 é mais que o suficiente para
# ver filtros, ordenação e paginação funcionando.
QUANTOS = 160
UF_PADRAO = ("PE",)


def recortar(imoveis: list[dict]) -> list[dict]:
    """Pega os melhores, mais alguns vetados, alguns em lote e de interior.

    A prévia precisa mostrar os casos ruins também: um layout que só foi
    visto com imóveis bons esconde como ficam o aviso de armadilha e as
    ressalvas longas.
    """
    escolhidos, vistos = [], set()

    def juntar(candidatos, quantos):
        for i in candidatos:
            if len(escolhidos) >= QUANTOS or quantos <= 0:
                return
            if i["id"] in vistos:
                continue
            vistos.add(i["id"])
            escolhidos.append(i)
            quantos -= 1

    juntar([i for i in imoveis if i["classe"] == "vetado"], 12)
    juntar([i for i in imoveis if i["lote"] >= 5], 12)
    juntar([i for i in imoveis if i["praca"] == "interior"], 40)
    juntar(imoveis, QUANTOS)
    return escolhidos


def main() -> None:
    ufs = [u.upper() for u in sys.argv[1:]] or list(UF_PADRAO)

    caminho_indice = ORIGEM / "dados" / "indice.json"
    if not caminho_indice.exists():
        raise SystemExit("Rode primeiro: python scripts/gerar_dados.py")
    indice = json.loads(caminho_indice.read_text(encoding="utf-8"))

    embutido: dict = {"indice": indice, "uf": {}}
    disponiveis = []
    for uf in ufs:
        arquivo = ORIGEM / "dados" / "uf" / f"{uf}.json"
        if not arquivo.exists():
            print(f"  ! {uf} não existe em site/dados/uf/, pulando")
            continue
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
        # descompacta, recorta e RECOMPACTA: a prévia tem de entregar à
        # página exatamente o formato que a página espera
        recorte = recortar(descompactar(dados["imoveis"]))
        resumo = dict(dados["resumo"])
        resumo["aviso_previa"] = (
            f"Prévia com {len(recorte)} dos {resumo['total']} imóveis de {uf}."
        )
        embutido["uf"][uf] = {"resumo": resumo, "imoveis": compactar(recorte)}
        disponiveis.append(uf)
        print(f"  {uf}: {len(recorte)} de {resumo['total']} imóveis")

    if not embutido["uf"]:
        raise SystemExit("Nenhum estado disponível para a prévia.")

    # O seletor de estados sai do índice, então o índice da prévia só pode
    # oferecer os estados que foram embutidos — senão escolher outro
    # estado daria erro de carregamento num arquivo que abre sem servidor.
    indice["estados"] = [e for e in indice["estados"]
                         if e["uf"] in disponiveis]

    html = (ORIGEM / "index.html").read_text(encoding="utf-8")
    if MARCADOR not in html:
        raise SystemExit(
            f"Não achei a linha '{MARCADOR}' em site/index.html — "
            "a prévia depende dela para saber onde injetar os dados."
        )
    saida = html.replace(MARCADOR, "const DADOS_EMBUTIDOS = " + json.dumps(
        embutido, ensure_ascii=False, separators=(",", ":")) + ";")

    DESTINO.mkdir(parents=True, exist_ok=True)
    destino = DESTINO / "index.html"
    destino.write_text(saida, encoding="utf-8")
    print(f"\nPrévia em {destino} ({destino.stat().st_size / 1024:.0f} KB)")
    print("Abra com dois cliques — não precisa de servidor.")


if __name__ == "__main__":
    main()
