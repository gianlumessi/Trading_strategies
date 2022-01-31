from Trading_strategies.BSM_model import BSM_option, BSM_position
import pandas as pd
import numpy as np
import yfinance as yf
from pylab import mpl, plt
plt.style.use('seaborn')
mpl.rcParams['savefig.dpi'] = 300
mpl.rcParams['font.family'] = 'calibri'


#TODO: consider transaction costs, including costs for short positions
#TODO: consider hedging using perpetual futures and funding costs on perpetual positions
#TODO: consider size of position


def make_plot(x_, y1_, y2_, val):
    fig, ax = plt.subplots()
    ax.plot(x_, y1_, label='Position value at t0')
    ax.plot(x_, y2_, label='Position value at expiry')
    ax.axvline(x=val, color='r', label='BTC price at t0')
    legend = ax.legend()
    plt.show()

###Just checking results agree with what seen on Deribit
btc_price_0 = 35683.0

# options info
days_in_year = 365
tau = 19  # time to maturity in days
r = 0

# call option
k_call = 40000
bid_call = 680
iv_call = 0.645 * np.sqrt(1 / days_in_year)
call_delta_deribit = 0.25  # as found on Deribit

# put option
k_put = 30000
bid_put = 573
iv_put = 0.852 * np.sqrt(1 / days_in_year)
put_delta_deribit = -0.15  # as found on Deribit

long_call = BSM_option(S_=btc_price_0, K_=k_call, iv_=iv_call, tau_=tau, option_type_='call',
                        position_='long', option_price_=bid_call, pair_='BTC_USD')

long_put = BSM_option(S_=btc_price_0, K_=k_put, iv_=iv_put, tau_=tau, option_type_='put',
                       position_='long', option_price_=bid_put, pair_='BTC_USD')

call_delta = long_call.calc_option_delta()
put_delta = long_put.calc_option_delta()

print(call_delta, put_delta)
#### Ok Deltas agree ######
##########################################

x = np.linspace(20000, 60000, 200)
short_call = BSM_option(S_=x, K_=k_call, iv_=iv_call, tau_=tau, option_type_='call',
                        position_='short', option_price_=bid_call, pair_='BTC_USD')

short_put = BSM_option(S_=x, K_=k_put, iv_=iv_put, tau_=tau, option_type_='put',
                       position_='short', option_price_=bid_put, pair_='BTC_USD')

option_dict = {'opt1': [1, short_call], 'opt2': [1, short_put]}
position = BSM_position(option_dict)

position_delta = position.calculate_position_delta()
position_value = position.calculate_position_value()
#print(position_delta, position_value)

short_call_expiry = BSM_option(S_=x, K_=k_call, iv_=iv_call, tau_=0.01, option_type_='call',
                        position_='short', option_price_=bid_call, pair_='BTC_USD')

short_put_expiry = BSM_option(S_=x, K_=k_put, iv_=iv_put, tau_=0.01, option_type_='put',
                       position_='short', option_price_=bid_put, pair_='BTC_USD')


option_dict_expiry = {'opt1': [1, short_call_expiry], 'opt2': [1, short_put_expiry]}
position_expiry = BSM_position(option_dict_expiry)
position_value_expiry = position_expiry.calculate_position_value()

make_plot(x, position_value, position_value_expiry, btc_price_0)


#############################################################
## Simulation of delta hedged position

short_call = BSM_option(S_=btc_price_0, K_=k_call, iv_=iv_call, tau_=tau, option_type_='call',
                        position_='short', option_price_=bid_call, pair_='BTC_USD')

short_put = BSM_option(S_=btc_price_0, K_=k_put, iv_=iv_put, tau_=tau, option_type_='put',
                       position_='short', option_price_=bid_put, pair_='BTC_USD')

size = 1
option_dict = {'opt1': [size, short_call], 'opt2': [size, short_put]}
position = BSM_position(option_dict)

position_delta = position.calculate_position_delta()
position_value = position.calculate_position_value()


