"""
conferir_equacoes_3_3.py - confere o motor da plataforma contra as equacoes
escritas na secao 3.3 do artigo (Equacoes 1 a 11).

COMO FOI FEITO: as equacoes abaixo foram programadas A PARTIR DO TEXTO do
artigo, sem chamar nenhuma funcao do calculo.py. Depois o motor real
(simulacao.simular) e rodado com as mesmas entradas e os dois resultados sao
comparados numero a numero.

Tres procedimentos, os mesmos descritos no ultimo paragrafo da secao 3.3:
  1. CASOS RESOLVIDOS A MAO: os cinco casos de validacao, com os numeros
     conferidos na tela da plataforma em 23/09/2026;
  2. VARREDURA: toda a faixa de consumo, os tres tipos de ligacao (e o \"nao
     sei\"), varios estados, tarifas e perfis de sol, no modo media e no modo
     historico, conferindo as equacoes e as propriedades que valem para
     qualquer entrada;
  3. ERROS PLANTADOS: erros conhecidos sao introduzidos no motor, um de cada
     vez, e o programa confirma que os procedimentos 1 e 2 os detectam.

Roda sem internet: a geocodificacao e a NASA POWER sao substituidas por
dubles que devolvem o estado e os 12 valores de HSP informados no teste.

Uso, dentro da pasta da plataforma:
    python teste/conferir_equacoes_3_3.py
"""

import math
import os
import sys
import types

PASTA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PASTA)

# ---------------------------------------------------------------------------
# Dubles da geocodificacao e da NASA POWER (sem internet)
# ---------------------------------------------------------------------------
_ENTRADA = {"uf": None, "hsp": None}

geo = types.ModuleType("geocoding")
geo.buscar_coordenadas = lambda cidade: {
    "latitude": 0.0, "longitude": 0.0, "nome_encontrado": cidade, "uf": _ENTRADA["uf"]}
nasa = types.ModuleType("nasa_power")
nasa.buscar_hsp_mensal = lambda lat, lon: list(_ENTRADA["hsp"])
sys.modules["geocoding"] = geo
sys.modules["nasa_power"] = nasa

import calculo      # noqa: E402  (o motor real)
import simulacao    # noqa: E402

# ---------------------------------------------------------------------------
# AS EQUACOES DA SECAO 3.3, escritas a partir do texto (nao usam o calculo.py)
# ---------------------------------------------------------------------------
DIAS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
TD = 0.80                     # taxa de desempenho (Equacoes 5 e 8)
FDI = 0.80                    # fator de dimensionamento do inversor (Eq. 7)
P_MOD = 0.600                 # kWp, modulo Jinko de 600 Wp (secao 3.2)
DEGRAUS = [1.5, 2.0, 2.5, 3.0, 4.2, 5.0, 6.0, 7.0, 7.5, 8.0, 9.0, 10.0]
C_DISP = {"monofasica": 30.0, "bifasica": 50.0, "trifasica": 100.0}
P_FIO_B_2026 = 0.60           # Lei 14.300/2022, art. 27, IV
SISTEMA = [(2, 3.44), (4, 2.66), (8, 2.21), (12, 2.04), (30, 1.91)]   # R$/Wp
KIT = [(2, 1.68), (4, 1.42)]  # R$/Wp, trecho usado abaixo de 2 kWp
SERVICO_FIXO = 3520.0         # R$ = (3,44 - 1,68) x 2.000 Wp


def eq1(H):
    return sum(h * d for h, d in zip(H, DIAS)) / 365


def eq2(V_fat, C_fat):
    return V_fat / C_fat


def eq3(F_B, p, T):
    f = F_B * p
    return f, T - f


def eq4(C_meses, C_disp, T, f):
    Ccm = [min(C, max(C - C_disp, 0.0) * T / (T - f)) for C in C_meses]
    return Ccm, sum(Ccm)


def eq5(C_comp, H_ano):
    E_d = C_comp / 365
    return E_d, E_d / (H_ano * TD)


def eq6(P_t):
    N = math.ceil(P_t / P_MOD - 1e-12)
    return N, N * P_MOD


