# Radar Imóveis Brasil

Site estático que lê a lista oficial de imóveis retomados da **Caixa
Econômica Federal** nos 27 estados, calcula **quanto de desconto realmente
sobra** depois de todo o custo, e se atualiza sozinho três vezes por dia.

São **18.266 imóveis em 1.084 municípios** na lista de 30/09/2026.

Para instalar ou reconstruir sem saber nada de programação, leia o
**[GUIA.md](GUIA.md)**.

---

## O problema

Todo radar de imóveis da Caixa mostra o **desconto anunciado**: preço
dividido pela avaliação do banco. Esse número ignora tudo que você ainda
vai gastar depois de comprar.

Aqui o **desconto real** compara a avaliação com o custo que você de fato
desembolsa para ter o imóvel pronto:

```
custo real    = preço + reforma + provisão de desocupação + comissão
desconto real = 1 − (custo real ÷ avaliação da Caixa)
```

Na lista nacional de 30/09/2026:

| | |
|---|---|
| Desconto anunciado, mediana | **42,6%** |
| Desconto real, mediana | **26,4%** |

Dezesseis pontos percentuais. É a diferença entre uma planilha bonita e
uma conta que fecha.

---

## O acervo não está onde se imagina

Três números que mudam a leitura do mercado, todos medidos no arquivo:

**O Rio de Janeiro é um terço do país.** São 5.995 imóveis de 18.266 —
mais que Goiás, São Paulo e Pernambuco somados. Só São Gonçalo tem 1.360,
mais que o estado inteiro de Pernambuco.

**O estoque de Goiás é a periferia de Brasília, não Goiânia.** Goiânia tem
75 imóveis. Luziânia, Cidade Ocidental, Santo Antônio do Descoberto, Águas
Lindas e Valparaíso somam 2.233 — todos no Entorno do DF.

**A capital é minoria em quase todo estado.** No Recife são 19 de 1.060
(2%); o estoque de Pernambuco está em Jaboatão, Paulista, Igarassu e São
Lourenço da Mata. Por isso o radar não classifica por "capital ou
interior": classifica em **capital, região metropolitana e interior**, e
81% do acervo nacional está nas duas primeiras.

| | Imóveis | |
|---|---|---|
| Capital | 4.770 | 26% |
| Região metropolitana | 10.143 | 56% |
| Interior | 3.353 | 18% |

---

## O que ele faz que os outros não fazem

**Veta imóvel pedido acima da avaliação da própria Caixa.** São 1.607 dos
18.266, quase todos Leilão SFI — ali o preço mínimo é o saldo da dívida do
antigo mutuário, não uma avaliação de venda. Saem com nota zero.

**Confere, uma a uma, se o imóvel ainda existe.** A lista é a fotografia
do dia em que foi gerada; entre ela e agora, imóvel é arrematado e leilão
encerra. A mesma visita que lê a ocupação confere se a página ainda
responde. Quem a Caixa negar existir sai do site — mas continua no
histórico, para voltar com a data original se o leilão não arrematar.

**Só remove com negação explícita.** A regra é de três estados: vivo,
morto e indefinido. Erro de rede, lentidão ou página estranha devolvem
indefinido e não tiram ninguém. Apagar um imóvel bom por causa de um
soluço de rede seria pior do que mostrar um que acabou de sair.

**Trata a ocupação como o que ela é: desconhecida.** O arquivo que a Caixa
publica não informa ocupação — conferido, zero menções nos 18.266
registros. A página de cada imóvel às vezes informa, e o robô vai lá ver.
Mas a palavra sequer aparece na imensa maioria das páginas. Por isso a
conta reserva provisão de desocupação em todo imóvel não confirmado como
vazio: tratar "não sei" como "vazio" é assumir o melhor cenário no item
mais caro, e é o que faz toda lista de leilão parecer barata no papel.

**Explica como se desocupa.** Quando o imóvel está ocupado, os detalhes
trazem o roteiro: acordo antes de processo, o que muda conforme a retomada
tenha sido por alienação fiduciária (art. 30 da Lei 9.514/97 — reintegração
concedida liminarmente, 60 dias) ou por execução hipotecária (imissão na
posse, sem liminar automática), prazos e o que costuma travar.

