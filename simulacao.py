"""
simulacao.py - junta as pecas (calculo.py, geocoding.py e nasa_power.py)
numa unica funcao "simular", que recebe os dados que o usuario digita no
site (app.py) e devolve TODOS os resultados prontos, num unico pacote.

Os comentarios usam a numeracao de equacoes do desenvolvimento; a
correspondencia com o artigo esta no README.md. Varios comentarios
registram correcoes e numeros medidos durante o desenvolvimento (com a
data); os numeros oficiais sao os do artigo.
"""

from geocoding import buscar_coordenadas
from nasa_power import buscar_hsp_mensal
from calculo import (
    hsp_medio_anual,
    hsp_medio_anual_simples,
    energia_diaria,
    consumo_alvo_dimensionamento,
    potencia_sistema_teorica,
    numero_paineis,
    potencia_instalada,
    geracao_estimada,
    tarifa_total,
    valor_economizado_por_kwh,
    percentual_fio_b_vigente,
    ano_referencia_fio_b,
    fio_b_do_estado,
    DATA_REFERENCIA_FIO_B,
    FONTE_FIO_B,
    energia_compensavel_anual,
    piso_disponibilidade,
    # NOTA T16: "piso_anual_efetivo" saiu desta lista porque deixou de ser
    # chamada DIRETAMENTE aqui. Ela continua viva e continua sendo a unica
    # definicao do piso do ano - agora e chamada por dentro de
    # consumo_alvo_dimensionamento() e de energia_compensavel_anual(), que
    # e justamente o que garante que o dimensionamento e a economia usem o
    # mesmo numero.
    economia_anual_estimada,
    faturas_mensais_com_creditos,
    payback_meses,
    payback_dentro_da_vida_util,
    VIDA_UTIL_MODULOS_ANOS,
    # NOTA T15: "potencia_inversor" e "potencia_inversor_comercial" deixaram
    # de ser chamadas DIRETAMENTE aqui. Elas continuam sendo a unica
    # definicao do encaixe na grade comercial (T4) - agora sao chamadas por
    # dentro de dimensionar_arranjo(), porque o numero de modulos pode subir
    # pelo minimo eletrico e isso muda o degrau do inversor. Ficam no import
    # porque o bloco de teste deste arquivo ainda pode querer usa-las.
    potencia_inversor,
    potencia_inversor_comercial,
    pnom_ratio,
    FABRICANTE_REFERENCIA_INVERSOR,
    # CORRECAO T15 (15/09/2026): a verificacao eletrica do arranjo. O
    # catalogo de modulos e inversores e as quatro verificacoes moram no
    # calculo.py pelo mesmo motivo da tabela do Fio B (T3a), da tabela do
    # piso de disponibilidade (T7) e do calendario (T17): sao dados de
    # fabricante e regras de projeto, e o motor e o unico lugar do sistema
    # que precisa conhece-los. O simulacao.py apenas consulta.
    CATALOGO_MODULOS,
    CATALOGO_INVERSORES,
    dimensionar_arranjo,
    TEMP_MINIMA_PROJETO_C,
    TEMP_MAXIMA_CELULA_C,
    EXCESSO_CORRENTE_ACEITAVEL,
    custo_sistema_greener,
    REFERENCIA_PRECOS,
    # CORRECAO T17 (14/09/2026): o calendario deixou de ser definido aqui
    # e passou a ser importado do motor. Manter uma copia local era o que
    # permitia que a Equacao 2 usasse 360 dias enquanto a Equacao 5 usava
    # 365 (Achado B). Agora ha um calendario so, em um lugar so.
    DIAS_NO_MES,
    NOMES_MESES,
)

# Opcoes de painel - AGORA SO PARA REPRODUZIR CASO DE TESTE (T15/T12,
# 15/09/2026). O USUARIO NAO ESCOLHE MAIS O PAINEL.
#
# POR QUE A ESCOLHA SAIU DO FORMULARIO. A verificacao eletrica do T15
# mostrou que a escolha do painel nao era uma preferencia: era uma decisao
# tecnica que o leigo nao tem como avaliar, e em boa parte da faixa
# residencial ela nem existe. Os modulos de 550 e 670 Wp sao de celula
# 210 mm e puxam cerca de 17,5 A, contra os 13 A de entrada e 16 A de
# curto-circuito do inversor de corrente baixa - eles REPROVAM na
# verificacao de seguranca em qualquer porte, e so passam a ter par valido
# a partir de cerca de 450 kWh/mes, quando aparece inversor de corrente
# alta. Oferecer ao usuario uma opcao que a norma reprova e oferecer
# escolha falsa - o mesmo defeito que o T5 removeu do seletor de inversor.
#
# ALEM DISSO, medido no T12 (14/09/2026): escolher o painel nao muda a
# economia, so muda o desperdicio. O modelo de geracao e kWp x HSP x TD e
# e CEGO AO MODULO - dois sistemas de mesmo kWp dao o mesmo numero. O
# painel so entra pelo arredondamento para painel inteiro.
#
# ARGUMENTO QUE FECHOU A QUESTAO, e vale para o artigo: na vida real quem
# escolhe o modulo e a empresa integradora, conforme o estoque e a
# compatibilidade. Pedir essa escolha ao morador e pedir uma decisao que
# nao e dele.
#
# ESTE DICIONARIO CONTINUA EXISTINDO por um motivo so: os 5 casos de
# validacao do PVsyst precisam seguir reproduziveis. Passar opcao_painel
# na chamada forca aquele modulo, do mesmo jeito que passar
# percentual_fio_b ou piso_disponibilidade_kwh na mao reproduz os casos
# antigos. O formulario NAO envia mais este campo.
#
# ATENCAO (correcao T1, 12/09/2026): "preco_por_wp" NAO entra no custo do
# sistema desde o T1 - o custo vem da curva de preco da Greener, que
# depende do PORTE e nao da marca. Os precos ficam como memoria do modelo
# anterior, porque o artigo descreve a evolucao do motor.
PAINEIS = {
    "economico":     {"potencia_wp": 550, "preco_por_wp": 0.90,
                      "chave_catalogo": "trina_550"},
    "intermediario": {"potencia_wp": 600, "preco_por_wp": 1.20,
                      "chave_catalogo": "jinko_600"},
    "premium":       {"potencia_wp": 670, "preco_por_wp": 1.50,
                      "chave_catalogo": "trina_670"},
}

# O dicionario INVERSORES (preco por kW das tres faixas) foi REMOVIDO na
# correcao T1: com o custo vindo da curva Greener, o preco por kW do
# inversor deixou de ser usado. O parametro "opcao_inversor", que tinha
# ficado na assinatura de simular() so para nao quebrar chamadas antigas,
# foi REMOVIDO na correcao T5 (14/09/2026), junto com o seletor da tela.
# O mesmo vale para "percentual_bos": ele alimentava o modelo de custo
# antigo (equipamento + 35% de BOS) e ficou sem uso depois do T1.
# A POTENCIA do inversor continua sendo calculada normalmente (kWp x FDI)
# e encaixada na grade comercial - o que saiu foi a escolha de faixa de
# preco pedida ao usuario, que devolvia resultado identico nas tres.