def eq7(P_inst):
    for g in DEGRAUS:
        if g >= FDI * P_inst - 1e-12:
            return g
    return None               # acima de 10 kW: nao ha degrau na grade


def eq8(P_inst, H):
    G_m = [P_inst * h * TD * d for h, d in zip(H, DIAS)]
    return G_m, sum(G_m)


def eq9(G_ano, C_comp, v):
    E_comp = min(G_ano, C_comp)
    return E_comp, E_comp * v


def _interp(x, pontos):
    (x1, y1), (x2, y2) = pontos[0], pontos[1]
    if x <= x1:
        return y1 + (y2 - y1) / (x2 - x1) * (x - x1)
    for (x1, y1), (x2, y2) in zip(pontos, pontos[1:]):
        if x1 <= x <= x2:
            return y1 + (y2 - y1) / (x2 - x1) * (x - x1)
    return pontos[-1][1]


def eq10(P_inst):
    if P_inst >= 2:
        return 1000 * _interp(P_inst, SISTEMA) * P_inst
    return 1000 * _interp(P_inst, KIT) * P_inst + SERVICO_FIXO


def eq11(I, S_ano):
    return math.inf if S_ano <= 0 else 12 * I / S_ano


# ---------------------------------------------------------------------------
# Fio B da concessionaria da capital: conferido contra a tabela da ANEEL
# ---------------------------------------------------------------------------
CAPITAL = {"AC": "EAC", "AL": "EQUATORIAL AL", "AP": "CEA", "AM": "Âmbar Amazonas",
           "BA": "COELBA", "CE": "ENEL CE", "DF": "Neoenergia Brasília", "ES": "EDP ES",
           "GO": "EQUATORIAL GO", "MA": "EQUATORIAL MA", "MT": "EMT", "MS": "EMS",
           "MG": "CEMIG-D", "PA": "EQUATORIAL PA", "PB": "EPB", "PR": "COPEL-DIS",
           "PE": "Neoenergia PE", "PI": "EQUATORIAL PI", "RJ": "LIGHT SESA",
           "RN": "COSERN", "RS": "CEEE-D", "RO": "ERO", "RR": "ÂMBAR ENERGIA RR",
           "SC": "CELESC", "SP": "ELETROPAULO", "SE": "ESE", "TO": "ETO"}


def fio_b_da_tabela_aneel():
    arq = os.path.join(PASTA, "fio_b_aneel_vigente_22-09-2026.csv")
    tab = {}
    with open(arq, encoding="utf-8-sig") as fh:
        next(fh)
        for linha in fh:
            partes = linha.rstrip("\n").split(";")
            tab[partes[0].strip()] = float(partes[2].replace(",", "."))
    # A tabela da ANEEL publica em R$/MWh; o motor guarda em R$/kWh com 6 casas.
    return {uf: round(tab[nome], 6) for uf, nome in CAPITAL.items()}


# ---------------------------------------------------------------------------
# Uma simulacao pelas equacoes do texto
# ---------------------------------------------------------------------------
def pelas_equacoes(C_meses, V_fat, C_fat, ligacao, uf, H, fio_b_uf, mediana):
    C_disp = C_DISP.get(ligacao, C_DISP["bifasica"])     # sem tipo: bifasica
    T = eq2(V_fat, C_fat)
    F_B = fio_b_uf.get(uf, mediana)
    f, v = eq3(F_B, P_FIO_B_2026, T)
    H_ano = eq1(H)
    Ccm, C_comp = eq4(C_meses, C_disp, T, f)
    r = {"T": T, "f": f, "v": v, "H_ano": H_ano, "C_comp": C_comp, "Ccm": Ccm,
         "C_disp": C_disp}
    if C_comp <= 0:
        r["guarda"] = "sem_energia_compensavel"
        return r
    E_d, P_t = eq5(C_comp, H_ano)
    N, P_inst = eq6(P_t)
    r.update(E_d=E_d, P_t=P_t, N=N, P_inst=P_inst)
    return r


