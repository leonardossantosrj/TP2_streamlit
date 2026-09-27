import altair as alt
import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pydeck as pdk
import seaborn as sns
import streamlit as st
from plotly.subplots import make_subplots

st.set_page_config(page_title="COVID-19 no Brasil", layout="wide")
st.title("COVID-19 no Brasil")
st.caption("Fonte: Ministerio da Saude - covid.saude.gov.br")

# -----------------------------------------------------------------------------
# Carga dos dados
# -----------------------------------------------------------------------------
@st.cache_data
def carregar(arquivos):
    partes = []
    for arquivo in arquivos:
        df = pd.read_csv(arquivo, sep=";", encoding="latin-1", low_memory=False)
        partes.append(df)
 
    dados = pd.concat(partes, ignore_index=True)
    dados["data"] = pd.to_datetime(dados["data"])
    # semana com o ano junto, para nao misturar a semana 7 de anos diferentes
    dados["semana"] = (
        dados["data"].dt.year.astype(str)
        + "-S"
        + dados["semanaEpi"].astype(str).str.zfill(2)
    )
    return dados
 
 
@st.cache_data
def carregar_coordenadas():
    url = "https://raw.githubusercontent.com/kelvins/municipios-brasileiros/main/csv/municipios.csv"
    municipios = pd.read_csv(url)
    municipios["codmun6"] = municipios["codigo_ibge"].astype(str).str[:6]
    return municipios[["codmun6", "latitude", "longitude"]]
 
 
st.sidebar.header("Dados")
arquivos = st.sidebar.file_uploader(
    "Necessário fazer o upload dos dados HIST_PAINEL_COVIDBR_*.csv",
    type=["csv"],
    accept_multiple_files=True,
)


# =============================================================================
# EXERCICIO 1 - IMPORTANCIA DA VISUALIZACAO DE DADOS
# =============================================================================

st.header("1. Importancia da visualizacao de dados")
st.markdown(
    """
O painel do Ministerio da Saude publicava uma tabela com milhoes de linhas por dia, um formato
que nenhum gestor consegue ler no ritmo em que a decisao precisa ser tomada. A visualizacao
resolve tres coisas: mostra a **inclinacao** da curva (e a inclinacao, nao o numero do dia, que
diz se um leito vai faltar daqui a duas semanas), permite **comparar** estados de tamanhos
diferentes quando os dados sao normalizados por populacao, e **localiza** o problema no mapa,
orientando onde colocar vacina, leito e barreira sanitaria.
 
Para o gestor, isso vira alocacao de recurso. Para a populacao, cumpre papel de transparencia e
de percepcao de risco.
 
Vale a ressalva: o grafico tambem engana. Escala logaritmica ou linear muda a percepcao da mesma
curva, e dado por data de notificacao nao e a mesma coisa que dado por data de ocorrencia.
    """
)

if not arquivos:
    st.info("Envie os arquivos CSV na barra lateral para carregar os graficos.")
    st.stop()
 
dados = carregar(arquivos)
 
# O arquivo mistura tres granularidades nas mesmas linhas: total do pais, total
# por UF e municipios. Sem separar, o mesmo caso seria somado tres vezes.
brasil = dados[dados["regiao"] == "Brasil"]
estados = dados[dados["estado"].notna() & dados["municipio"].isna() & dados["codmun"].isna()]
municipios = dados[dados["municipio"].notna()]
 
st.success(f"{len(dados)} linhas carregadas.")


# =============================================================================
# EXERCICIO 2 - GRAFICO DE BARRAS COM STREAMLIT
# Casos novos por semana epidemiologica no Rio de Janeiro
# =============================================================================
st.header("2. Casos novos por semana - RJ (barras)")
 
casos_rj = estados[estados["estado"] == "RJ"].groupby("semana")["casosNovos"].sum()
st.bar_chart(casos_rj)
 