# DIAS_NO_MES e NOMES_MESES vem do calculo.py desde o T17 - ver o import
# no topo do arquivo. A copia local que existia aqui foi removida.


# Como o nome do tipo de ligacao e escrito na TELA. A chave interna e sem
# acento de proposito (ela vem da tabela do motor e e comparada em codigo);
# o que o usuario le precisa ser portugues correto.
NOME_LIGACAO_NA_TELA = {
    "monofasica": "monofásica",
    "bifasica": "bifásica",
    "trifasica": "trifásica",
}


def _reais(valor):
    """Formata um numero no padrao brasileiro: 1.234,56 (ponto de milhar,
    virgula decimal). Feito com um passo intermediario porque trocar
    virgula por ponto direto na string corromperia a pontuacao do texto
    em volta - erro cometido e corrigido durante a implementacao do T18."""
    return f"{valor:,.2f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _numero(valor, casas=2):
    """Numero decimal no padrao brasileiro, sem separador de milhar."""
    return f"{valor:.{casas}f}".replace(".", ",")


def simular(cidade, consumo_medio_kwh, valor_fatura_reais,
            opcao_painel=None,
            td=0.80, fdi=0.80, fio_b=None,
            percentual_fio_b=None,
            piso_disponibilidade_kwh=None,
            tipo_ligacao=None,
            consumo_por_mes_kwh=None, consumo_da_fatura_kwh=None):
    """
    Funcao principal do protótipo: recebe os dados do usuario (o que vai
    vir do formulario do site) e devolve um dicionario com todos os
    resultados - numero de paineis, potencias, geracao mes a mes, economia
    e payback.
    """

    # 0) perfil de consumo do ano
    #
    # MODO MEDIA (padrao): a pessoa informa so o consumo medio mensal, e
    # o mesmo valor vale para os 12 meses. E o uso correto de uma media, e
    # e a decisao descrita na secao 3.3 do artigo.
    #
    # MODO MENSAL (opcional, 12/09/2026): a pessoa digita os 12 valores do
    # historico impresso na propria fatura. Nao e estimativa nem indice
    # regional - e o consumo real daquela casa. O dimensionamento continua
    # saindo do consumo do ano (mesma justificativa do HSP medio anual,
    # Equacao 1 do artigo); o que melhora e a fatura mes a mes e a tarifa.
    if consumo_por_mes_kwh:
        if not isinstance(consumo_por_mes_kwh, dict):
            consumo_por_mes_kwh = dict(zip(NOMES_MESES, consumo_por_mes_kwh))
        if len(consumo_por_mes_kwh) != 12:
            return {"erro": "Informe os 12 meses de consumo, ou deixe todos em branco "
                            "e use apenas o consumo médio."}
        modo_consumo = "mensal"
        # A media passa a ser derivada dos 12 valores, para nao existir
        # chance de o dimensionamento discordar do historico informado.
        consumo_medio_kwh = sum(consumo_por_mes_kwh.values()) / 12
    else:
        modo_consumo = "media"
        consumo_por_mes_kwh = {mes: consumo_medio_kwh for mes in NOMES_MESES}

    # 1) localizacao do usuario -> coordenadas (Passo 2)
    coordenadas = buscar_coordenadas(cidade)
    if coordenadas is None:
        return {"erro": f"Nao foi possivel encontrar a cidade '{cidade}'."}

    # 2) coordenadas -> HSP mensal real (Passo 3)
    hsp_mensal = buscar_hsp_mensal(coordenadas["latitude"], coordenadas["longitude"])
    # CORRECAO T17 (14/09/2026), Achado C: a media anual passou a ser
    # ponderada pelos dias de cada mes, o mesmo peso que a Equacao 5 ja
    # aplicava na geracao. A media simples continua sendo calculada, mas
    # NAO alimenta nada - vai so para a tela e para o artigo poderem
    # mostrar de quanto foi a diferenca.
    hsp_medio = hsp_medio_anual(hsp_mensal)
    hsp_medio_simples = hsp_medio_anual_simples(hsp_mensal)

    # 2b) custo de disponibilidade e ALVO DE DIMENSIONAMENTO
    #
    # CORRECAO T16 (14/09/2026, Achado A da auditoria): este bloco SUBIU.
    # Ate aqui ele ficava la embaixo, no passo 5, junto com a economia -
    # porque o piso de disponibilidade so era usado para calcular dinheiro.
    # Agora ele tambem define o ALVO do dimensionamento, entao precisa ser
    # conhecido ANTES do passo 3. Nenhuma linha do bloco mudou de conteudo;
    # ele apenas mudou de lugar.
    #
    # CORRECAO T7 (14/09/2026): custo de disponibilidade, art. 291 da REN
    # ANEEL 1.000/2021. Ate aquele momento o piso valia 0, ou seja, a
    # plataforma assumia que os paineis podiam zerar a conta de luz - o que
    # nao acontece: a distribuidora fatura um minimo todo mes (30 kWh na
    # monofasica, 50 na bifasica, 100 na trifasica) mesmo de quem gera a
    # propria energia. Era o erro E4 da auditoria de 11/09/2026.
    #
    # O padrao do parametro mudou de 0.0 para None, seguindo o mesmo
    # desenho do percentual do Fio B no T3a: quando ninguem informa, o
    # valor vem da tabela do motor; quem informa na mao continua mandando,
    # e e assim que os 5 casos de validacao seguem reproduziveis.
    #
    # O impacto e DESIGUAL, e essa e a razao de o item ter entrado: como o
    # piso e fixo em kWh, ele pesa pouco em consumo alto (+10% de payback
    # a 550 kWh/mes) e muito em consumo baixo (+38% a 180 kWh/mes) - ou
    # seja, o erro era maior justamente no perfil em que a decisao de
    # instalar solar e mais delicada.
    if piso_disponibilidade_kwh is None:
        ligacao = piso_disponibilidade(tipo_ligacao)
        piso_disponibilidade_kwh = ligacao["piso_kwh"]
        tipo_ligacao_usado = ligacao["tipo_ligacao"]
        tipo_ligacao_informado = ligacao["tipo_informado"]
    else:
        # Piso informado na mao (reproducao de caso de teste): nao ha tipo
        # de ligacao a declarar, do mesmo jeito que o Fio B informado na
        # mao nao tem ano de referencia.
        tipo_ligacao_usado = None
        tipo_ligacao_informado = False

    # CORRECAO T20 (23/09/2026): a tarifa (Equacao 6), o Fio B e o valor
    # economizado por kWh (Equacao 7) SUBIRAM para antes do dimensionamento.
    # Motivo: pelo art. 655-I da REN ANEEL 1.000/2021, o custo de
    # disponibilidade e um minimo EM REAIS da conta, e o Fio B cobrado sobre
    # a energia compensada conta para atingi-lo. O quanto do consumo pode ser
    # compensado - e, portanto, o alvo do dimensionamento - passa a depender
    # da tarifa e do Fio B. Nenhum dos dois depende do tamanho do sistema,
    # entao podem ser calculados antes. Nenhuma linha deste bloco mudou de
    # conteudo; ele apenas mudou de lugar (o mesmo que o T16 fez com o piso).
    # Tarifa (Equacao 6): valor em R$ dividido pelo consumo em kWh DA MESMA
    # CONTA. Os dois vem da mesma folha de papel, entao a divisao e exata,
    # independente de qual mes seja.
    #
    # Ate 12/09/2026 o divisor era o consumo MEDIO ANUAL, enquanto o valor
    # em R$ vinha de uma conta especifica. O erro na tarifa era igual ao
    # quanto aquele mes fugia da media - e ia direto para a economia e o
    # payback. Quando o consumo da conta nao e informado, mantemos o
    # comportamento antigo para nao quebrar chamadas existentes.
    #
    # Limitacao declarada: a tarifa vem de UMA conta e carrega a bandeira
    # tarifaria daquele mes. O modelo adota essa tarifa para todo o periodo
    # de payback.
    consumo_de_referencia = consumo_medio_kwh
    if consumo_da_fatura_kwh and consumo_da_fatura_kwh > 0:
        consumo_de_referencia = consumo_da_fatura_kwh

    tarifa = tarifa_total(valor_fatura_reais, consumo_de_referencia)

    # CORRECAO T3a (13/09/2026): o percentual do Fio B deixou de ser um
    # 0,60 fixo na assinatura desta funcao. Quando ninguem informa um
    # valor, ele vem da tabela da Lei 14.300/2022 pelo ano corrente
    # (calculo.py). Em 2026 o resultado e identico ao de antes - 60% -,
    # mas a partir de 01/01/2027 a plataforma se corrige sozinha.
    # Quem passar o percentual na mao continua mandando, e e assim que os
    # 5 casos de validacao seguem reproduziveis depois da virada do ano.
    if percentual_fio_b is None:
        ano_fio_b = ano_referencia_fio_b()
        percentual_fio_b = percentual_fio_b_vigente(ano_fio_b)
    else:
        ano_fio_b = None   # percentual informado na mao, sem ano de referencia

    # CORRECAO T19 (22/09/2026): o VALOR do Fio B em R$/kWh deixou de ser
    # um 0,20 fixo e sem fonte na assinatura desta funcao. Quando ninguem
    # informa, ele vem da tabela da ANEEL por estado (calculo.py), pelo
    # estado que a geocodificacao devolveu - o mesmo desenho do percentual
    # (T3a) e do piso (T7). Quem informa na mao continua mandando, e e
    # assim que os 5 casos de validacao antigos seguem reproduziveis.
    if fio_b is None:
        referencia_fio_b = fio_b_do_estado(coordenadas.get("uf"))
        fio_b = referencia_fio_b["fio_b"]
    else:
        referencia_fio_b = {"fio_b": fio_b, "uf": None, "distribuidora": None,
                            "resolucao": None, "estado_identificado": False,
                            "informado_na_chamada": True}

    economia_kwh = valor_economizado_por_kwh(tarifa, fio_b, percentual_fio_b)

    # Parcela cobrada por kWh compensado (Fio B x percentual do ano), R$/kWh.
    parcela_fio_b_por_kwh = tarifa - economia_kwh

    consumo_anual_kwh = sum(consumo_por_mes_kwh.values())

    # O piso do ANO nao e sempre 12 x o piso mensal: num mes em que o
    # consumo fica abaixo do minimo, so o consumo daquele mes deixa de ser
    # compensado. Por isso o consumo mes a mes e passado adiante - e o que
    # mantem a Equacao 8a alinhada com o grafico da fatura (Equacao 8c) e,
    # desde o T16, tambem com o dimensionamento.
    alvo = consumo_alvo_dimensionamento(consumo_anual_kwh,
                                        piso_disponibilidade_kwh,
                                        consumo_por_mes_kwh,
                                        tarifa,
                                        parcela_fio_b_por_kwh)
    piso_anual_kwh = alvo["piso_anual_kwh"]
    consumo_compensavel_anual_kwh = alvo["consumo_compensavel_anual_kwh"]
    consumo_alvo_mensal_kwh = alvo["alvo_mensal_kwh"]

    # 2c) GUARDA DE VIABILIDADE, PARTE 1 (correcao T18, Achado E)
    #
    # Quando o consumo da casa nao passa do minimo que a distribuidora
    # fatura, nao existe energia a compensar. Antes desta guarda o motor
    # seguia em frente, chegava a economia zero e estourava numa divisao
    # por zero, derrubando o site com erro 500.
    #
    # A resposta certa nao e um erro de programa nem um numero: e dizer,
    # em portugues, que naquele perfil de consumo o sistema on-grid nao
    # se paga - e POR QUE. Isso e informacao util, e e exatamente o tipo
    # de resposta que uma ferramenta comercial de geracao de leads nao
    # daria.
    #
    # Os campos extras vao junto do erro para a tela poder, no futuro,
    # montar uma pagina propria em vez de uma caixa de aviso. Enquanto
    # essa tela nao existe, o app.py so exibe a mensagem.
    if consumo_compensavel_anual_kwh <= 0:
        piso_texto = f"{piso_disponibilidade_kwh:.0f}".replace(".", ",")
        nome_ligacao = NOME_LIGACAO_NA_TELA.get(tipo_ligacao_usado, tipo_ligacao_usado)
        ligacao_texto = (f"na ligação {nome_ligacao}"
                         if tipo_ligacao_informado else
                         "na ligação bifásica, que é o que consideramos quando "
                         "o tipo não é informado")
        return {
            # TEXTO EM BLOCO CORRIDO DE PROPOSITO: o resultado.html de hoje
            # nao preserva quebra de linha na caixa de aviso. Conferido no
            # navegador. Quando a tela ganhar um lugar proprio para este
            # caso (junto do T5 passo 4 e do T15), o texto pode voltar a ter
            # paragrafos.
            "erro": (
                f"Com um consumo de {consumo_medio_kwh:.0f} kWh por mês, um sistema "
                f"solar conectado à rede não se paga, e o motivo não está na sua "
                f"conta: a distribuidora cobra um mínimo de {piso_texto} kWh todo "
                f"mês ({ligacao_texto}), mesmo de quem tem painéis. É o custo de "
                f"disponibilidade, previsto no art. 291 da Resolução ANEEL "
                f"nº 1.000/2021, e ele paga a rede que continua à sua disposição. "
                f"Como o seu consumo não passa desse mínimo, não sobra nada para os "
                f"painéis abaterem: eles gerariam energia que viraria crédito e "
                f"expiraria sem nunca virar desconto. Se o consumo da casa aumentar, "
                f"ou se você souber que a ligação é de outro tipo, vale refazer a "
                f"simulação."
            ),
            "inviavel": True,
            "motivo_inviabilidade": "sem_energia_compensavel",
            "consumo_medio_mensal_kwh": consumo_medio_kwh,
            "piso_disponibilidade_kwh": piso_disponibilidade_kwh,
            "piso_anual_kwh": piso_anual_kwh,
            "tipo_ligacao": tipo_ligacao_usado,
            "tipo_ligacao_informado": tipo_ligacao_informado,
        }

    # 3) dimensionamento do sistema (Equacoes 3 e 4)
    #
    # CORRECAO T16 (14/09/2026): o que entra na Equacao 2 deixou de ser o
    # consumo medio CHEIO e passou a ser o alvo compensavel calculado
    # acima. A plataforma dimensionava para 300 kWh/mes e informava, na
    # mesma tela, que so 250 kWh podiam ser compensados - a diferenca era
    # painel comprado com retorno garantidamente zero. O raciocinio
    # completo esta em consumo_alvo_dimensionamento(), no calculo.py.
    # CORRECAO T17: quem entra na Equacao 2 e o consumo compensavel do
    # ANO, dividido pelos 365 dias do mesmo calendario da Equacao 5.
    # Antes era o valor mensal dividido por 30, o que dimensionava para um
    # ano de 360 dias e avaliava num ano de 365.
    e_diaria = energia_diaria(consumo_compensavel_anual_kwh)
    pot_teorica = potencia_sistema_teorica(e_diaria, hsp_medio, td)

    # CORRECAO T15 (15/09/2026), Achado D da auditoria: A PLATAFORMA PASSA
    # A ESCOLHER O MODULO, E A CONFERIR SE ELE CABE NO INVERSOR.
    #
    # Ate aqui este bloco pegava o painel que o usuario tinha escolhido no
    # formulario, calculava quantos cabiam e entregava. Nunca conferia se
    # aqueles modulos podiam ser ligados naquele inversor. Era meio
    # dimensionamento: a metade energetica estava certa e a metade
    # eletrica nao existia.
    #
    # O QUE ACONTECE AGORA, e e o que um projetista faz:
    #   1. calcula quantos modulos de CADA modelo do catalogo atendem a
    #      potencia teorica;
    #   2. fecha o arranjo de cada um - numero de strings, tensao a frio,
    #      tensao a quente, e o MINIMO ELETRICO de modulos;
    #   3. roda as quatro verificacoes contra os inversores daquele degrau,
    #      nas duas familias (corrente baixa e corrente alta);
    #   4. DESCARTA os pares reprovados;
    #   5. entre os aprovados, fica com o de MENOR CORRENTE (ver abaixo).
    #
    # CRITERIO DE ESCOLHA: MENOR CORRENTE PRIMEIRO. Entre os aprovados,
    # fica o modulo de corrente mais baixa - ordem fixa, que nao muda com
    # o consumo.
    #
    # POR QUE NAO E "MENOR PAYBACK". Medido no T12 (14/09/2026): rodando
    # os tres modulos de 100 a 900 kWh/mes, o vencedor troca 12 vezes em
    # 17 pontos, e em varios deles a vantagem e menor que 1% - duas
    # semanas em quatro anos. A razao e estrutural: o modelo de geracao e
    # kWp x HSP x TD e e CEGO AO MODULO, entao dois sistemas de mesmo kWp
    # dao o mesmo numero e o modulo so entra pelo arredondamento.
    # "Escolher o melhor painel pelo payback" e escolher qual
    # arredondamento desperdica menos.
    #
    # POR QUE TAMBEM NAO E "MENOR DESPERDICIO", que foi a primeira versao
    # desta funcao e chegou a ser implementada. Ela cai na MESMA armadilha,
    # e isso foi MEDIDO em 15/09/2026: o modulo escolhido troca 72 vezes
    # ao longo das tres ligacoes, de 10 a 1.480 kWh/mes. Duas pessoas com
    # 620 e 630 kWh/mes receberiam modulos diferentes E marcas diferentes
    # de inversor. Isso nao e recomendacao tecnica, e ruido: a diferenca
    # que produz a troca e menor que o erro do proprio modelo contra o
    # PVsyst (3,98% a 6,89%, secao 4.2 do artigo). E a mesma armadilha do
    # indice sazonal da EPE
    # (T11) e da faixa de preco com fontes comerciais (T6) - pareceria
    # mais preciso sem ser mais correto.
    #
    # POR QUE A CORRENTE E O CRITERIO CERTO. Ela e a grandeza que de fato
    # LIMITA a compatibilidade, e a unica que nao melhora com sistema
    # maior (numa string em serie a corrente do arranjo e a de um modulo
    # so). Margem contra o limite do inversor e seguranca de graca. E,
    # diferente do desperdicio, a ordem por corrente e ESTAVEL: e a mesma
    # em qualquer consumo e em qualquer cidade.
    #
    # CUSTO DESTA ESCOLHA, MEDIDO E DECLARADO: adotar a ordem fixa em vez
    # do menor desperdicio encarece +0,93% no custo somado de toda a faixa
    # residencial (419 pontos), e +7,21% no pior ponto individual
    # (540 kWh/mes monofasica: R$ 12.336,00 contra R$ 11.506,00, payback
    # de 3,20 contra 2,98 anos). Em troca, a resposta da plataforma para
    # de oscilar. Como 0,93% esta bem abaixo do erro do proprio modelo,
    # otimizar por ali seria dar ao numero uma autoridade que ele nao tem.
    #
    # RESULTADO QUE VALE PARA O ARTIGO: medido nos mesmos 419 pontos, o
    # modulo de 182 mm forma arranjo valido em 100% da faixa residencial,
    # e o de 210 mm so passa a ter par valido a partir de cerca de
    # 450 kWh/mes, quando aparece inversor de corrente alta. Ou seja: em
    # sistema residencial quem decide o modulo e a COMPATIBILIDADE
    # ELETRICA, nao o preco nem o payback. Isso responde "por que este
    # modulo?" na banca sem depender de criterio adotado.
    if opcao_painel is None:
        chaves_a_testar = list(CATALOGO_MODULOS.keys())
        escolha_automatica = True
    else:
        # Caminho de REPRODUCAO DE CASO DE TESTE, nao caminho de usuario.
        # O formulario nao envia mais este campo.
        chaves_a_testar = [PAINEIS[opcao_painel]["chave_catalogo"]]
        escolha_automatica = False

    arranjos = []
    for chave_modulo in chaves_a_testar:
        modulo_candidato = CATALOGO_MODULOS[chave_modulo]
        n_candidato = numero_paineis(pot_teorica, modulo_candidato["potencia_wp"])
        arranjo_candidato = dimensionar_arranjo(n_candidato, chave_modulo, fdi)
        arranjo_candidato["desperdicio_kwp"] = (
            arranjo_candidato["potencia_instalada_kwp"] - pot_teorica)
        arranjos.append(arranjo_candidato)

    aprovados = [a for a in arranjos if a["aprovado"]]

    # 3b) GUARDA DE VIABILIDADE, PARTE 3 (correcao T15)
    #
    # Nenhum modulo do catalogo forma arranjo valido neste porte. Na faixa
    # residencial isso so acontece acima de cerca de 1.450 kWh/mes, quando
    # o sistema passa de 12 kWp e a potencia do inversor sai da grade
    # monofasica - nao existe inversor monofasico com certificacao INMETRO
    # desse tamanho, e a partir dai o mercado passa para a linha
    # TRIFASICA, que exige ligacao trifasica na casa.
    #
    # ISTO SUBSTITUI, DE FORMA MELHOR, A PENDENCIA DO T4. O aviso de "fora
    # da grade" estava reservado desde 12/09 para a tela, e ate hoje a
    # plataforma imprimia a potencia calculada crua ("inversor de
    # 12,60 kW") no mesmo formato de sempre, como se fosse um produto que
    # existe para comprar. Agora a resposta e a explicacao, e nao um
    # numero que nao da para comprar.
    if escolha_automatica and not aprovados:
        pior = arranjos[0]
        return {
            # Bloco corrido pelo mesmo motivo das guardas do T18: a caixa
            # de aviso do resultado.html nao preserva quebra de linha.
            "erro": (
                f"Com um consumo de {consumo_medio_kwh:.0f} kWh por mês, o sistema "
                f"precisaria de cerca de {_numero(pior['potencia_instalada_kwp'])} kWp, "
                f"e para esse porte não existe inversor monofásico com certificação "
                f"INMETRO. Acima de mais ou menos 10 kW os fabricantes passam para a "
                f"linha trifásica, em 380 V, que exige ligação trifásica na casa. "
                f"{'Como a sua ligação já é trifásica, o caminho existe e passa por um inversor trifásico' if tipo_ligacao_usado == 'trifasica' else 'O primeiro passo é verificar com a distribuidora se a sua ligação suporta essa potência (art. 31 da Resolução ANEEL nº 1.000/2021)'}, "
                f"e um sistema desse tamanho precisa de projeto assinado por "
                f"profissional habilitado — está fora do que esta simulação, que é "
                f"residencial, consegue dimensionar com honestidade."
            ),
            "inviavel": True,
            "motivo_inviabilidade": "sem_arranjo_valido",
            "motivo_tecnico": pior["motivo"],
            "consumo_medio_mensal_kwh": consumo_medio_kwh,
            "potencia_teorica_kwp": pot_teorica,
            "potencia_instalada_kwp": pior["potencia_instalada_kwp"],
            "numero_paineis": pior["numero_modulos"],
            "tipo_ligacao": tipo_ligacao_usado,
            "tipo_ligacao_informado": tipo_ligacao_informado,
        }

    if aprovados:
        arranjo = min(aprovados, key=lambda a: (
            CATALOGO_MODULOS[a["chave_modulo"]]["imp"],
            CATALOGO_MODULOS[a["chave_modulo"]]["formato_celula_mm"],
            CATALOGO_MODULOS[a["chave_modulo"]]["potencia_wp"],
        ))
    else:
        # Modulo FORCADO na chamada que reprovou na verificacao. Nao e
        # caminho de usuario: e reproducao de caso de teste. O resultado
        # sai mesmo assim, para o caso continuar reproduzivel, mas com
        # "arranjo_aprovado" False e o laudo junto. QUEM EXIBIR ISSO NA
        # TELA PRECISA LER ESSE CAMPO - e o Caso 5 do PVsyst (Trina de
        # 670 Wp num inversor de 2,0 kW) cai exatamente aqui.
        arranjo = arranjos[0]

    painel = CATALOGO_MODULOS[arranjo["chave_modulo"]]
    n_paineis = arranjo["numero_modulos"]
    pot_instalada = arranjo["potencia_instalada_kwp"]
    laudo_arranjo = arranjo["laudo"]

    # CORRECAO T4 (12/09/2026): a potencia calculada (kWp x FDI) e continua
    # e quase nunca existe para comprar - a plataforma chegava a indicar
    # "inversor de 2,14 kW". Agora ela e encaixada no menor degrau da grade
    # comercial que a atenda, sempre PARA CIMA ("antes sobrar do que
    # faltar"). Efeito colateral positivo: derruba o Pnom ratio e reduz o
    # clipping, aproximando a estimativa do PVsyst.
    # NOTA T15: o encaixe na grade agora acontece DENTRO de
    # dimensionar_arranjo(), porque o numero de modulos pode subir pelo
    # minimo eletrico e isso muda o degrau. A conta e a mesma do T4.
    inversor_comercial = arranjo["inversor_comercial"]
    pot_inversor_calculada = inversor_comercial["potencia_calculada_kw"]
    pot_inversor = inversor_comercial["potencia_kw"]
    razao_pnom = pnom_ratio(pot_instalada, pot_inversor)

    # 4) geracao mes a mes (Equacao 5)
    geracao_por_mes = {}
    for nome_mes, hsp_do_mes in zip(NOMES_MESES, hsp_mensal):
        dias = DIAS_NO_MES[nome_mes]
        geracao_por_mes[nome_mes] = geracao_estimada(pot_instalada, hsp_do_mes, td, dias)

    geracao_anual = sum(geracao_por_mes.values())
    geracao_media_mensal = geracao_anual / 12

    # 5) economia financeira (Equacoes 6, 7, 8a e 8b)
    #
    # CORRECAO T2 (12/09/2026): antes daqui saia
    #     economia_media_mensal = economia_mensal(geracao_media_mensal, economia_kwh)
    # ou seja, a geracao INTEIRA virava dinheiro, sem nenhum teto. Como o
    # numero de paineis e arredondado para cima, a geracao supera o consumo
    # (de +14,5% a +25,1% nos 5 casos de teste), e esse excedente estava
    # sendo contado como economia. No mundo real ele vira credito e expira
    # em 60 meses. Era o que produzia o resultado impossivel dos Casos 2 e 4:
    # economia mensal MAIOR que a fatura inteira.
    #
    # Agora a economia sai da energia COMPENSAVEL: min(geracao, consumo),
    # cortada no ANO e nunca no mes (ver comentario em energia_compensavel_anual).
    #
    # NOTA T16: "consumo_anual_kwh", o piso do ano e o alvo de
    # dimensionamento sao calculados agora no passo 2b, mais acima, porque
    # o dimensionamento passou a depender deles.
    # NOTA T20: a tarifa (Equacao 6) e o valor economizado por kWh (Equacao
    # 7) tambem subiram para o passo 2b, pelo mesmo motivo.

    energia_compensavel = energia_compensavel_anual(
        geracao_anual,
        consumo_anual_kwh,
        piso_disponibilidade_kwh,
        consumo_por_mes_kwh,
        tarifa,
        parcela_fio_b_por_kwh,
    )
    economia_anual = economia_anual_estimada(energia_compensavel, economia_kwh)
    economia_media_mensal = economia_anual / 12

    # Excedente estrutural de geracao: a parte que o sistema gera a mais do
    # que a casa consome no ano e que, por isso, NAO virou dinheiro no
    # calculo acima. Guardado para ser exibido na tela com honestidade.
    excedente_anual_kwh = max(geracao_anual - consumo_anual_kwh, 0.0)
    excedente_percentual = (
        (geracao_anual / consumo_anual_kwh - 1) * 100 if consumo_anual_kwh > 0 else 0.0
    )

    # 5b) CORRECAO T2b (12/09/2026): a fatura mes a mes passa a ser
    # calculada AQUI, no motor, e nao mais dentro do resultado.html.
    # Antes o template fazia a propria conta financeira e chegava a um
    # numero diferente do bloco de economia - a mesma pagina mostrava duas
    # economias para o mesmo sistema. Com a conta num lugar so, as duas
    # partes da tela leem o MESMO valor por construcao.
    serie_faturas = faturas_mensais_com_creditos(
        geracao_por_mes_kwh=geracao_por_mes,
        consumo_por_mes_kwh=consumo_por_mes_kwh,
        tarifa=tarifa,
        valor_economizado_kwh=economia_kwh,
        piso_disponibilidade_kwh=piso_disponibilidade_kwh,
    )
    fatura_por_mes = serie_faturas["fatura_por_mes"]
    fatura_sem_solar_por_mes = serie_faturas["fatura_sem_solar_por_mes"]
    fatura_media_com_solar = sum(fatura_por_mes.values()) / 12
    fatura_media_sem_solar = sum(fatura_sem_solar_por_mes.values()) / 12
    reducao_percentual_fatura = (
        (1 - fatura_media_com_solar / fatura_media_sem_solar) * 100
        if fatura_media_sem_solar > 0 else 0.0
    )

    # 6) custo do sistema e payback (Equacao 9)
    #
    # CORRECAO T1 (12/09/2026): antes daqui saia
    #     custo = (paineis + inversor) + 35% de BOS
    # O BOS de 35% era o maior erro do motor (E1): a Greener mede o servico
    # de instalacao entre 69% e 105% do equipamento nos portes residenciais.
    # O custo saia de 3% (5,4 kWp) a 31% (1,8 kWp) abaixo do mercado, com o
    # erro crescendo conforme o sistema encolhe.
    #
    # Agora o custo vem do preco de mercado do SISTEMA PRONTO, medido pela
    # Greener (marco/2026, precos de janeiro/2026), interpolado pelo porte.
    # O parametro percentual_bos foi removido da assinatura no T5.
    custos = custo_sistema_greener(pot_instalada)
    custo_total = custos["custo_total"]
    payback = payback_meses(custo_total, economia_media_mensal)

    # 6b) GUARDA DE VIABILIDADE, PARTE 2 (correcao T18, Achado E)
    #
    # Aqui ha energia a compensar, mas pouca. O sistema existe, tem custo
    # e tem economia - so que a economia e pequena demais para pagar o
    # investimento antes de os modulos acabarem. Antes desta guarda a
    # plataforma imprimia "128,8 anos" no mesmo formato de um payback
    # normal, sem nenhum aviso.
    #
    # DECISAO DE DESENHO A REGISTRAR: optou-se por NAO exibir a tabela de
    # resultados nesse caso, e sim a explicacao - mas com os numeros
    # dentro dela, para nao esconder nada de quem quiser conferir. O
    # criterio e a garantia de desempenho dos modulos (25 anos, Pinho e
    # Galdino, 2014), secao 3.3 do artigo.
    if not payback_dentro_da_vida_util(payback):
        anos = payback / 12
        payback_texto = (f"{anos:.0f} anos" if anos < 1000
                         else "mais de mil anos")
        return {
            # Bloco corrido pelo mesmo motivo da guarda anterior. Os numeros
            # vao DENTRO da mensagem de proposito: a plataforma nao mostra a
            # tabela nesse caso, mas tambem nao esconde nada de quem quiser
            # conferir a conta.
            "erro": (
                f"Com um consumo de {consumo_medio_kwh:.0f} kWh por mês, um sistema "
                f"solar conectado à rede não chega a se pagar. A simulação indicaria "
                f"{n_paineis} {'painel' if n_paineis == 1 else 'painéis'} "
                f"({_numero(pot_instalada)} kWp) por cerca de "
                f"R$ {_reais(custo_total)}, com economia de cerca de "
                f"R$ {_reais(economia_media_mensal)} por mês, o que levaria "
                f"{payback_texto} para voltar, mais do que os "
                f"{VIDA_UTIL_MODULOS_ANOS} anos da garantia de desempenho dos próprios "
                f"painéis. "
                + (
                    # CORRECAO (auditoria de 23/09/2026): o motivo so e o
                    # custo de disponibilidade quando ele de fato limitou a
                    # compensacao (piso_anual_kwh > 0). Antes a mensagem
                    # culpava o minimo em qualquer caso.
                    f"O motivo é o valor mínimo que a distribuidora cobra todo "
                    f"mês de qualquer conta, equivalente a {piso_disponibilidade_kwh:.0f} kWh "
                    f"(arts. 291 e 655-I da Resolução ANEEL nº 1.000/2021): em consumo "
                    f"baixo, a conta com os painéis já chega a esse mínimo e não desce "
                    f"mais, o que limita a economia possível, enquanto o custo de "
                    f"projeto, instalação e homologação quase não diminui."
                    if piso_anual_kwh > 0 else
                    f"O motivo é que cada kWh compensado economiza pouco: pela conta "
                    f"que você informou, a tarifa é de R$ {_numero(tarifa)}/kWh, e "
                    f"parte dela continua sendo cobrada sobre a energia compensada "
                    f"(o Fio B, Lei nº 14.300/2022). Confira se o valor e o consumo "
                    f"informados são da mesma conta de luz."
                )
            ),
            "inviavel": True,
            "motivo_inviabilidade": "payback_acima_da_vida_util",
            "consumo_medio_mensal_kwh": consumo_medio_kwh,
            "numero_paineis": n_paineis,
            "potencia_instalada_kwp": pot_instalada,
            "custo_total_sistema": custo_total,
            "economia_mensal_media": economia_media_mensal,
            "payback_meses": payback,
            "piso_disponibilidade_kwh": piso_disponibilidade_kwh,
            "tipo_ligacao": tipo_ligacao_usado,
            "tipo_ligacao_informado": tipo_ligacao_informado,
        }

    return {
        "cidade_encontrada": coordenadas["nome_encontrado"],
        # hsp_medio_anual passa a ser a media PONDERADA pelos dias do mes
        # (correcao T17). A media simples, que era o valor ate 14/09/2026,
        # vai junto para a tela e o artigo poderem comparar as duas.
        "hsp_medio_anual": hsp_medio,
        "hsp_medio_anual_simples": hsp_medio_simples,
        "hsp_por_mes": dict(zip(NOMES_MESES, hsp_mensal)),
        "numero_paineis": n_paineis,
        "potencia_instalada_kwp": pot_instalada,
        # potencia_inversor_kw passa a ser a COMERCIAL (correcao T4) - e a
        # que a tela mostra e a que deve ser replicada no PVsyst.
        "potencia_inversor_kw": pot_inversor,
        "potencia_inversor_calculada_kw": pot_inversor_calculada,
        "inversor_fora_da_grade": inversor_comercial["fora_da_grade"],
        "fabricante_referencia_inversor": FABRICANTE_REFERENCIA_INVERSOR,
        "pnom_ratio": razao_pnom,
        # --- campos novos da correcao T15 (verificacao eletrica) --------
        # O MODULO. A plataforma passou a escolher, entao ela precisa
        # DIZER qual escolheu e de onde veio o dado - um numero de
        # datasheet sem a folha citada nao se defende em banca.
        "modulo_modelo": painel["nome"],
        "modulo_fabricante": painel["fabricante"],
        "modulo_potencia_wp": painel["potencia_wp"],
        "modulo_formato_celula_mm": painel["formato_celula_mm"],
        "modulo_fonte_datasheet": painel["fonte"],
        "modulo_escolhido_pela_plataforma": escolha_automatica,
        # Modelos que a plataforma testou e DESCARTOU, com o motivo. Existe
        # para a tela poder responder "por que este modulo e nao aquele" -
        # que e a diferenca entre uma ferramenta que decide e uma que
        # manda obedecer.
        "modulos_descartados": [
            {
                "modelo": CATALOGO_MODULOS[a["chave_modulo"]]["nome"],
                "potencia_wp": CATALOGO_MODULOS[a["chave_modulo"]]["potencia_wp"],
                "formato_celula_mm": CATALOGO_MODULOS[a["chave_modulo"]]["formato_celula_mm"],
                "motivo": a["motivo"],
            }
            for a in arranjos if not a["aprovado"]
        ],
        # O INVERSOR, agora com modelo e nao so potencia.
        "inversor_modelo": arranjo["inversor"],
        "inversor_familia": (CATALOGO_INVERSORES[arranjo["inversor"]]["familia"]
                             if arranjo["inversor"] else None),
        "inversor_classe_corrente": (
            CATALOGO_INVERSORES[arranjo["inversor"]]["classe_corrente"]
            if arranjo["inversor"] else None),
        # O ARRANJO. E isto que faltava: a plataforma dizia "5 paineis" e
        # nao dizia COMO eles se ligam.
        "arranjo_aprovado": arranjo["aprovado"],
        "arranjo_strings": laudo_arranjo["strings"] if laudo_arranjo else None,
        "arranjo_modulos_por_string": (laudo_arranjo["modulos_por_string"]
                                       if laudo_arranjo else None),
        "arranjo_tensao_maxima_a_frio_v": (laudo_arranjo["tensao_maxima_a_frio_v"]
                                           if laudo_arranjo else None),
        "arranjo_tensao_mpp_a_quente_v": (laudo_arranjo["tensao_mpp_a_quente_v"]
                                          if laudo_arranjo else None),
        "arranjo_excesso_corrente": (laudo_arranjo["excesso_corrente"]
                                     if laudo_arranjo else None),
        "arranjo_laudo": laudo_arranjo,
        "arranjo_motivo_reprovacao": arranjo["motivo"],
        # MINIMO ELETRICO: True quando o arranjo teve de crescer porque um
        # modulo so nao alcanca o piso da janela de MPPT do inversor. A
        # tela PRECISA declarar isso, porque nesses casos o sistema ficou
        # maior do que o consumo justifica - e esconder isso repetiria o
        # erro que o T16 corrigiu.
        "arranjo_subiu_pelo_minimo_eletrico": arranjo["subiu_pelo_minimo_eletrico"],
        "numero_paineis_por_energia": arranjo["numero_modulos_por_energia"],
        "potencia_teorica_kwp": pot_teorica,
        "desperdicio_kwp": arranjo["desperdicio_kwp"],
        # Premissas declaradas da verificacao, para a tela e o artigo nao
        # precisarem repetir numero na mao.
        "temperatura_minima_projeto_c": TEMP_MINIMA_PROJETO_C,
        "temperatura_maxima_celula_c": TEMP_MAXIMA_CELULA_C,
        "excesso_corrente_aceitavel": EXCESSO_CORRENTE_ACEITAVEL,
        "geracao_por_mes_kwh": geracao_por_mes,
        "geracao_anual_kwh": geracao_anual,
        # --- novos campos da correcao T2 (nenhum campo antigo foi removido) ---
        "consumo_anual_kwh": consumo_anual_kwh,
        "energia_compensavel_anual_kwh": energia_compensavel,
        "excedente_anual_kwh": excedente_anual_kwh,
        "excedente_percentual": excedente_percentual,
        "valor_economizado_por_kwh": economia_kwh,
        # --- novos campos da correcao T3a (Fio B pelo ano corrente) ---
        # ano_referencia_fio_b vem None quando o percentual foi informado
        # na chamada; a tela so deve exibir o ano quando ele existir.
        "percentual_fio_b": percentual_fio_b,
        "valor_fio_b_por_kwh": fio_b,
        # --- novos campos da correcao T19 (Fio B por estado) ---
        # fio_b_estado_identificado False significa que a tela PRECISA
        # declarar que foi usada a mediana nacional, e nao o valor do
        # estado da pessoa.
        "fio_b_uf": referencia_fio_b["uf"],
        "fio_b_distribuidora_referencia": referencia_fio_b["distribuidora"],
        "fio_b_resolucao": referencia_fio_b["resolucao"],
        "fio_b_estado_identificado": referencia_fio_b["estado_identificado"],
        "fio_b_informado_na_chamada": referencia_fio_b.get("informado_na_chamada", False),
        "fio_b_data_referencia": DATA_REFERENCIA_FIO_B,
        "fio_b_fonte": FONTE_FIO_B,
        "ano_referencia_fio_b": ano_fio_b,
        # --- novos campos da correcao T7 (custo de disponibilidade) ---
        # tipo_ligacao vem None quando o piso foi informado na mao.
        # tipo_ligacao_informado False significa que a tela PRECISA
        # declarar que a bifasica foi uma premissa, e nao um dado.
        "tipo_ligacao": tipo_ligacao_usado,
        "tipo_ligacao_informado": tipo_ligacao_informado,
        "piso_disponibilidade_kwh": piso_disponibilidade_kwh,
        "piso_anual_kwh": piso_anual_kwh,
        # --- novos campos da correcao T16 (alvo do dimensionamento) ---
        # CUIDADO PARA NAO CONFUNDIR COM "energia_compensavel_anual_kwh",
        # que esta mais acima e e OUTRA grandeza:
        #   consumo_compensavel_anual_kwh = teto de DEMANDA
        #       (consumo do ano - piso do ano). Nao depende do sistema.
        #       E o alvo do dimensionamento.
        #   energia_compensavel_anual_kwh = o que de fato sera abatido
        #       (o menor entre a geracao e o teto acima). Depende do
        #       sistema que foi dimensionado.
        # Quando o sistema esta bem dimensionado os dois numeros coincidem
        # ou ficam muito proximos. Ficam para a tela e para o artigo
        # poderem mostrar POR QUE o sistema tem o tamanho que tem.
        "consumo_compensavel_anual_kwh": consumo_compensavel_anual_kwh,
        "consumo_alvo_dimensionamento_kwh": consumo_alvo_mensal_kwh,
        # --- novos campos da correcao T2b (grafico da fatura mes a mes) ---
        "fatura_informada": valor_fatura_reais,
        "modo_consumo": modo_consumo,
        "consumo_da_fatura_kwh": consumo_de_referencia,
        "consumo_medio_mensal_kwh": consumo_medio_kwh,
        "consumo_por_mes_kwh": consumo_por_mes_kwh,
        "fatura_por_mes_reais": fatura_por_mes,
        "fatura_sem_solar_por_mes_reais": fatura_sem_solar_por_mes,
        "fatura_media_sem_solar": fatura_media_sem_solar,
        "compensado_por_mes_kwh": serie_faturas["compensado_por_mes"],
        "saldo_creditos_por_mes_kwh": serie_faturas["saldo_creditos_por_mes"],
        "fatura_media_com_solar": fatura_media_com_solar,
        "reducao_percentual_fatura": reducao_percentual_fatura,
        # ---------------------------------------------------------------
        "tarifa_calculada": tarifa,
        "economia_mensal_media": economia_media_mensal,
        "economia_anual": economia_anual,
        # --- campos de custo da correcao T1 ---
        # custo_paineis e custo_inversor DEIXARAM DE EXISTIR: o custo nao e
        # mais montado peca por peca. No lugar deles vem a decomposicao que
        # a propria Greener publica - equipamento (kit) e servico de
        # integracao -, que somam exatamente o custo total.
        "custo_equipamentos": custos["custo_equipamentos"],
        "custo_servico_instalacao": custos["custo_servico_instalacao"],
        "custo_total_sistema": custo_total,
        "custo_por_wp": custos["preco_por_wp"],
        # True quando o sistema e menor que 2 kWp, porte que a pesquisa da
        # Greener nao mede. A tela usa isso para avisar o usuario.
        "custo_fora_da_faixa_medida": custos["fora_da_faixa_medida"],
        "referencia_precos": REFERENCIA_PRECOS,
        "payback_meses": payback,
    }