def completar(r, N_final, H):
    """Equacoes 7 a 11 com o N final (que a verificacao eletrica pode ter subido)."""
    P_inst = N_final * P_MOD
    P_inv = eq7(P_inst)
    G_m, G_ano = eq8(P_inst, H)
    E_comp, S_ano = eq9(G_ano, r["C_comp"], r["v"])
    I = eq10(P_inst)
    PB = eq11(I, S_ano)
    r.update(P_inst_final=P_inst, P_inv=P_inv, G_m=G_m, G_ano=G_ano,
             E_comp=E_comp, S_ano=S_ano, I=I, PB=PB)
    return r


def perto(a, b, rel=1e-9, absol=1e-6):
    return abs(a - b) <= max(absol, rel * max(abs(a), abs(b)))


def comparar(entrada, fio_b_uf, mediana, motor=None):
    """Roda o motor e as equacoes; devolve a lista de divergencias."""
    motor = motor or simulacao.simular
    C_meses, V_fat, C_fat, ligacao, uf, H, modo = entrada
    _ENTRADA["uf"], _ENTRADA["hsp"] = uf, H
    media = sum(C_meses) / 12
    kwargs = dict(cidade="teste", consumo_medio_kwh=media, valor_fatura_reais=V_fat,
                  tipo_ligacao=ligacao, consumo_da_fatura_kwh=C_fat)
    if modo == "mensal":
        kwargs["consumo_por_mes_kwh"] = list(C_meses)
    res = motor(**kwargs)
    eq = pelas_equacoes(C_meses, V_fat, C_fat, ligacao, uf, H, fio_b_uf, mediana)
    erros = []

    def conf(nome, a, b):
        if a is None or b is None or not perto(a, b):
            erros.append(f"{nome}: motor={a} texto={b}")

    if eq.get("guarda") == "sem_energia_compensavel":
        if res.get("motivo_inviabilidade") != "sem_energia_compensavel":
            erros.append("guarda de consumo sem compensacao nao acionada")
        return erros, res, eq
    if res.get("motivo_inviabilidade") == "sem_energia_compensavel":
        erros.append("motor acionou a guarda sem energia compensavel e o texto nao")
        return erros, res, eq

    if res.get("motivo_inviabilidade") == "sem_arranjo_valido":
        # Pelo texto: acima de 10 kW nao ha degrau. O sistema pedido pela
        # energia (Eq. 6) precisa estar acima do maior degrau.
        if eq7(eq["P_inst"]) is not None:
            erros.append(f"guarda acima de 10 kW acionada com P_inst={eq['P_inst']:.2f} kWp, "
                         f"que a grade atende")
        return erros, res, eq

    N_final = res["numero_paineis"]
    if res.get("motivo_inviabilidade") != "payback_acima_da_vida_util":
        if res["modulo_modelo"] != "Jinko Tiger Neo JKM600N-72HL4-V":
            erros.append(f"modulo escolhido: {res['modulo_modelo']}")
        # Equacoes 1 a 6
        conf("T (Eq. 2)", res["tarifa_calculada"], eq["T"])
        conf("v (Eq. 3)", res["valor_economizado_por_kwh"], eq["v"])
        conf("H_ano (Eq. 1)", res["hsp_medio_anual"], eq["H_ano"])
        conf("C_comp (Eq. 4)", res["consumo_compensavel_anual_kwh"], eq["C_comp"])
        conf("P_t (Eqs. 5)", res["potencia_teorica_kwp"], eq["P_t"])
        if N_final != eq["N"] and not (res["arranjo_subiu_pelo_minimo_eletrico"]
                                       and N_final > eq["N"]):
            erros.append(f"N (Eq. 6): motor={N_final} texto={eq['N']}")
        completar(eq, N_final, H)
        conf("P_inst (Eq. 6)", res["potencia_instalada_kwp"], eq["P_inst_final"])
        conf("P_inv (Eq. 7)", res["potencia_inversor_kw"], eq["P_inv"])
        for (mes, g_motor), g_txt in zip(res["geracao_por_mes_kwh"].items(), eq["G_m"]):
            conf(f"G_{mes} (Eq. 8)", g_motor, g_txt)
        conf("G_ano (Eq. 8)", res["geracao_anual_kwh"], eq["G_ano"])
        conf("E_comp (Eq. 9)", res["energia_compensavel_anual_kwh"], eq["E_comp"])
        conf("S_ano (Eq. 9)", res["economia_anual"], eq["S_ano"])
        conf("I (Eq. 10)", res["custo_total_sistema"], eq["I"])
        conf("PB (Eq. 11)", res["payback_meses"], eq["PB"])
        # Propriedades que valem para qualquer entrada
        if res["geracao_anual_kwh"] < res["consumo_compensavel_anual_kwh"] - 1e-6:
            erros.append("PROPRIEDADE: geracao anual abaixo do consumo compensavel")
        if not perto(res["energia_compensavel_anual_kwh"], res["consumo_compensavel_anual_kwh"]):
            erros.append("PROPRIEDADE: energia compensada diferente de C_comp")
        minimo = eq["C_disp"] * eq["T"]
        for mes, fat in res["fatura_por_mes_reais"].items():
            if fat < minimo - 1e-6:
                erros.append(f"PROPRIEDADE: fatura de {mes} abaixo do minimo")
        for (mes, comp), ccm in zip(res["compensado_por_mes_kwh"].items(), eq["Ccm"]):
            if comp > ccm + 1e-6:
                erros.append(f"PROPRIEDADE: compensado de {mes} acima do C_comp,m")
        if not perto(sum(res["compensado_por_mes_kwh"].values()),
                     res["energia_compensavel_anual_kwh"], rel=1e-6, absol=0.05):
            erros.append("PROPRIEDADE: serie mensal nao fecha com a Eq. 9")
        if eq["PB"] > 300:
            erros.append("PROPRIEDADE: payback acima de 25 anos exibido")
    else:
        # Guarda dos 25 anos: o motor devolve so os numeros principais.
        if N_final != eq["N"] and N_final < eq["N"]:
            erros.append(f"N (Eq. 6) na guarda: motor={N_final} texto={eq['N']}")
        completar(eq, N_final, H)
        conf("P_inst (Eq. 6) na guarda", res["potencia_instalada_kwp"], eq["P_inst_final"])
        conf("I (Eq. 10) na guarda", res["custo_total_sistema"], eq["I"])
        conf("S_ano/12 (Eq. 9) na guarda", res["economia_mensal_media"], eq["S_ano"] / 12)
        conf("PB (Eq. 11) na guarda", res["payback_meses"], eq["PB"])
        if eq["PB"] <= 300:
            erros.append("guarda de 25 anos acionada com payback de "
                         f"{eq['PB']:.1f} meses")
    return erros, res, eq


