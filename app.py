from backtesting import tools
import streamlit as st
import datetime

st.title("Python para finanzas")
st.markdown("> Mini prueba de backtesting.")

RSI_Q = 15
FAST = 20
SLOW = 60
RSI_BUY = 75
RSI_SELL= 35
INIT_DATE = datetime.date(2000, 1, 1)
with st.sidebar:
    st.write("Parametros del backtest")
    RSI_Q = st.number_input("Cantidad de velas para RSI ", value=RSI_Q, step=1)
    FAST = st.number_input("Media movil rapida ", value=FAST, step=1)
    SLOW = st.number_input("Media movil lenta ", value=SLOW, step=1)
    RSI_BUY = st.number_input("Comprar si RSI >= a ", value=RSI_BUY, step=1)
    RSI_SELL = st.number_input("Vender si RSI <= a ", value=RSI_SELL, step=1)
    INIT_DATE = st.date_input("Fecha de inicio para backtest", value = INIT_DATE)

input_user = st.chat_input("Ingresa aca elticker que quieras: ")


if input_user:

    text = input_user.upper().replace("$","")
    input_list = text.split()
    ticker = input_list[0]
    with st.spinner(f"Aguanta que estoy descargando la data de {ticker}"):
        data = tools.getData(ticker, start=INIT_DATE.isoformat()[:10])
    
    df = tools.addSignal(data, fast=FAST, slow=SLOW, rsi_q=RSI_Q, buy_cr=0, buy_rsi=RSI_BUY, sell_cr=0, sell_rsi=RSI_SELL).dropna()
    actions = tools.getActions(df, tipo='long')
    trades = tools.getTrades(actions,  tipo='long')
    r, metricas = tools.resumen(trades)
    final = tools.eventDrivenLong(df)

    tabs_list = ["Resumen general","Indicadores","Descargar actions","Descargar trades","Ver payoff final del backtest"]
    tab_summary, tab2, tab3, tab4, tab5 = st.tabs(tabs_list)

    with tab_summary:
        st.subheader("Resumen del backtest")
        st.write(r)

    with tab2:
        st.subheader("Indicadores de la estrategia")
        st.download_button("Download indicadores", file_name=f'{ticker}_indicadores.csv', data=df.to_csv(), mime='text/csv')
        st.write(df)

    with tab3:
        st.subheader("Descargar disparadores")
        st.download_button("Descargar disparadores", file_name=f'{ticker}_disparadores.csv', data=actions.to_csv(), mime='text/csv')
        st.write(actions)

    with tab4:
        st.subheader("trades de la estrategia")
        st.download_button("Download trades", file_name=f'{ticker}_trades.csv', data=trades.to_csv(), mime='text/csv')
        st.write(trades)

    with tab5:
        st.subheader("Descargar payoff")
        st.download_button("Download payoff", file_name=f'{ticker}_payoff.csv', data=final.to_csv(), mime='text/csv')
        st.write(final)


    returns = final.loc[: , ['pct_change','strategy']]
    returns.columns = ["Buy & Hold", "Strategy"]
    yoy = returns.add(1).groupby(returns.index.year).prod().sub(1)

    st.subheader("Charts")
    st.write("Retornos anuales")
    st.bar_chart(yoy, stack=False)

    ALPHA = 0.05
    st.write(f"Value at Risk con alpha de {ALPHA:.2%}")
    VaR = returns.groupby(returns.index.year).quantile(ALPHA)
    st.bar_chart(VaR, stack=False)

    st.write("Sharpe ratio")
    sharpe = yoy / returns.groupby(returns.index.year).std()
    st.bar_chart(sharpe, stack=False)