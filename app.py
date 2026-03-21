import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import sqlalchemy as sa
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf

# 1. Configuração de Estado (State Management)
st.set_page_config(page_title="My Public Portfolio", page_icon="📈", layout="wide", initial_sidebar_state="expanded")

if 'lang' not in st.session_state:
    st.session_state['lang'] = 'pt'

# Tradução Estática (i18n)
TEXTS = {
    "title": {"pt": "Portfólio Público", "en": "Public Portfolio"},
    "subtitle": {"pt": "Powered by Thiago Alves", "en": "Powered by Thiago Alves"},
    "filters_title": {"pt": "Filtros Inteligentes", "en": "Smart Filters"},
    "signal": {"pt": "Sinal da IA", "en": "AI Signal"},
    "min_conf": {"pt": "Confiança Mínima da IA (%)", "en": "Minimum AI Confidence (%)"},
    "search": {"pt": "Buscar Ativo (ex: PETR4)", "en": "Search Asset (e.g. AAPL)"},
    "no_assets": {"pt": "Nenhum ativo atende aos critérios de filtro informados.", "en": "No assets match the current filters."},
    "tab_ov": {"pt": "Visão Geral", "en": "Overview"},
    "tab_tr": {"pt": "Tendências de Mercado", "en": "Market Trends"},
    "tab_op": {"pt": "Otimizador de Portfólio", "en": "Portfolio Optimizer"},
    "ov_title": {"pt": "Resumo da Carteira", "en": "Portfolio Summary"},
    "equity": {"pt": "Patrimônio Total", "en": "Total Equity"},
    "invested": {"pt": "Valor Gasto (Aporte)", "en": "Total Invested"},
    "result": {"pt": "Resultado Aberto", "en": "Open Result"},
    "dist": {"pt": "Distribuição do Patrimônio", "en": "Equity Distribution"},
    "profit": {"pt": "Rentabilidade por Ativo (%)", "en": "Profitability by Asset (%)"},
    "radar": {"pt": "Radar de Ativos & Visão do Modelo", "en": "Asset Radar & Model Vision"},
    "col_asset": {"pt": "Ativo", "en": "Asset"},
    "col_qty": {"pt": "Qtd", "en": "Qty"},
    "col_avg": {"pt": "Preço Médio (R$)", "en": "Avg Price ($)"},
    "col_price": {"pt": "Cotação (R$)", "en": "Current Price ($)"},
    "col_prof": {"pt": "Rentabilidade (%)", "en": "Profitability (%)"},
    "col_sig": {"pt": "Sinal da IA", "en": "AI Signal"},
    "col_conf": {"pt": "Confiança da IA", "en": "AI Confidence"},
    "trend_title": {"pt": "Análise Gráfica Histórica", "en": "Historical Graphical Analysis"},
    "sel_asset": {"pt": "Selecione o Ativo para Análise Profunda", "en": "Select Asset for Deep Analysis"},
    "period": {"pt": "Período", "en": "Period"},
    "loading": {"pt": "Carregando dados históricos do Yahoo Finance para", "en": "Loading historical data from Yahoo Finance for"},
    "no_hist": {"pt": "Histórico não encontrado no Yahoo Finance.", "en": "History not found in Yahoo Finance."},
    "api_err": {"pt": "Erro ao puxar API do formato financeiro.", "en": "Error fetching from financial API."},
    "no_asset_avail": {"pt": "Nenhum ativo disponível para análise histórica com os filtros atuais.", "en": "No assets available for historical analysis with current filters."},
    "opt_title": {"pt": "Inteligência de Alocação de Capital", "en": "Capital Allocation Intelligence"},
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

# 2. Global Aesthetic & CSS Injection (Ultra-modern React Dark Mode)
st.markdown("""
<style>
    @import url('https://unpkg.com/@phosphor-icons/web@2.1.1/src/regular/style.css');
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    /* Core App */
    .stApp {
        background-color: #0b0e14;
        color: #e2e8f0;
        font-family: 'Inter', sans-serif;
    }
    
    /* Hide top header and footer */
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    .block-container {
        padding-top: 1.5rem !important;
        max-width: 1400px;
    }

    /* Streamlit Cards (st.container with border) styling */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(23, 25, 30, 0.4) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 16px !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3) !important;
        backdrop-filter: blur(10px) !important;
        -webkit-backdrop-filter: blur(10px) !important;
        transition: all 0.3s ease;
        padding: 10px !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: rgba(59, 130, 246, 0.3) !important;
        box-shadow: 0 10px 40px rgba(59, 130, 246, 0.1) !important;
    }

    /* Custom React-Like Header Component */
    .react-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: rgba(23, 25, 30, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 16px 24px;
        margin-bottom: 30px;
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    }
    .header-left .title-main {
        font-size: 1.5rem;
        font-weight: 700;
        color: #f8fafc;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .badge-overview {
        background: rgba(59, 130, 246, 0.15);
        color: #60a5fa;
        font-size: 0.75rem;
        padding: 4px 10px;
        border-radius: 999px;
        font-weight: 600;
        border: 1px solid rgba(59, 130, 246, 0.3);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .header-right {
        display: flex;
        align-items: center;
        gap: 24px;
    }
    .search-mock {
        display: flex;
        align-items: center;
        background: rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 8px 16px;
        border-radius: 8px;
        color: #94a3b8;
        font-size: 0.9rem;
        gap: 8px;
        width: 250px;
        transition: all 0.2s ease;
    }
    .search-mock:hover {
        border-color: rgba(59, 130, 246, 0.5);
    }
    .user-profile {
        display: flex;
        align-items: center;
        gap: 12px;
        border-left: 1px solid rgba(255, 255, 255, 0.1);
        padding-left: 24px;
    }
    .avatar {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        border: 2px solid #3b82f6;
    }
    .user-info {
        display: flex;
        flex-direction: column;
    }
    .user-name {
        font-size: 0.9rem;
        font-weight: 600;
        color: #f8fafc;
        line-height: 1.2;
    }
    .user-role {
        font-size: 0.75rem;
        color: #94a3b8;
    }

    /* Elevated KPI Metrics Cards */
    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, rgba(26, 30, 36, 0.9), rgba(15, 17, 21, 0.95));
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        transition: all 0.3s ease;
        min-height: 120px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    div[data-testid="stMetric"]:hover {
        border-color: rgba(59, 130, 246, 0.4);
        transform: translateY(-4px);
        box-shadow: 0 10px 30px rgba(59, 130, 246, 0.15);
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
        color: #94a3b8 !important;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2.2rem !important;
        font-weight: 800 !important;
        color: #ffffff !important;
        letter-spacing: -0.5px;
    }
    div[data-testid="stMetricDelta"] {
        font-size: 1.0rem !important;
        font-weight: 500 !important;
    }

    /* Customizing DataFrame Header and Body */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
    }
    
    /* Segmented Control / Radio Buttons (Navigation) */
    div.row-widget.stRadio > div {
        background: transparent;
        padding: 0;
        gap: 8px;
    }
    div.row-widget.stRadio > div > label {
        padding: 12px 16px;
        border-radius: 8px;
        background: transparent;
        transition: all 0.2s ease;
        margin-bottom: 4px;
    }
    div.row-widget.stRadio > div > label:hover {
        background: rgba(255, 255, 255, 0.03);
    }
    div.row-widget.stRadio > div > label[data-checked="true"] {
        background: rgba(59, 130, 246, 0.15);
        border: 1px solid rgba(59, 130, 246, 0.3);
    }
    div.row-widget.stRadio > div > label[data-checked="true"] > div:first-child > div {
        color: #60a5fa !important;
        font-weight: 600;
    }

    /* Typography Overrides */
    h1, h2, h3, h4 {
        color: #f8fafc !important;
        font-weight: 700 !important;
        letter-spacing: -0.5px;
    }
    hr {
        border-color: rgba(255, 255, 255, 0.05);
        margin: 2rem 0;
    }
    
    /* Section Headers */
    .section-header {
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 1.25rem;
        font-weight: 700;
        color: #e2e8f0;
        margin-bottom: 1rem;
    }
    .section-icon {
        color: #3b82f6;
        font-size: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Graph Colors
plotly_font = "#e2e8f0"
grid_color = "rgba(255, 255, 255, 0.05)"
pie_colors = ['#3b82f6', '#10b981', '#8b5cf6', '#0ea5e9', '#f43f5e']
bar_colors = ['#f43f5e', '#10b981']

# 3. Funções de Coleta de Dados
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

@st.cache_data(ttl=3600)
def obter_cotacao_dolar():
    try:
        return yf.Ticker("BRL=X").history(period="1d")['Close'].iloc[-1]
    except:
        return 5.0

# 4. Construindo a Interface Principal
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
            
    currency_sim = "$" if st.session_state['lang'] == 'en' else "R$"

    # ─── SIDEBAR NAVIGATION & LANGUAGE ───
    with st.sidebar:
        st.markdown("""
        <div style='text-align: center; margin-bottom: 40px; margin-top: 10px;'>
            <div style='width: 48px; height: 48px; background: linear-gradient(135deg, #3b82f6, #8b5cf6); border-radius: 12px; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 12px; box-shadow: 0 4px 15px rgba(59,130,246,0.3);'>
                <i class='ph ph-chart-line-up' style='color: white; font-size: 28px;'></i>
            </div>
            <h2 style='font-size: 1.1rem; margin:0; color: #f8fafc; font-weight: 700;'>AI Portfolio</h2>
            <p style='color: #64748b; font-size: 0.8rem; margin:0;'>Pro Edition Dashboard</p>
        </div>
        """, unsafe_allow_html=True)
        tab_tr = "Market Trends" if st.session_state['lang'] == 'en' else "Tendências de Mercado"
        tab_opt = "Portfolio Optimizer" if st.session_state['lang'] == 'en' else "Otimizador de Portfólio"
        st.markdown("<div style='font-size:0.75rem; color:#64748b; margin-bottom:10px; font-weight:600; text-transform:uppercase;'>Navigation</div>", unsafe_allow_html=True)
        nav_options = {
            "Dashboard": {"icon": "home", "label": "Dashboard"},
            f"{tab_tr}": {"icon": "trending_up", "label": "Market Trends"},
            f"{tab_opt}": {"icon": "build", "label": "Portfolio Optimizer"}
        }
        nav_selection = st.radio("Navigation", list(nav_options.keys()), label_visibility="collapsed")
        active_page = nav_options[nav_selection]["label"]
        
        st.markdown("<hr style='border-color: rgba(255,255,255,0.05); margin: 30px 0;'>", unsafe_allow_html=True)
        
        # Language Toggle (Styled Button)
        if st.button("🌐 English (US)" if st.session_state['lang'] == 'pt' else "🌐 Português (BR)", use_container_width=True):
            st.session_state['lang'] = 'en' if st.session_state['lang'] == 'pt' else 'pt'
            st.rerun()

    # ─── TOP HEADER ───
    search_bar_based_on_language = "Search assets..." if st.session_state['lang'] == 'en' else "Buscar ativos..."   
    if nav_selection == "Dashboard":
        active_page = "Dashboard" if st.session_state['lang'] == 'en' else "Dashboard" 
    elif nav_selection == tab_tr:
        active_page = "Market Trends" if st.session_state['lang'] == 'en' else "Tendências de Mercado" 
    elif nav_selection == tab_opt:
        active_page = "Portfolio Optimizer" if st.session_state['lang'] == 'en' else "Otimizador de Portfólio" 
    st.markdown(f"""
    <div class="react-header">
        <div class="header-left">
            <h1 class="title-main">
                {_('title')}
                <span class="badge-overview">{active_page}</span>
            </h1>
        </div>
        <div class="header-right">
            <div class="search-mock">
                <i class="ph ph-magnifying-glass"></i>
                <span>{search_bar_based_on_language}</span>
            </div>
            <div class="user-profile">
                <img class="avatar" src="https://ui-avatars.com/api/?name=Thiago+Alves&background=1e293b&color=3b82f6&bold=true" alt="Thiago Alves">
                <div class="user-info">
                    <span class="user-name">Thiago Alves</span>
                    <span class="user-role">Admin</span>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ─── MAIN CONTENT ROUTING ───
    if active_page == "Dashboard":
        
        # --- Upper KPI Cards ---
        col1, col2, col3 = st.columns(3)
        patrimonio_total = df_final['Patrimonio'].sum()
        valor_gasto_total = df_final['Valor Gasto'].sum()
        lucro_prejuizo = patrimonio_total - valor_gasto_total
        
        col1.metric(_('equity'), f"{currency_sim} {patrimonio_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        col2.metric(_('invested'), f"{currency_sim} {valor_gasto_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        col3.metric(_('result'), f"{currency_sim} {lucro_prejuizo:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'), 
                    f"{(lucro_prejuizo/valor_gasto_total)*100:.2f}%" if valor_gasto_total > 0 else "0.00%")

        st.markdown("<br>", unsafe_allow_html=True)

        # --- Smart Filters Component (Card) ---
        with st.container(border=True):
            st.markdown(f"<div class='section-header'><i class='ph ph-sliders-horizontal section-icon'></i> {_('filters_title')}</div>", unsafe_allow_html=True)
            col_f1, col_f2, col_f3 = st.columns([1, 1, 1.5])
            
            with col_f1:
                opcoes_rec = df_final['recomendacao'].dropna().unique().tolist()
                filtro_rec = st.multiselect(_('signal'), opcoes_rec)
            
            with col_f2:
                df_final['probabilidade_compra'] = pd.to_numeric(df_final['probabilidade_compra'], errors='coerce').fillna(0)
                min_confianca = st.slider(_('min_conf'), 0, 100, 0)
                
            with col_f3:
                busca_ticker = st.text_input(_('search'), "").upper()

        # Apply Filters Data Logic
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

        st.markdown("<br>", unsafe_allow_html=True)

        # --- Data Visualizations Cards ---
        col_graf1, col_graf2 = st.columns(2)
        with col_graf1:
            with st.container(border=True):
                st.markdown(f"<div class='section-header'><i class='ph ph-chart-donut section-icon'></i> {_('dist')}</div>", unsafe_allow_html=True)
                fig_pie = px.pie(df_final, values='Patrimonio', names='Ação', hole=0.65, color_discrete_sequence=pie_colors)
                fig_pie.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                    font=dict(color=plotly_font, family='Inter', size=13), showlegend=True, 
                    margin=dict(t=20, b=20, l=0, r=0),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5)
                )
                fig_pie.update_traces(marker={"line": {"color": "rgba(255,255,255,0.05)", "width": 2}}, hoverinfo='label+percent+value')
                st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False})
                
        with col_graf2:
            with st.container(border=True):
                st.markdown(f"<div class='section-header'><i class='ph ph-chart-bar section-icon'></i> {_('profit')}</div>", unsafe_allow_html=True)
                try:
                    df_final['Percentual_Num'] = pd.to_numeric(df_final['Percentual de Valorização'].astype(str).str.replace('%', '').str.replace(',', '.'), errors='coerce')
                except:
                    df_final['Percentual_Num'] = df_final['Percentual de Valorização']
                    
                fig_bar = px.bar(df_final, x='Ação', y='Percentual_Num', color='Percentual_Num', color_continuous_scale=bar_colors)
                fig_bar.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                    font=dict(color=plotly_font, family='Inter', size=13), 
                    margin=dict(t=20, b=20, l=0, r=0),
                    xaxis={"showgrid": False, "title": ""}, 
                    yaxis={"showgrid": True, "gridcolor": grid_color, "gridwidth": 1, "title": ""},
                    coloraxis_showscale=False
                )
                fig_bar.update_traces(marker_line_width=0, opacity=0.9)
                st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False})

        st.markdown("<br>", unsafe_allow_html=True)

        # --- Asset Radar (Data Grid Card) ---
        with st.container(border=True):
            st.markdown(f"<div class='section-header'><i class='ph ph-crosshair section-icon'></i> {_('radar')}</div>", unsafe_allow_html=True)
            
            df_display = df_final[['Ação', 'Qtd', 'Valor Médio', 'Cotação Atual', 'Percentual_Num', 'recomendacao', 'probabilidade_compra']].copy()
            col_names = [_('col_asset'), _('col_qty'), _('col_avg'), _('col_price'), _('col_prof'), _('col_sig'), _('col_conf')]
            df_display.columns = col_names
            
            num_cols = [_('col_avg'), _('col_price'), _('col_prof'), _('col_conf')]
            for col in num_cols:
                df_display[col] = pd.to_numeric(df_display[col], errors='coerce')
                
            if not df_display.empty and df_display[_('col_conf')].max() <= 1.05:
                df_display[_('col_conf')] = df_display[_('col_conf')] * 100
            
            # Decorate the Signal column with emojis
            def format_signal(val):
                if pd.isna(val): return val
                val_str = str(val).upper()
                if "COMPRAR" in val_str or "BUY" in val_str:
                    return f"🟢 {val}"
                elif "ESPERAR" in val_str or "WAIT" in val_str or "HOLD" in val_str:
                    return f"🟠 {val}"
                elif "VENDER" in val_str or "SELL" in val_str:
                    return f"🔴 {val}"
                return val

            df_display[_('col_sig')] = df_display[_('col_sig')].apply(format_signal)
            
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

    # ─── MARKET TRENDS ───
    elif active_page == "Market Trends" or active_page == "Tendências de Mercado":
        with st.container(border=True):
            st.markdown(f"<div class='section-header'><i class='ph ph-trend-up section-icon'></i> {_('trend_title')}</div>", unsafe_allow_html=True)
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
                            
                            inc_color = '#10b981' # Emerald Green
                            dec_color = '#f43f5e' # Rose Red
                                
                            fig_candle = go.Figure(data=[go.Candlestick(x=df_historico.index,
                                            open=df_historico['Open'], high=df_historico['High'],
                                            low=df_historico['Low'], close=df_historico['Close'],
                                            increasing_line_color=inc_color, decreasing_line_color=dec_color)])
                            
                            fig_candle.update_layout(
                                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                                font=dict(color=plotly_font, family='Inter', size=13),
                                xaxis_rangeslider_visible=False,
                                margin=dict(t=30, b=20, l=10, r=10),
                                yaxis={"gridcolor": grid_color, "title": ""}, xaxis={"gridcolor": grid_color, "title": ""}
                            )
                            st.plotly_chart(fig_candle, use_container_width=True)
                        else:
                            st.warning(_('no_hist'))
                    except Exception as ex:
                        st.error(_('api_err'))
            else:
                st.info(_('no_asset_avail'))

    # ─── PORTFOLIO OPTIMIZER ───
    elif active_page == "Portfolio Optimizer" or active_page == "Otimizador de Portfólio":
        with st.container(border=True):
            st.markdown(f"<div class='section-header'><i class='ph ph-lightbulb section-icon'></i> {_('opt_title')}</div>", unsafe_allow_html=True)
            st.markdown(f"<p style='color: #94a3b8; font-size: 0.95rem; margin-bottom: 24px;'>{_('opt_desc')}</p>", unsafe_allow_html=True)
            
            col_opt1, col_opt2 = st.columns([1, 2])
            with col_opt1:
                caixa_disponivel = st.number_input(_('avail_cash'), min_value=0.0, value=1000.0, step=100.0)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
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