# 📈 AI-Powered Public Stocks Portfolio

Bem-vindo ao meu projeto de portfólio público! Este dashboard é uma aplicação de **Machine Learning em Produção (MLOps)** que cruza dados reais da minha carteira de investimentos com previsões diárias de uma Inteligência Artificial.

A aplicação está hospedada e rodando ao vivo no Streamlit Community Cloud: 
👉 **[Insira o seu link do Streamlit aqui]**

## 🎯 O Objetivo
Sair do ambiente de testes e construir uma arquitetura de dados *end-to-end*. O sistema coleta dados do mercado financeiro, gera previsões de compra/espera usando um modelo preditivo, armazena os resultados em nuvem e exibe tudo em uma interface interativa bilíngue (PT-BR / EN), com conversão cambial em tempo real.

## 🏗️ Arquitetura e Tecnologias

Este projeto foi construído usando tecnologias modernas de Engenharia de Dados e Ciência de Dados:

* **Ingestão de Dados:** `yfinance` (Yahoo Finance API) e API do Banco Central (Câmbio).
* **Armazenamento (Cloud):** `Supabase` (PostgreSQL com Connection Pooler).
* **Integração de Dados Pessoais:** `gspread` (Google Sheets API) para leitura segura da carteira atual.
* **Machine Learning:** `XGBoost` (Gradient Boosting) para classificação binária (COMPRAR / AGUARDAR) baseado em indicadores técnicos (RSI, Bandas de Bollinger).
* **Orquestração e CI/CD:** `GitHub Actions` (Pipeline rodando via `cron` todos os dias úteis às 18h).
* **Frontend:** `Streamlit` e `Plotly` para visualização interativa e gestão de estado (Tradução e Conversão de Moeda).

## 🚀 Principais Funcionalidades

- **Pipeline Automatizado:** Um robô no GitHub Actions acorda diariamente, puxa os dados de fechamento, roda a inferência no modelo `.pkl` e salva no banco de dados.
- **Smart Filters & Bilingual UI:** O usuário pode alternar a interface para Inglês. Ao fazer isso, o sistema consome a cotação atualizada do Dólar e recalcula todos os ativos (como WEGE3, PETR4, BBSE3) e KPIs de Real (R$) para Dólar ($).
- **Otimizador de Portfólio:** Uma aba dedicada que utiliza o nível de confiança (%) do modelo XGBoost para sugerir pesos de aporte dinâmicos, baseados no caixa disponível do usuário.

## 🛠️ Como rodar localmente

1. Clone o repositório:

   ```git clone [https://github.com/seu-usuario/public-stocks-portfolio.git](https://github.com/seu-usuario/public-stocks-portfolio.git)```

2.Instale as dependências:
    ```pip install -r requirements.txt```

3. Configure os Secrets: Crie uma pasta .streamlit com um arquivo secrets.toml contendo suas credenciais do GCP e a SUPABASE_URL.

4. Inicie o dashboard:
  ```streamlit run app.py```

Desenvolvido por Thiago Alves.
