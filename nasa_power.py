"""
nasa_power.py - Passo 3 do prototipo
Busca os 12 valores medios mensais de HSP (Horas de Sol Pleno) para uma
coordenada geografica, usando a API publica e gratuita NASA POWER.
Nao precisa de chave nem cadastro - so precisa de internet. Usamos o
"endpoint de climatologia", que devolve a MEDIA historica de varios anos
para cada mes - exatamente o que precisamos (nao precisamos escolher um
ano especifico).
Para rodar:
    py nasa_power.py        (Windows)
    python3 nasa_power.py   (Mac/Linux)
"""
import requests
# Ordem dos meses como a NASA POWER devolve (em ingles, 3 letras)
MESES_NASA = [
    "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
    "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
]
NOMES_MESES_PT = [
    "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
    "Jul", "Ago", "Set", "Out", "Nov", "Dez",
]
def buscar_hsp_mensal(latitude, longitude):
    """
    Recebe latitude e longitude e devolve uma lista com 12 numeros de HSP
    (kWh/m2/dia - numericamente igual as Horas de Sol Pleno), um para cada
    mes do ano, na ordem: Janeiro, Fevereiro, ..., Dezembro.
    """
    url = "https://power.larc.nasa.gov/api/temporal/climatology/point"
    parametros = {
        "parameters": "ALLSKY_SFC_SW_DWN",  # irradiacao solar = equivale ao HSP
        "community": "RE",                  # RE = Renewable Energy
        "longitude": longitude,
        "latitude": latitude,
        "format": "JSON",
    }
    resposta = requests.get(url, params=parametros)
    dados = resposta.json()
    # a resposta vem "aninhada" dentro de varias gavetinhas - aqui a gente
    # entra em cada uma ate achar os 12 valores mensais
    valores_por_mes = dados["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"]
    # monta a lista final, na ordem certa (Jan a Dez)
    hsp_mensal = [valores_por_mes[mes] for mes in MESES_NASA]
    return hsp_mensal
# =======================================================================
# TESTE - usa as coordenadas de Guaira/PR que ja encontramos no Passo 2
# =======================================================================
if __name__ == "__main__":
    lat_teste = -24.0851924
    lon_teste = -54.2567519
    print(f"Buscando HSP para lat={lat_teste}, lon={lon_teste}...\n")
    hsp = buscar_hsp_mensal(lat_teste, lon_teste)
    for nome_mes, valor in zip(NOMES_MESES_PT, hsp):
        print(f"{nome_mes}: {valor:.2f} HSP")
    # Media SIMPLES, so para conferencia rapida. A Equacao 1 do artigo e a
    # media PONDERADA pelos dias do mes (calculo.hsp_medio_anual); o
    # rotulo abaixo ficou do prototipo.
    media_anual = sum(hsp) / len(hsp)
    print(f"\nMedia anual (Equacao 1): {media_anual:.2f} HSP")