st.markdown(
    """
**Estado escolhido: RJ.** Foi um dos primeiros focos de transmissao comunitaria do pais, e a
regiao metropolitana densa faz as ondas aparecerem bem definidas no grafico. O volume alto de
notificacao tambem reduz o ruido em comparacao com UFs menores.
 
Agrupar por semana epidemiologica elimina o serrilhado do dado diario: sabado e domingo aparecem
artificialmente baixos porque as secretarias nao fecham boletim, e a segunda-feira aparece
inflada.
    """
)
 
 
# =============================================================================
# EXERCICIO 3 - GRAFICO DE LINHA COM STREAMLIT
# Obitos acumulados no Brasil por semana
# =============================================================================
st.header("3. Obitos acumulados no Brasil (linha)")
 
obitos_brasil = brasil.groupby("semana")["obitosAcumulado"].max()
st.line_chart(obitos_brasil)
 
st.markdown(
    """
A curva acumulada nunca desce, entao o que informa nao e o nivel e sim a **inclinacao**. Trecho
ingreme significa muitas mortes por semana; trecho horizontal significa desaceleracao, nao queda
no total.
 
Os saltos verticais isolados geralmente nao sao um dia tragico: sao revisoes retroativas, quando
um estado reprocessa obitos represados e lanca tudo de uma vez.
    """
)
 
 
# =============================================================================
# EXERCICIO 4 - GRAFICO DE AREA COM STREAMLIT
# Casos acumulados em tres estados
# =============================================================================
st.header("4. Casos acumulados em SP, RJ e AM (area)")
 
tres_estados = estados[estados["estado"].isin(["SP", "RJ", "AM"])]
area = (
    tres_estados.groupby(["semana", "estado"])["casosAcumulado"]
    .max()
    .reset_index()
    .pivot(index="semana", columns="estado", values="casosAcumulado")
)
st.area_chart(area)
 
st.markdown(
    """
Sao Paulo domina em numeros absolutos porque tem a maior populacao do pais, nao necessariamente
porque a situacao epidemiologica foi pior. O Amazonas mostra o padrao oposto: volume menor, mas
dois saltos abruptos e concentrados (abril de 2020 e janeiro de 2021, o colapso de oxigenio em
Manaus). O Rio fica no meio, com crescimento mais continuo.
 
Em valores absolutos, o grafico mede tamanho de populacao tanto quanto intensidade da epidemia.
Para comparar gravidade seria preciso normalizar por 100 mil habitantes.
    """
)
 

# =============================================================================
# EXERCICIO 5 - MAPA COM st.map
# Casos acumulados por municipio no Rio de Janeiro
# =============================================================================
st.header("5. Casos acumulados por municipio - RJ (st.map)")
 
coordenadas = carregar_coordenadas()
 
municipios_rj = municipios[municipios["estado"] == "SP"].copy()
municipios_rj["codmun6"] = municipios_rj["codmun"].astype(int).astype(str).str[:6]
 
mapa = (
    municipios_rj.groupby(["codmun6", "municipio"])["casosAcumulado"]
    .max()
    .reset_index()
    .merge(coordenadas, on="codmun6")
)
mapa["tamanho"] = mapa["casosAcumulado"] ** 0.5 * 30
 
st.map(mapa, latitude="latitude", longitude="longitude", size="tamanho")
 
st.markdown(
    """
Uma tabela ordenada por numero de casos sempre devolve as mesmas capitais no topo. O mapa mostra
o que a tabela esconde: o **padrao espacial**. Da para ver a difusao saindo da capital para a
regiao metropolitana e depois acompanhando os eixos rodoviarios ate o interior, e da para
identificar municipios vizinhos com comportamentos diferentes, o que costuma indicar diferenca
de politica sanitaria ou de capacidade de testagem.
    """
)
 

# =============================================================================
# EXERCICIO 6 - MATPLOTLIB
# Casos novos x obitos novos por estado na semana mais recente
# =============================================================================
st.header("6. Casos novos x obitos novos por estado (Matplotlib)")
 
semana_recente = estados["semana"].max()
comparativo = (
    estados[estados["semana"] == semana_recente]
    .groupby("estado")[["casosNovos", "obitosNovos"]]
    .sum()
    .sort_values("casosNovos", ascending=False)
)
 