**Marca lotes de unidades idênticas.** Onze apartamentos de 41,79 m² no
mesmo bairro são um empreendimento retomado em bloco, não onze
oportunidades: quem compra um concorre com os outros dez na revenda.

**Compara com os pares, e diz com quais.** R$/m² contra a mediana da mesma
cidade e tipologia. Quando não há pares suficientes, a referência desce
uma escada — cidade, estado, Brasil — e **o peso na nota cai junto**,
porque comparar com a mediana nacional é evidência fraca. O parecer diz
qual nível foi usado.

**Não confunde cidades de nome igual.** São 1.084 municípios na lista, mas
só 1.068 nomes distintos: dezesseis nomes existem em mais de um estado,
cobrindo 535 imóveis. Contar por nome já erra o total de municípios em 16 — Santa Rita é MA e PB (205
imóveis), São Gonçalo do Amarante é CE e RN (99), e **Paulista é PB e PE**
— uma é interior, a outra está na Região Metropolitana do Recife. Toda
chave de geografia e de comparação carrega a UF por isso.

**Não publica lista quebrada.** Se a coleta falhar, a execução para antes
de publicar e o site continua mostrando os dados bons da véspera, em vez
de uma página vazia. A trava confere os 27 arquivos, não só o total: um
estado inteiro faltando derrubaria o total em 3% e passaria despercebido.

---

## Como roda

```
GitHub Actions, três vezes por dia (06:10, 13:40 e 20:25 de Brasília)
  ├── baixa     venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_geral.csv
  ├── analisa   lê, calcula custos, dá o parecer de cada imóvel
  ├── confere   600 páginas da Caixa: o imóvel existe? está ocupado?
  ├── analisa   de novo, agora com o que descobriu nas páginas
  ├── trava     scripts/conferir.py para tudo se o resultado não fizer sentido
  ├── grava     o histórico de volta no repositório
  └── publica   envia site/ empacotado para o GitHub Pages
```

**É um download, não 27.** A Caixa publica um arquivo por estado e também
um arquivo com tudo. Conferido: o nacional é byte a byte a soma dos 27.

Sem token, sem senha, sem servidor.

**A fila de conferência é por mérito, não por ordem.** Com 18.266 imóveis,
reconferir todos a cada 7 dias exigiria 2.609 páginas por dia e só cabem
1.800. Então: primeiro os marcados como fora do ar (todo dia, porque é
isso que permite um imóvel voltar), depois os destaques nunca lidos,
depois os destaques com leitura vencida, e só então o resto. Destaque é
reconferido a cada 7 dias; o resto a cada 30. Em regime são cerca de 1.005
páginas por dia. O que você olha fica conferido em dois ou três dias.

**São três horários porque execução agendada em repositório gratuito
atrasa.** O GitHub avisa na documentação que ela entra numa fila de baixa
prioridade e pode ser adiada ou descartada; medido aqui, um disparo
programado para 06:10 rodou às 11:17 num dia e às 11:45 no outro. Com três
tentativas, basta uma pegar fila curta.

Para rodar na hora: **Actions → Atualizar radar → Run workflow**. Se você
voltar ao site enquanto roda, uma tarja mostra o andamento e os dados
trocam sozinhos ao terminar, sem recarregar a página e sem perder os
filtros.

> Não há botão de disparo no site, de propósito: disparar exigiria uma
> credencial de escrita guardada dentro da página, que qualquer visitante
> leria no código-fonte.

---

## A página

`site/index.html` é a página inteira, num arquivo só, sem biblioteca
externa nenhuma. Duas abas:

- **Lista** — todos os imóveis com o parecer, filtros, 20 por vez
- **Comparar** — até três imóveis lado a lado, linha por linha

**Um estado por vez.** O seletor de estado é o primeiro filtro e é o
único que baixa outro arquivo. Num arquivo único os 18.266 imóveis dariam
24 MB de JSON, e o Rio de Janeiro sozinho pesaria 8 MB — nenhum celular
abre isso. Dividido por estado e compactado, o Rio tem 1,8 MB (406 KB na
transferência) e carrega em cerca de um segundo. Estado já visitado fica
em memória: voltar a ele é instantâneo.

A página abre no último estado que você escolheu; na primeira visita, em
Pernambuco.