# ---------------------------------------------------------------------------
# Os casos e a varredura
# ---------------------------------------------------------------------------
# HSP de Guaira extraidos da tela (o_que_falta_fazer, T17). Para as outras
# cidades, perfis sinteticos com a HSP media de cada uma (so o formato muda).
HSP_GUAIRA = [6.49, 5.93, 5.56, 4.60, 3.43, 3.02, 3.34, 4.17, 4.71, 5.31, 6.29, 6.47]


def perfil(media, amplitude, fase=0.0):
    base = [1 + amplitude * math.cos(2 * math.pi * (m - fase) / 12) for m in range(12)]
    k = media * 365 / sum(b * d for b, d in zip(base, DIAS))
    return [k * b for b in base]


PERFIS = {
    "BA": perfil(4236 / (2.4 * 0.8 * 365), 0.10),
    "PR": HSP_GUAIRA,
    "AM": perfil(7369 / (5.4 * 0.8 * 365), 0.05, 6),
    "SP": perfil(2702 / (1.8 * 0.8 * 365), 0.20),
    "MT": perfil(3691 / (2.4 * 0.8 * 365), 0.08, 3),
    "SC": perfil(4.3, 0.30),
    "TO": perfil(5.6, 0.12, 8),
    None: perfil(5.0, 0.15),
}

