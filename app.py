import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import sqlalchemy as sa
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf

# 1. Configuração de Estado (State Management)
st.set_page_config(page_title="My Public Portfolio", layout="wide", initial_sidebar_state="expanded")

if 'lang' not in st.session_state:
    st.session_state['lang'] = 'pt'
if 'theme' not in st.session_state:
    st.session_state['theme'] = 'dark'

# Tradução Estática (i18n)
TEXTS = {
    "title": {"pt": "My Public Portfolio with AI", "en": "My Public Portfolio with AI"},
    "subtitle": {"pt": "Powered by Thiago Alves", "en": "Powered by Thiago Alves"},
    "filters_title": {"pt": "<i class='ph ph-sliders-horizontal'></i> Filtros Inteligentes", "en": "<i class='ph ph-sliders-horizontal'></i> Smart Filters"},
    "signal": {"pt": "Sinal da IA", "en": "AI Signal"},
    "min_conf": {"pt": "Confiança Mínima da IA (%)", "en": "Minimum AI Confidence (%)"},
    "search": {"pt": "Buscar Ativo (ex: PETR4)", "en": "Search Asset (e.g. AAPL)"},
    "no_assets": {"pt": "Nenhum ativo atende aos critérios de filtro informados.", "en": "No assets match the current filters."},
    "tab_ov": {"pt": "Visão Geral", "en": "Overview"},
    "tab_tr": {"pt": "Tendências de Mercado", "en": "Market Trends"},
    "tab_op": {"pt": "Otimizador de Portfólio", "en": "Portfolio Optimizer"},
    "ov_title": {"pt": "<i class='ph ph-chart-pie-slice'></i> Resumo da Carteira", "en": "<i class='ph ph-chart-pie-slice'></i> Portfolio Summary"},
    "equity": {"pt": "Patrimônio Total", "en": "Total Equity"},
    "invested": {"pt": "Valor Gasto (Aporte)", "en": "Total Invested"},
    "result": {"pt": "Resultado Aberto", "en": "Open Result"},
    "dist": {"pt": "Distribuição do Patrimônio", "en": "Equity Distribution"},
    "profit": {"pt": "Rentabilidade por Ativo (%)", "en": "Profitability by Asset (%)"},
    "radar": {"pt": "<i class='ph ph-crosshair'></i> Radar de Ativos & Visão do Modelo (XGBoost)", "en": "<i class='ph ph-crosshair'></i> Asset Radar & Model Vision (XGBoost)"},
    "col_asset": {"pt": "Ativo", "en": "Asset"},
    "col_qty": {"pt": "Qtd", "en": "Qty"},
    "col_avg": {"pt": "Preço Médio (R$)", "en": "Avg Price ($)"},
    "col_price": {"pt": "Cotação (R$)", "en": "Current Price ($)"},
    "col_prof": {"pt": "Rentabilidade (%)", "en": "Profitability (%)"},
    "col_sig": {"pt": "Sinal da IA", "en": "AI Signal"},
    "col_conf": {"pt": "Confiança da IA", "en": "AI Confidence"},
    "trend_title": {"pt": "<i class='ph ph-trend-up'></i> Análise Gráfica Histórica", "en": "<i class='ph ph-trend-up'></i> Historical Graphical Analysis"},
    "sel_asset": {"pt": "Selecione o Ativo para Análise Profunda", "en": "Select Asset for Deep Analysis"},
    "period": {"pt": "Período", "en": "Period"},
    "loading": {"pt": "Carregando dados históricos do Yahoo Finance para", "en": "Loading historical data from Yahoo Finance for"},
    "no_hist": {"pt": "Histórico não encontrado no Yahoo Finance.", "en": "History not found in Yahoo Finance."},
    "api_err": {"pt": "Erro ao puxar API do formato financeiro.", "en": "Error fetching from financial API."},
    "no_asset_avail": {"pt": "Nenhum ativo disponível para análise histórica com os filtros atuais.", "en": "No assets available for historical analysis with current filters."},
    "opt_title": {"pt": "<i class='ph ph-lightbulb'></i> Inteligência de Alocação de Capital", "en": "<i class='ph ph-lightbulb'></i> Capital Allocation Intelligence"},
    "opt_desc": {"pt": "Utilize o modelo de Machine Learning para guiar novos aportes financeiros baseado na confiança da IA (Recomendação de COMPRA).", "en": "Use the Machine Learning model to guide new investments based on AI confidence (BUY Recommendation)."},
    "avail_cash": {"pt": "Caixa Disponível para Investir", "en": "Available Cash to Invest"},
    "tgt_asset": {"pt": "Ativo Alvo", "en": "Target Asset"},
    "tgt_price": {"pt": "Cotação Atual", "en": "Current Price"},
    "tgt_conf": {"pt": "Confiança IA", "en": "AI Confidence"},
    "tgt_weight": {"pt": "Peso % do Aporte", "en": "Allocation Weight %"},
    "tgt_alloc": {"pt": "Cap. Alocado", "en": "Allocated Cap."},
    "tgt_qty": {"pt": "Qtd. a Comprar (Aprox.)", "en": "Qty to Buy (Approx.)"},
    "opt_success": {"pt": "O modelo apontou {n} excelentes oportunidades de compra no seu radar atual!", "en": "The model discovered {n} excellent buying opportunities on your radar!"},
    "opt_low": {"pt": "A confiança calculada não é alta o suficiente para sugerir aportes agora.", "en": "The calculated confidence is not high enough to suggest investments right now."},
    "opt_zero": {"pt": "Insira um valor maior que Zero para simular aportes.", "en": "Enter a value greater than Zero to simulate investments."},
    "opt_none": {"pt": "Nenhum ativo com recomendação firme de COMPRA filtrado no momento. Mantenha seu capital protegido.", "en": "No assets with firm BUY recommendation filtered at the moment. Keep your capital protected."},
    "data_err": {"pt": "Erro ao carregar os dados:", "en": "Error loading data:"},
}

