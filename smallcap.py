'''
非创业板盈利小市值二八轮动止损
'''
from MailSenderHTML import MailSenderHTML
import helpers
from api import *
from cli import *
from httpserver import *


def initialize(context):
    # copy('yjb_verify_code.jar')
    g.trade_stat = tradestat.trade_stat()
    set_params(context)  # 1设置策参数
    set_variables(context)  # 2设置中间变量
    set_backtest(context)  # 3设置回测条件
    log.info("开始回测,%d天%d只", g.period, g.buy_stock_count)


# 1 设置参数
def set_params(context):
    set_benchmark('000300.XSHG')  # 设置对照基准收益
    g.index = '000001.XSHG'  # 上证指数
    g.index2 = '000016.XSHG'  # 上证50指数，表示二，大盘股
    g.index8 = '399333.XSHE'  # 中小板R指数，表示八，小盘股


# 2 设置中间变量
def set_variables(context):
    g.period = 3  # 调仓频率，单位：日
    g.buy_stock_count = 3  # 买入股票数量
    g.shortlist_count = 100  # 备选股票数量
    g.rank_stock_count = 25  # 评分股票数量
    g.max_buy_cash = 5000000  # 最大单笔买入金额
    g.day_count = 0  # 调仓日计数器，单位：日
    g.message = ""  # 微信发送信息
    g.is_real_trade = True  # 是否进行实盘交易
    g.is_yjb_trade = True  # 是否进行佣金宝交易
    g.index_stoploss = False  # 初始化大盘止损
    g.portfolio = 1.00  # 仓位100%
    g.max_capital = context.portfolio.portfolio_value


# 3 设置回测条件
def set_backtest(context):
    set_slippage(PriceRelatedSlippage(0.003))
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, close_commission=0.0003,
                             close_today_commission=0, min_commission=5), type='stock')
    set_option('use_real_price', True)  # 用真实价格交易
    set_option('order_volume_ratio', 0.05)  # 成交量不超过总成交量的十分之一
    log.set_level('order', 'error')


'''
=================================================
每天开盘前
=================================================
'''


# 每天开盘前要做的事情
def before_trading_start(context):
    g.index_stoploss = False
    g.is_yjb_trade = True
    g.message = ""
    try:
        TradeConfig = helpers.file2dict('TradeConfig.txt')
        g.period = int(TradeConfig['period'])
        g.buy_stock_count = int(TradeConfig['buy_stock_count'])
        g.is_real_trade = bool(TradeConfig['real_trade'])
        g.portfolio = float(TradeConfig['portfolio'])
        # copy('yjb_verify_code.jar')
    except:
        pass


'''
=================================================
每天收盘后
=================================================
'''


# 每天收盘后要做的事情
def after_trading_end(context):
    protfolio_details(context)


# 持仓明细
def protfolio_details(context):
    message = ""
    g.trade_stat.report(context)
    inout_cash = context.portfolio.inout_cash
    curr_capital = context.portfolio.total_value
    returns = 1 + context.portfolio.returns
    if curr_capital > g.max_capital:
        g.max_capital = curr_capital
        # rise_capital = (curr_capital / g.max_capital - 1) * 100

    position = context.portfolio.positions
    curr_data = get_current_data()

    stock_info = ""
    for stock in position.keys():
        stock_name = curr_data[stock].name
        stock_code = position[stock].security[0:6]
        stock_price = position[stock].avg_cost
        stock_amount = position[stock].total_amount
        stock_value = position[stock].value
        stock_info = stock_info + "%s[%s]，成本：%.2f元 数量：%d股 价值：%.2f元 \n" % (
        stock_name, stock_code, stock_price, stock_amount, stock_value)
    if stock_info == "":
        stock_info = "无"
    message = "今日持仓：%d只\n%s\n初始投入：%.2f元 当前资产:%.2f元 最高资产：%.2f元 净值：%.4f \n" % (
    len(position), stock_info, inout_cash, curr_capital, g.max_capital, returns)
    sendmail(context, "今日持仓，净值：%.4f。" % returns, message.replace("\n", "<br>"))
    log.info(message)


'''
=================================================
每日交易时
=================================================
'''


def handle_data(context, data):
    if not g.index_stoploss and stop_loss_index(context):
        message = "清仓，%s指数前160日内最高价超过最低价2.2倍" % g.index
        log.error(message)
        clear_all_positions(context)
        sendmail(context, "清仓！", message)
        g.index_stoploss = True
        return

    if not g.index_stoploss:
        # 14:48 执行交易
        if context.current_dt.hour == 14 and context.current_dt.minute == 48:
            do_trade(context, data)


def stop_loss_index(context):
    h = attribute_history(g.index, 160, unit='1d', fields=('close', 'high', 'low'), skip_paused=True)
    return h.high.max() > h.low.min() * 2.2 and h['close'][-1] < h['close'][-4] * 1 and h['close'][-1] > h['close'][
        -100]