CASOS_OFICIAIS = [  # (cidade, UF, consumo, economia/mes, custo, payback em meses, modulos, inversor)
    ("Bom Jesus da Lapa", "BA", 300, 162.08, 7881.60, 48.6, 4, 2.0),
    ("Guaira", "PR", 300, 186.38, 9150.00, 49.1, 5, 2.5),
    ("Manaus", "AM", 550, 355.49, 13513.50, 38.0, 9, 5.0),
    ("Campinas", "SP", 180, 97.50, 6590.80, 67.6, 3, 1.5),
    ("Cuiaba", "MT", 300, 168.28, 7881.60, 46.8, 4, 2.0),
]


def varredura():
    ligacoes = [None, "monofasica", "bifasica", "trifasica"]
    for uf in ["BA", "PR", "AM", "SP", "MT", "SC", "TO", None]:
        for lig in ligacoes:
            for tarifa in (0.60, 0.75, 0.95):
                for consumo in range(20, 1660, 20):
                    C = [float(consumo)] * 12
                    yield (C, consumo * tarifa, consumo, lig, uf, PERFIS[uf], "media")
                    # modo historico: sazonalidade de +-35%, fatura de um mes qualquer
                    Cm = [consumo * (1 + 0.35 * math.sin(2 * math.pi * m / 12)) for m in range(12)]
                    yield (Cm, Cm[4] * tarifa, Cm[4], lig, uf, PERFIS[uf], "mensal")


def rodar(motor=None, mostrar=True):
    fio_b_uf = fio_b_da_tabela_aneel()
    mediana = sorted(fio_b_uf.values())[13]
    falhas, n, guardas = [], 0, {}
    # 0) a tabela do motor e a da ANEEL
    for uf, valor in fio_b_uf.items():
        if not perto(calculo.FIO_B_POR_UF[uf]["fio_b"], valor, rel=1e-5):
            falhas.append(f"Fio B de {uf}: motor={calculo.FIO_B_POR_UF[uf]['fio_b']} ANEEL={valor}")
    if not perto(calculo.FIO_B_PADRAO_REAIS_POR_KWH, mediana, rel=1e-5):
        falhas.append("mediana do Fio B diferente")
    # 1) casos resolvidos a mao (numeros da tela de 23/09/2026)
    for nome, uf, consumo, eco, custo, pb, n_mod, inv in CASOS_OFICIAIS:
        H = PERFIS[uf]
        eq = pelas_equacoes([float(consumo)] * 12, consumo * 0.75, consumo, "bifasica", uf,
                            H, fio_b_uf, mediana)
        completar(eq, eq["N"], H)
        for rotulo, a, b, tol in (("economia/mes", eq["S_ano"] / 12, eco, 0.005),
                                  ("custo", eq["I"], custo, 0.005),
                                  ("payback", eq["PB"], pb, 0.05)):
            if abs(a - b) > tol:
                falhas.append(f"caso {nome}, {rotulo}: equacoes={a:.2f} tela={b:.2f}")
        if eq["N"] != n_mod or eq["P_inv"] != inv:
            falhas.append(f"caso {nome}: N={eq['N']} P_inv={eq['P_inv']}")
        erros, _, _ = comparar(([float(consumo)] * 12, consumo * 0.75, consumo, "bifasica",
                                uf, H, "media"), fio_b_uf, mediana, motor)
        falhas += [f"caso {nome}: {e}" for e in erros]
    # 2) varredura
    for entrada in varredura():
        n += 1
        erros, res, _ = comparar(entrada, fio_b_uf, mediana, motor)
        chave = res.get("motivo_inviabilidade", "normal")
        guardas[chave] = guardas.get(chave, 0) + 1
        if erros:
            falhas.append(f"{entrada[3]}/{entrada[4]}/{entrada[6]}/"
                          f"{sum(entrada[0])/12:.0f} kWh: " + "; ".join(erros[:3]))
    if mostrar:
        print(f"Simulacoes da varredura: {n}")
        print(f"Resultados: {guardas}")
        print(f"Divergencias: {len(falhas)}")
        for f_ in falhas[:15]:
            print("  ", f_)
    return falhas


