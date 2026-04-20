import requests, json, os, time
from datetime import datetime

prices = {}
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.morningstar.es/es/funds/',
    'Accept': 'application/json',
}

def morningstar(isin, name):
    url = (f'https://tools.morningstar.es/api/rest.svc/timeseries_price/'
           f'2nhcdckzon?id={isin}&idtype=Isin&frequency=daily&outputType=JSON')
    try:
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code != 200:
            print(f"  ❌ {name}: HTTP {r.status_code}")
            return None
        data = r.json()
        if isinstance(data, list):
            ts = data[0].get('TimeSeries', {})
        elif isinstance(data, dict):
            ts = data.get('TimeSeries', {})
        else:
            return None
        securities = ts.get('Security', [])
        if not securities: return None
        hist = securities[0].get('HistoryDetail', [])
        if not hist: return None
        last = hist[-1]
        price = float(last.get('Value') or last.get('Close') or 0)
        if 0 < price < 10000:
            print(f"  ✅ {name}: €{price}")
            return round(price, 5)
        return None
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        return None

print("🔄 Actualizando precios Marco...\n")

funds = [
    ('IE000QAZP7L2', 'iShares Emerging Markets'),
    ('IE000ZYRH0Q7', 'iShares Developed World'),
    ('IE00B4ND3602', 'iShares Physical Gold'),
    ('LU1694789451', 'DNCA Alpha Bonds'),
    ('ES0140794001', 'Gamma Global FI'),
    ('ES0175902008', 'Sigma Internacional'),
    ('ES0112231016', 'Avantage Fund B'),
]
for isin, name in funds:
    p = morningstar(isin, name)
    if p: prices[isin] = p
    time.sleep(1.5)

# Tesla
try:
    r = requests.get('https://query1.finance.yahoo.com/v8/finance/chart/TSLA?interval=1d&range=1d',
                     headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
    raw = r.json()['chart']['result'][0]['meta']['regularMarketPrice']
    prices['US88160R1014'] = round(raw * 0.92, 5)
    print(f"  ✅ Tesla: €{prices['US88160R1014']}")
except Exception as e:
    print(f"  ❌ Tesla: {e}")

# Bitcoin
try:
    r = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=eur', timeout=10)
    btc = r.json()['bitcoin']['eur']
    prices['BTC'] = btc
    print(f"  ✅ Bitcoin: €{btc:,}")
except Exception as e:
    print(f"  ❌ Bitcoin: {e}")

portfolio = [
    {'isin': 'ES0140794001', 'qty': 375.445466},
    {'isin': 'ES0112231016', 'qty': 171.477127},
    {'isin': 'LU1694789451', 'qty': 19.2085},
    {'isin': 'IE000ZYRH0Q7', 'qty': 113.57},
    {'isin': 'IE000QAZP7L2', 'qty': 24.15},
    {'isin': 'ES0175902008', 'qty': 14.039623},
    {'isin': 'IE00B4ND3602', 'qty': 26},
    {'isin': 'US88160R1014', 'qty': 0.543552},
    {'isin': 'BTC',          'qty': 0.00842437},
]
fallback = {
    'ES0140794001': 13.72501, 'ES0112231016': 29.571,
    'LU1694789451': 130.47,   'IE000ZYRH0Q7': 11.06,
    'IE000QAZP7L2': 12.683,   'ES0175902008': 20.28139,
    'IE00B4ND3602': 79.17,    'US88160R1014': 340.05,
    'BTC': 63850,
}
total = round(sum((prices.get(a['isin']) or fallback.get(a['isin'], 0)) * a['qty'] for a in portfolio), 2)
today = datetime.now().strftime('%Y-%m-%d')
print(f"\n📊 Total Marco ({today}): €{total:,.2f} ({len(prices)}/9 precios)")

existing = json.load(open('prices.json')) if os.path.exists('prices.json') else {}
history = existing.get('history', [])
entry = next((h for h in history if h['date'] == today), None)
if entry: entry['total'] = total
else: history.append({'date': today, 'total': total})
history.sort(key=lambda x: x['date'])

with open('prices.json', 'w') as f:
    json.dump({'updated': datetime.now().strftime('%Y-%m-%d %H:%M UTC'), 'prices': prices, 'history': history}, f, indent=2)
print(f'✅ prices.json: {len(prices)} precios, {len(history)} puntos')
