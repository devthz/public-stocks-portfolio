import pandas as pd
import yfinance as yf
import sqlalchemy as sa
import numpy as np
import joblib
from datetime import datetime
import os
import warnings
warnings.filterwarnings('ignore')

print(f"--- Iniciando Pipeline Diário: {datetime.now().strftime('%Y-%m-%d')} ---")

# O GitHub vai injetar essa variável de ambiente de forma segura
DATABASE_URL = os.environ.get('SUPABASE_URL')
engine = sa.create_engine(DATABASE_URL)

# ---------------------------------------------------------
# FASE 1: INGESTÃO DIÁRIA (O que aconteceu hoje na bolsa?)
# ---------------------------------------------------------
tickers = ['PETR4.SA', 'BBSE3.SA', 'WEGE3.SA', 'ITUB4.SA', 'SANB11.SA', 'CMIG4.SA', '^BVSP', 'BRL=X']
print("Baixando fechamento de hoje no Yahoo Finance...")
dados = yf.download(tickers, period="1d") # Puxa apenas o dia atual

df_close = dados['Close'].reset_index().melt(id_vars="Date", var_name="ticker_id", value_name="preco_fechamento")
df_volume = dados['Volume'].reset_index().melt(id_vars="Date", var_name="ticker_id", value_name="volume")
df_hoje = pd.merge(df_close, df_volume, on=['Date', 'ticker_id']).dropna()
df_hoje = df_hoje.rename(columns={'Date': 'data_pregao'})

print("Salvando cotações de hoje no Supabase...")
df_hoje.to_sql('ml_ativos_cotacoes', engine, if_exists='append', index=False)

# ---------------------------------------------------------
# FASE 2: PREVISÃO (O que eu faço amanhã?)
# ---------------------------------------------------------
print("Carregando o modelo XGBoost...")
modelo = joblib.load('xgboost_calibrado_v2.pkl')

print("Puxando histórico recente para calcular RSI e Bollinger...")
# Puxamos os últimos 40 pregões para garantir que a média de 21 dias calcule certinho
df_bruto = pd.read_sql("SELECT data_pregao, ticker_id, preco_fechamento, volume FROM ml_ativos_cotacoes ORDER BY data_pregao DESC LIMIT 400", engine)
df_bruto['data_pregao'] = pd.to_datetime(df_bruto['data_pregao'])
df_bruto = df_bruto.sort_values(by=['ticker_id', 'data_pregao'])

# Cruzamento Macro
df_acoes = df_bruto[~df_bruto['ticker_id'].isin(['^BVSP', 'BRL=X'])].copy()
df_ibov = df_bruto[df_bruto['ticker_id'] == '^BVSP'][['data_pregao', 'preco_fechamento']].rename(columns={'preco_fechamento': 'fechamento_ibov'})
df_dolar = df_bruto[df_bruto['ticker_id'] == 'BRL=X'][['data_pregao', 'preco_fechamento']].rename(columns={'preco_fechamento': 'fechamento_dolar'})

df = pd.merge(df_acoes, df_ibov, on='data_pregao', how='left')
df = pd.merge(df, df_dolar, on='data_pregao', how='left')

# Calculando Features
df['Retorno_Acao'] = df.groupby('ticker_id')['preco_fechamento'].pct_change()
df['Retorno_Ibov'] = df.groupby('ticker_id')['fechamento_ibov'].pct_change()
df['Forca_Relativa_Ibov'] = df['Retorno_Acao'] - df['Retorno_Ibov']
df['Variacao_Dolar'] = df.groupby('ticker_id')['fechamento_dolar'].pct_change()
df['Variacao_Volume'] = df.groupby('ticker_id')['volume'].pct_change()

def calcular_rsi(serie, periodo=14):
    delta = serie.diff()
    ganho = delta.where(delta > 0, 0)
    perda = -delta.where(delta < 0, 0)
    rs = ganho.rolling(window=periodo).mean() / perda.rolling(window=periodo).mean().replace(0, 0.001)
    return 100 - (100 / (1 + rs))

df['RSI_14'] = df.groupby('ticker_id')['preco_fechamento'].transform(calcular_rsi)
df['BB_SMA_20'] = df.groupby('ticker_id')['preco_fechamento'].transform(lambda x: x.rolling(window=20).mean())
df['BB_STD_20'] = df.groupby('ticker_id')['preco_fechamento'].transform(lambda x: x.rolling(window=20).std())
df['Dist_Banda_Inf'] = (df['preco_fechamento'] - (df['BB_SMA_20'] - (2 * df['BB_STD_20']))) / df['preco_fechamento']

# Isolar apenas a última linha (que acabamos de inserir) para prever
df_prever = df.groupby('ticker_id').tail(1).copy().dropna()
features = ['Retorno_Acao', 'Forca_Relativa_Ibov', 'Variacao_Dolar', 'Variacao_Volume', 'RSI_14', 'Dist_Banda_Inf']

print("Gerando recomendações e salvando...")
probabilidades = modelo.predict_proba(df_prever[features])[:, 1]

df_previsoes = pd.DataFrame({
    'data_previsao': datetime.now().date(),
    'ticker_id': df_prever['ticker_id'],
    'probabilidade_compra': probabilidades,
    'recomendacao': np.where(probabilidades > 0.65, 'COMPRAR', 'AGUARDAR'),
    'versao_modelo': 'XGBoost_v2_Calibrado'
})

df_previsoes.to_sql('ml_ativos_previsoes', engine, if_exists='append', index=False)
print("🚀 Pipeline finalizado com sucesso! Power BI atualizado indiretamente.")