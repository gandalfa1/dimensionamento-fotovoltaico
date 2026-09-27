"""
geocoding.py - Passo 2 do prototipo
Transforma o nome de uma cidade (texto que o usuario digita) em coordenadas
geograficas (latitude e longitude) - que e o que a API da NASA POWER (Passo
3) vai precisar para buscar o HSP daquele lugar.
Usa o servico gratuito Nominatim (projeto OpenStreetMap). Nao precisa de
cadastro nem senha - so precisa de internet.
Para rodar: dentro da pasta do projeto, no terminal:
    py geocoding.py       (Windows)
    python3 geocoding.py  (Mac/Linux)
"""
import requests

# CORRECAO T19 (22/09/2026): a geocodificacao passou a devolver tambem o
# ESTADO. O motivo e o Fio B: ele e homologado pela ANEEL para cada
# distribuidora, e o calculo.py adota o valor da distribuidora da capital
# do estado (FIO_B_POR_UF). Nao e dado novo pedido ao usuario - o estado ja
# vinha dentro da resposta do Nominatim, so nao era lido.
#
# Dois caminhos, do mais confiavel para o de reserva:
#   1. o codigo ISO do estado ("BR-PR"), no campo "ISO3166-2-lvl4" dos
#      detalhes de endereco (addressdetails=1);
#   2. o NOME do estado dentro do nome completo encontrado, que tem o
#      formato "Guaíra, Paraná, Região Sul, 85980-000, Brasil" (formato
#      conferido nos resultados da plataforma de 16/09/2026).
NOME_PARA_UF = {
    "acre": "AC", "alagoas": "AL", "amapá": "AP", "amazonas": "AM",
    "bahia": "BA", "ceará": "CE", "distrito federal": "DF",
    "espírito santo": "ES", "goiás": "GO", "maranhão": "MA",
    "mato grosso": "MT", "mato grosso do sul": "MS", "minas gerais": "MG",
    "pará": "PA", "paraíba": "PB", "paraná": "PR", "pernambuco": "PE",
    "piauí": "PI", "rio de janeiro": "RJ", "rio grande do norte": "RN",
    "rio grande do sul": "RS", "rondônia": "RO", "roraima": "RR",
    "santa catarina": "SC", "são paulo": "SP", "sergipe": "SE",
    "tocantins": "TO",
}


def _uf_do_resultado(resultado):
    """Sigla do estado a partir de um resultado do Nominatim, ou None."""
    endereco = resultado.get("address") or {}
    iso = endereco.get("ISO3166-2-lvl4") or ""
    if iso.startswith("BR-") and len(iso) == 5:
        return iso[3:]
    # Reserva: procurar o nome do estado entre as partes do nome completo.
    # Compara a parte INTEIRA (e nao "contem"), para "Pará" nao casar com
    # "Paraná" nem "Mato Grosso" com "Mato Grosso do Sul". A leitura vai
    # do FIM para o comeco, porque o estado vem depois da cidade e existem
    # cidades com nome de estado (Tocantins, em Minas Gerais, por exemplo).
    for parte in reversed(resultado.get("display_name", "").split(",")):
        uf = NOME_PARA_UF.get(parte.strip().lower())
        if uf:
            return uf
    estado = (endereco.get("state") or "").strip().lower()
    return NOME_PARA_UF.get(estado)


def buscar_coordenadas(cidade):
    """
    Recebe uma cidade como texto, ex: "Guaira, PR, Brasil".
    Devolve um dicionario com latitude, longitude, o nome completo que o
    servico encontrou e o estado ("uf", desde o T19) - ou None, se nao
    encontrar nada.
    """
    url = "https://nominatim.openstreetmap.org/search"
    parametros = {
        "q": cidade,      # o texto que estamos buscando
        "format": "json", # queremos a resposta em formato JSON
        "limit": 1,       # so precisamos do 1o (melhor) resultado
        "addressdetails": 1,  # T19: traz o estado, usado pelo Fio B
    }
    # O Nominatim pede que a gente se identifique - por isso o User-Agent.
    cabecalhos = {
        "User-Agent": "TCC-Brenda-EngenhariaEletrica-Uninter/1.0"
    }
    resposta = requests.get(url, params=parametros, headers=cabecalhos)
    dados = resposta.json()
    if not dados:
        # dados veio como uma lista vazia -> nao achou a cidade
        return None
    primeiro_resultado = dados[0]
    return {
        "latitude": float(primeiro_resultado["lat"]),
        "longitude": float(primeiro_resultado["lon"]),
        "nome_encontrado": primeiro_resultado["display_name"],
        "uf": _uf_do_resultado(primeiro_resultado),
    }
# =======================================================================
# TESTE
# =======================================================================
if __name__ == "__main__":
    cidade_teste = "Guaira, PR, Brasil"
    print(f"Buscando coordenadas para: {cidade_teste}...\n")
    resultado = buscar_coordenadas(cidade_teste)
    if resultado:
        print(f"Encontrado: {resultado['nome_encontrado']}")
        print(f"Latitude:   {resultado['latitude']}")
        print(f"Longitude:  {resultado['longitude']}")
        print(f"Estado:     {resultado['uf']}")
    else:
        print("Cidade nao encontrada. Tente escrever de outra forma, "
              "ex: incluindo o estado ou o pais.")