def _(key):
    return TEXTS[key].get(st.session_state['lang'], TEXTS[key]['en'])

# 2. Configuração de Tema Dinâmico
t_val = st.session_state['theme']

bg_app = "radial-gradient(circle at 10% 20%, rgb(14, 17, 23) 0%, rgb(8, 10, 15) 100%)" if t_val == 'dark' else "#f0f4f8"
text_primary = "#e0e0e0" if t_val == 'dark' else "#1e293b"
text_secondary = "#8b949e" if t_val == 'dark' else "#64748b"
header_bg = "rgba(255, 255, 255, 0.03)" if t_val == 'dark' else "rgba(255, 255, 255, 0.8)"
header_border = "rgba(255, 255, 255, 0.05)" if t_val == 'dark' else "rgba(0, 0, 0, 0.05)"
title_gradient = "-webkit-linear-gradient(45deg, #00C9FF, #92FE9D)" if t_val == 'dark' else "-webkit-linear-gradient(45deg, #0F2027, #203A43)"
metric_bg = "linear-gradient(145deg, rgba(26, 30, 36, 0.8), rgba(15, 17, 21, 0.9))" if t_val == 'dark' else "linear-gradient(145deg, #ffffff, #f8fafc)"
metric_border = "rgba(255, 255, 255, 0.08)" if t_val == 'dark' else "rgba(0, 0, 0, 0.05)"
metric_val_col = "#ffffff" if t_val == 'dark' else "#0f172a"
df_bg = "rgba(255, 255, 255, 0.02)" if t_val == 'dark' else "rgba(255, 255, 255, 0.7)"
df_border = "rgba(255, 255, 255, 0.05)" if t_val == 'dark' else "rgba(0, 0, 0, 0.05)"
divider_bg = "linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent)" if t_val == 'dark' else "linear-gradient(90deg, transparent, rgba(0, 0, 0, 0.1), transparent)"
grid_color = "rgba(255,255,255,0.05)" if t_val == 'dark' else "rgba(0,0,0,0.05)"
pie_colors = ['#00C9FF', '#92FE9D', '#1A2980', '#26D0CE', '#f85032'] if t_val == 'dark' else ['#0052D4', '#65C7F7', '#9CECFB', '#11998e', '#38ef7d']
bar_colors = ['#f85032', '#92FE9D'] if t_val == 'dark' else ['#eb3349', '#38ef7d']
plotly_font = "#e2e0e0" if t_val == 'dark' else "#334155"
plotly_marker_line = "#080a0f" if t_val == 'dark' else "#ffffff"

