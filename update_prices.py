import requests, json
from datetime import datetime

prices = {}
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
EUR_GBP = 1.17

# ── ETFs Londres y acciones US via Yahoo Finance ──────────────────────────
# IMPORTANTE: ETFs .L cotizan en GBp (peniques) → dividir /100 luego ×EUR_GBP
yahoo_map = {
    'IE000QAZP7L2': ('EIMI.L',  'GBp'),   # iShares Emerging Markets
    'IE000ZYRH0Q7': ('SWDA.L',  'GBp'),   # iShares Developed World
    'IE00B4ND3602': ('IGLN.L',  'GBp'),   # iShares Physical Gold
    'US88160R1014': ('TSLA',    'USD'),   # Tesla
}

for isin, (ticker, expected_curr) in yahoo_map.items():
    try:
        url = f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d'
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        result = data['chart']['result'][0]
        raw = result['meta']['regularMarketPrice']
        curr = result['meta']['currency']
        print(f"  {ticker}: raw={raw} currency={curr}")
        if curr == 'GBp':
            price = (raw / 100) * EUR_GBP
        elif curr == 'GBP':
            price = raw * EUR_GBP
        elif curr == 'USD':
            price = raw * 0.92
        else:
            price = raw
        if price > 10000 and ticker.endswith('.L'):
            print(f"  ⚠️  {ticker}: precio {price} parece en peniques, corrigiendo")
            price = price / 100
        prices[isin] = round(price, 5)
        print(f"  ✅ {ticker}: €{prices[isin]}")
    except Exception as e:
        print(f"  ❌ {ticker}: {e}")

# ── Fondos ES/LU via Morningstar ─────────────────────────────────────────
ms_headers = {**headers, 'Referer': 'https://www.morningstar.es/'}
fund_isins = [
    ('LU1694789451', 'DNCA Alpha Bonds'),
    ('ES0140794001', 'Gamma Global FI'),
    ('ES0175902008', 'Sigma Internacional'),
    ('ES0112231016', 'Avantage Fund B'),
]

for isin, name in fund_isins:
    try:
        url = (f'https://tools.morningstar.es/api/rest.svc/timeseries_price/'
               f'2nhcdckzon?id={isin}&idtype=Isin&frequency=daily&outputType=JSON')
        r = requests.get(url, headers=ms_headers, timeout=10)
        data = r.json()
        history = data[0]['TimeSeries']['Security'][0]['HistoryDetail']
        price = float(history[-1]['Value'])
        if price > 10000:
            print(f"  ⚠️  {name}: precio {price} parece incorrecto, omitiendo")
            continue
        prices[isin] = round(price, 5)
        print(f"  ✅ {name}: €{price}")
    except Exception as e:
        print(f"  ❌ {name}: {e}")

# ── Bitcoin via CoinGecko ────────────────────────────────────────────────
try:
    r = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=eur', timeout=10)
    btc = r.json()['bitcoin']['eur']
    prices['BTC'] = btc
    print(f"  ✅ Bitcoin: €{btc:,}")
except Exception as e:
    print(f"  ❌ Bitcoin: {e}")

# ── Guardar prices.json ──────────────────────────────────────────────────
output = {'updated': datetime.now().strftime('%Y-%m-%d %H:%M UTC'), 'prices': prices}
with open('prices.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f'\n✅ prices.json: {len(prices)} precios guardados')
for k, v in prices.items():
    print(f'   {k}: €{v}')