**Os sete números do topo contam o conjunto filtrado**, não o estado
inteiro: filtrando por um bairro, o card de Destaques diz quantos
destaques existem ali, com o total do estado em letra miúda ao lado.
Quatro deles também ligam e desligam o filtro que representam. O card de
Vetados conta os que estão **escondidos** pelo filtro padrão, senão
mostraria zero para sempre.

**Filtro de bairro** que segue a cidade: são 4.926 bairros no país
contando cidade por cidade, e a lista só mostra os da cidade escolhida.

**Favoritos** com a estrela em cada imóvel. Ficam no `localStorage` do
navegador de quem marcou — são seus, deste aparelho. Marcar no computador
não aparece no celular, e limpar os dados do navegador apaga. Guardar no
servidor exigiria conta, login e banco de dados; isto é um site estático
de propósito.

Cada linha traz **Detalhes**, **+ comparar** e **Página da Caixa**. A
ordenação tem os dois sentidos de cada critério.

Ela se adapta ao aparelho: no computador os filtros ficam numa coluna; no
tablet e no celular viram gaveta, com um contador de quantos estão ligados.
Os alvos de toque crescem quando a tela é tocada com o dedo
(`pointer: coarse`) em vez do mouse.

---

## Estrutura

| Pasta | O que tem |
|---|---|
| `site/` | a página e os dados publicados |
| `site/dados/indice.json` | o resumo do país e as 27 UFs (24 KB) |
| `site/dados/uf/` | um arquivo por estado, compactado |
| `analise/` | o núcleo: leitor da Caixa, custos, geografia, ocupação, parecer, compactação |
| `scripts/` | gerador dos dados, conferência e prévias |
| `dados/` | histórico, leituras das páginas, datas importadas, catálogo de RM |
| `.github/workflows/` | a automação diária |

O `site/vercel.json` só interessa se você publicar também na Vercel. Ele
fica **dentro** de `site/`, e não na raiz, de propósito: com o Root
Directory do projeto apontado para `site`, a Vercel não enxerga os
arquivos `.py` do repositório e para de tentar construir isto como se
fosse uma aplicação Python.

Dois arquivos de `dados/` **não dão para reconstruir**: `historico.json`
guarda quando cada imóvel apareceu e o último preço visto; `ocupacao.json`
guarda o que foi lido em cada página da Caixa. A lista da Caixa é uma
fotografia do dia — se esses dois sumirem, todo imóvel volta a contar como
novidade e o robô tem de revisitar o acervo inteiro.

### Por que os arquivos de estado são compactados

Medido no arquivo do Rio de Janeiro, antes: 7,47 MB para 5.995 imóveis.
Desses, **4,00 MB (54%) eram os nomes dos 56 campos repetidos em cada
registro** — `"desconto_anunciado":` escrito 5.995 vezes.

O formato grava os nomes dos campos uma vez, cada imóvel vira uma lista de
valores na mesma ordem, e texto que repete muito (cidade, modalidade,
situação) guarda um índice para um dicionário. Mais sete campos que a
página calcula sozinha e o texto do parecer, que é a mesma frase com três
números trocados. Resultado: **7,87 MB → 1,80 MB**.

O gzip do GitHub Pages já derrubaria a transferência para 580 KB, mas o
gzip resolve a rede, não o que vem depois: o navegador ainda teria de
interpretar 8 MB de JSON e montar 6 mil objetos. Detalhes em
`analise/compactar.py`.

---

## As premissas, e onde mudá-las

Tudo em `analise/custos.py`, no alto do arquivo, cada constante com um
comentário dizendo de onde veio.

| Premissa | Valor |
|---|---|
| ITBI | 3% do preço |
| Escritura e registro | 1,8% + R$ 800 |
| Comissão do leiloeiro | 5%, só em leilão e licitação |
| Reforma declarada | R$ 1.200/m², até 30% do preço |
| Acerto mínimo | R$ 450/m², até 12% do preço |
| Provisão de desocupação | 8% do preço, mínimo R$ 15.000 |

Os **tetos percentuais da reforma** existem por um motivo: calcular reforma
só por m² quebra em imóvel barato. Uma casa de 58 m² a R$ 1.000/m² custa
R$ 58 mil, e R$ 450/m² de acerto daria R$ 26 mil — 45% do valor do imóvel.
Ninguém gasta isso num banho de loja. Sem o teto, o modelo condena
sistematicamente o imóvel barato e o interior, que é justamente onde os
descontos aparecem — e a conclusão sobre investir no interior se inverte
conforme esse teto exista ou não.