st.markdown(f"""
<style>
    @import url('https://unpkg.com/@phosphor-icons/web@2.1.1/src/regular/style.css');
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    .stApp {{
        background: {bg_app};
        color: {text_primary};
        font-family: 'Inter', sans-serif;
    }}
    
    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    .main .block-container {{
        animation: fadeIn 0.8s ease-out;
        padding-top: 2rem;
        max-width: 1400px;
    }}
    
    .dash-header {{
        background: {header_bg};
        border: 1px solid {header_border};
        padding: 30px;
        border-radius: 20px;
        margin-bottom: 40px;
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        text-align: center;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, {0.4 if t_val=='dark' else 0.05});
    }}
    
    .dash-title {{
        font-weight: 800;
        font-size: 3rem;
        background: {title_gradient};
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        letter-spacing: -1px;
    }}
    
    .dash-subtitle {{
        color: {text_secondary};
        font-weight: 400;
        font-size: 1.1rem;
        margin-top: 10px;
    }}
    
    #MainMenu {{visibility: hidden;}}
    header {{visibility: hidden;}}
    footer {{visibility: hidden;}}

    div[data-testid="stMetricValue"] {{
        font-size: 2.4rem !important;
        font-weight: 800 !important;
        color: {metric_val_col} !important;
        letter-spacing: -0.5px;
    }}
    div[data-testid="stMetricLabel"] {{
        font-size: 0.95rem !important;
        color: {text_secondary} !important;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 5px;
    }}
    div[data-testid="stMetricDelta"] {{
        font-size: 1.0rem !important;
        font-weight: 500 !important;
    }}
    
    div[data-testid="stMetric"] {{
        background: {metric_bg};
        border: 1px solid {metric_border};
        padding: 28px;
        border-radius: 24px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, {0.4 if t_val=='dark' else 0.05});
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        display: flex;
        flex-direction: column;
        justify-content: center;
        min-height: 140px;
    }}
    div[data-testid="stMetric"]:hover {{
        transform: translateY(-8px) scale(1.02);
        box-shadow: 0 15px 45px rgba(0, 201, 255, {0.15 if t_val=='dark' else 0.08});
        border: 1px solid rgba(0, 201, 255, 0.3);
    }}
    
    .stDataFrame {{
        background: {df_bg};
        border-radius: 16px;
        padding: 10px;
        border: 1px solid {df_border};
        box-shadow: 0 8px 32px rgba(0, 0, 0, {0.2 if t_val=='dark' else 0.05});
    }}
    
    h2, h3, h4 {{
        color: {text_primary} !important;
        font-weight: 700 !important;
        letter-spacing: -0.5px;
        margin-top: 15px;
        margin-bottom: 10px;
    }}
    
    hr {{
        border: none;
        height: 1px;
        background: {divider_bg};
        margin: 40px 0;
    }}
    
    .stTabs [data-baseweb="tab-list"] {{
        gap: 20px;
    }}
    .stTabs [data-baseweb="tab"] {{
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
        color: {text_secondary};
        font-size: 1.1rem;
        font-weight: 600;
    }}
    .stTabs [aria-selected="true"] {{
        color: {text_primary};
        border-bottom: 3px solid #00C9FF;
    }}
</style>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="dash-header">
    <h1 class="dash-title">{_('title')}</h1>
    <div class="dash-subtitle">{_('subtitle')}</div>
</div>
""", unsafe_allow_html=True)

