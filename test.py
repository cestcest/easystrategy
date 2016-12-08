# encoding: UTF-8

from datetime import date, timedelta
import pandas as pd
import tushare as ts
import easytrader as et

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


def rank_stock(stockcode_list):    # 股票评分
    dst_stocks = {}
    for stock in stockcode_list:
        his = ts.get_k_data(stock, ktype='D')
        his15 = his.tail(15)
        his130 = his.tail(130)
        low_price_130 = his130.low.min()
        high_price_130 = his130.high.max()

        avg_15 = his15.close.astype('float64').mean()
        cur_price = his15.iloc[-1]['close']

        score = (cur_price - low_price_130) + (cur_price - high_price_130) + (cur_price - avg_15)
        dst_stocks[stock] = score

    df_stock = pd.DataFrame.from_dict(dst_stocks, orient='index')
    df_stock.columns = ['score']
    df_stock = df_stock.sort_values(by='score', ascending=True)

    return df_stock.index


def get_stock_data(filename):
    # 基本面数据
    basic = ts.get_stock_basics()
    # 行情和市值数据
    hq = ts.get_today_all()

    # 当前股价,如果停牌则设置当前价格为上一个交易日股价
    # hq['trade'] = hq.apply(lambda x: x.settlement if x.trade == 0 else x.trade, axis=1)

    # 分别选取流通股本,总股本,每股公积金,每股收益
    basedata = basic[['esp', 'timeToMarket', 'profit']]

    # 选取股票代码,名称,当前价格,总市值,流通市值
    hqdata = hq[['code', 'name', 'trade', 'mktcap', 'turnoverratio', 'changepercent']]
    hqdata = hqdata[hqdata['trade'] > 0]
    hqdata = hqdata[hqdata.code.map(lambda x: not x.startswith('300'))]
    hqdata = hqdata[hqdata.name.map(lambda x: 'ST' not in x)]
    hqdata = hqdata[hqdata.name.map(lambda x: 'N' not in x)]
    hqdata = hqdata[hqdata.name.map(lambda x: u'退市' not in x)]

    # 设置行情数据code为index列
    hqdata = hqdata.set_index('code')

    # 合并两个数据表
    stocksdata = hqdata.merge(basedata, left_index=True, right_index=True)

    # 将总市值和流通市值换成亿元单位
    stocksdata['mktcap'] /= 10000
    # 保存到excel文件
    stocksdata.to_excel(filename)


def select_stock(filename):
    today = date.today()
    week4 = today - timedelta(days=60)
    valid_day = int(week4.strftime('%Y%m%d'))
    df = pd.read_excel(filename, encoding='gbk', converters={'code': str, 'timeToMarket': int})
    df = df[df['esp'] > 0]


    df = df[df['timeToMarket'] < valid_day]
    df = df.sort_values(by='mktcap', ascending=True)
    stocks = df[0:25]
    stock_list = list(stocks['code'])

    return rank_stock(stock_list)


def stop_loss_index(index):
    his = ts.get_k_data(index, index=True, ktype='D')
    his160 = his.tail(160)
    print(his160)
    today_max = his160.high.max()
    today_min = his160.low.min() * 2.2
    close1 = his160.iloc[-1]['close']
    close4 = his160.iloc[-4]['close']
    close100 = his160.iloc[-100]['close']

    return today_max > today_min and close4 > close1 > close100


def get_index_four_week_chg(index):
    df_index = ts.get_k_data(index, index=True, ktype='W')
    index0 = df_index.iloc[-1]['close']
    index4 = df_index.iloc[-5]['close']

    if index4 != 0:
        return (index0/index4 - 1) * 100
    else:
        return 0

index2 = '000016'  # 上证50指数，表示二，大盘股
index8 = '399333'  # 中小板R指数，表示八，小盘股

today = date.today()
tomorrow = today + timedelta(days=1)
week4 = today - timedelta(days=60)
yesterday = today - timedelta(days=1)
lastday = today - timedelta(days=600)
print(tomorrow,today, yesterday, lastday)
filepath = 'stockdata%s.xls' % today

# df = ts.get_realtime_quotes('162411')

# df = ts.get_k_data('000001', index=True, ktype='D', start=week4.strftime('%Y-%m-%d'), end=today.strftime('%Y-%m-%d'))
# print(df)
# stock_price = df['ask'][0]

# print(stop_loss_index('000001'))
print(get_index_four_week_chg(index2))
print(get_index_four_week_chg(index8))
# df2 = ts.get_k_data(index2, index=True, ktype='W')
# print(df2, df2.iloc[-1]['close'], df2.iloc[-4]['close'])

# df8 = ts.get_k_data(index8, index=True, ktype='D')
# print(df8, df8.iloc[-1]['close'], df8.iloc[-20]['close'])
# get_stock_data(filepath)

# print(select_stock(filepath))

# print(his.low.min(), his.high.max(), his.iloc[-1]['close'])

# print(df, df.iloc[-1]['close'], df.iloc[-130]['close'])

# yjb = easytrader.use('yjb')
# yjb.prepare('yjb_ylj.json')
# ret = yjb.sell('162411', price=stock_price, amount=100)
# ret = yjb.sell('162411', price=stock_price, amount=100)
# print('ret', ret)