figura, eixo = plt.subplots(figsize=(12, 5))
posicoes = range(len(comparativo))
eixo.bar([p - 0.2 for p in posicoes], comparativo["casosNovos"], width=0.4, label="Casos novos")
eixo.bar([p + 0.2 for p in posicoes], comparativo["obitosNovos"], width=0.4, label="Obitos novos")
eixo.set_xticks(list(posicoes))
eixo.set_xticklabels(comparativo.index, rotation=90)
eixo.set_title(f"Casos novos x obitos novos por UF - semana {semana_recente}")
eixo.set_yscale("log")  # sem log os obitos somem ao lado dos casos
eixo.legend()
st.pyplot(figura)
 
st.markdown(
    """
As duas series sao de ordens de grandeza muito diferentes, por isso a escala logaritmica. Isso ja
e a informacao principal: a letalidade registrada fica na casa de poucos por cento.
 
A razao obitos/casos nao e igual entre os estados, e a diferenca raramente e biologica. Ela
reflete testagem (quanto mais se testa, mais casos leves entram no denominador e menor parece a
letalidade), estrutura hospitalar e perfil etario. Ha ainda a defasagem: o obito de uma semana
corresponde ao caso de duas ou tres semanas antes, entao comparar a mesma semana subestima a
letalidade quando a curva esta subindo.
    """
)
 
 
# =============================================================================
# EXERCICIO 7 - BOXPLOT COM SEABORN
# Distribuicao dos casos novos semanais em tres regioes
# =============================================================================
st.header("7. Distribuicao dos casos novos por regiao (Seaborn)")
 
tres_regioes = estados[estados["regiao"].isin(["Norte", "Nordeste", "Sudeste"])]
base_box = tres_regioes.groupby(["regiao", "semana"])["casosNovos"].sum().reset_index()
 
figura_box, eixo_box = plt.subplots(figsize=(9, 5))
sns.boxplot(data=base_box, x="regiao", y="casosNovos", ax=eixo_box)
eixo_box.set_title("Casos novos por semana epidemiologica")
st.pyplot(figura_box)
 
st.markdown(
    """
O Sudeste tem mediana e amplitude bem maiores, mas parte disso e so populacao: sao mais que o
dobro de habitantes do Nordeste.
 
O achado que importa e a **assimetria**, igual nas tres regioes: a mediana fica na parte inferior
da caixa e ha muitos outliers acima. Essa e a assinatura de uma epidemia em ondas, onde a maior
parte das semanas tem transmissao baixa e poucas semanas concentram um volume enorme de casos. E
justamente isso que estoura a capacidade hospitalar, porque o sistema e dimensionado para a
mediana e nao para o outlier.
    """
)
 
 
# =============================================================================
# EXERCICIO 8 - GRAFICO DE AREA COM ALTAIR
# Casos novos por semana na regiao Sudeste
# =============================================================================
st.header("8. Casos novos por semana - Sudeste (Altair)")
 
sudeste = estados[estados["regiao"] == "Sudeste"].groupby("semana")["casosNovos"].sum().reset_index()
 
grafico_area = (
    alt.Chart(sudeste)
    .mark_area(opacity=0.7)
    .encode(
        x=alt.X("semana:N", title="Semana epidemiologica", axis=alt.Axis(labelAngle=-90)),
        y=alt.Y("casosNovos:Q", title="Casos novos"),
        tooltip=["semana", "casosNovos"],
    )
    .properties(height=380)
)
st.altair_chart(grafico_area, use_container_width=True)
 
st.markdown(
    """
**Regiao escolhida: Sudeste.** Maior populacao e maior volume de notificacao do pais, o que da
uma serie com menos ruido e ondas de contorno limpo.
 
A area desenha as ondas sucessivas separadas por vales, e os picos nao tem o mesmo formato. A
onda da Omicron, no inicio de 2022, e muito mais alta e mais estreita em casos que as anteriores
(transmissao explosiva e rapida) sem um pico proporcional de obitos, efeito combinado da
vacinacao e da menor gravidade da variante.
    """
)
 
 
# =============================================================================
# EXERCICIO 9 - HEATMAP COM ALTAIR
# Correlacao entre as variaveis disponiveis no RJ
# =============================================================================
st.header("9. Heatmap de correlacao - RJ (Altair)")
 