# 3. Funções de Coleta de Dados (Com Cache para não travar o app)
@st.cache_data(ttl=3600)
def carregar_dados_planilha():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    cred_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(cred_dict, scopes=scopes)
    client = gspread.authorize(creds)
    
    planilha = client.open("20 25").worksheet("Status").get("A1:M8")
    df = pd.DataFrame(planilha[1:], columns=planilha[0])
    
    df["Ação"] = df["Ação"].str.replace(r'F$', '', regex=True)  
    colunas_monetarias = ['Cotação Atual', 'Valor Gasto', 'Valor Médio', 'Patrimonio']
    for col in colunas_monetarias:
        df[col] = df[col].str.replace('R\$ ', '', regex=True).str.replace('.', '', regex=False).str.replace(',', '.').astype(float)
    
    df['Qtd'] = df['Qtd'].astype(int)
    return df

@st.cache_data(ttl=3600)
def carregar_previsoes_ml():
    DATABASE_URL = st.secrets["DATABASE_URL"]
    engine = sa.create_engine(DATABASE_URL)
    query = """
        SELECT REPLACE(ticker_id, '.SA', '') AS ticker_id, probabilidade_compra, recomendacao 
        FROM ml_ativos_previsoes 
        WHERE data_previsao = (SELECT MAX(data_previsao) FROM ml_ativos_previsoes)
    """
    df_ml = pd.read_sql(query, engine)
    return df_ml

# 4. Construindo a Interface Principal
@st.cache_data(ttl=3600)
def obter_cotacao_dolar():
    try:
        return yf.Ticker("BRL=X").history(period="1d")['Close'].iloc[-1]
    except:
        return 5.0

