# Dimensionamento fotovoltaico residencial na web

Código-fonte da plataforma descrita no artigo **"Dimensionamento fotovoltaico residencial na web"**, Trabalho de Conclusão de Curso de Engenharia Elétrica (Uninter, 2026), de Brenda Morel Bueno Ferreira.

A pessoa informa o consumo de energia da casa, o valor e o consumo de uma conta de luz e a cidade. A plataforma devolve o número de painéis solares, a potência do sistema, o inversor, a geração de cada mês, a economia na conta e o tempo de retorno do investimento. O sistema considerado é residencial e ligado à rede (on-grid).

> **Aviso:** a plataforma é uma simulação educativa. Ela não substitui o projeto de um profissional habilitado.

## O que tem aqui

| Pasta ou arquivo | O que é |
|---|---|
| `calculo.py` | O motor de cálculo: as equações do artigo, a verificação elétrica e o catálogo de módulos e inversores |
| `simulacao.py` | Junta tudo numa função só, `simular()` |
| `geocoding.py` | Transforma a cidade em coordenadas e identifica o estado (Nominatim/OpenStreetMap) |
| `nasa_power.py` | Busca a irradiação solar de cada mês (NASA POWER) |
| `app.py`, `templates/`, `static/` | O site (Flask): o formulário e a tela de resultado |
| `fio_b_aneel_vigente_22-09-2026.csv` | Valores do Fio B da ANEEL vigentes em 22/09/2026, usados na tabela do motor |
| `requirements.txt` | As bibliotecas e as versões usadas |
| `teste/` | O programa que confere as equações contra o motor, e o resultado dele |
| `resultados/plataforma/` | A tela de resultado dos cinco casos de validação, em PDF |
| `resultados/pvsyst/` | Os relatórios das simulações no PVsyst 8.1.5, com todos os parâmetros (cinco casos e a simulação adicional de Campinas com dois módulos) |

## Como rodar no computador

É preciso ter o Python instalado (a plataforma foi feita com o Python 3.14) e internet, porque a cidade e a irradiação são buscadas na hora.

```
pip install -r requirements.txt
python app.py
```

Depois, abra `http://127.0.0.1:5000` no navegador.

## Como conferir as equações

O programa de conferência roda sem internet:

```
python teste/conferir_equacoes_3_3.py
```

Ele faz três coisas:

1. Calcula de novo, com as equações escritas a partir do texto do artigo, os cinco casos de validação.
2. Roda a plataforma 15.744 vezes, em toda a faixa residencial de consumo.
3. Introduz dez erros de propósito no motor, um de cada vez, para confirmar que a conferência os percebe.

O resultado esperado é **0 divergências** e **10 de 10 erros detectados**. A saída completa está em `teste/resultado_da_conferencia.txt`.

## Correspondência das equações

Os comentários do código usam a numeração de equações do desenvolvimento, anterior ao artigo:

| No artigo | No código | Função |
|---|---|---|
| 1 – HSP média anual | Equação 1 | `hsp_medio_anual()` |
| 2 – Tarifa | Equação 6 | `tarifa_total()` |
| 3 – Parcela do Fio B e valor economizado | Equação 7 | `valor_economizado_por_kwh()` |
| 4 – Consumo compensável | Equação 2a | `compensavel_do_mes()`, `consumo_compensavel_do_ano()`, `consumo_alvo_dimensionamento()` |
| 5 – Energia diária e potência teórica | Equações 2 e 3 | `energia_diaria()`, `potencia_sistema_teorica()` |
| 6 – Número de módulos | Equação 4 | `numero_paineis()`, `potencia_instalada()` |
| 7 – Potência do inversor | Equação 10 | `potencia_inversor()`, `potencia_inversor_comercial()` |
| 8 – Geração | Equação 5 | `geracao_estimada()` |
| 9 – Energia compensada e economia anual | Equações 8a e 8b | `energia_compensavel_anual()`, `economia_anual_estimada()` |
| 10 – Custo | (curva da Greener) | `custo_sistema_greener()` |
| 11 – Payback | Equação 9 | `payback_meses()` |
| 12 – Correção pela temperatura | (verificação elétrica) | `voc_na_temperatura_minima()`, `vmp_na_temperatura_maxima()`, `isc_na_temperatura_maxima()` |

## Dados e créditos

- **Irradiação solar:** The data was obtained from National Aeronautics and Space Administration (NASA) Langley Research Center's Prediction Of Worldwide Energy Resources (POWER) project funded through the NASA Earth Science Division.
- **Localização:** a cidade é convertida em coordenadas pelo Nominatim, com dados © OpenStreetMap contributors, disponíveis sob a Open Database License (ODbL): https://www.openstreetmap.org/copyright
- **Fio B:** ANEEL, Portal de Dados Abertos, conjunto "Componentes Tarifárias" (tarifas vigentes em 22/09/2026, sem impostos).
- **Preços:** Greener, Estudo Estratégico – Mercado Fotovoltaico, março de 2026 (preços de janeiro de 2026).
- **Módulos e inversores:** folhas de dados dos fabricantes, citadas no artigo.
