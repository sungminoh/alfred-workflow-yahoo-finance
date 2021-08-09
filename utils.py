import json
import re
import sys
import unicodedata
from threading import Thread

if sys.version_info[0] == 3:
    from urllib import request as urllib
else:
    import urllib2 as urllib


def platten_nested_list(l):
    ret = []
    for v in l:
        if isinstance(v, list):
            if len(v) == 1:
                if isinstance(v[0], list):
                    ret.append(platten_nested_list(v[0]))
                else:
                    ret.append(v[0])
            elif len(v) > 1:
                ret.append(platten_nested_list(v))
        else:
            ret.append(v)
    return ret


def run_threads(func, args_list):
    results = {}
    procs = []
    for i, args in enumerate(args_list):
        proc = Thread(
            target=lambda idx, args: results.setdefault(idx, func(*args)),
            args=(i, args))
        proc.start()
        procs.append(proc)
    for proc in procs:
        proc.join()
    return [results[i] for i in range(len(args_list))]


def make_depth_two(l):
    ret = []
    for v in l:
        if isinstance(v, list):
            if len(v) > 0:
                if not isinstance(v[0], list):
                    ret.append(v)
                else:
                    ret.extend(make_depth_two(v))
        else:
            ret.append([v])
    return ret


def build_dic(l):
    appeared = set()
    ret = []
    for v in l:
        if v[0] in appeared:
            continue
        appeared.add(v[0])
        dic = dict(label=v[0],
                   name=v[1],
                   market=v[2],
                   code=v[4])
        ret.append(dic)
    return ret


def data_to_dic(data):
    return build_dic(make_depth_two(platten_nested_list(data)))


def get_json(url):
    headers = {
        'authority': 'query1.finance.yahoo.com',
        'pragma': 'no-cache',
        'cache-control': 'no-cache',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.192 Safari/537.36',
        'accept': '*/*',
        'origin': 'https://finance.yahoo.com',
        'sec-fetch-site': 'same-site',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'accept-language': 'en-US,en;q=0.9,ko;q=0.8',
    }
    request = urllib.Request(url, headers=headers)
    response = urllib.urlopen(request)
    content = response.read()
    data = json.loads(content.decode('utf-8'))
    return data


def parse_url(url):
    # p = '(?:http.*://)?(?P<host>[^:/ ]+).?(?P<port>[0-9]*)(?P<uri>.*)'
    p = '((?P<schema>https?)://)?(?P<host>[^:/ ]+).?(?P<port>[0-9]*)(?P<uri>[^\?]*)\??(?P<params>.*)'
    m = re.search(p, str(url))
    schema = m.group('schema')
    host = m.group('host')
    port = m.group('port')
    uri = m.group('uri')
    params = m.group('params')
    return schema, host, port, uri, params


def format_num(num, decimal=0):
    return ('{:,.%sf}' % decimal).format(float(num))


def encode(query):
    return urllib.quote(unicodedata.normalize('NFC', query).encode('euc-kr'))


def get_query(argv):
    try:
        query = u'%s' % ' '.join(argv)
        return encode(query)
    except Exception:
        return ''


def filter_none(lst):
    return [x for x in lst if x is not None]
