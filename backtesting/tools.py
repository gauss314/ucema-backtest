import yfinance as yf
import pandas as pd
import numpy as np
import datetime

def getData(ticker: str, start: str = None, end:str = None, src:str = 'yahoo') -> pd.DataFrame:
    """
    Parameters:
        ticker (str): Es el ticker a descargar
        
    Return:
        Devuelve un dataframe OHLCV con las columnas 'open', 'high', 'low', 'close', 'vol_n', 'vol_mln', 'pct_change'
        
    """
    if src == 'yahoo':
        data = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
        data.columns = data.columns.droplevel(1)
        data['vol_mln'] = data.Volume * data.Close / 10**6
        data['chg'] = data.Close.pct_change()
        data.columns = ['open', 'high', 'low', 'close', 'vol_n', 'vol_mln', 'pct_change']
                
    else:
        data = pd.DataFrame()
        
    
    return data

def addSignal(data: pd.DataFrame, 
              fast: int = 5, # La cantidad de valores para la media movil rapida
              slow:int = 20,  # La cantidad de valores para la media movil lenta
              rsi_q: int = 14, # La cantidad de valores para el RSI
              buy_cr:float =0, # El % <= de compra para el cruce de medias
              buy_rsi:float = 60, # El valor >= de compra para el RSI
              sell_cr: float = 0, # El % <= de venta para el cruce medias
              sell_rsi: float = 35 # El Valor <= RSI para venta
             ) -> pd.DataFrame:

        
    data['Cruce'] = (data.close.rolling(fast).mean() /
                     data.close.rolling(slow).mean() - 1) * 100

    dif = data['close'].diff()
    win = pd.DataFrame(np.where(dif > 0, dif, 0))
    loss = pd.DataFrame(np.where(dif < 0, abs(dif), 0))
    ema_win = win.ewm(alpha=1 / rsi_q).mean()
    ema_loss = loss.ewm(alpha=1 / rsi_q).mean()
    rs = ema_win / ema_loss
    rsi = 100 - (100 / (1 + rs))
    rsi.index = data.index
    data['rsi'] = rsi

    data['signal'] = 'Sin Señal'
    comprar = (data.Cruce >= buy_cr) & (data.rsi >= buy_rsi)
    data.loc[comprar, 'signal'] = 'Compra'

    vender = (data.Cruce <= sell_cr) & (data.rsi <= sell_rsi) 
    data.loc[vender, 'signal'] = 'Venta'

    return data


def getActions(data: pd.DataFrame, tipo:str = 'long') -> pd.DataFrame:
    """
    Estoy asumiendo que el dataframe data tiene una columna que se llama Signal que tiene Compra, Venta o Sin Señal
    """
    actions = data.loc[data.signal != 'Sin Señal'].copy()
    actions['signal'] = np.where(actions.signal != actions.signal.shift(), actions.signal,'Sin Señal')
    actions = actions.loc[actions.signal != 'Sin Señal'].copy()

    # Este if es para que empiece comprado y termine vendiendo si es Long  o viceversa si es short
    if len(actions) > 2:
        if tipo == 'long':
            if actions.iloc[0].loc['signal'] == 'Venta':
                actions = actions.iloc[1:]

            if actions.iloc[-1].loc['signal'] == 'Compra':
                actions = actions.iloc[:-1]

        elif tipo == 'short':
            if actions.iloc[0].loc['signal'] == 'Compra':
                actions = actions.iloc[1:]

            if actions.iloc[-1].loc['signal'] == 'Venta':
                actions = actions.iloc[:-1]
                
        else:
            print(f'Chouzeadas no permitidas: Solo tipo long o short, ingresaste {tipo}')
            actions = None

    return actions


