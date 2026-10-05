# Guia de instalação, do zero

Este guia supõe que você nunca usou GitHub. Cada passo diz **onde clicar** e
**o que você vai ver na tela**. Se alguma tela estiver diferente do descrito,
pare e confira a seção **Quando der errado**, no fim.

Tempo total: cerca de 25 minutos. Custo: zero.

---

## Índice

1. [Antes de começar](#1-antes-de-começar)
2. [O que já vem pronto](#2-o-que-já-vem-pronto)
3. [Criar a conta e o repositório no GitHub](#3-criar-a-conta-e-o-repositório-no-github)
4. [Enviar os arquivos](#4-enviar-os-arquivos)
5. [O endereço do repositório](#5-o-endereço-do-repositório-não-precisa-fazer-nada)
6. [Ligar o GitHub Pages](#6-ligar-o-github-pages)
7. [Rodar a primeira pesquisa](#7-rodar-a-primeira-pesquisa)
8. [Conferir se funcionou](#8-conferir-se-funcionou)
9. [Opcional: ligar a Vercel também](#9-opcional-ligar-a-vercel-também)
10. [O dia a dia](#10-o-dia-a-dia)
11. [Quando der errado](#11-quando-der-errado)

---

## 1. Antes de começar

Você precisa de:

- Um computador com navegador (Chrome, Edge, Firefox — qualquer um).
- Um e-mail.
- A pasta `radar-imoveis-br` que veio junto com este guia.

Você **não** precisa instalar Python, Git, nem programa nenhum. Tudo roda
nos servidores do GitHub, de graça.

### O que vai acontecer, em uma frase

Você sobe os arquivos para o GitHub. Três vezes por dia o GitHub acorda
sozinho, baixa a lista de imóveis da Caixa dos 27 estados, calcula o
desconto real de cada um e republica o seu site. Você acessa de qualquer
celular.

São **18.266 imóveis em 1.068 cidades**. O site mostra **um estado por
vez** — o seletor "Estado" é o primeiro filtro, e ele abre em Pernambuco
na primeira visita e depois sempre no último estado que você escolheu.
Isso não é limitação de tela: num arquivo só, os 18 mil imóveis dariam 24
MB de JSON e nenhum celular abriria a página.

---

## 2. O que já vem pronto

O layout já está escolhido e posto no lugar certo: `site/index.html`. Você
não precisa renomear nada.

A página tem duas abas:

| Aba | O que faz |
|---|---|
| **Lista** | todos os imóveis com o parecer, filtros na lateral, 20 por vez |
| **Comparar** | até três imóveis lado a lado, linha por linha |

Em cada imóvel da lista há três botões: **Detalhes**, **+ comparar** e
**Página da Caixa**, que abre o anúncio oficial onde ficam as fotos, o
edital, a matrícula e a situação de ocupação.

**Detalhes** abre uma gaveta lateral com tudo: área privativa, área total,
área do terreno, a conta completa de custo, a comparação com os pares da
lista, as ressalvas e o bloco de **ocupação e desocupação** — que diz se o
imóvel está ocupado e, quando está, explica passo a passo como se desocupa,
quanto costuma custar e quanto costuma demorar.

O site se adapta sozinho ao aparelho: no computador os filtros ficam numa
coluna à esquerda; no tablet e no celular eles viram uma gaveta que abre
pelo botão **Filtros**, com um contador de quantos estão ligados. Os botões
crescem quando o aparelho é tocado com o dedo em vez do mouse.

> **Para ver antes de subir:** o arquivo de `site/` só funciona depois de
> publicado, porque ele busca os dados de um arquivo separado. Se quiser
> olhar antes, `python scripts/gerar_previa.py` gera uma cópia com os
> dados embutidos, que abre com dois cliques.

---

## 3. Criar a conta e o repositório no GitHub

### 3.1 Criar a conta (pule se já tem)

1. Abra <https://github.com/signup>
2. Digite seu e-mail → **Continue**
3. Crie uma senha → **Continue**
4. Escolha um nome de usuário (ex.: `jleoandrade`) → **Continue**

   > **Anote esse nome de usuário.** Você vai precisar dele no passo 5.

5. Responda se quer receber novidades (pode escrever `n`) → **Continue**
6. Resolva o quebra-cabeça de verificação → **Create account**
7. Abra seu e-mail, copie o código de 8 dígitos e cole na tela do GitHub.

### 3.2 Criar o repositório

Um "repositório" é só uma pasta na nuvem.

1. Abra <https://github.com/new>
2. Preencha assim:

   | Campo | O que colocar |
   |---|---|
   | **Repository name** | `radar-imoveis-br` |
   | **Description** | Radar de imóveis da Caixa no Brasil |
   | **Public / Private** | **Public** — é obrigatório, o GitHub Pages de graça só funciona em repositório público |
   | Add a README file | **deixe desmarcado** |
   | Add .gitignore | **None** |
   | Choose a license | **None** |

3. Clique no botão verde **Create repository**, embaixo.

Você cai numa tela escrita **"Quick setup — if you've done this kind of
thing before"**, com vários comandos. Ignore os comandos. Procure a frase,
no meio da tela:

> *uploading an existing file*

Ela está num link azul. **Não clique ainda** — o próximo passo explica.

---

## 4. Enviar os arquivos

> **Atenção ao ponto que mais confunde:** o GitHub precisa receber as
> **pastas**, não só os arquivos soltos. Se você arrastar só os arquivos,
> o site não funciona.

1. Na tela do repositório, clique no link **uploading an existing file**.
   (Se já saiu dessa tela: clique em **Add file** no alto à direita →
   **Upload files**.)

2. Abra o Explorador de Arquivos (Windows) ou o Finder (Mac) na pasta
   `radar-imoveis-br`.

3. Selecione **tudo o que está dentro** dela — `Ctrl+A` no Windows,
   `Cmd+A` no Mac. Devem ficar selecionados:

   ```
   .github/     analise/     scripts/     site/
   dados/       docs/        GUIA.md      README.md
   vercel.json  .gitignore
   ```

   > **Não selecione a pasta `previa/`** — ela é só para você olhar os
   > layouts no computador e não precisa ir para o site. Se já tiver
   > subido, não causa problema nenhum.

4. **Arraste tudo** para a área tracejada do navegador que diz
   *"Drag files here to add them to your repository"*.

5. Aguarde. Aparece uma lista com os nomes dos arquivos e uma barra de
   progresso. São uns 30 arquivos — leva de 10 segundos a 1 minuto.

6. Role a página até o fim. No campo **"Commit changes"**, escreva:

   ```
   primeira versão do radar
   ```

7. Deixe marcado **"Commit directly to the main branch"**.

8. Clique no botão verde **Commit changes**.

A tela recarrega e agora mostra a lista de pastas. **Confira que aparecem
`analise`, `scripts`, `site`** — se aparecerem só arquivos soltos, as
pastas não subiram: apague tudo e repita arrastando as pastas.

---

## 5. O endereço do repositório (não precisa fazer nada)

Esta etapa existia antes e **foi eliminada**. O site agora descobre
sozinho o endereço do seu repositório, de duas formas independentes:

- pelo próprio endereço da página, quando servido pelo GitHub Pages
  (`jleoandrade.github.io/radar-imoveis-br` já diz tudo);
- pelo que o robô grava no `indice.json` a cada execução.

Se um dia nenhuma das duas funcionar, o site mostra um aviso explicando o
que preencher. Siga para o passo 6.

---

## 6. Ligar o GitHub Pages

É aqui que o site ganha endereço.

1. No alto da página do repositório, clique em **Settings** (ícone de
   engrenagem, na faixa de abas junto com Code, Issues, Pull requests).
2. Na coluna da esquerda, role até **Pages** e clique.
3. Em **"Build and deployment"**, no campo **Source**, está escrito
   *"Deploy from a branch"*. Clique nele e escolha **GitHub Actions**.

   > Esse é o passo que mais gente esquece. Se ficar em "Deploy from a
   > branch", o site nunca aparece.

4. Não precisa salvar — o GitHub salva sozinho.

---

## 7. Rodar a primeira pesquisa

1. Volte para a aba **Actions**, no alto da página do repositório.
2. Se aparecer um aviso grande dizendo *"Workflows aren't being run on this
   forked repository"* ou um botão verde **"I understand my workflows, go
   ahead and enable them"**, clique nele.
3. Na coluna da esquerda, clique em **Atualizar radar**.
4. À direita aparece a faixa: *"This workflow has a workflow_dispatch event
   trigger."* e, no fim dela, um botão cinza **Run workflow**.
5. Clique em **Run workflow**. Abre uma caixinha com o campo "Use workflow
   from: Branch: main". Clique no botão verde **Run workflow** dentro dela.
6. Espere uns 5 segundos e **atualize a página** (F5). Aparece uma linha
   nova com uma bolinha amarela girando.
7. Clique nessa linha para acompanhar. Leva de 1 a 3 minutos.

Quando terminar, a bolinha vira:

- **✅ verde** — deu certo, vá para o passo 8.
- **❌ vermelho** — veja a seção **Quando der errado**.

---

## 8. Conferir se funcionou

### 8.1 Ver o resumo da execução

Ainda na tela da execução, role até o fim. Tem um quadro **"Radar
atualizado"** mostrando mais ou menos isto:

```
- 18266 imóveis em 27 estados
- 193 destaques, 1060 novos
- 42 vetados (preço acima da avaliação)
- Desconto anunciado 44.6% → real 27.6%
- Lista da Caixa de 30/09/2026
```

> **Por que "1060 novos" na primeira vez?** Porque o sistema nunca tinha
> visto nenhum imóvel antes, então todos são novidade. A partir da segunda
> execução esse número fica pequeno — são os que entraram de verdade.

### 8.2 Abrir o site

O endereço é:

```
https://SEU-USUARIO.github.io/radar-imoveis-br/
```

Trocando `SEU-USUARIO` pelo seu. Também aparece em **Settings → Pages**,
num quadro escrito *"Your site is live at..."*.

> A primeira publicação pode levar até 10 minutos para o endereço começar a
> funcionar. Se der "404", espere 5 minutos e tente de novo.

**O que você deve ver:** o número de imóveis no topo, a data da lista da
Caixa, e os imóveis listados. Se aparecer "Não foi possível carregar a
lista", veja a seção de erros.

### 8.3 Salvar no celular

Abra o endereço no celular e adicione à tela de início:

- **Android (Chrome):** menu ⋮ → *Adicionar à tela inicial*
- **iPhone (Safari):** botão de compartilhar → *Adicionar à Tela de Início*

---

## 9. Opcional: ligar a Vercel também

O site já está no ar pelo GitHub Pages. Este passo coloca **o mesmo site
também na Vercel**, com outro endereço. Não substitui nada: os dois passam a
funcionar lado a lado, atualizados pelo mesmo robô.

Não precisa mexer em arquivo nenhum. O workflow já publica nos dois.

1. Abra <https://vercel.com/new>
2. Clique em **Continue with GitHub** e autorize.
3. Na lista de repositórios, ache **radar-imoveis-br** e clique em **Import**.
4. Não mexa em nada nas opções — o arquivo `vercel.json` já configura tudo.
   Clique em **Deploy**.
5. Espere 1 minuto. A Vercel mostra o endereço, algo como
   `radar-imoveis-br.vercel.app`.

Daí em diante, toda vez que o robô atualizar os dados, os dois republicam:
o GitHub Pages recebe o site empacotado, e a Vercel enxerga o commit dos
dados.

### Se a Vercel falhar dizendo "No python entrypoint found"

A Vercel olhou os arquivos `.py` de `analise/` e `scripts/`, concluiu que
isto é uma aplicação Python e foi procurar um `app.py` para servir. Ela
decide o tipo do projeto antes de ler o `outputDirectory`.

O conserto é tirar o Python do campo de visão dela:

1. No projeto da Vercel: **Settings** → **General**.
2. Em **Root Directory**, clique em **Edit** e escreva: `site`
3. Em **Framework Preset**, escolha **Other**.
4. Deixe Build Command e Install Command vazios, com os interruptores de
   *Override* desligados.
5. **Save**, e depois **Deployments** → nos três pontinhos do último →
   **Redeploy**.

A partir daí a Vercel só enxerga a pasta `site/`, que tem só HTML e JSON.
A configuração de cabeçalhos mora em `site/vercel.json`, que é lido a
partir do Root Directory.

### Por que o repositório cresce um pouco

Para a Vercel enxergar a atualização, o robô precisa gravar os dados dentro
do repositório. São cerca de 1,2 MB por dia, e o Git guarda o histórico.
Como o arquivo muda pouco de um dia para o outro, o crescimento real fica
bem abaixo disso. O GitHub recomenda repositório abaixo de 1 GB — você tem
anos de folga.

> **Atenção aos termos de uso.** O plano gratuito da Vercel (Hobby) e o
> GitHub Pages são para uso pessoal, não comercial. Se o site virar canal
> de captação de clientes, leia os termos dos dois antes de continuar.

---

## 10. O dia a dia

### O site atualiza sozinho

O robô roda **três vezes por dia**, nos horários de Brasília:

| | |
|---|---|
| Manhã | 06:10 |
| Tarde | 13:40 |
| Noite | 20:25 |

Você não faz nada. O site mostra, no alto, a data da última atualização e
a hora da próxima.

São três e não um porque execução agendada em repositório gratuito entra
numa fila de baixa prioridade do GitHub e costuma atrasar — aqui já chegou
a rodar cinco horas depois do programado. Com três tentativas, basta uma
pegar fila curta para os dados do dia entrarem.

Quando a lista da Caixa não mudou, a execução termina em 40 segundos sem
publicar nada. Não há desperdício em rodar três vezes.

### Como funcionam os favoritos

A estrela ao lado de cada imóvel guarda o imóvel na sua lista. O filtro
**Favoritos**, na lateral, mostra só eles; o card **Favoritos**, no topo,
diz quantos são.

**Eles ficam no seu navegador, neste aparelho.** Não vão para o GitHub nem
para servidor nenhum. Três consequências práticas:

- o que você marcar no computador não aparece no celular;
- limpar os dados de navegação apaga a lista;
- em janela anônima, os favoritos somem ao fechar a janela.

Guardar isso de verdade exigiria conta, senha e banco de dados — e o
projeto inteiro funciona sem servidor justamente por isso ser gratuito e
não quebrar sozinho.

### Os números do topo

Eles contam **o que está filtrado**, não o estado inteiro. Filtrando por
um bairro, o card de Destaques diz quantos destaques existem ali, e o
total geral fica ao lado em letra miúda.

Quatro deles são clicáveis e ligam o filtro que representam: Destaques,
Novos, Favoritos e Vetados. O de Vetados conta os que estão **escondidos**
pelo filtro padrão — clicar nele mostra os 42.

### Quando quiser atualizar na hora

1. Abra `https://github.com/SEU-USUARIO/radar-imoveis-br/actions`
2. Na coluna da esquerda, clique em **Atualizar radar**.
3. À direita, botão **Run workflow** → de novo **Run workflow**.
4. Em uns 25 minutos termina (são 600 páginas da Caixa sendo visitadas,
   uma a cada 1,2 segundo, mais a análise de 18 mil imóveis duas vezes).

Se você voltar para o site enquanto roda, uma tarja azul aparece no topo
mostrando o andamento, e **os dados trocam sozinhos quando terminar** —
sem recarregar a página e sem perder os filtros que você montou. Isso
funciona porque perguntar ao GitHub como vai a execução é leitura
pública, que não precisa de senha.

> **Por que não existe um botão de pesquisar no site?** Porque para o
> site MANDAR o robô rodar ele precisaria guardar uma credencial sua
> dentro da página, e qualquer visitante leria essa credencial no
> código-fonte — teria acesso de escrita ao seu repositório. O próprio
> GitHub varre repositórios públicos atrás de senhas vazadas e revogaria
> a credencial em poucas horas. Disparar pelo GitHub é o caminho certo.

### Receber as novidades sem abrir o site

O site gera um RSS em `dados/feed.xml` com os imóveis novos que passaram na
régua. Instale um leitor de RSS no celular (Feedly, Inoreader) e assine:

```
https://SEU-USUARIO.github.io/radar-imoveis-br/dados/feed.xml
```

### Ajustar as premissas da conta

As estimativas de reforma, desocupação e taxas ficam em
`analise/custos.py`, no alto do arquivo, cada uma com um comentário
explicando de onde veio. Edite pelo lápis do GitHub, dê **Commit changes**,
e rode a pesquisa de novo.

---

## 11. Quando der errado

### "404 — There isn't a GitHub Pages site here"

O Pages não foi ligado ou a publicação ainda não terminou.

1. Confira **Settings → Pages → Source = GitHub Actions**.
2. Veja na aba **Actions** se a última execução está verde.
3. Espere 10 minutos depois da primeira execução verde.

### O site abre mas diz "Não foi possível carregar a lista"

O arquivo de dados não foi publicado.

1. Vá em **Actions** e confira se a última execução terminou em verde.
2. Se estiver vermelha, clique nela e leia o passo em vermelho.
3. Se estiver verde, confira em **Code → site → dados** se existe o arquivo
   `indice.json` e os arquivos de `uf/`.

### A execução falhou no passo "Conferir se o resultado faz sentido"

Isso é o sistema funcionando. Significa que a lista da Caixa veio
estranha — vazia, incompleta, ou com as colunas trocadas. A mensagem diz
qual foi o problema.

**O site continua no ar com os dados do dia anterior**, que é o certo.
Tente de novo no dia seguinte; se repetir, a Caixa mudou o formato do
arquivo e o leitor precisa de ajuste.

### A execução falhou no passo "Baixar a lista da Caixa"

O site da Caixa estava fora do ar ou recusou a conexão. Espere algumas
horas e rode de novo pelo botão **Run workflow**.

### A execução falhou no passo "Guardar o histórico"

Falta permissão de escrita.

1. **Settings → Actions → General**
2. Role até **Workflow permissions**
3. Marque **Read and write permissions**
4. **Save**
5. Rode de novo.

### A tarja diz "O GitHub limitou as consultas por hora"

O site pergunta ao GitHub como vai a execução sem usar senha nenhuma, e
sem senha o GitHub permite 60 perguntas por hora. Se você ficou abrindo e
fechando a página muitas vezes, bateu no limite. Não quebra nada: a
execução continua e o site volta ao normal na hora seguinte.

### De onde vêm as datas "No acervo há ≥ N dias"

O arquivo `dados/semente_historico.json` traz 743 datas importadas de um
radar público de outra pessoa
(`github.com/heitoribeiro/radar-imoveis-caixa-ba`), que já observava o
acervo nacional em setembro de 2026.

**Essas datas não dizem quando o imóvel apareceu na Caixa.** Dizem que
aquele radar já o enxergava naquele dia — ou seja, o imóvel existia *pelo
menos* desde então. Por isso a tela mostra `≥ 12 dias`, com o sinal de
"pelo menos", e a legenda diz "data importada de outro radar". Datas
observadas por este projeto aparecem sem o sinal.

A regra de uso é de piso: a semente só **recua** uma data, nunca avança.
Se um dia este projeto observar o imóvel antes do que a semente diz, a
data observada vence e a marcação de "importada" cai.

O arquivo pode ser apagado a qualquer momento — o histórico já absorveu as
datas na primeira execução. Ele fica no repositório como comprovante de
onde os números vieram.

### O número de imóveis caiu de um dia para o outro

Duas causas possíveis, e as duas são certas:

- a Caixa tirou imóveis da lista (ela regenera o arquivo todo dia);
- o verificador achou imóveis que a página da Caixa diz não existir mais,
  e os removeu. O resumo da execução mostra a linha *"N estavam na lista
  mas já saíram do site da Caixa"*, e o topo do site mostra o mesmo número.

Nenhum deles some do `historico.json`. Se o imóvel voltar — leilão não
arrematado volta para o acervo —, ele reaparece com a data de primeira
aparição original, e não conta como novo de novo.

### A data da lista é a mesma de ontem

A Caixa regenera o arquivo de madrugada, mas não é garantido todo dia —
feriado ou falha do lado deles e o arquivo continua o mesmo. Não é defeito
do radar: ele baixou, conferiu e viu que nada mudou. O topo do site mostra
a data da lista justamente para você perceber isso.

### Um imóvel aparece no radar de outra pessoa e não no meu

Confira, nesta ordem:

1. **Você está no estado certo?** O site mostra um estado por vez — confira
   o seletor "Estado", no alto dos filtros.
2. **Está na aba com "Sem vetados" ligado?** Esse filtro vem ligado e
   esconde os imóveis com preço acima da avaliação da Caixa. Desmarque.
3. **A página do imóvel ainda abre?** Cole o link no navegador. Se disser
   *"Nenhum imóvel encontrado para o filtro selecionado"*, o imóvel saiu
   do ar e quem está desatualizado é o outro radar, não o seu.
4. **A sua lista é de quando?** O topo do site diz. Imóvel cujo edital foi
   publicado depois dessa data só entra na próxima atualização.

### Nenhum imóvel mostra "Ocupado" ou "Desocupado"

Nos primeiros dias é esperado: o robô lê 600 páginas por execução, então
o acervo inteiro leva uns quatro dias. O resumo da execução mostra a
porcentagem já apurada.

Se depois de alguns dias continuar tudo em "Ocupação não informada", o
resumo da execução traz um aviso amarelo dizendo que a página da Caixa
provavelmente mudou de formato. O site segue funcionando — a provisão de
desocupação continua entrando na conta por precaução, que é como era
antes desta funcionalidade existir.

### Mudei um arquivo e o site não mudou

Toda alteração em `site/` dispara uma nova publicação automaticamente, mas
leva 1 a 2 minutos. Confira a aba **Actions**. Se não apareceu execução
nova, dê um F5 forte no navegador (`Ctrl+Shift+R`).

### As pastas não subiram, só arquivos soltos

Apague tudo e repita o passo 4 arrastando as **pastas**, não o conteúdo
delas. Para apagar: cada arquivo → lixeira → Commit. Ou, mais rápido,
apague o repositório inteiro em **Settings → Danger Zone → Delete this
repository** e comece o passo 3.2 de novo.

---

## Onde fica cada coisa

```
radar-imoveis-br/
├── site/                      o que vira o site
│   ├── index.html             a página (o layout que você escolheu)
│   └── dados/                 gerado pelo robô, não edite à mão
│       ├── indice.json        o país e as 27 UFs (carrega primeiro)
│       ├── uf/PE.json         os imóveis de cada estado, compactados
│       └── feed.xml           o RSS
├── analise/                   o cérebro
│   ├── caixa.py               lê o arquivo da Caixa
│   ├── custos.py              ITBI, cartório, reforma, desocupação  ← edite aqui
│   ├── ocupacao.py            lê a situação na página e o roteiro de desocupação
│   ├── geografia.py           capitais, regiões metropolitanas, bairros
│   ├── compactar.py           encolhe o arquivo de cada estado
│   ├── tipos.py               normaliza a tipologia do imóvel
│   └── parecer.py             desconto real, nota e ressalvas
├── scripts/
│   ├── gerar_dados.py         junta tudo e escreve o site
│   ├── ocupacao.py            visita as páginas da Caixa, 600 por execução
│   ├── conferir.py            impede publicar lista quebrada
│   └── gerar_previa.py        gera uma prévia para olhar no computador
├── dados/
│   ├── historico.json         quando cada imóvel apareceu  ← não apague
│   ├── ocupacao.json          o que foi lido em cada página  ← não apague
│   ├── regioes_metropolitanas.json  quais cidades formam cada RM
│   └── semente_historico.json datas importadas de outro radar (comprovante)
└── .github/workflows/         o robô que roda todo dia
```

---

## Corrigir uma região metropolitana

O arquivo `dados/regioes_metropolitanas.json` diz quais cidades formam a
região metropolitana de cada estado. **Só a do Recife foi conferida na
lei**; as outras 20 foram montadas com as cidades centrais reconhecidas de
cada região, e cada uma traz `"conferido": false` mais a lei a consultar.

Se você souber que uma cidade entrou ou saiu de uma região metropolitana:

1. Abra o arquivo no GitHub e clique no lápis.
2. Ache o estado (`"PE"`, `"RJ"`…) e a lista `"municipios"`.
3. Acrescente ou tire o nome, **entre aspas e com vírgula**, escrito como
   aparece na lista da Caixa. Acento não importa: a comparação ignora.
4. Se conferiu na lei, troque `"conferido": false` por `true`.
5. **Commit changes**. O robô usa o arquivo novo na próxima execução.

Se errar e o JSON ficar inválido, nada explode: o catálogo volta a ficar
vazio e todo mundo cai em "capital ou interior" até você corrigir.

---

**Projeto independente, sem vínculo oficial com a CAIXA.** Confirme
disponibilidade, condições, edital, ocupação e débitos nos canais oficiais
antes de qualquer decisão. Nada aqui é recomendação de investimento.
