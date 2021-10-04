# -*- coding: utf-8 -*-
"""
    nv: 현재가
    cd: 종목코드
    eps: nv/eps PER(배)
    bps: nv/bps PBR(배)
    ov: 시가
    sv: 전일?
    pcv: 전일
    cv: 전일 대비
    cr: 전일 대비 증감 %
    aq: 거래량
    aa: 거래대금
    ms: 장상태 ('OPEN', 'CLOSE')
    hv: 고가
    lv: 저가
    ul: 상한가
    ll: 하한가
    nm: 이름
    keps:
    dv:
    cnsEps:
    nav:
    rf:
    mt:
    tyn:
"""

import traceback
from collections import namedtuple
import json
from pprint import pprint

from utils import get_json, format_num, run_threads, filter_none
from os.path import exists
from os import remove
import re
import sys
from workflow import Workflow

if sys.version_info[0] == 3:
    pass
else:
    reload(sys)
    sys.setdefaultencoding("utf-8")


Item = namedtuple('Item', ['title', 'subtitle', 'url', 'icon', 'description'])

class StockItem:
    def __init__(
        self,
        symbol,
        regularMarketPrice=0,
        currency='',
        previousClose=0,
        exchange='',
        quoteType='',
        volume=0,
        high=0,
        low=0,
        link='',
        description='',
        note='', *args, **kwargs):
        self.symbol = symbol
        self.price = regularMarketPrice
        self.currency = currency
        self.closing_price = previousClose
        self.exchange = exchange
        self.quote_type = quoteType
        self.volume = volume
        self.high = high
        self.low = low
        self.link = link
        self.description = description
        self.note = note

    @property
    def icon(self):
        if self.price > self.closing_price:
            return './icons/red-arrow-up.png'
        elif self.price < self.closing_price:
            return './icons/blue-arrow-down.png'
        return ''

    @property
    def sign(self):
        if self.price > self.closing_price:
            return '+'
        elif self.price < self.closing_price:
            return '-'
        return ''

    @property
    def percent(self):
        if not self.closing_price:
            return 0
        return abs(100 * (self.price / self.closing_price - 1))

    @property
    def difference(self):
        return self.price - self.closing_price

    def get_title(self):
        return u'{name:<50}\t{currency} {price:<10}\t( {sign} {percent} %, {difference})'.format(
            name=self.symbol,
            currency=self.currency,
            price=format_num(self.price, 2),
            sign=self.sign,
            percent=format_num(self.percent, 2),
            difference=format_num(self.difference, 2))

    def get_subtitle(self):
        if self.note:
            return self.note
        return u'{market} {type}{volumn}{high}{low}  PER: {PER}  PBR: {PBR}'.format(
            market=self.exchange,
            type=self.quote_type,
            volumn='  volumn: {}'.format(format_num(self.volume)) if self.volume else '',
            high='  high: {}'.format(format_num(self.high, 2)) if self.high else '',
            low='  low: {}'.format(format_num(self.low, 2)) if self.low else '',
            PER='',
            PBR='')