# 获取信号
def get_signal(context):
    signal = None
    message = "无操作。"
    Index2chg = get_index_chg(g.index2)  # 二指数前20日变动
    Index8chg = get_index_chg(g.index8)  # 八指数前20日变动

    if Index2chg <= 0 and Index8chg <= 0:
        message = "大盘股指数%.3f%%和小盘股指数%.3f%%的20日涨幅均小于0" % (Index2chg * 100, Index8chg * 100)
        signal = 'SELLALL'
    elif Index2chg > 0.01:
        message = "大盘股指数的20日涨幅%.3f%%大于1%%" % (Index2chg * 100)
        signal = 'BUY2'
    elif Index8chg > 0.01:
        message = "小盘股指数的20日涨幅%.3f%%大于1%%" % (Index8chg * 100)
        signal = 'BUY8'

    log.info(message)
    return signal


def do_trade(context, data):
    # 前20日两指数涨幅均小于0，卖出所有持仓股票
    # 前20日若有一个指数涨幅大于0，买入靠前的小市值股票
    buy_flag = False
    signal = get_signal(context)
    message = '第%s日轮动：' % g.day_count
    if signal == 'SELLALL':
        if clear_all_positions(context):
            message = message + '清仓!\n'
    else:
        if signal == 'BUY2':
            buy_flag = True
            message = message + '大盘股行情。\n'
        elif signal == 'BUY8':
            buy_flag = True
            message = message + '小盘股行情。\n'

        if buy_flag:
            if g.day_count % g.period == 0:
                buy_stocks = pick_stocks(context, data)
                rebalance_positions(context, buy_stocks)
            g.day_count += 1

    if g.message == "":
        message = message + "实盘不操作！"
    else:
        message = message + "实盘操作：\n" + g.message
    sendmail(context, message, message.replace("\n", "<br>"))
    # log.info(message)


# 选取指定数目的小市值股票，再进行过滤，最终挑选指定可买数目的股票
def pick_stocks(context, data):
    q = query(
        valuation.code,
    ).filter(
        indicator.eps > 0,
        valuation.code.notlike('300%')
    ).order_by(valuation.market_cap.asc()
               ).limit(g.shortlist_count)
    df = get_fundamentals(q)

    stock_list = list(df['code'])

    if is_sim_trade(context):
        stock_list = filter_blacklist_stock(stock_list)

    stock_list = filter_stock(stock_list)
    stock_list = filter_limitup_stock(context, stock_list)
    stock_list = filter_limitdown_stock(context, stock_list)

    if len(stock_list) > g.rank_stock_count:
        stock_list = stock_list[:g.rank_stock_count]

    if len(stock_list) > 0:
        stock_list = rank_stocks(data, stock_list)

    # 选取指定可买数目的股票
    if len(stock_list) > g.buy_stock_count:
        stock_list = stock_list[:g.buy_stock_count]
    return stock_list


# 股票评分
def rank_stocks(data, stock_list):
    dst_stocks = {}
    for stock in stock_list:
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
    # log.info(df[0:10])
    return df.index


def copy(path):
    c = read_file(path)
    with open(path, 'wb') as f:
        f.write(c)


''' 获取佣金宝交易功能 '''


def get_yjb(context):
    yjb = None
    if g.is_real_trade and is_sim_trade(context):
        try:
            yjb = use('yjb')
            yjb.prepare('yjb_ylj.json')
            g.is_yjb_trade = True
        except Exception, e:
            g.is_yjb_trade = False
            sendmail(context, "佣金宝登录出现问题,请马上手动接管交易！")
            log.error("佣金宝登录出现问题：%s" % (e.message))
    return yjb


''' 根据待买股票创建或调整仓位 '''


def rebalance_positions(context, buy_stocks):
    # yjb = get_yjb(context)
    yjb = None
    sell_all_problem_stock(context, yjb)
    sell_positions(context, buy_stocks, yjb)
    buy_positions(context, buy_stocks, yjb)


''' 卖出所有问题持仓 '''


def sell_all_problem_stock(context, yjb):
    position = context.portfolio.positions
    curr_data = get_current_data()

    for stock in position.keys():
        stock_name = curr_data[stock].name
        stock_amount = position[stock].sellable_amount
        if stock_amount > 0 and not curr_data[stock].paused and (
                    curr_data[stock].is_st or 'ST' in stock_name or '*' in stock_name or '退' in stock_name):
            stock_price = position[stock].price
            order_amount(context, yjb, stock_name, stock, stock_price, 0 - stock_amount)
            message = "卖出问题股票：%s[%s]：%.2f元 %s股" % (stock_name, stock, stock_price, 0 - stock_amount)
            sendmail(context, "卖出问题股票", message)
            log.error(message)


''' 卖出股票仓位 '''