**O ITBI é a premissa mais frágil do modelo nacional.** É imposto
municipal, fixado por cada uma das prefeituras, e a lista cobre 1.084
municípios. Levantar 1.084 leis está fora do que este projeto faz com
fonte aberta, então entra 3% para todos, que é o teto da faixa usual
(2% a 3%). Onde a alíquota real é menor, o desconto real sai
**subestimado** — erro deliberado, para o lado seguro.

---

## O catálogo de regiões metropolitanas

Fica em `dados/regioes_metropolitanas.json`, cobre 21 estados e 619
municípios, e **só a Região Metropolitana do Recife foi conferida na lei**.
As demais foram montadas com os municípios centrais reconhecidos de cada
região e trazem `"conferido": false` mais a lei a consultar.

Região metropolitana é criada por lei estadual e a composição muda. Se um
município estiver de fora, ele cai em "interior", perde 0,05 de nota e
recebe a ressalva de mercado raso — nada quebra. Estado sem entrada no
catálogo funciona igual, só sem a camada do meio, e **a página avisa**:
"neste estado o projeto ainda não tem lista de região metropolitana
conferida". Dizer "é interior" quando não se sabe seria afirmar o que não
se apurou.

Para corrigir ou acrescentar um estado: edite o arquivo, escreva o nome do
município como aparece na lista da Caixa e rode `gerar_dados.py`.

---

## Rodar no seu computador

Opcional — o site funciona sem isto.

```bash
pip install -r scripts/requirements.txt

python scripts/gerar_dados.py                 # Brasil inteiro
python scripts/gerar_dados.py PE              # só um estado
python scripts/gerar_dados.py Lista_geral.csv # ou usa um CSV já baixado
python scripts/ocupacao.py --limite 50        # confere algumas páginas
python scripts/ocupacao.py --uf PE            # ou só as de um estado
python scripts/conferir.py                    # valida o resultado
python scripts/gerar_previa.py PE GO          # prévia offline, sem servidor

python -m http.server 8000 --directory site   # e abra localhost:8000
```

---

## Limites

- A referência de valor é a **avaliação da Caixa**, que é número interno do
  banco e não preço praticado. Avaliação de mercado de verdade exige
  transação registrada (ITBI), e isso ainda não está aqui.
- A comparação com pares usa o próprio acervo retomado, não o mercado.
- O **ITBI é único para o país** (3%), quando na verdade é municipal.
- O **catálogo de regiões metropolitanas é parcial e, fora de PE, não foi
  conferido na lei**. Veja a seção acima.
- O **catálogo de bairros existe só para o Recife** (93 bairros, para
  reconhecer `VARZEA` como `Várzea`). Nos outros 1.083 municípios o bairro
  fica como a Caixa escreveu, em caixa alta e sem acento.
- A ocupação é lida da página por leitura automática de texto. O site
  mostra o trecho original justamente porque pode errar, e o roteiro de
  desocupação é orientação geral, não consultoria jurídica.
- Débitos de condomínio e IPTU, estado real do imóvel e locação averbada
  na matrícula não estão em lugar nenhum do que este projeto lê. Nenhuma
  coluna aqui substitui ler o edital e a matrícula.
- A lista é regenerada pela Caixa **todo dia, de madrugada**, e o arquivo
  carrega a data do dia anterior. Observado: durante todo o dia 01/10 o
  download ainda servia o arquivo de 30/09; na manhã de 02/10 já era o de
  01/10. Por isso a execução das 06:10 sempre pega o mais novo disponível.

---

## Fonte

Lista pública da Caixa Econômica Federal:
<https://venda-imoveis.caixa.gov.br/sistema/download-lista.asp>

**Projeto independente, sem vínculo oficial com a CAIXA.** O parecer, a
nota e os cálculos de custo são deste projeto, não da Caixa. Confirme
disponibilidade, condições, edital, matrícula, ocupação e débitos nos
canais oficiais antes de qualquer decisão. Nada aqui é recomendação de
investimento.

Código sob licença MIT — veja [LICENSE](LICENSE).