def getTrades(actions, tipo='long', CT=0):
    """
    El CT es una cte con el costo transaccional que incluye:
        - comision de la compra  0.03
        - comision de la venta  0.03 (si es ...)
        - comision del prestamo si es short
        - derechos de mercado en compra
        - derechos de mercado en venta 
        - spread bid/ask
    """
    
    try:
        pares = actions.iloc[::2].loc[:,['close']].reset_index()
        impares = actions.iloc[1::2].loc[:,['close']].reset_index()
        trades = pd.concat([pares, impares], axis=1)
        
        if tipo=='long':
            trades.columns = ['fecha_compra','px_compra','fecha_venta','px_venta']
            trades['rendimiento'] = trades.px_venta / trades.px_compra - 1
            #trades['rendimiento'] -= CT
            
            trades['days'] = (trades.fecha_venta - trades.fecha_compra).dt.days

        elif tipo=='short':
            trades.columns = ['fecha_venta','px_venta', 'fecha_compra','px_compra']
            trades['rendimiento'] = 1- trades.px_compra / trades.px_venta
            trades['days'] = (trades.fecha_compra - trades.fecha_venta).dt.days

        else:
            trades = []
            print(f'Chouzeadas no permitidas: Solo tipo long o short, ingresaste {tipo}')

        if len(trades):
            trades['resultado'] = np.where(trades['rendimiento'] > 0 , 'Ganador' , 'Perdedor')
            trades['rendimientoAcumulado'] = (trades['rendimiento']+1).cumprod()

    except:
        print('Fallo en el ingreso de tabla de acciones')
        trades = []
        
    return trades


def resumen(trades):
    
    if len(trades):
        resultado = float((trades.iloc[-1:].rendimientoAcumulado-1).iloc[0])
        agg_cantidades = trades.groupby('resultado').size()
        agg_rendimientos = trades.groupby('resultado').mean()['rendimiento']
        agg_tiempos = trades.groupby('resultado').days.sum()
        agg_tiempos_medio = trades.groupby('resultado').days.mean()

        r = pd.concat([agg_cantidades,agg_rendimientos, agg_tiempos, agg_tiempos_medio ], axis=1)
        r.columns = ['Cantidad', 'Rendimiento x Trade', 'Dias Total', 'Dias x Trade']
        resumen = r.T
        
        try:
            t_win = r['Dias Total']['Ganador'] 
        except:
            t_win = 0
            
        try:
            t_loss = r['Dias Total']['Perdedor']
        except:
            t_loss = 0

        t = t_win + t_loss
        tea = (resultado +1)**(365/t)-1 if t > 0 else 0
        
        metricas = {'rendimiento':round(resultado,4), 'dias_in':round(t,4), 'TEA':round(tea,4)}
    else:
        resumen = pd.DataFrame()
        metricas = {'rendimiento':0, 'dias_in':0, 'TEA':0}
        
    return resumen, metricas



def eventDrivenLong(df):
    '''
    El dataframe que le pasas como argumento tiene que tener al menos las columnas:
        - signal: Compra o Venta el dia que da señal al precio de cierre 
        - pct_change: La variacion porcentual de los precios de cierre cada dia
        
    La funcion devuelve un df igual al pasado como argumento pero agregando la columna <strategy> 
        Dicha columna tiene 0 o el valor de pct_change
        Para saber si un dia se está comprado o no, se toma la señal del dia anterior (precios de cierre)
    '''
    signals = df['signal'].tolist()
    pct_changes = df['pct_change'].tolist()

    total = len(signals)
    i = 1
    results = [0]
    
    while i < total:

        if signals[i-1] == 'Compra' :

            j = i
            while  j < total:
                results.append(pct_changes[j])         
                j +=1

                if signals[j-1]=='Venta'  :
                    i = j
                    break
                if j == total:
                    i = j
                    print('Ojo que queda compra abierta..')
                    break
        else:
            results.append(0)
            i +=1

    result = pd.concat ([df,pd.Series(data=results, index=df.index)], axis=1)
    result.columns.values[-1] = "strategy"
    return result