def sell_positions(context, buy_stocks, yjb):
    position = context.portfolio.positions
    curr_data = get_current_data()

    for stock in position.keys():
        stock_amount = position[stock].sellable_amount
        if stock not in buy_stocks and stock_amount > 0 and not curr_data[stock].paused:
            stock_name = curr_data[stock].name
            stock_price = position[stock].price
            order_amount(context, yjb, stock_name, stock, stock_price, 0 - stock_amount)


''' 买入股票仓位 '''


def buy_positions(context, buy_stocks, yjb):
    # 按股票数量分仓,根据可用金额平均分配购买
    position = context.portfolio.positions
    curr_data = get_current_data()
    buy_stock_count = g.buy_stock_count - len(position)

    if buy_stock_count > 0:
        buy_cash = context.portfolio.cash / buy_stock_count
        if buy_cash > g.max_buy_cash:
            buy_cash = g.max_buy_cash
        i = 0
        for stock in buy_stocks:
            if position[stock].total_amount == 0 and not curr_data[stock].paused:
                i += 1
                stock_price = get_close_price(stock, 1, '1m')
                if stock_price > 0:
                    stock_amount = int(math.floor(buy_cash / stock_price / 100.0) * 100)
                    stock_name = curr_data[stock].name
                    order_amount(context, yjb, stock_name, stock, stock_price, stock_amount)
                if i >= buy_stock_count: break


''' 卖出所有持仓 '''


def clear_all_positions(context):
    position = context.portfolio.positions
    curr_data = get_current_data()
    if len(position) > 0:
        log.info("--------------清仓--------------")
        g.day_count = 0
        # yjb = get_yjb(context)
        yjb = None
        for stock in position.keys():
            stock_amount = position[stock].sellable_amount
            if stock_amount > 0 and not curr_data[stock].paused:
                stock_name = curr_data[stock].name
                stock_price = position[stock].price
                order_amount(context, yjb, stock_name, stock, stock_price, 0 - stock_amount)
        return True
    else:
        return False


def is_sim_trade(context):
    # 判断是否模拟盘：
    if context.run_params.type == 'sim_trade':
        return True
    else:
        return False


''' 按交易数量下单 '''


def order_amount(context, yjb, name, stock, price, amount):
    if amount > 0:
        curr_price = price * 1.003
        message = "买入%s[%s]：%.2f元 %s股" % (name, stock[:6], curr_price, amount)
    else:
        curr_price = price * 0.997
        message = "卖出%s[%s]：%.2f元 %s股" % (name, stock[:6], curr_price, amount)
    order(stock, amount)  # 市价单
    # order(stock, amount, LimitOrderStyle(curr_price)) #限价单
    g.message += message + "\n"


''' 过滤黑名单 名单可自行修改'''


def filter_blacklist_stock(stock_list):
    black_list = blacklist.get_blacklist()
    return [stock for stock in stock_list if stock not in black_list]


def filter_stock(stock_list):
    current_data = get_current_data()
    return [stock for stock in stock_list
            if not current_data[stock].paused
            and not current_data[stock].is_st
            and 'ST' not in current_data[stock].name
            and '*' not in current_data[stock].name
            and '退' not in current_data[stock].name]


# 过滤涨停的股票
def filter_limitup_stock(context, stock_list):
    last_prices = history(1, unit='1m', field='close', security_list=stock_list)
    current_data = get_current_data()

    # 已存在于持仓的股票即使涨停也不过滤，避免此股票再次可买，但因被过滤而导致选择别的股票
    return [stock for stock in stock_list if stock in context.portfolio.positions.keys()
            or last_prices[stock][-1] < current_data[stock].high_limit]


# 过滤跌停的股票
def filter_limitdown_stock(context, stock_list):
    last_prices = history(1, unit='1m', field='close', security_list=stock_list)
    current_data = get_current_data()

    return [stock for stock in stock_list if stock in context.portfolio.positions.keys()
            or last_prices[stock][-1] > current_data[stock].low_limit]


# 获取股票n日以来涨跌幅，根据当前价计算
# n 默认20日
def get_index_chg(security, n=20):
    lc = get_close_price(security, n)
    c = get_close_price(security, 1, '1m')

    if not isnan(lc) and not isnan(c) and lc != 0:
        return c / lc - 1
    else:
        log.error("数据非法, security: %s, %d日收盘价: %f, 当前价: %f" % (security, n, lc, c))
        return 0


# 获取前n个单位时间当时的收盘价
def get_close_price(security, n, unit='1d'):
    return attribute_history(security, n, unit, ('close'), True)['close'][0]


def sendmail(context, subject="", message=""):
    try:
        if is_sim_trade(context):
            mailSenderHTML = MailSenderHTML(context, g)
            mailSenderHTML.sendMail("养老金1号：%s" % subject, message)
    except Exception, e:
        message = "发送邮件错误:%s" % e.message
        log.error(message)
        webchat(message)


# 发送微信信息
def wechat(message):
    send_message(message, channel='weixin')