#trans_fees = 0.005
hedging_threshold = 0.05
pair = 'BTC-USD'
data_start_date = '2021-12-01'
data = pd.DataFrame(data=yf.download(pair, start=data_start_date))
data['return'] = np.log(data['Adj Close'] / data['Adj Close'].shift(1)).dropna()

col_list = ['Date', 'Stock price', 'Cash in / out', 'BTC AH', 'Delta AH']
df_accounting = pd.DataFrame(columns=col_list)

df_accounting.at[0, col_list[0]] = data.index[-tau - 2]
df_accounting.at[0, col_list[1]] = btc_price_0
hedging_costs_at_inception = 0
if np.abs(position_delta) > hedging_threshold:
    hedging_costs_at_inception = btc_price_0 * position_delta #same sign as delta. E.g. is delta negative,
    #you need to buy the stock to hedge, so that is cash out and has - sign
    position.set_underlying_amount(-position_delta) #if delta is negative, you need to buy the underlying
cash_in_out_at_inception = hedging_costs_at_inception + bid_call + bid_put
df_accounting.at[0, col_list[2]] = cash_in_out_at_inception
df_accounting.at[0, col_list[3]] = position.get_underlying_amount()
df_accounting.at[0, col_list[4]] = position.calculate_position_delta()


btc_price = btc_price_0
is_maturity = False
is_test = False


for i in range(tau):

    n = - tau - 1 + i
    updated_time_to_mat = tau - i - 1
    if updated_time_to_mat == 0:
        print('Expiry date, i =', i)
        updated_time_to_mat = 0.0000001

    if is_test:
        btc_price = btc_price * 0.95
    else:
        btc_price = btc_price * (1 + data['return'].iloc[n])
    df_accounting.at[i+1, col_list[0]] = data.index[n]
    df_accounting.at[i+1, col_list[1]] = btc_price

    underlying_held = position.get_underlying_amount()

    short_call.update_values(btc_price, updated_time_to_mat)
    short_put.update_values(btc_price, updated_time_to_mat)

    option_dict = {'opt1': [1, short_call], 'opt2': [1, short_put]}
    position.update_option_positions(option_dict)

    position_delta_before_hedging = position.calculate_position_delta()

    cash_in_out = 0

    if np.abs(position_delta_before_hedging) > hedging_threshold:
        cash_in_out = btc_price * position_delta_before_hedging
        position.set_underlying_amount(-position_delta_before_hedging + underlying_held)

    df_accounting.at[i+1, col_list[2]] = cash_in_out
    df_accounting.at[i+1, col_list[3]] = position.get_underlying_amount()
    df_accounting.at[i+1, col_list[4]] = position.calculate_position_delta()

### Close position
is_close_position = False

if btc_price > k_call:
    is_close_position = True
    underlying_to_buy_to_close_position = 1 - position.get_underlying_amount()
    cash_in_out = - btc_price * underlying_to_buy_to_close_position
    cash_in_out = cash_in_out + k_call
    position.set_underlying_amount(underlying_to_buy_to_close_position + position.get_underlying_amount())
elif btc_price < k_put:
    is_close_position = True
    underlying_to_short_to_close_position = 1 + position.get_underlying_amount()
    cash_in_out = btc_price * underlying_to_short_to_close_position
    cash_in_out = cash_in_out - k_put
    position.set_underlying_amount(-underlying_to_short_to_close_position + position.get_underlying_amount())

if is_close_position:
    df_accounting.at[i+1, col_list[0]] = data.index[n]
    df_accounting.at[i+1, col_list[1]] = btc_price
    df_accounting.at[i+1, col_list[2]] = cash_in_out
    df_accounting.at[i+1, col_list[3]] = position.get_underlying_amount()
    df_accounting.at[i+1, col_list[4]] = position.calculate_position_delta()
    df_accounting.at[i+1, 'comment'] = 'Option exercised'


df_accounting['Cash balance'] = np.cumsum(df_accounting[col_list[2]])

print(df_accounting)


print('\nThe end?')