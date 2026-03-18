import pandas as pd
import sqlalchemy as sa
import numpy as np
import os

from xgboost import XGBClassifier
from sklearn.metrics import classification_report

import numpy as np

import joblib

# 1. Conectando na sua Nuvem
DATABASE_URL = os.environ.get('SUPABASE_URL')
engine = sa.create_engine(DATABASE_URL)

print("Puxando dados da nuvem...")
# Lemos a tabela inteira do Supabase
query = "SELECT data_pregao, ticker_id, preco_fechamento, volume FROM ml_ativos_cotacoes"
df_bruto = pd.read_sql(query, engine)

# Convertendo a data para o formato correto do Pandas e ordenando
df_bruto['data_pregao'] = pd.to_datetime(df_bruto['data_pregao'])
df_bruto = df_bruto.sort_values(by=['ticker_id', 'data_pregao'])

# 2. Separando Ações dos Indicadores Macro
print("Criando cruzamento macroeconômico...")
df_acoes = df_bruto[~df_bruto['ticker_id'].isin(['^BVSP', 'BRL=X'])].copy()
df_ibov = df_bruto[df_bruto['ticker_id'] == '^BVSP'][['data_pregao', 'preco_fechamento']].rename(columns={'preco_fechamento': 'fechamento_ibov'})
df_dolar = df_bruto[df_bruto['ticker_id'] == 'BRL=X'][['data_pregao', 'preco_fechamento']].rename(columns={'preco_fechamento': 'fechamento_dolar'})

# 3. Juntando tudo: Cada linha da ação agora sabe quanto estava o Ibov e o Dólar naquele dia
df = pd.merge(df_acoes, df_ibov, on='data_pregao', how='left')
df = pd.merge(df, df_dolar, on='data_pregao', how='left')

# 4. Feature Engineering: Calculando o "Humor do Mercado"
# Retorno diário da Ação
df['Retorno_Acao'] = df.groupby('ticker_id')['preco_fechamento'].pct_change()

# Retorno diário do Ibovespa
df['Retorno_Ibov'] = df.groupby('ticker_id')['fechamento_ibov'].pct_change()

# A FEATURE MÁGICA: Força Relativa ao Ibovespa
# Se a ação subiu 2% e o Ibov caiu 1%, a força é +3% (Ação está ignorando o pânico e subindo)
df['Forca_Relativa_Ibov'] = df['Retorno_Acao'] - df['Retorno_Ibov']

# 5. Volatilidade e Volume
df['Variacao_Dolar'] = df.groupby('ticker_id')['fechamento_dolar'].pct_change()
df['Variacao_Volume'] = df.groupby('ticker_id')['volume'].pct_change()

# Limpando os nulos gerados pelos cálculos
df_limpo = df.dropna().copy()

print("\n--- Amostra das Novas Features (Exemplo WEGE3) ---")
exemplo_weg = df_limpo[df_limpo['ticker_id'] == 'WEGE3.SA']
print(exemplo_weg[['data_pregao', 'preco_fechamento', 'Retorno_Acao', 'Retorno_Ibov', 'Forca_Relativa_Ibov', 'Variacao_Dolar']].tail())


print("\nAdicionando os Indicadores Técnicos Clássicos...")
# Recalculando o RSI e Bollinger para a nossa nova base da nuvem
def calcular_rsi(serie, periodo=14):
    delta = serie.diff()
    ganho = delta.where(delta > 0, 0)
    perda = -delta.where(delta < 0, 0)
    rs = ganho.rolling(window=periodo).mean() / perda.rolling(window=periodo).mean().replace(0, 0.001)
    return 100 - (100 / (1 + rs))

df_limpo['RSI_14'] = df_limpo.groupby('ticker_id')['preco_fechamento'].transform(calcular_rsi)
df_limpo['BB_SMA_20'] = df_limpo.groupby('ticker_id')['preco_fechamento'].transform(lambda x: x.rolling(window=20).mean())
df_limpo['BB_STD_20'] = df_limpo.groupby('ticker_id')['preco_fechamento'].transform(lambda x: x.rolling(window=20).std())
df_limpo['Dist_Banda_Inf'] = (df_limpo['preco_fechamento'] - (df_limpo['BB_SMA_20'] - (2 * df_limpo['BB_STD_20']))) / df_limpo['preco_fechamento']

print("Criando o Gabarito (Alvo de 5 dias)...")
# O preço daqui a 5 dias
df_limpo['Preco_Futuro_5d'] = df_limpo.groupby('ticker_id')['preco_fechamento'].shift(-5)
# A nossa regra: 1 se subir, 0 se cair
df_limpo['Alvo_Compra'] = np.where(df_limpo['Preco_Futuro_5d'] > df_limpo['preco_fechamento'], 1, 0)

# Limpeza final dos nulos gerados pelas janelas de tempo e pelo shift do futuro
df_modelagem = df_limpo.dropna().copy()

print("Separando Treino e Teste (Ordem Cronológica)...")
# O nosso "Super" conjunto de Features
features = ['Retorno_Acao', 'Forca_Relativa_Ibov', 'Variacao_Dolar', 'Variacao_Volume', 'RSI_14', 'Dist_Banda_Inf']

X = df_modelagem[features]
y = df_modelagem['Alvo_Compra']

# 80% passado para treino, 20% futuro recente para teste
tamanho = int(len(df_modelagem) * 0.8)
X_treino, X_teste = X.iloc[:tamanho], X.iloc[tamanho:]
y_treino, y_teste = y.iloc[:tamanho], y.iloc[tamanho:]

print("Treinando o XGBoost...")
# Criando o modelo XGBoost. 
# learning_rate é a "cautela" de cada estagiário ao corrigir o erro do anterior
modelo_xgb = XGBClassifier(n_estimators=100, learning_rate=0.1, random_state=42)
modelo_xgb.fit(X_treino, y_treino)

print("Realizando a Prova Final...")
previsoes_xgb = modelo_xgb.predict(X_teste)

print("\n--- Resultado da Prova Final (XGBoost v2) ---")
print(classification_report(y_teste, previsoes_xgb))



print("\nAjustando a Régua de Exigência (Threshold de 65%)...")

# 1. Em vez de pedir a resposta final (0 ou 1), pedimos a probabilidade matemática.
# O [:, 1] no final serve para pegar apenas a coluna que mostra a chance de ser 1 (Compra).
probabilidades = modelo_xgb.predict_proba(X_teste)[:, 1]

# 2. Criamos a nossa própria regra de ouro: Só é 1 se a certeza for MAIOR que 65% (0.65)
previsoes_calibradas = np.where(probabilidades > 0.70, 1, 0)

# 3. Imprimimos o novo boletim de notas com a nossa regra aplicada
print("\n--- Resultado da Prova Final (XGBoost Calibrado > 70%) ---")
print(classification_report(y_teste, previsoes_calibradas))


joblib.dump(modelo_xgb, 'xgboost_calibrado_v2.pkl')