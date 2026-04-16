import requests, json, os
from datetime import datetime

prices = {}
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
EUR_GBP = 1.17

def yahoo_to_eur(raw, currency, ticker):
    if currency == 'USD':
        return raw * 0.92
    if ticker.endswith('.L'):
        if currency == 'GBp' or (currency == 'GBP' and raw > 50):
            return (raw / 100) * EUR_GBP
        else:
            return raw * EUR_GBP
    return raw

# ── ETFs y acciones via Yahoo Finance ────────────────────────────────────
yahoo_map = {
    'IE000QAZP7L2': 'EIMI.L',
    'IE000ZYRH0Q7': 'SWDA.L',
    'IE00B4ND3602': 'IGLN.L',
    'US88160R1014': 'TSLA',
}
for isin, ticker in yahoo_map.items():
    try:
        url = f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d'
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        result = data['chart']['result'][0]
        raw = result['meta']['regularMarketPrice']
        curr = result['meta']['currency']
        price = yahoo_to_eur(raw, curr, ticker)
        if price > 10000:
            print(f"  ⚠️  {ticker}: precio {price} parece incorrecto, omitiendo")
            continue
        prices[isin] = round(price, 5)
        print(f"  ✅ {ticker}: raw={raw} curr={curr} → €{prices[isin]}")
    except Exception as e:
        print(f"  ❌ {ticker}: {e}")

# ── Bitcoin via CoinGecko ─────────────────────────────────────────────────
try:
    r = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=eur', timeout=10)
    prices['BTC'] = r.json()['bitcoin']['eur']
    print(f"  ✅ Bitcoin: €{prices['BTC']:,}")
except Exception as e:
    print(f"  ❌ Bitcoin: {e}")

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
            print(f"  ⚠️  {name}: {price} parece incorrecto, omitiendo")
            continue
        prices[isin] = round(price, 5)
        print(f"  ✅ {name}: €{price}")
    except Exception as e:
        print(f"  ❌ {name}: {e}")

# ── Calcular valor total de la cartera de Marco ───────────────────────────
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
    'ES0140794001': 13.67134, 'ES0112231016': 29.32158,
    'LU1694789451': 130.52,   'IE000ZYRH0Q7': 10.947,
    'IE000QAZP7L2': 12.339,   'ES0175902008': 19.81392,
    'IE00B4ND3602': 79.335,   'US88160R1014': 330.70,
    'BTC': 63246,
}

total = 0
for asset in portfolio:
    price = prices.get(asset['isin']) or fallback.get(asset['isin'], 0)
    total += asset['qty'] * price

total = round(total, 2)
today = datetime.now().strftime('%Y-%m-%d')
print(f"\n  📊 Valor total cartera Marco hoy ({today}): €{total:,.2f}")

# ── Leer prices.json existente y actualizar history ───────────────────────
existing = {}
if os.path.exists('prices.json'):
    with open('prices.json') as f:
        existing = json.load(f)

history = existing.get('history', [])
entry = next((h for h in history if h['date'] == today), None)
if entry:
    entry['total'] = total
else:
    history.append({'date': today, 'total': total})

history.sort(key=lambda x: x['date'])

# ── Escribir prices.json ──────────────────────────────────────────────────
output = {
    'updated': datetime.now().strftime('%Y-%m-%d %H:%M UTC'),
    'prices': prices,
    'history': history
}
with open('prices.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f'✅ prices.json actualizado: {len(prices)} precios, {len(history)} puntos históricos')