# =======================================================================
# TESTE - roda a simulacao completa, do jeito que o usuario vai usar
# =======================================================================
if __name__ == "__main__":
    # CORRECAO T15 (15/09/2026): "opcao_painel" saiu desta chamada. A
    # plataforma escolhe o modulo sozinha, e o teste precisa exercitar o
    # caminho que o usuario de fato percorre. Para reproduzir um caso de
    # validacao com modulo forcado, basta passar opcao_painel de volta.
    resultado = simular(
        cidade="Guaira, PR, Brasil",
        consumo_medio_kwh=350,
        valor_fatura_reais=262.50,
    )

    if "erro" in resultado:
        print(resultado["erro"])
    else:
        print(f"Cidade encontrada:        {resultado['cidade_encontrada']}")
        print(f"HSP medio anual:          {resultado['hsp_medio_anual']:.2f}")
        # --- bloco novo da correcao T15 -------------------------------
        print(f"Modulo escolhido:         {resultado['modulo_modelo']} "
              f"({resultado['modulo_potencia_wp']} Wp, celula "
              f"{resultado['modulo_formato_celula_mm']} mm)")
        print(f"  escolhido pela plataforma: {resultado['modulo_escolhido_pela_plataforma']}"
              f" | fonte: {resultado['modulo_fonte_datasheet']}")
        for descartado in resultado["modulos_descartados"]:
            print(f"  descartado: {descartado['modelo']} -> {descartado['motivo']}")
        print(f"Inversor escolhido:       {resultado['inversor_modelo']} "
              f"({resultado['inversor_familia']}, corrente "
              f"{resultado['inversor_classe_corrente']})")
        print(f"Arranjo:                  "
              f"{'+'.join(str(x) for x in resultado['arranjo_modulos_por_string'])} "
              f"modulos ({resultado['arranjo_strings']} string(s))")
        print(f"  tensao maxima a frio:   {resultado['arranjo_tensao_maxima_a_frio_v']:.1f} V "
              f"(limite {CATALOGO_INVERSORES[resultado['inversor_modelo']]['tensao_max_v']:.0f} V)")
        print(f"  Vmp a quente:           {resultado['arranjo_tensao_mpp_a_quente_v']:.1f} V "
              f"(piso do MPPT {CATALOGO_INVERSORES[resultado['inversor_modelo']]['mppt_min_v']:.0f} V)")
        print(f"  excesso de corrente:    {resultado['arranjo_excesso_corrente']*100:.2f}% "
              f"(limiar {resultado['excesso_corrente_aceitavel']*100:.0f}%)")
        print(f"  verificacao aprovada:   {resultado['arranjo_aprovado']}")
        if resultado["arranjo_subiu_pelo_minimo_eletrico"]:
            print(f"  ATENCAO: o arranjo subiu de "
                  f"{resultado['numero_paineis_por_energia']} para "
                  f"{resultado['numero_paineis']} modulos pelo MINIMO ELETRICO")
        # --------------------------------------------------------------
        print(f"Numero de paineis:        {resultado['numero_paineis']}")
        print(f"Potencia instalada:       {resultado['potencia_instalada_kwp']:.2f} kWp")
        print(f"Potencia do inversor:     {resultado['potencia_inversor_kw']:.2f} kW "
              f"(calculado {resultado['potencia_inversor_calculada_kw']:.2f} kW, "
              f"Pnom ratio {resultado['pnom_ratio']:.2f})")
        print(f"Geracao anual:            {resultado['geracao_anual_kwh']:.0f} kWh")
        print(f"Consumo anual:            {resultado['consumo_anual_kwh']:.0f} kWh")
        print(f"Excedente de geracao:     {resultado['excedente_anual_kwh']:.0f} kWh "
              f"({resultado['excedente_percentual']:.1f}%)")
        print(f"Energia compensavel (T2): {resultado['energia_compensavel_anual_kwh']:.0f} kWh")
        print(f"Tarifa calculada:         R$ {resultado['tarifa_calculada']:.2f}/kWh")
        print(f"Equipamentos (kit):       R$ {resultado['custo_equipamentos']:.2f}")
        print(f"Instalacao e servicos:    R$ {resultado['custo_servico_instalacao']:.2f}")
        print(f"Custo total do sistema:   R$ {resultado['custo_total_sistema']:.2f} "
              f"(R$ {resultado['custo_por_wp']:.2f}/Wp)")
        print(f"Economia mensal media:    R$ {resultado['economia_mensal_media']:.2f}")
        print(f"Economia anual:           R$ {resultado['economia_anual']:.2f}")
        print(f"Payback:                  {resultado['payback_meses']:.1f} meses")