st.info(
    "O painel Coronavirus Brasil nao publica ocupacao de leitos (esse dado ficava no e-SUS/SRAG "
    "e nos paineis estaduais). Como o enunciado condiciona o item a disponibilidade, o heatmap "
    "usa as variaveis que o arquivo traz."
)
 
colunas = ["casosNovos", "obitosNovos", "Recuperadosnovos", "emAcompanhamentoNovos"]
correlacao = estados[estados["estado"] == "RJ"][colunas].corr()
matriz = correlacao.reset_index().melt(id_vars="index")
matriz.columns = ["variavel_x", "variavel_y", "correlacao"]
 
heatmap = (
    alt.Chart(matriz)
    .mark_rect()
    .encode(
        x=alt.X("variavel_x:N", title=None),
        y=alt.Y("variavel_y:N", title=None),
        color=alt.Color("correlacao:Q", scale=alt.Scale(scheme="redblue", domain=[-1, 1])),
        tooltip=["variavel_x", "variavel_y", "correlacao"],
    )
    .properties(height=330)
)
rotulos = heatmap.mark_text(fontSize=13).encode(
    text=alt.Text("correlacao:Q", format=".2f"), color=alt.value("black")
)
st.altair_chart(heatmap + rotulos, use_container_width=True)
 
st.markdown(
    """
Casos novos e obitos novos aparecem positivamente correlacionados, mas com coeficiente bem abaixo
de 1. O motivo e a defasagem: o obito ocorre duas a tres semanas depois do caso, e a correlacao
calculada sobre a mesma data subestima a relacao real. Com um deslocamento de 14 a 21 dias em
casosNovos o coeficiente sobe bastante.
 
Vale lembrar que correlacao nao e causalidade. Aqui as duas series compartilham um fator externo,
o volume de testagem, que infla as duas ao mesmo tempo.
    """
)
 
 
# =============================================================================
# EXERCICIO 10 - GRAFICO DE PIZZA COM PLOTLY
# Casos acumulados entre as cinco regioes
# =============================================================================
st.header("10. Casos acumulados por regiao (Plotly)")
 
ultimo_por_estado = estados.sort_values("data").groupby("estado").tail(1)
por_regiao = ultimo_por_estado.groupby("regiao")["casosAcumulado"].sum().reset_index()
 
figura_pizza = px.pie(por_regiao, names="regiao", values="casosAcumulado", hole=0.35)
figura_pizza.update_traces(textinfo="percent+label")
st.plotly_chart(figura_pizza, use_container_width=True)
 
st.markdown(
    """
O Sudeste responde sozinho por cerca de 40% dos casos acumulados, seguido de Nordeste e Sul.
Parece um mapa da epidemia, mas e em boa medida um mapa da populacao brasileira: o Sudeste
concentra por volta de 42% dos habitantes do pais, praticamente a mesma fatia.
 
Essa e a limitacao do grafico de pizza aqui. Ele mostra participacao no total, nao intensidade.
Dividindo por populacao o ranking muda. A pizza serve para dimensionar a carga absoluta sobre
cada regiao, nao para dizer onde a epidemia foi pior.
    """
)
 
 
# =============================================================================
# EXERCICIO 11 - SUBPLOTS COM PLOTLY
# Casos novos e obitos novos em duas regioes
# =============================================================================
st.header("11. Norte x Sudeste lado a lado (Subplots Plotly)")
 
norte = estados[estados["regiao"] == "Norte"].groupby("semana")[["casosNovos", "obitosNovos"]].sum().reset_index()
sudeste_sub = estados[estados["regiao"] == "Sudeste"].groupby("semana")[["casosNovos", "obitosNovos"]].sum().reset_index()
 
