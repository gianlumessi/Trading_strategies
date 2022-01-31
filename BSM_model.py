'''File implementing option objects in the Black-Scholes-Merton model'''

import numpy as np
import pandas as pd
from scipy.stats import norm
import yfinance as yf
pd.set_option('display.max_columns', 500)

class BSM_option:

    def __init__(self, S_, K_, iv_, tau_, option_type_='call', position_ = 'long',
                 option_price_ = None, r_=0, q_=0, pair_='BTC_USD'):

        '''

        :param underlying_: e.g. BTC spot
        :param S_: spot price
        :param K_: option strike
        :param iv_: option implied vol (daily)
        :param tau_: time to maturity in days
        :param option_type_: 'call' or 'put'
        :param position_: 'long' or 'short'
        :param option_price_: price at which the option was bought (if long) or sold (if sold)
        :param r_: applicable interest rate
        :param q_: dividend yield of underlying
        '''

        self.S_ = S_
        self.K_ = K_
        self.iv_ = iv_
        self.tau_ = tau_
        self.option_type_ = option_type_
        self.position_ = position_
        self.option_price_ = option_price_
        self.r_ = r_
        self.q_ = q_
        self.pair = pair_

        if option_type_ not in ['call', 'put']:
            print('!!!ERROR, option type not call nor put!!!')

        if position_ not in ['long', 'short']:
            print('!!!ERROR, position not long nor short!!!')

    def set_r_(self, val):
        self.r_ = val

    def set_tau_(self, val):
        self.tau_ = val

    def set_iv_(self, val):
        self.iv_ = val

    def set_S_(self, val):
        self.S_ = val

    def update_values(self, vs, vt, viv=None, vr=None):
        self.set_S_(vs)
        self.set_tau_(vt)

        if vr is not None:
            self.set_r_(vr)

        if viv is not None:
            self.set_iv_(viv)



    def calc_d1(self, x=None):
        '''It looks correct'''
        if x is None:
            x = self.S_

        return (np.log(x / self.K_) + (self.r_ - self.q_ + 0.5 * self.iv_ ** 2) * self.tau_) / (self.iv_ * np.sqrt(self.tau_))


    def calc_option_value(self, x=None):
        if x is None:
            x = self.S_

        d1 = self.calc_d1(x)
        d2 = d1 - self.iv_ * np.sqrt(self.tau_)

        sign_ = 1
        if self.position_ == 'short':
            sign_ = -1

        tmp1 = self.r_ * self.tau_
        F = x * np.exp((self.r_ - self.q_) * self.tau_)

        if self.option_type_ == 'call':
            option_value = sign_ * np.exp(-tmp1) * (F * norm.cdf(d1) - self.K_ * norm.cdf(d2)) - sign_ * self.option_price_
        else:
            option_value = sign_ * np.exp(-tmp1) * (self.K_ * norm.cdf(-d2) - F * norm.cdf(-d1)) - sign_ * self.option_price_
        return option_value

    def calc_option_delta(self, x=None):
        if x is None:
            x = self.S_

        sign_ = 1
        if self.position_ == 'short':
            sign_ = -1

        d1 = self.calc_d1(x)

        if self.option_type_ == 'call':
            return sign_ * norm.cdf(d1)
        else:
            return - sign_ * norm.cdf(-d1)

    def download_price_data(self, start_date):
        data = pd.DataFrame(data=yf.download(self.pair, start=start_date))
        data['return'] = np.log(data['Adj Close'] / data['Adj Close'].shift(1))

        return data


class BSM_position:
    def __init__(self, option_dict_):
        self.size_list_ = []
        self.option_list_ = []
        self.underlying_stock_held_ = 0
        self.inverse_future_held_ = 0

        for key in option_dict_:
            self.size_list_.append(option_dict_[key][0])
            self.option_list_.append(option_dict_[key][1])

    def update_option_positions(self, option_dict_):
        self.option_list_ = []
        for key in option_dict_:
            self.option_list_.append(option_dict_[key][1])


    def calculate_position_delta(self):
        position_delta_ = 0
        for i in range(len(self.size_list_)):
            delta = self.option_list_[i].calc_option_delta()
            sz = self.size_list_[i]
            position_delta_ = position_delta_ + sz * delta

        position_delta_ = position_delta_ + self.underlying_stock_held_

        return position_delta_


    def calculate_position_value(self):
        position_value_ = 0
        for i in range(len(self.size_list_)):
            value = self.option_list_[i].calc_option_value()
            sz = self.size_list_[i]
            position_value_ = position_value_ + sz * value

        position_value_ = position_value_ + self.underlying_stock_held_

        return position_value_


    def set_underlying_amount(self, val):
        self.underlying_stock_held_ = val

    def set_inverse_fut_amount(self, val):
        self.inverse_future_held_ = val

    def get_underlying_amount(self):
        return self.underlying_stock_held_