# ---------------------------------------------------------------------------
# 3) Erros plantados: cada um precisa ser detectado
# ---------------------------------------------------------------------------
def erros_plantados():
    orig = {n: getattr(calculo, n) for n in ("compensavel_do_mes", "hsp_medio_anual",
                                            "energia_diaria", "potencia_inversor_comercial",
                                            "custo_sistema_greener", "payback_meses",
                                            "valor_economizado_por_kwh", "geracao_estimada")}
    orig_sim = {n: getattr(simulacao, n) for n in ("hsp_medio_anual", "energia_diaria",
                                                  "valor_economizado_por_kwh",
                                                  "custo_sistema_greener", "payback_meses",
                                                  "geracao_estimada", "numero_paineis")}

    def regra_antiga(C, P=0.0, T=None, f=0.0):             # minimo descontado em energia
        return max(C - P, 0.0) if P else max(C, 0.0)

    def sem_minimo(C, P=0.0, T=None, f=0.0):
        return max(C, 0.0)

    mutacoes = {
        "regra antiga do minimo (em energia)": ("calculo", "compensavel_do_mes", regra_antiga),
        "minimo ignorado": ("calculo", "compensavel_do_mes", sem_minimo),
        "HSP pela media simples": ("simulacao", "hsp_medio_anual",
                                   lambda H: sum(H) / len(H)),
        "ano de 360 dias": ("simulacao", "energia_diaria", lambda c: c / 360),
        "Fio B sem o percentual": ("simulacao", "valor_economizado_por_kwh",
                                   lambda T, fb, p: T - fb),
        "servico fixo esquecido abaixo de 2 kWp": (
            "simulacao", "custo_sistema_greener",
            lambda P: dict(orig["custo_sistema_greener"](P),
                           custo_total=orig["custo_sistema_greener"](P)["custo_total"]
                           - (3520 if P < 2 else 0))),
        "payback em anos no lugar de meses": ("simulacao", "payback_meses",
                                              lambda I, e: I / (e * 12) if e > 0 else math.inf),
        "geracao sem a TD": ("simulacao", "geracao_estimada",
                             lambda P, h, td, d: P * h * d),
        "modulos arredondados para baixo": ("simulacao", "numero_paineis",
                                            lambda pt, wp: max(math.floor(pt / (wp / 1000)), 1)),
        "inversor arredondado para baixo": (
            "calculo", "potencia_inversor_comercial",
            lambda kw: (lambda abaixo: {"potencia_kw": abaixo, "potencia_calculada_kw": kw,
                                        "fora_da_grade": False})(
                max([g for g in calculo.GRADE_INVERSORES_KW if g <= kw] or [1.5]))
            if kw <= 10 else orig["potencia_inversor_comercial"](kw)),
    }
    detectadas = 0
    for nome, (modulo, funcao, nova) in mutacoes.items():
        alvo = calculo if modulo == "calculo" else simulacao
        antiga = getattr(alvo, funcao)
        setattr(alvo, funcao, nova)
        try:
            falhas = rodar(mostrar=False)
        except Exception as e:                                   # quebra tambem e deteccao
            falhas = [f"excecao: {e}"]
        finally:
            setattr(alvo, funcao, antiga)
        ok = len(falhas) > 0
        detectadas += ok
        print(f"  {'DETECTADO' if ok else 'NAO DETECTADO'}: {nome} ({len(falhas)} divergencias)")
    for n_, f_ in orig.items():
        setattr(calculo, n_, f_)
    for n_, f_ in orig_sim.items():
        setattr(simulacao, n_, f_)
    print(f"Erros plantados detectados: {detectadas} de {len(mutacoes)}")
    return detectadas == len(mutacoes)


if __name__ == "__main__":
    print("=== 1 e 2: casos resolvidos a mao e varredura ===")
    falhas = rodar()
    print("\n=== 3: erros plantados ===")
    todos = erros_plantados()
    print("\nRESULTADO:", "OK" if (not falhas and todos) else "HA PROBLEMAS")