figura_sub = make_subplots(rows=1, cols=2, subplot_titles=("Norte", "Sudeste"))
figura_sub.add_trace(go.Bar(x=norte["semana"], y=norte["casosNovos"], name="Casos novos"), row=1, col=1)
figura_sub.add_trace(go.Bar(x=norte["semana"], y=norte["obitosNovos"], name="Obitos novos"), row=1, col=1)
figura_sub.add_trace(go.Bar(x=sudeste_sub["semana"], y=sudeste_sub["casosNovos"], name="Casos novos", showlegend=False), row=1, col=2)
figura_sub.add_trace(go.Bar(x=sudeste_sub["semana"], y=sudeste_sub["obitosNovos"], name="Obitos novos", showlegend=False), row=1, col=2)
figura_sub.update_layout(barmode="group", height=480)
st.plotly_chart(figura_sub, use_container_width=True)
 
st.markdown(
    """
Os eixos Y sao independentes, senao o Norte viraria uma faixa achatada. Isso exige atencao: a
altura das barras nao e comparavel entre os dois paineis, so o formato das curvas e.
 
E o formato mostra que a epidemia nao foi simultanea no pais. O Norte teve um primeiro pico
precoce e severo (Manaus, abril de 2020), enquanto o Sudeste teve sua onda mais grave depois.
Essa defasagem foi o que permitiu, em alguns momentos, transferir pacientes entre estados. Dentro
de cada painel, a proporcao entre a barra de casos e a de obitos diminui a partir de 2021, efeito
da vacinacao sobre a letalidade.
    """
)
 
 
# =============================================================================
# EXERCICIO 12 - MAPA INTERATIVO COM PYDECK
# Casos acumulados por municipio ajustados pela populacao - Sudeste
# =============================================================================
st.header("12. Casos por 100 mil habitantes - Sudeste (PyDeck)")
 
municipios_sudeste = municipios[municipios["regiao"] == "Sudeste"].copy()
municipios_sudeste["codmun6"] = municipios_sudeste["codmun"].astype(int).astype(str).str[:6]
 
resumo = (
    municipios_sudeste.groupby(["codmun6", "municipio", "estado"])
    .agg(casos=("casosAcumulado", "max"), populacao=("populacaoTCU2019", "max"))
    .reset_index()
    .merge(coordenadas, on="codmun6")
)
resumo = resumo[resumo["populacao"] > 0]
resumo["casos_por_100mil"] = resumo["casos"] / resumo["populacao"] * 100000
resumo["altura"] = resumo["casos_por_100mil"] * 2
 
camada = pdk.Layer(
    "ColumnLayer",
    data=resumo,
    get_position=["longitude", "latitude"],
    get_elevation="altura",
    radius=6000,
    get_fill_color=[200, 30, 0, 160],
    pickable=True,
)
visao = pdk.ViewState(
    latitude=resumo["latitude"].mean(),
    longitude=resumo["longitude"].mean(),
    zoom=4.5,
    pitch=45,
)
st.pydeck_chart(
    pdk.Deck(
        layers=[camada],
        initial_view_state=visao,
        tooltip={"text": "{municipio}/{estado}\nCasos por 100 mil: {casos_por_100mil}"},
    )
)
 
st.markdown(
    """
A COVID-19 se transmite por contato proximo, entao a taxa de contato entre pessoas e o parametro
central. Densidade alta aumenta essa taxa por varias vias ao mesmo tempo: transporte coletivo
lotado, domicilios com muitos moradores por comodo e menor possibilidade pratica de isolamento.
Por isso as capitais e regioes metropolitanas aparecem como as colunas mais altas, e por isso a
epidemia comecou nelas antes de chegar ao interior.
 
Duas ressalvas. O mapa mostra casos por 100 mil habitantes, que e incidencia e nao densidade:
municipio denso e municipio com muita testagem produzem colunas altas pelo mesmo motivo aparente.
E densidade nao e destino, ja que cidades asiaticas densas controlaram a transmissao com testagem
e rastreamento. A densidade define o potencial de disseminacao; a resposta sanitaria define o
resultado.
    """
)