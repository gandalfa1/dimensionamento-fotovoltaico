from flask import Flask, render_template, request
from simulacao import simular

app = Flask(__name__)

# Ordem dos meses, igual a usada no simulacao.py. Os campos do modo
# avancado no index.html se chamam consumo_jan, consumo_fev, etc.
NOMES_MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
               "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def ler_consumo_mensal(formulario):
    """
    Le os 12 campos opcionais do modo avancado (historico da fatura).

    Regra: ou os doze, ou nenhum. Meio preenchido nao serve - a media
    sairia errada e o grafico mes a mes mentiria. Devolve (dicionario, erro):
    o dicionario e None quando a pessoa nao usou o modo avancado.
    """
    valores = {}
    vazios = []

    for mes in NOMES_MESES:
        bruto = (formulario.get("consumo_" + mes.lower()) or "").strip()
        if bruto == "":
            vazios.append(mes)
            continue
        try:
            valor = float(bruto.replace(",", "."))
        except ValueError:
            return None, "O consumo de " + mes + " nao parece um numero valido."
        if valor <= 0:
            return None, "O consumo de " + mes + " precisa ser maior que zero."
        valores[mes] = valor

    if len(vazios) == 12:
        return None, None          # modo media, o padrao
    if vazios:
        return None, ("Para usar o consumo mes a mes, preencha os 12 meses. "
                      "Faltou: " + ", ".join(vazios) + ". Se preferir, apague "
                      "todos e informe apenas o consumo medio.")
    return valores, None


@app.route("/")
def pagina_inicial():
    return render_template("index.html")


@app.route("/simular", methods=["POST"])
def rota_simular():
    cidade = request.form["cidade"]
    fatura = float(request.form["fatura"])
    # kWh da MESMA conta de onde veio o valor em R$. E o par que define a
    # tarifa (Equacao 6). Antes a tarifa saia de "R$ de um mes qualquer
    # dividido pela media do ano", o que produzia um erro igual ao quanto
    # aquele mes fugiu da media - e sempre na direcao otimista quando a
    # pessoa pegava uma conta de mes caro.
    consumo_da_fatura = (request.form.get("consumo_fatura") or "").strip()
    consumo_da_fatura = float(consumo_da_fatura.replace(",", ".")) if consumo_da_fatura else None
    # CORRECAO T15/T12 (15/09/2026): o campo "painel" deixou de ser lido
    # aqui. A plataforma passou a ESCOLHER o modulo, porque a verificacao
    # eletrica do T15 mostrou que essa nao e uma escolha de preferencia: os
    # modulos de celula 210 mm reprovam na verificacao de seguranca com o
    # inversor de corrente baixa em qualquer porte, e so passam a ter par
    # valido acima de cerca de 450 kWh/mes. Oferecer ao leigo uma opcao que
    # a norma reprova e oferecer escolha falsa - o mesmo defeito que o T5
    # removeu do seletor de inversor.
    # Mesma ordem de passos do T5: o back-end para de LER o campo primeiro,
    # e so depois o campo sai do index.html. Ao contrario do "inversor", o
    # "painel" era lido com colchete, entao tirar da tela antes derrubaria
    # o site com erro 400 na primeira simulacao.
    # CORRECAO T5 (14/09/2026): o campo "inversor" deixou de ser lido aqui e
    # de ser repassado ao motor. Ele era um seletor morto desde o T1: com o
    # custo vindo da curva Greener por porte, o preco por kW do inversor
    # deixou de ser usado, e escolher Economico/Intermediario/Premium
    # devolvia resultado identico. A POTENCIA do inversor continua sendo
    # calculada (kWp x FDI 0,80) e encaixada na grade comercial (T4) - o que
    # saiu foi a escolha falsa pedida ao usuario, nao o calculo.

    # Tipo de ligacao da casa (correcao T7, 14/09/2026). E o que define o
    # custo de disponibilidade: o minimo que a distribuidora fatura todo
    # mes mesmo de quem tem paineis (art. 291 da REN ANEEL 1.000/2021).
    # Usamos .get() e nao [] de proposito: o campo e OPCIONAL. Quando vier
    # vazio, ou com a opcao "nao sei", o motor aplica a premissa bifasica
    # e devolve tipo_ligacao_informado=False, para a tela declarar que
    # aquele resultado nasceu de uma premissa e nao de um dado da pessoa.
    tipo_ligacao = (request.form.get("ligacao") or "").strip()

    # Modo avancado (opcional): historico de 12 meses e mes da fatura.
    consumo_por_mes, erro_consumo = ler_consumo_mensal(request.form)
    if erro_consumo:
        return render_template("resultado.html", erro=erro_consumo, resultado=None)

    # Dois caminhos validos para o consumo, e a pessoa escolhe um:
    # (a) digitar a media mensal; (b) preencher os 12 meses do historico e
    # deixar a plataforma calcular a media. O campo da media NAO e
    # obrigatorio - exigir os dois seria pedir a mesma informacao duas vezes.
    consumo_bruto = (request.form.get("consumo") or "").strip()
    if consumo_por_mes:
        consumo = sum(consumo_por_mes.values()) / 12
    elif consumo_bruto:
        try:
            consumo = float(consumo_bruto.replace(",", "."))
        except ValueError:
            return render_template("resultado.html", resultado=None,
                                   erro="O consumo medio nao parece um numero valido.")
        if consumo <= 0:
            return render_template("resultado.html", resultado=None,
                                   erro="O consumo medio precisa ser maior que zero.")
    else:
        return render_template("resultado.html", resultado=None,
                               erro=("Falta dizer quanto voce consome. Informe o consumo "
                                     "medio mensal, ou preencha os 12 meses do historico "
                                     "da sua conta e nos calculamos a media para voce."))

    resultado = simular(
        cidade=cidade,
        consumo_medio_kwh=consumo,
        valor_fatura_reais=fatura,
        consumo_da_fatura_kwh=consumo_da_fatura,
        consumo_por_mes_kwh=consumo_por_mes,
        tipo_ligacao=tipo_ligacao,
    )

    if "erro" in resultado:
        return render_template("resultado.html", erro=resultado["erro"], resultado=None)

    return render_template(
        "resultado.html",
        resultado=resultado,
        erro=None,
        fatura_informada=fatura,
    )


if __name__ == "__main__":
    app.run(debug=True)