class Stock(Workflow):
    LIST_URL = u'https://query1.finance.yahoo.com/v1/finance/search?q=%s&enableFuzzyQuery=true&enableCb=true&enableNavLinks=true&enableEnhancedTrivialQuery=true'
    POLLING_URL = u'https://query1.finance.yahoo.com/v8/finance/chart/%s'
    PAGE_URL = 'https://finance.yahoo.com/quote/%s'
    FAVORITE_FILE = './favorite.json'

    def __init__(self, *args):
        super(Stock, self).__init__()
        self.search_cache = {}

    def add(self, title, subtitle='', url=None, icon=None, description=''):
        subtitles = {
            'ctrl': 'Add to favorite.',
            'alt': 'Remove from favorite.'
        }
        if description:
            subtitles['cmd'] = description
        self.add_item(
            title, subtitle,
            valid=True,
            modifier_subtitles=subtitles,
            arg=url,
            icon=icon)

    def build_item(self, item):
        link = self.PAGE_URL % item['symbol']
        description = item.get('shortname', item.get('longname'))
        stock_item = StockItem(link=link, description=description, **item)
        return Item(stock_item.get_title(),
                    stock_item.get_subtitle(),
                    stock_item.link,
                    stock_item.icon,
                    stock_item.description)
        price = float(item['regularMarketPrice'])
        if item['currency'] == 'USD':
            currency = '$'
        elif item['currency'] == 'EUR':
            currency = '€'
        else:
            currency = ''
        closing_price = float(item['previousClose'])
        if price > closing_price:
            sign = '+'
            icon = './icons/red-arrow-up.png'
        elif price < closing_price:
            sign = '-'
            icon = './icons/blue-arrow-down.png'
        else:
            sign = ' '
            icon = ''
        percent = abs(100 * (price / closing_price - 1))
        difference = price - closing_price
        title = u'{name:<50}\t{currency} {price:<10}\t( {sign} {percent} %, {difference})'.format(
            name=item['symbol'],
            currency=currency,
            price=format_num(price, 2),
            sign=sign,
            percent=format_num(percent, 2),
            difference=format_num(difference, 2))
        subtitle = u'{market} {type}{volumn}{high}{low}  PER: {PER}  PBR: {PBR}'.format(
            market=item['exchange'],
            type=item['quoteType'],
            volumn='  volumn: {}'.format(format_num(item['volume'])) if 'volume' in item else '',
            high='  high: {}'.format(format_num(item['high'], 2)) if 'high' in item else '',
            low='  low: {}'.format(format_num(item['low'], 2)) if 'low' in item else '',
            PER='',
            PBR='')
        return Item(title, subtitle, url, icon, description)

    def load_favorites(self):
        if exists(self.FAVORITE_FILE):
            with open(self.FAVORITE_FILE, 'r') as f:
                return json.load(f)
        else:
            return []

    def get_items(self, query):
        '''
        [{
            "exchange": "NYQ",
            "shortname": "Canadian Pacific Railway Limite",
            "quoteType": "EQUITY",
            "symbol": "CP",
            "index": "quotes",
            "score": 2373100,
            "typeDisp": "Equity",
            "longname": "Canadian Pacific Railway Limited",
            "isYahooFinance": true
        }, ...]
        '''
        if query in self.search_cache:
            return self.search_cache[query]
        url = self.LIST_URL % query
        quotes = get_json(url)['quotes']
        self.search_cache[query] = quotes
        return quotes

    def fetch(self, ticker):
        '''
        {
            "chart": {
                "result": [{
                    "meta": {
                        "currency": "USD",
                        "symbol": "CPNG",
                        "exchangeName": "NYQ",
                        "instrumentType": "EQUITY",
                        "firstTradeDate": null,
                        "regularMarketTime": 1615496401,
                        "gmtoffset": -18000,
                        "timezone": "EST",
                        "exchangeTimezoneName": "America/New_York",
                        "regularMarketPrice": 49.52,
                        "chartPreviousClose": 35,
                        "previousClose": 35,
                        "scale": 3,
                        "priceHint": 2,
                        "currentTradingPeriod": {
                            "pre": {
                            "timezone": "EST",
                            "start": 1615453200,
                            "end": 1615473000,
                            "gmtoffset": -18000
                            },
                            "regular": {
                            "timezone": "EST",
                            "start": 1615473000,
                            "end": 1615496400,
                            "gmtoffset": -18000
                            },
                            "post": {
                            "timezone": "EST",
                            "start": 1615496400,
                            "end": 1615510800,
                            "gmtoffset": -18000
                            }
                        },
                        "tradingPeriods": [
                            [
                            {
                                "timezone": "EST",
                                "start": 1615473000,
                                "end": 1615496400,
                                "gmtoffset": -18000
                            }
                            ]
                        ],
                        "dataGranularity": "1m",
                        "range": "1d",
                        "validRanges": [
                            "1d",
                            "5d"
                        ]
                    } ...
        '''
        url = self.POLLING_URL % ticker
        ret = {'url': url}
        result = None
        try:
            result = get_json(url)['chart']['result']
        except Exception as e:
            return {'note': str(e)}  #traceback.format_exc()}
        if not result:
            return ret
        result = result[0]
        quote = result['indicators']['quote'][0]
        ret.update(result['meta'])
        if 'high' in quote:
            ret['high'] = max(filter_none(quote['high']))
        if 'low' in quote:
            ret['low'] = min(filter_none(quote['low']))
        if 'volume' in quote:
            volumes = filter_none(quote['volume'])
            if volumes: ret['volume'] = volumes[-1]
        if 'open' in quote:
            opens = filter_none(quote['open'])
            if opens: ret['open'] = opens[0]
        if 'close' in quote:
            closes = filter_none(quote['close'])
            if closes: ret['close'] = closes[-1]
        return ret

    def search(self, *args):
        query = u'%s' % ' '.join(args)
        if query:
            items = self.get_items(query)
        else:
            items = self.load_favorites()
        items = [item for item in items if item.get('symbol', None)]
        metas = run_threads(self.fetch, [(item['symbol'], ) for item in items])
        for item, meta in zip(items, metas):
            item.update(meta)
        for item in items:
            self.add(**self.build_item(item)._asdict())

    def search_for_delete(self):
        self.add('Select to delete from favorite.')
        self.search()

    def set_favorite(self, url):
        ticker = re.search(r'quote/([^&]*)', url).groups()[0]
        item = self.get_items(ticker)[0]
        if exists(self.FAVORITE_FILE):
            with open(self.FAVORITE_FILE, 'r') as f:
                favorites = json.load(f)
                favorites.append(item)
        else:
            favorites = [item]
        with open(self.FAVORITE_FILE, 'w') as f:
            json.dump(favorites, f, indent=4)

    def del_favorite(self, url):
        ticker = re.search(r'quote/([^&]*)', url).groups()[0]
        if exists(self.FAVORITE_FILE):
            with open(self.FAVORITE_FILE, 'r') as f:
                favorites = json.load(f)
                favorites = [item for item in favorites if item['symbol'] != ticker]
        else:
            favorites = []
        with open(self.FAVORITE_FILE, 'w') as f:
            json.dump(favorites, f, indent=4)

    def reset_favorite(self):
        if exists(self.FAVORITE_FILE):
            remove(self.FAVORITE_FILE)


def main():
    command = sys.argv[1]
    stock = Stock()
    getattr(stock, command)(*sys.argv[2:])
    stock.send_feedback()


if __name__ == '__main__':
    main()
