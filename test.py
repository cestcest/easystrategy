# encoding: UTF-8

from datetime import date, timedelta, datetime
import pandas as pd
import tushare as ts
import timeit as ti
import easytrader

'''
code,代码
name,名称
industry,所属行业
area,地区
pe,市盈率
outstanding,流通股本(亿)
totals,总股本(亿)
totalAssets,总资产(万)
liquidAssets,流动资产
fixedAssets,固定资产
reserved,公积金
reservedPerShare,每股公积金
esp,每股收益
bvps,每股净资
pb,市净率
timeToMarket,上市日期
undp,未分利润
perundp, 每股未分配
rev,收入同比(%)
profit,利润同比(%)
gpr,毛利率(%)
npr,净利润率(%)
holders,股东人数

返回值说明：
•code：代码
•name:名称
•changepercent:涨跌幅
•trade:现价
•open:开盘价
•high:最高价
•low:最低价
•settlement:昨日收盘价
•volume:成交量
•turnoverratio:换手率
•amount:成交量
•per:市盈率
•pb:市净率
•mktcap:总市值
•nmc:流通市值
'''

index2 = '000016'  # 上证50指数，表示二，大盘股
index8 = '399333'  # 中小板R指数，表示八，小盘股

# df = ts.get_realtime_quotes('162411')
today = date.today()
week4 = today - timedelta(days=90)
yesterday = today - timedelta(days=1)
lastday = today - timedelta(days=600)
print(yesterday, lastday)
filename = 'stockdata%s.xls' % today
# df = ts.get_k_data('000001', index=True, ktype='D', start=week4.strftime('%Y-%m-%d'), end=today.strftime('%Y-%m-%d'))
# print(df)
# stock_price = df['ask'][0]

# df = ts.get_k_data('000001', index=True, ktype='W')
# print(df, df.iloc[-1]['close'],df.iloc[-4]['close'])

# df2 = ts.get_k_data(index2, index=True, ktype='D')
# print(df2, df2.iloc[-1]['close'], df2.iloc[-20]['close'])

# df8 = ts.get_k_data(index8, index=True, ktype='D')
# print(df8, df8.iloc[-1]['close'], df8.iloc[-20]['close'])

'''
# 基本面数据
basic = ts.get_stock_basics()
# 行情和市值数据
hq = ts.get_today_all()

# 当前股价,如果停牌则设置当前价格为上一个交易日股价
# hq['trade'] = hq.apply(lambda x: x.settlement if x.trade == 0 else x.trade, axis=1)

# 分别选取流通股本,总股本,每股公积金,每股收益
basedata = basic[['esp', 'timeToMarket', 'profit']]

# 选取股票代码,名称,当前价格,总市值,流通市值
df = hq[['code', 'name', 'trade', 'mktcap']]
df = df[df['trade'] > 0]
df = df[df.code.map(lambda x: not x.startswith('300'))]
df = df[df.name.map(lambda x: 'ST' not in x)]
df = df[df.name.map(lambda x: 'N' not in x)]
df = df[df.name.map(lambda x: u'退市' not in x)]

hqdata = df
# 设置行情数据code为index列
hqdata = hqdata.set_index('code')

# 合并两个数据表
stocksdata = hqdata.merge(basedata, left_index=True, right_index=True)

# 将总市值和流通市值换成亿元单位
stocksdata['mktcap'] /= 10000


stocksdata.to_excel(filename)
'''

df = pd.read_excel(filename, encoding='gbk', converters={'code': str, 'timeToMarket': int})

# df['timeToMarket'] = str.format(df['timeToMarket'],'%Y%M%D')
df = df[df['esp'] > 0]
vaildday = int(week4.strftime('%Y%m%d'))
df = df[df['timeToMarket'] < vaildday]
df = df.sort_values(by='mktcap', ascending=True)
# stocks = df.set_index('mktcap')
stocks = df[0:25]
stock_list = list(stocks['code'])
print(stock_list)

dst_stocks = {}
for stock in stock_list:
    # his = ts.get_k_data(stock, ktype='D', start='2014-12-06', end='2016-12-06')
    his = ts.get_k_data(stock, ktype='D')
    his15 = his.tail(15)
    his130 = his.tail(130)
    low_price_130 = his130.low.min()
    high_price_130 = his130.high.max()

    avg_15 = his15.close.astype('float64').mean()
    # print(avg_15)
    cur_price = his15.iloc[-1]['close']

    score = (cur_price - low_price_130) + (cur_price - high_price_130) + (cur_price - avg_15)
    dst_stocks[stock] = score

df = pd.DataFrame.from_dict(dst_stocks, orient='index')
df.columns = ['score']
df = df.sort_values(by='score', ascending=True)
stocks = df.index
print(df, stocks)

# print(his.low.min(), his.high.max(), his.iloc[-1]['close'])

# print(df, df.iloc[-1]['close'], df.iloc[-130]['close'])

# yjb = easytrader.use('yjb')
# yjb.prepare('yjb_ylj.json')
# ret = yjb.sell('162411', price=stock_price, amount=100)
# ret = yjb.sell('162411', price=stock_price, amount=100)
# print('ret', ret)

# 股票评分
def rank_stocks(data, stock_list):
    dst_stocks = {}
    for stock in stock_list:
        df = ts.get_k_data(stock, ktype='D', start=lasyday130.strftime('%Y-%m-%d'),
                           end=today.strftime('%Y-%m-%d'))
        h = attribute_history(stock, 130, unit='1d', fields=('close', 'high', 'low'), skip_paused=True)
        low_price_130 = h.low.min()
        high_price_130 = h.high.max()

        avg_15 = data[stock].mavg(15, field='close')
        cur_price = data[stock].close

        score = (cur_price - low_price_130) + (cur_price - high_price_130) + (cur_price - avg_15)
        dst_stocks[stock] = score

    df = pd.DataFrame(dst_stocks.values(), index=dst_stocks.keys())
    df.columns = ['score']
    df = df.sort(columns='score', ascending=True)

    return df.index
