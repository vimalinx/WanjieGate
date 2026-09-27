"""Read-only public market adapters; every displayed price carries a source time."""
import concurrent.futures
import json
import math
import re
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo


def read_url(url, encoding='utf-8'):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json,text/plain,*/*'})
    with urllib.request.urlopen(req, timeout=8) as response:
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ValueError('行情响应过大')
    return raw.decode(encoding)


def finite(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError('行情数值无效')
    return result


def parse_tencent(raw):
    quotes = []
    for symbol, body in re.findall(r'v_(\w+)="([^"\n]*)"', raw):
        fields = body.split('~')
        if len(fields) < 34 or not re.fullmatch(r'\d{14}', fields[30]):
            continue
        price, previous = finite(fields[3]), finite(fields[4])
        if price <= 0 or previous <= 0:
            continue
        stamp = datetime.strptime(fields[30], '%Y%m%d%H%M%S').replace(tzinfo=ZoneInfo('Asia/Shanghai'))
        quotes.append({'symbol': symbol, 'name': fields[1], 'price': price,
                       'change': finite(fields[31]), 'percent': finite(fields[32]),
                       'currency': 'HKD' if symbol.startswith('hk') else 'CNY',
                       'asof': stamp.isoformat(), 'source': '腾讯行情',
                       'url': 'https://gu.qq.com/' + symbol})
    if not quotes:
        raise ValueError('行情源未返回有效报价')
    return quotes


def parse_yahoo(payload):
    item = payload['chart']['result'][0]
    meta = item['meta']
    price = finite(meta['regularMarketPrice'])
    previous = finite(meta.get('chartPreviousClose') or meta.get('previousClose'))
    stamp = datetime.fromtimestamp(meta['regularMarketTime'], ZoneInfo(meta.get('exchangeTimezoneName', 'UTC')))
    values = item['indicators']['quote'][0]['close']
    points = [{'time': stamp, 'value': finite(v)} for stamp, v in zip(item.get('timestamp', []), values) if v is not None]
    return {'symbol': meta['symbol'], 'name': meta.get('shortName') or meta.get('longName') or meta['symbol'],
            'price': price, 'change': price-previous, 'percent': (price/previous-1)*100 if previous else 0,
            'currency': meta.get('currency', ''), 'asof': stamp.isoformat(), 'points': points,
            'source': 'Yahoo Finance', 'url': 'https://finance.yahoo.com/quote/' + urllib.parse.quote(meta['symbol'], safe='') + '/'}


class Market:
    def __init__(self):
        self.cache = {}
        self.lock = threading.Lock()

    def cached(self, key, fetch):
        with self.lock:
            old = self.cache.get(key)
        if old and time.monotonic()-old[0] < 30:
            return old[1]
        result = fetch()
        with self.lock:
            if len(self.cache) >= 128:
                self.cache.pop(next(iter(self.cache)))
            self.cache[key] = (time.monotonic(), result)
        return result

    def tencent(self, symbols):
        if any(not re.fullmatch(r'(?:sh|sz)\d{6}|hk\d{5}', s) for s in symbols):
            raise ValueError('股票代码无效')
        key = ','.join(symbols)
        quotes = self.cached(key, lambda: parse_tencent(read_url('https://qt.gtimg.cn/q='+key, 'gb18030')))
        def with_history(q):
            try:
                url='https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?'+urllib.parse.urlencode({'param':q['symbol']+',day,,,30,qfq'})
                data=self.cached('history:'+q['symbol'],lambda:json.loads(read_url(url)))['data'][q['symbol']]
                points=[{'time':row[0],'value':finite(row[2])} for row in data.get('qfqday',data.get('day',[]))]
                return {**q,'points':points,'period':'近 30 个交易日'}
            except Exception:
                return {**q,'chart_error':'走势暂不可用'}
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            return list(pool.map(with_history,quotes))

    def yahoo(self, symbol):
        if not re.fullmatch(r'[A-Z^][A-Z0-9.^=-]{0,14}', symbol):
            raise ValueError('股票代码无效')
        # One-day chart's previous close is the daily change baseline.
        url = 'https://query1.finance.yahoo.com/v8/finance/chart/'+urllib.parse.quote(symbol,safe='')+'?interval=5m&range=1d'
        return self.cached(symbol, lambda: parse_yahoo(json.loads(read_url(url))))

    def resolve(self, text):
        codes = re.findall(r'(?<!\d)(?:sh|sz|hk)?\d{5,6}(?!\d)', text, re.I)
        if codes:
            symbols=[]
            for c in codes[:4]:
                c=c.lower()
                symbols.append(c if c.startswith(('sh','sz','hk')) else ('hk'+c if len(c)==5 else ('sh' if c.startswith(('6','9')) else 'sz')+c))
            return '个股行情', self.tencent(symbols)
        tickers = re.findall(r'(?<![A-Za-z])\$?([A-Z]{2,7})(?![A-Za-z])',text)
        tickers=[s for s in tickers if s not in {'ETF','USD','CNY','HKD','IPO'}]
        if tickers:
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                return '个股行情', list(pool.map(self.yahoo,dict.fromkeys(tickers[:4])))
        if re.search('美股|纳斯达克|标普|道琼斯',text):
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
                return '美股概览',list(pool.map(self.yahoo,['^GSPC','^IXIC','^DJI']))
        if re.search('港股|恒生',text):
            return '港股概览',[self.yahoo('^HSI')]
        # Resolve a named security with the provider's directory, never invent a ticker.
        name = re.sub(r'股票|股价|行情|走势|怎么样|怎么|怎样|咋样|如何|情况|今天|现在|最近|帮我|看看|查看|查询|一下|的|了|呢|[？?！!，,。\s]','',text).strip()
        if name and name not in {'股市','大盘','A股','a股','上证','深证','创业板','股'}:
            raw=read_url('https://smartbox.gtimg.cn/s3/?'+urllib.parse.urlencode({'q':name,'t':'all'}))
            match=re.search(r'v_hint="(.*)"',raw)
            hint=json.loads('"'+match.group(1)+'"') if match else ''
            choices=[]
            for row in hint.split('^')[:8]:
                f=row.split('~')
                if len(f)>=3 and f[0] in {'sh','sz','hk'}:
                    choices.append({'label':f[2]+' · '+f[1], 'value':f[0]+f[1]+' 股票行情'})
            if len(choices)==1:
                symbol=choices[0]['value'].split()[0]
                return '个股行情',self.tencent([symbol])
            if choices:
                return '选择标的',choices
            return '未匹配到标的',[]
        return 'A 股概览',self.tencent(['sh000001','sz399001','sz399006'])

    def scene(self, text):
        title, items = self.resolve(text)
        if title in {'选择标的','未匹配到标的'}:
            return {'title':title,'blocks':[{'type':'choices','title':'输入股票代码，或选择匹配的标的','items':items}], 'source':'腾讯证券目录'}
        return {'title': title, 'blocks':[
            {'type':'quotes','title':title,'items':items},
            {'type':'choices','title':'切换市场','items':[{'label':s,'value':s+'行情'} for s in ['A股','港股','美股']]}],
            'source':'公开行情 · 可能延迟，以报价时间为准'}