try:
    df_carteira = carregar_dados_planilha()
    df_ml = carregar_previsoes_ml()
    
    df_final = pd.merge(df_carteira, df_ml, left_on='Ação', right_on='ticker_id', how='left')
    
    # Converte os valores para Dólar se o idioma for Inglês
    if st.session_state['lang'] == 'en':
        usd_rate = obter_cotacao_dolar()
        colunas_monetarias = ['Cotação Atual', 'Valor Gasto', 'Valor Médio', 'Patrimonio']
        for col in colunas_monetarias:
            df_final[col] = df_final[col] / usd_rate
    
    # ─── SIDEBAR TOGGLES & FILTERS ───
    with st.sidebar:
        # Toggles
        col_t1, col_t2 = st.columns(2)
        if col_t1.button("EN 🇺🇸" if st.session_state['lang'] == 'pt' else "PT 🇧🇷", use_container_width=True):
            st.session_state['lang'] = 'en' if st.session_state['lang'] == 'pt' else 'pt'
            st.rerun()
            
        # btn_theme_label = "Light ☀️" if st.session_state['theme'] == 'dark' else "Dark 🌙"
        # if col_t2.button(btn_theme_label, use_container_width=True):
        #     st.session_state['theme'] = 'light' if st.session_state['theme'] == 'dark' else 'dark'
        #     st.rerun()
            
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"### {_('filters_title')}", unsafe_allow_html=True)
        st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
        
        opcoes_rec = df_final['recomendacao'].dropna().unique().tolist()
        if opcoes_rec:
            filtro_rec = st.multiselect(_('signal'), opcoes_rec)
        else:
            filtro_rec = []
            
        df_final['probabilidade_compra'] = pd.to_numeric(df_final['probabilidade_compra'], errors='coerce').fillna(0)
        min_confianca = st.slider(_('min_conf'), 0, 100, 0)
        busca_ticker = st.text_input(_('search'), "").upper()
        
    if len(filtro_rec) > 0:
        df_final = df_final[df_final['recomendacao'].isin(filtro_rec)]
        
    if min_confianca > 0:
        limiar = min_confianca / 100.0 if df_final['probabilidade_compra'].max() <= 1.05 else min_confianca
        df_final = df_final[df_final['probabilidade_compra'] >= limiar]
        
    if busca_ticker:
        df_final = df_final[df_final['Ação'].str.contains(busca_ticker, na=False)]
        
    if df_final.empty:
        st.warning(_('no_assets'))
        st.stop()
    
    # ─── TABS LAYOUT ───
    tab_geral, tab_historico, tab_otimiza = st.tabs([_('tab_ov'), _('tab_tr'), _('tab_op')])
    
    with tab_geral:
        st.markdown(f"### {_('ov_title')}", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        
        patrimonio_total = df_final['Patrimonio'].sum()
        valor_gasto_total = df_final['Valor Gasto'].sum()
        lucro_prejuizo = patrimonio_total - valor_gasto_total
        currency_sim = "$" if st.session_state['lang'] == 'en' else "R$"
        
        col1.metric(_('equity'), f"{currency_sim} {patrimonio_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        col2.metric(_('invested'), f"{currency_sim} {valor_gasto_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        col3.metric(_('result'), f"{currency_sim} {lucro_prejuizo:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'), 
                    f"{(lucro_prejuizo/valor_gasto_total)*100:.2f}%" if valor_gasto_total > 0 else "0.00%")

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        col_graf1, col_graf2 = st.columns(2)
        with col_graf1:
            st.markdown(f"#### {_('dist')}")
            fig_pie = px.pie(df_final, values='Patrimonio', names='Ação', hole=0.6, 
                             color_discrete_sequence=pie_colors)
            fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                                  font=dict(color=plotly_font, family='Inter'), showlegend=True, margin=dict(t=20, b=20, l=0, r=0))
            fig_pie.update_traces(marker={"line": {"color": plotly_marker_line, "width": 2}}, hoverinfo='label+percent')
            st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False})
            
        with col_graf2:
            st.markdown(f"#### {_('profit')}")
            try:
                df_final['Percentual_Num'] = pd.to_numeric(df_final['Percentual de Valorização'].astype(str).str.replace('%', '').str.replace(',', '.'), errors='coerce')
            except:
                df_final['Percentual_Num'] = df_final['Percentual de Valorização']
                
            fig_bar = px.bar(df_final, x='Ação', y='Percentual_Num', 
                             color='Percentual_Num', color_continuous_scale=bar_colors)
            fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                                  font=dict(color=plotly_font, family='Inter'), margin=dict(t=20, b=20, l=0, r=0),
                                  xaxis={"showgrid": True}, yaxis={"showgrid": True, "gridcolor": grid_color, "gridwidth": 1})
            fig_bar.update_traces(marker_line_color=plotly_marker_line, marker_line_width=1.5, opacity=0.9)
            st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False})

        st.markdown("<hr>", unsafe_allow_html=True)

        st.markdown(f"### {_('radar')}", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        df_display = df_final[['Ação', 'Qtd', 'Valor Médio', 'Cotação Atual', 'Percentual_Num', 'recomendacao', 'probabilidade_compra']].copy()
        
        col_names = [_('col_asset'), _('col_qty'), _('col_avg'), _('col_price'), _('col_prof'), _('col_sig'), _('col_conf')]
        df_display.columns = col_names
        
        num_cols = [_('col_avg'), _('col_price'), _('col_prof'), _('col_conf')]
        for col in num_cols:
            df_display[col] = pd.to_numeric(df_display[col], errors='coerce')
            
        if not df_display.empty and df_display[_('col_conf')].max() <= 1.05:
            df_display[_('col_conf')] = df_display[_('col_conf')] * 100
        
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                _('col_conf'): st.column_config.ProgressColumn(
                    _('col_conf'), format="%.1f%%", min_value=0, max_value=100
                ),
                _('col_prof'): st.column_config.NumberColumn(_('col_prof'), format="%.2f%%"),
                _('col_avg'): st.column_config.NumberColumn(_('col_avg'), format=f"{currency_sim} %.2f"),
                _('col_price'): st.column_config.NumberColumn(_('col_price'), format=f"{currency_sim} %.2f")
            }
        )

    # ─── TAB 2: HISTÓRICO YFINANCE ───
    with tab_historico:
        st.markdown(f"### {_('trend_title')}", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        ativos_disponiveis = df_final['Ação'].unique().tolist()
        
        if ativos_disponiveis:
            col_sel1, col_sel2 = st.columns([2, 1])
            with col_sel1:
                ativo_selecionado = st.selectbox(_('sel_asset'), ativos_disponiveis)
            with col_sel2:
                periodo = st.selectbox(_('period'), options=["1mo", "3mo", "6mo", "1y", "ytd"], index=2)
            
            ticker_yf = ativo_selecionado if ativo_selecionado.endswith('.SA') else f"{ativo_selecionado}.SA"
            
            with st.spinner(f"{_('loading')} {ticker_yf}..."):
                try:
                    df_historico = yf.download(ticker_yf, period=periodo, progress=False)
                    if not df_historico.empty:
                        if isinstance(df_historico.columns, pd.MultiIndex):
                            df_historico.columns = df_historico.columns.get_level_values(0)
                        
                        inc_color = '#92FE9D' if t_val == 'dark' else '#38ef7d'
                        dec_color = '#f85032' if t_val == 'dark' else '#eb3349'
                            
                        fig_candle = go.Figure(data=[go.Candlestick(x=df_historico.index,
                                        open=df_historico['Open'], high=df_historico['High'],
                                        low=df_historico['Low'], close=df_historico['Close'],
                                        increasing_line_color=inc_color, decreasing_line_color=dec_color)])
                        
                        fig_candle.update_layout(
                            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color=plotly_font, family='Inter'),
                            xaxis_rangeslider_visible=False,
                            margin=dict(t=30, b=20, l=10, r=10),
                            yaxis={"gridcolor": grid_color}, xaxis={"gridcolor": grid_color}
                        )
                        st.plotly_chart(fig_candle, use_container_width=True)
                    else:
                        st.warning(_('no_hist'))
                except Exception as ex:
                    st.error(_('api_err'))
        else:
            st.info(_('no_asset_avail'))

    # ─── TAB 3: OTIMIZADOR DE PORTFÓLIO ───
    with tab_otimiza:
        st.markdown(f"### {_('opt_title')}", unsafe_allow_html=True)
        st.markdown(f"<p style='color: {text_secondary};'>{_('opt_desc')}</p>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        caixa_disponivel = st.number_input(_('avail_cash'), min_value=0.0, value=1000.0, step=100.0)
        
        if 'recomendacao' in df_final.columns:
            ativos_recomendados = df_final[df_final['recomendacao'] == 'COMPRAR'].copy()
        else:
            ativos_recomendados = pd.DataFrame()
        
        if not ativos_recomendados.empty and caixa_disponivel > 0:
            soma_col = 'probabilidade_compra' if 'probabilidade_compra' in ativos_recomendados.columns else _('col_conf')
            soma_v = ativos_recomendados[soma_col].sum()
            
            if soma_v > 0:
                ativos_recomendados['Peso Ideal'] = ativos_recomendados[soma_col] / soma_v
                ativos_recomendados['Aporte Sugerido (R$)'] = ativos_recomendados['Peso Ideal'] * caixa_disponivel
                ativos_recomendados['Cotas Inteiras'] = (ativos_recomendados['Aporte Sugerido (R$)'] // ativos_recomendados['Cotação Atual']).astype(int)
                
                df_sugestao = ativos_recomendados[['Ação', 'Cotação Atual', soma_col, 'Peso Ideal', 'Aporte Sugerido (R$)', 'Cotas Inteiras']].copy()
                df_sugestao.columns = [_('tgt_asset'), _('tgt_price'), _('tgt_conf'), _('tgt_weight'), _('tgt_alloc'), _('tgt_qty')]
                
                is_pct = df_sugestao[_('tgt_conf')].max() <= 1.05
                df_sugestao[_('tgt_conf')] = (df_sugestao[_('tgt_conf')]*100).apply(lambda x: f"{x:.1f}%") if is_pct else df_sugestao[_('tgt_conf')].apply(lambda x: f"{x:.1f}%")
                
                st.dataframe(
                    df_sugestao.style.format({_('tgt_weight'): '{:.1%}', _('tgt_alloc'): f'{currency_sim} {{:.2f}}', _('tgt_price'): f'{currency_sim} {{:.2f}}'}),
                    use_container_width=True, hide_index=True
                )
                
                st.success(_('opt_success').replace("{n}", str(len(df_sugestao))))
            else:
                st.info(_('opt_low'))
        else:
            if caixa_disponivel == 0:
                st.info(_('opt_zero'))
            else:
                st.info(_('opt_none'))

except Exception as e:
    st.error(f"{_('data_err')} {e}")