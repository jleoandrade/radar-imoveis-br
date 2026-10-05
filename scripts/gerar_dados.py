"""Baixa a lista da Caixa, analisa e escreve os dados do site.

    python scripts/gerar_dados.py                    # Brasil inteiro
    python scripts/gerar_dados.py PE                 # só um estado
    python scripts/gerar_dados.py Lista_geral.csv    # usa arquivo local

Escreve em ``site/dados/``:

    indice.json      resumo do país, a lista das 27 UFs com a contagem de
                     cada uma, as premissas e os textos compartilhados
    uf/<UF>.json     os imóveis daquele estado, com o parecer de cada um
    feed.xml         RSS com as oportunidades novas, para assinar num leitor

**Por que dividido por estado.** São 18.266 imóveis no país (medido em
30/09/2026) contra 1.060 só de Pernambuco. Num arquivo único isso daria
perto de 25 MB de JSON, e o Rio de Janeiro sozinho — 5.995 imóveis, um terço
do acervo — já pesaria 8 MB. Nenhum celular abre uma página assim. Dividido
por UF, o navegador baixa só o estado que a pessoa está olhando, e troca de
arquivo quando ela troca de estado.

E mantém ``dados/historico.json`` fora do site, com a primeira vez que cada
imóvel apareceu e o último preço visto. É isso que permite marcar "novo" e
detectar queda de preço — a informação mais perecível do acervo. O histórico
continua sendo UM arquivo para o país inteiro: o número do imóvel da Caixa é
único nacionalmente, então não há colisão entre estados.

Este script é o único lugar que escreve dados. A página só lê o JSON.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.sax.saxutils import escape

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from analise import compactar as mod_compactar  # noqa: E402
from analise import custos as mod_custos  # noqa: E402
from analise import ocupacao as mod_ocupacao  # noqa: E402
from analise.caixa import AVISOS_CAIXA, ListaCaixa  # noqa: E402
from analise.geografia import (  # noqa: E402
    CAPITAIS,
    NOMES_PRACA,
    NOMES_UF,
    REGIAO_DA_UF,
    mercado_liquido,
    praca,
    reconhecer_bairro,
    regiao_metropolitana,
    tem_catalogo_rm,
)
from analise.parecer import (  # noqa: E402
    DESCRICAO_NIVEL,
    LOTE_RELEVANTE,
    MOLDES,
    avaliar,
    mediana,
    referencia_do_imovel,
    referencias_por_cidade,
)

ORIGEM_PADRAO = "BR"
SAIDA = RAIZ / "site" / "dados"
SAIDA_UF = SAIDA / "uf"
HISTORICO = RAIZ / "dados" / "historico.json"
OCUPACAO = RAIZ / "dados" / "ocupacao.json"
SEMENTE = RAIZ / "dados" / "semente_historico.json"
FUSO = timezone(timedelta(hours=-3))      # America/Sao_Paulo

# Os horários que o robô tenta, em hora de Recife. TÊM DE BATER com os
# três "cron" de .github/workflows/atualizar.yml, lembrando que lá os
# números estão em UTC (some 3 horas: 06:10 daqui é 09:10 lá).
# Mudou um, mude o outro — senão o site anuncia uma hora e o robô roda
# em outra.
HORARIOS = ((6, 10), (13, 40), (20, 25))

# O prefixo da página de cada imóvel no site da Caixa. Fica aqui porque
# o id é a única parte que varia, e repetir a URL inteira em cada registro
# custaria 1,5 MB no arquivo nacional.
PAGINA_CAIXA = ("https://venda-imoveis.caixa.gov.br/sistema/"
                "detalhe-imovel.asp?hdnimovel=")


def proxima_execucao(agora: datetime) -> datetime:
    """O próximo horário programado depois de 'agora'.

    Com três disparos por dia, "amanhã às 06:10" deixou de ser verdade:
    quem roda de manhã tem a próxima à tarde, não no dia seguinte.
    """
    for hora, minuto in HORARIOS:
        alvo = agora.replace(hour=hora, minute=minuto, second=0,
                             microsecond=0)
        if alvo > agora:
            return alvo
    hora, minuto = HORARIOS[0]
    return (agora + timedelta(days=1)).replace(
        hour=hora, minute=minuto, second=0, microsecond=0)


# nota a partir da qual o imóvel entra no RSS e no destaque da página
NOTA_DESTAQUE = 0.60
# quantos dias um imóvel continua marcado como "novo"
DIAS_NOVO = 7
# arredondamento da área para agrupar unidades idênticas (em m²)
TOLERANCIA_LOTE = 0.5


# --------------------------------------------------------------- histórico
def normalizar_chaves(dados: dict) -> dict:
    """Tira o espaço das chaves antigas sem perder o que elas guardavam.

    O histórico foi gravado com o número sujo (" 8444411406630 "), porque
    é assim que a Caixa publica. Agora o número é limpo na leitura. Sem
    esta migração, TODO imóvel viraria "novo" de novo no primeiro dia e a
    data de primeira aparição — que não dá para reconstruir, porque a
    lista da Caixa é uma fotografia de hoje — seria perdida.

    Quando as duas versões existem, vence a mais antiga: é a verdadeira.
    """
    limpo: dict = {}
    for chave, valor in dados.items():
        k = chave.strip()
        atual = limpo.get(k)
        if atual and isinstance(atual, dict) and isinstance(valor, dict):
            if (atual.get("visto_em") or "9") <= (valor.get("visto_em") or "9"):
                continue
        limpo[k] = valor
    return limpo


def carregar_historico() -> dict:
    # ATENÇÃO à ordem: a semente tem de ser aplicada TAMBÉM quando não há
    # histórico nenhum — instalação nova, ou primeira execução depois de
    # criar o repositório do zero. Antes isto devolvia {} direto e a
    # semente era ignorada justamente no caso em que ela mais importa.
    if not HISTORICO.exists():
        return aplicar_semente({})
    try:
        bruto = json.loads(HISTORICO.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print("! historico.json ilegível, começando de novo")
        return aplicar_semente({})
    limpo = normalizar_chaves(bruto)
    if len(limpo) != len(bruto) or any(k != k.strip() for k in bruto):
        print(f"  histórico migrado: {len(bruto)} chaves -> {len(limpo)} "
              f"sem espaço (nenhuma data perdida)")
    return aplicar_semente(limpo)


def aplicar_semente(historico: dict) -> dict:
    """Puxa a data para trás quando a semente conhece uma mais antiga.

    A semente (dados/semente_historico.json) traz datas importadas de
    outro radar público. Elas não dizem quando o imóvel apareceu na
    Caixa; dizem que ele JÁ EXISTIA naquela data. Por isso a regra aqui é
    de PISO, não de substituição:

      - sem registro nosso        -> adota a data da semente
      - nosso registro é MAIS NOVO-> recua para a data da semente
      - nosso registro é MAIS ANTIGO -> mantém o nosso, que é melhor

    Assim a importação nunca piora uma data que já observamos, e roda
    quantas vezes for sem mudar o resultado. O campo 'origem' fica no
    registro para você saber, depois, qual data veio de fora.
    """
    if not SEMENTE.exists():
        return historico
    try:
        dados = json.loads(SEMENTE.read_text(encoding="utf-8"))
        itens = dados.get("itens") or {}
    except (json.JSONDecodeError, OSError, AttributeError):
        print("! semente_historico.json ilegível, seguindo sem ela")
        return historico

    recuados = adotados = 0
    for chave, data in itens.items():
        chave = str(chave).strip()
        if not chave or not isinstance(data, str) or len(data) != 10:
            continue
        atual = historico.get(chave)
        if atual is None:
            historico[chave] = {"visto_em": data, "ultima_vez": data,
                                "origem": "semente"}
            adotados += 1
        elif (atual.get("visto_em") or "9999") > data:
            atual["visto_em"] = data
            atual["origem"] = "semente"
            recuados += 1

    if recuados or adotados:
        print(f"  semente aplicada: {adotados} datas adotadas (não havia "
              f"registro), {recuados} recuadas (o registro era mais novo)")
    return historico


def atualizar_historico(historico: dict, imoveis: list[dict], hoje: str
                        ) -> dict:
    """Registra primeira aparição e queda de preço de cada imóvel.

    Começa do histórico ANTIGO, não de um dicionário vazio. Antes, quem
    saísse da lista da Caixa era apagado daqui — e aí, se o imóvel
    voltasse (o que acontece direto: leilão não arrematado volta para o
    acervo), ele contava como "novo" outra vez e a data de primeira
    aparição ia embora. Essa data não dá para reconstruir depois, porque
    a lista da Caixa é uma fotografia do dia.

    Quem some fica guardado com o 'ultima_vez' congelado no último dia em
    que apareceu. É o que permite dizer "sumiu há 12 dias" e reconhecer o
    imóvel quando ele voltar.
    """
    novo = dict(historico)
    for i in imoveis:
        anterior = historico.get(i["id"], {})
        visto_em = anterior.get("visto_em", hoje)
        preco_antigo = anterior.get("preco")

        dias = (datetime.fromisoformat(hoje)
                - datetime.fromisoformat(visto_em)).days
        i["visto_em"] = visto_em
        i["dias_no_acervo"] = dias
        # data que veio da semente é limite, não observação nossa: a tela
        # precisa dizer "pelo menos" em vez de fingir precisão
        i["data_estimada"] = anterior.get("origem") == "semente"
        i["novo"] = dias < DIAS_NOVO
        i["queda_preco"] = (
            round(1 - i["preco"] / preco_antigo, 4)
            if preco_antigo and i["preco"] < preco_antigo else None
        )

        registro = {"visto_em": visto_em, "preco": i["preco"],
                    "ultima_vez": hoje}
        # preserva de onde veio a data; sem isto a marcação "estimada"
        # some na primeira execução e a data vira observação nossa
        if anterior.get("origem"):
            registro["origem"] = anterior["origem"]
        novo[i["id"]] = registro

    # imóveis que saíram da lista: guardamos por 90 dias para não perder a
    # data de primeira aparição se eles voltarem
    limite = (datetime.fromisoformat(hoje) - timedelta(days=90)).date()
    for chave, valor in historico.items():
        if chave in novo:
            continue
        ultima = valor.get("ultima_vez", hoje)
        if datetime.fromisoformat(ultima).date() >= limite:
            novo[chave] = valor

    return novo


# ------------------------------------------------------------- ocupação
def carregar_ocupacao() -> dict:
    """Leituras feitas por scripts/ocupacao.py nas páginas da Caixa.

    Arquivo ausente, vazio ou corrompido devolve {} e todo imóvel volta a
    "não informada" — exatamente o que o site mostrava antes de existir
    esta leitura. Nenhum caminho aqui deixa o site pior do que estava.
    """
    if not OCUPACAO.exists():
        return {}
    try:
        dados = json.loads(OCUPACAO.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(dados, dict):
        return {}

    # MESMA limpeza de chave do histórico, e pelo mesmo motivo. As
    # primeiras leituras foram gravadas com o número sujo (" 8444... "),
    # porque é assim que a Caixa publica e era assim que o id chegava
    # aqui. Agora o id é limpo na leitura da lista — e sem este strip
    # NENHUMA leitura casaria: 300 páginas visitadas, e o site mostrando
    # "não informada" em todas. Foi exatamente o que aconteceu.
    limpo = {}
    for chave, valor in dados.items():
        if str(chave).startswith("_"):      # metadados, não são imóveis
            continue
        k = str(chave).strip()
        anterior = limpo.get(k)
        # se as duas versões existirem, vence a leitura mais recente
        if anterior and (anterior.get("lido_em") or "") >= (
                (valor or {}).get("lido_em") or ""):
            continue
        limpo[k] = valor
    return limpo


def situacao_do_imovel(bruto: dict, lidas: dict) -> dict:
    """Combina o que veio na lista com o que foi lido na página.

    A página manda, porque é onde a Caixa de fato informa. A descrição da
    lista entra só quando a página não disse nada — e, na prática, ela
    quase nunca diz.
    """
    lida = lidas.get(bruto["id"]) or {}
    situacao = lida.get("situacao")
    fonte, trecho = "página do imóvel", lida.get("trecho", "")

    if situacao not in (mod_ocupacao.OCUPADO, mod_ocupacao.DESOCUPADO):
        if bruto["ocupado"]:
            situacao, fonte, trecho = mod_ocupacao.OCUPADO, "lista da Caixa", ""
        elif not bruto["ocupacao_desconhecida"]:
            situacao, fonte, trecho = (mod_ocupacao.DESOCUPADO,
                                       "lista da Caixa", "")
        else:
            situacao, fonte, trecho = mod_ocupacao.NAO_INFORMADA, "", ""

    return {
        "ocupacao": situacao,
        "ocupacao_fonte": fonte,
        "ocupacao_trecho": trecho,
        # quando a página deste imóvel foi conferida pela última vez.
        # Vazio = ainda não foi; a fila anda 300 por dia.
        "conferido_em": lida.get("lido_em", ""),
        "ocupado": situacao == mod_ocupacao.OCUPADO,
        "ocupacao_desconhecida": situacao == mod_ocupacao.NAO_INFORMADA,
        "situacao": mod_ocupacao.ROTULOS[situacao],
    }


# ------------------------------------------------------------------ lotes
def contar_lotes(linhas) -> list[int]:
    """Quantas unidades quase idênticas a Caixa vende juntas.

    A UF entra na chave porque bairro de nome igual em cidade de nome igual
    existe de verdade entre estados — sem ela, 11 apartamentos de 41,79 m²
    em Paulista/PE somariam com os de Paulista/PB e o aviso de lote sairia
    inflado nos dois.
    """
    chaves = [
        f"{linha['uf']}|{linha['cidade']}|{linha['bairro']}|"
        f"{linha['tipo_imovel']}|"
        f"{round(float(linha['area_m2'] or 0) / TOLERANCIA_LOTE)}"
        for _, linha in linhas.iterrows()
    ]
    contagem: dict[str, int] = {}
    for chave in chaves:
        contagem[chave] = contagem.get(chave, 0) + 1
    return [contagem[chave] for chave in chaves]


# ----------------------------------------------------------------- análise
def montar(tabela) -> tuple[list[dict], int]:
    """Transforma a tabela da Caixa na lista de imóveis com parecer."""
    lotes = contar_lotes(tabela)
    brutos = []

    for (_, linha), lote in zip(tabela.iterrows(), lotes, strict=True):
        uf = str(linha["uf"]).strip().upper()
        cidade = str(linha["cidade"])
        bairro, _ = reconhecer_bairro(uf, cidade, str(linha["bairro"]))
        area = float(linha["area_m2"] or 0)

        brutos.append({
            # .strip() não é zelo: a Caixa publica o número com um espaço
            # antes e outro depois (" 8444411406630 ") em TODAS as linhas.
            # Sem limpar, o número sai com espaço na tela, não cola na
            # busca do site da Caixa, e não casa com o número que vem na
            # URL da página do imóvel — que é como o verificador confere
            # se o imóvel ainda existe.
            "id": str(linha["id_externo"] or "").strip(),
            "uf": uf,
            "cidade": cidade,
            "bairro": bairro,
            # As três camadas de mercado. 'praca' é o rótulo; os dois
            # booleanos existem porque o parecer e a página precisam
            # distinguir "é interior" de "não temos catálogo de RM neste
            # estado" — são afirmações diferentes e o texto muda.
            "praca": praca(uf, cidade),
            "mercado_liquido": mercado_liquido(uf, cidade),
            "tem_catalogo_rm": tem_catalogo_rm(uf),
            "regiao_metropolitana": regiao_metropolitana(uf, cidade),
            "endereco": str(linha["endereco"] or ""),
            "tipo": str(linha["tipo_imovel"]),
            "area": area,
            "area_privativa": float(linha["area_privativa"] or 0),
            "area_total": float(linha["area_total"] or 0),
            "area_terreno": float(linha["area_terreno"] or 0),
            "quartos": int(linha["quartos"] or 0),
            "vagas": int(linha["vagas"] or 0),
            "preco": float(linha["preco"] or 0),
            "avaliacao": float(linha["avaliacao"] or 0),
            "modalidade": str(linha["modalidade"] or ""),
            "leilao": bool(linha["leilao"]),
            "aceita_financiamento": bool(linha["aceita_financiamento"]),
            "ocupado": bool(linha["ocupado"]),
            "ocupacao_desconhecida": bool(linha["ocupacao_desconhecida"]),
            "situacao": str(linha["situacao_informada"]),
            "reforma_declarada": bool(linha["precisa_reforma"]),
            "preco_acima_da_avaliacao": bool(linha["preco_acima_da_avaliacao"]),
            "lote": lote,
            # o "link" NÃO vai no registro: são 87 bytes de URL idêntica em
            # cada um dos 18.266 imóveis, 1,5 MB de texto para guardar uma
            # informação que é o id com um prefixo na frente. A página monta
            # o endereço a partir do id.
        })

    lidas = carregar_ocupacao()

    # FORA DO AR: a lista da Caixa é a fotografia do dia em que foi
    # gerada; entre ela e agora, imóvel é arrematado e leilão encerra.
    # Quem a própria página da Caixa negou existir sai daqui antes de
    # qualquer conta — não entra no radar.json, então nenhum filtro
    # consegue trazê-lo de volta à tela.
    #
    # Só sai quem recebeu "morto", nunca quem deu erro de rede: ver a
    # regra de três estados em analise/ocupacao.py.
    fora_do_ar = [b for b in brutos
                  if (lidas.get(b["id"]) or {}).get("existe")
                  == mod_ocupacao.MORTO]
    if fora_do_ar:
        vistos = {b["id"] for b in fora_do_ar}
        brutos = [b for b in brutos if b["id"] not in vistos]
        print(f"  {len(fora_do_ar)} fora do ar no site da Caixa, removidos")

    # depois do corte: os pares precisam refletir o que está à venda
    referencias = referencias_por_cidade(brutos)
    imoveis = []

    for bruto in brutos:
        # ANTES da conta: a ocupação muda a provisão de desocupação, que é
        # o segundo item mais caro do custo real.
        bruto.update(situacao_do_imovel(bruto, lidas))

        conta = mod_custos.calcular(
            bruto["preco"], bruto["area"], bruto["tipo"],
            reforma_declarada=bruto["reforma_declarada"],
            ocupado=bruto["ocupado"],
            ocupacao_desconhecida=bruto["ocupacao_desconhecida"],
            leilao=bruto["leilao"],
        )
        ref_m2, pares, nivel = referencia_do_imovel(bruto, referencias)
        parecer = avaliar(bruto, conta.custo_real, ref_m2, pares, nivel)

        bruto.update(conta.como_dict())
        bruto.update({
            "desconto_anunciado": (
                round(1 - bruto["preco"] / bruto["avaliacao"], 4)
                if bruto["avaliacao"] else None
            ),
            "preco_m2": (round(bruto["preco"] / bruto["area"], 2)
                         if bruto["area"] else None),
            "ref_m2": round(ref_m2, 2) if ref_m2 else None,
            "pares": pares,
            "nivel_pares": parecer.nivel_pares,
            "classe": parecer.classe,
            "nota": parecer.nota,
            "cor": parecer.cor,
            "veredito": parecer.rotulo,
            "desconto_real": parecer.desconto_real,
            "vs_pares": parecer.vs_pares,
            "ressalvas": parecer.ressalvas,
            "pagamento": ("financiável" if bruto["aceita_financiamento"]
                          else "à vista"),
        })
        imoveis.append(bruto)

    imoveis.sort(key=lambda i: (-i["nota"], i["uf"], i["cidade"], i["bairro"]))
    return imoveis, len(fora_do_ar)


def compactar_ressalvas(imoveis: list[dict]) -> list[str]:
    """Troca o texto da ressalva por um índice numa lista única.

    São cerca de 25 frases distintas repetidas em 18.266 imóveis — vários
    megabytes de texto idêntico. Guardar cada frase uma vez e referenciar
    por número é o maior corte de tamanho do projeto, e a página só precisa
    de um ``textos[n]`` para voltar ao original.

    A lista de textos é NACIONAL e vai no indice.json, não em cada arquivo
    de estado: senão as mesmas 25 frases seriam gravadas 27 vezes.
    """
    textos: list[str] = []
    indice: dict[str, int] = {}
    for imovel in imoveis:
        numeros = []
        for frase in imovel["ressalvas"]:
            if frase not in indice:
                indice[frase] = len(textos)
                textos.append(frase)
            numeros.append(indice[frase])
        imovel["ressalvas"] = numeros
    return textos


# ------------------------------------------------------------------ resumo
def med(valores: list[float]) -> float | None:
    return mediana(valores) if valores else None


def _contagens(imoveis: list[dict]) -> dict:
    """Os números que servem tanto para um estado quanto para o país."""
    return {
        "total": len(imoveis),
        "destaques": sum(1 for i in imoveis if i["nota"] >= NOTA_DESTAQUE),
        "novos": sum(1 for i in imoveis if i["novo"]),
        "vetados": sum(1 for i in imoveis if i["classe"] == "vetado"),
        "em_lote": sum(1 for i in imoveis if i["lote"] >= LOTE_RELEVANTE),
        "capital": sum(1 for i in imoveis if i["praca"] == "capital"),
        "metropolitana": sum(1 for i in imoveis
                             if i["praca"] == "metropolitana"),
        "interior": sum(1 for i in imoveis if i["praca"] == "interior"),
        "mercado_liquido": sum(1 for i in imoveis if i["mercado_liquido"]),
        "desconto_anunciado_mediano": med(
            [i["desconto_anunciado"] for i in imoveis
             if i["desconto_anunciado"] is not None]),
        "desconto_real_mediano": med(
            [i["desconto_real"] for i in imoveis
             if i["desconto_real"] is not None]),
        "preco_mediano": med([i["preco"] for i in imoveis if i["preco"]]),
        "ocupacao": {
            chave: sum(1 for i in imoveis if i["ocupacao"] == chave)
            for chave in (mod_ocupacao.OCUPADO, mod_ocupacao.DESOCUPADO,
                          mod_ocupacao.NAO_INFORMADA)
        },
        "conferidos": sum(1 for i in imoveis if i["conferido_em"]),
    }


def montar_resumo_uf(uf: str, imoveis: list[dict]) -> dict:
    """Os números de um estado, para o topo da página quando ele é o escolhido.

    Vai dentro de ``site/dados/uf/<UF>.json`` junto com os imóveis, e não no
    índice: são as cidades e os bairros daquele estado, e carregá-los todos
    de uma vez seria trazer de volta o arquivo gigante que a divisão evitou.
    """
    por_cidade: dict[str, dict] = {}
    for i in imoveis:
        c = por_cidade.setdefault(i["cidade"], {
            "cidade": i["cidade"], "praca": i["praca"],
            "rm": i["regiao_metropolitana"], "total": 0,
            "destaques": 0, "vetados": 0, "precos": [],
        })
        c["total"] += 1
        c["destaques"] += i["nota"] >= NOTA_DESTAQUE
        c["vetados"] += i["classe"] == "vetado"
        c["precos"].append(i["preco"])

    cidades = [{
        "cidade": c["cidade"], "praca": c["praca"], "rm": c["rm"],
        "total": c["total"], "destaques": c["destaques"],
        "vetados": c["vetados"], "preco_mediano": med(c["precos"]),
    } for c in por_cidade.values()]
    cidades.sort(key=lambda c: -c["total"])

    classes: dict[str, int] = {}
    tipos: dict[str, int] = {}
    for i in imoveis:
        classes[i["classe"]] = classes.get(i["classe"], 0) + 1
        tipos[i["tipo"]] = tipos.get(i["tipo"], 0) + 1

    return {
        "uf": uf,
        "nome": NOMES_UF.get(uf, uf),
        "regiao": REGIAO_DA_UF.get(uf, ""),
        # o nome, não a contagem: a contagem chega com _contagens, e as duas
        # chaves não podem se chamar igual
        "nome_capital": CAPITAIS.get(uf, ""),
        "tem_catalogo_rm": tem_catalogo_rm(uf),
        "cidades": cidades,
        "classes": classes,
        "tipos": tipos,
        **_contagens(imoveis),
    }


def montar_indice(imoveis: list[dict], resumos_uf: dict[str, dict],
                  gerado_em: datetime, data_da_lista: str,
                  fora_do_ar: int = 0) -> dict:
    """O arquivo que a página carrega primeiro.

    Tem de ser pequeno: ele decide o que aparece antes de qualquer imóvel
    chegar. Então leva só os totais do país, uma linha por estado, e os
    textos que valem para todos — premissas, avisos, roteiro de desocupação
    e a lista de ressalvas compactada.
    """
    estados = [{
        "uf": r["uf"], "nome": r["nome"], "regiao": r["regiao"],
        "total": r["total"], "destaques": r["destaques"],
        "novos": r["novos"], "vetados": r["vetados"],
        "cidades": len(r["cidades"]),
        "desconto_real_mediano": r["desconto_real_mediano"],
        "preco_mediano": r["preco_mediano"],
        "tem_catalogo_rm": r["tem_catalogo_rm"],
    } for r in resumos_uf.values()]
    estados.sort(key=lambda e: -e["total"])

    proxima = proxima_execucao(gerado_em)

    return {
        "gerado_em": gerado_em.isoformat(timespec="minutes"),
        "proxima_atualizacao": proxima.isoformat(timespec="minutes"),
        "data_da_lista": data_da_lista,
        "escopo": "BR",
        # estavam na lista da Caixa, mas a página de cada um negou
        # existir. Não aparecem em lugar nenhum do site.
        "fora_do_ar": fora_do_ar,
        "estados": estados,
        "nota_destaque": NOTA_DESTAQUE,
        "dias_novo": DIAS_NOVO,
        **_contagens(imoveis),
        "premissas": [
            {"nome": n, "valor": v, "nota": o}
            for n, v, o in mod_custos.PREMISSAS
        ],
        "avisos": [{"titulo": t, "texto": x} for t, x in AVISOS_CAIXA],
        "nomes_praca": NOMES_PRACA,
        # os moldes do parecer e os rótulos de ocupação: é com isto que a
        # página remonta o texto que não viaja em cada imóvel
        "moldes": MOLDES,
        "descricao_nivel": DESCRICAO_NIVEL,
        "rotulos_ocupacao": mod_ocupacao.ROTULOS,
        # os campos que o formato compacto deixa de fora porque a página
        # calcula; listados aqui para quem for depurar o arquivo
        "campos_derivados": list(mod_compactar.DERIVAVEIS),
        # o roteiro de desocupação vai inteiro para a página: a regra fica
        # no Python, num lugar só, e o HTML apenas desenha
        "roteiro_desocupacao": mod_ocupacao.ROTEIRO,
        "aviso_juridico": mod_ocupacao.AVISO_JURIDICO,
        # "usuario/repositorio": é com isto que a página pergunta ao
        # GitHub se há execução em andamento, para mostrar a tarja de
        # progresso. Leitura pública, sem credencial. Em execução no
        # GitHub Actions o valor vem pronto na variável de ambiente; fora
        # dele, a página descobre sozinha pelo próprio endereço. Dois
        # caminhos independentes de propósito.
        "repo": os.environ.get("GITHUB_REPOSITORY", ""),
    }


# --------------------------------------------------------------------- RSS
def montar_feed(imoveis: list[dict], resumo: dict, base: str) -> str:
    """RSS com os destaques novos. Assinar num leitor custa zero e dura."""
    novos = [i for i in imoveis
             if i["novo"] and i["nota"] >= resumo["nota_destaque"]][:40]

    itens = []
    for i in novos:
        desconto = (f"{i['desconto_real']:.0%}" if i["desconto_real"]
                    else "sem referência")
        titulo = (f"{i['tipo']} {i['area']:.0f} m² · {i['bairro']}, "
                  f"{i['cidade']}/{i['uf']} · R$ {i['preco']:,.0f} · "
                  f"{desconto} de desconto real").replace(",", ".")
        corpo = i["veredito"]
        if i["ressalvas"]:
            corpo += " RESSALVAS: " + " ".join(i["ressalvas"])
        itens.append(
            "    <item>\n"
            f"      <title>{escape(titulo)}</title>\n"
            f"      <link>{escape(PAGINA_CAIXA + i['id'])}</link>\n"
            f"      <guid isPermaLink=\"false\">{escape(i['id'])}</guid>\n"
            f"      <description>{escape(corpo)}</description>\n"
            "    </item>"
        )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        "  <channel>\n"
        "    <title>Radar de Imóveis Caixa · Brasil</title>\n"
        f"    <link>{escape(base)}</link>\n"
        "    <description>Imóveis retomados pela Caixa nos 27 estados com "
        "desconto real acima da média, já descontando reforma, provisão de "
        "desocupação e comissão de leiloeiro. Projeto independente, sem "
        "vínculo com a CAIXA.</description>\n"
        "    <language>pt-BR</language>\n"
        f"    <lastBuildDate>{resumo['gerado_em']}</lastBuildDate>\n"
        + "\n".join(itens) + "\n"
        "  </channel>\n"
        "</rss>\n"
    )


# -------------------------------------------------------------------- main
def limpar_antigos() -> None:
    """Apaga arquivos de UF que não existem mais na lista.

    Sem isto, um estado que saísse do acervo continuaria no site para sempre
    com os dados do dia em que saiu — e o seletor, que é montado a partir do
    índice, nem mostraria que ele está lá.
    """
    if not SAIDA_UF.exists():
        return
    for antigo in SAIDA_UF.glob("*.json"):
        antigo.unlink()


def main() -> None:
    origem = sys.argv[1] if len(sys.argv) > 1 else ORIGEM_PADRAO
    print(f"Lendo a lista da Caixa: {origem}")

    lista = ListaCaixa(origem)
    tabela = lista.tabela()
    print(f"  {len(tabela)} imóveis na lista, "
          f"{tabela['uf'].nunique()} estados")

    imoveis, fora_do_ar = montar(tabela)
    agora = datetime.now(FUSO)
    hoje = agora.date().isoformat()

    historico = atualizar_historico(carregar_historico(), imoveis, hoje)

    # Falhar aqui é melhor que publicar página vazia: o site continua
    # mostrando os dados bons da véspera em vez de uma tela em branco.
    if not imoveis:
        raise SystemExit("A lista veio vazia — nada será publicado.")

    # agrupa por estado ANTES de compactar as ressalvas, porque a compactação
    # troca o texto por um índice e o feed precisa do texto
    por_uf: dict[str, list[dict]] = {}
    for i in imoveis:
        por_uf.setdefault(i["uf"], []).append(i)

    resumos_uf = {uf: montar_resumo_uf(uf, lista_uf)
                  for uf, lista_uf in sorted(por_uf.items())}
    indice = montar_indice(imoveis, resumos_uf, agora,
                           lista.data_da_lista or "—", fora_do_ar)
    feed = montar_feed(imoveis, indice, "./")
    indice["textos_ressalvas"] = compactar_ressalvas(imoveis)

    print(f"  {indice['destaques']} destaques, {indice['novos']} novos, "
          f"{indice['vetados']} vetados")
    print(f"  desconto anunciado {indice['desconto_anunciado_mediano']:.1%} "
          f"-> real {indice['desconto_real_mediano']:.1%}")
    print(f"  capital {indice['capital']}, metropolitana "
          f"{indice['metropolitana']}, interior {indice['interior']}")

    SAIDA.mkdir(parents=True, exist_ok=True)
    SAIDA_UF.mkdir(parents=True, exist_ok=True)
    HISTORICO.parent.mkdir(parents=True, exist_ok=True)
    limpar_antigos()

    def escrever(caminho: Path, conteudo: str, rotulo: str) -> int:
        caminho.write_text(conteudo, encoding="utf-8")
        tamanho = caminho.stat().st_size
        print(f"  {rotulo:16} {tamanho / 1024:8.0f} KB")
        return tamanho

    escrever(SAIDA / "indice.json",
             json.dumps(indice, ensure_ascii=False, separators=(",", ":")),
             "indice.json")
    escrever(SAIDA / "feed.xml", feed, "feed.xml")

    maior = ("", 0)
    total_uf = 0
    for uf, lista_uf in sorted(por_uf.items()):
        tamanho = escrever(
            SAIDA_UF / f"{uf}.json",
            json.dumps({"resumo": resumos_uf[uf],
                        "imoveis": mod_compactar.compactar(lista_uf)},
                       ensure_ascii=False, separators=(",", ":")),
            f"uf/{uf}.json")
        total_uf += tamanho
        if tamanho > maior[1]:
            maior = (uf, tamanho)

    print(f"\n  somados: {total_uf / 1024 / 1024:.1f} MB em "
          f"{len(por_uf)} estados")
    print(f"  maior arquivo: {maior[0]} com {maior[1] / 1024 / 1024:.2f} MB "
          f"— é o que o navegador baixa de uma vez")

    HISTORICO.write_text(json.dumps(historico, ensure_ascii=False, indent=1),
                         encoding="utf-8")
    print(f"\nHistórico: {len(historico)} imóveis acompanhados")
    print("Pronto. Os arquivos do site estão em site/dados/")


if __name__ == "__main__":
    main()
