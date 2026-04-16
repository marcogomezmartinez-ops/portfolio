import requests, json, os
from datetime import datetime

prices = {}
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
ms_headers = {**headers, 'Referer': 'https://www.morningstar.es/'}

# ── Fondos y ETFs via Morningstar (EUR directo, sin conversion) ───────────
all_funds = [
    ('IE000QAZP7L2', 'iShares Emerging Markets'),
    ('IE000ZYRH0Q7', 'iShares Developed World'),
    ('IE00B4ND3602', 'iShares Physical Gold'),
    ('LU1694789451', 'DNCA Alpha Bonds'),
    ('ES0140794001', 'Gamma Global FI'),
    ('ES0175902008', 'Sigma Internacional'),
    ('ES0112231016', 'Avantage Fund B'),
]

for isin, name in all_funds:
    try:
        url = (f'https://tools.morningstar.es/api/rest.svc/timeseries_price/'
               f'2nhcdckzon?id={isin}&idtype=Isin&frequency=daily&outputType=JSON')
        r = requests.get(url, headers=ms_headers, timeout=10)
        data = r.json()
        hist = data[0]['TimeSeries']['Security'][0]['HistoryDetail']
        price = float(hist[-1]['Value'])
        if price <= 0 or price > 10000:
            print(f"  ⚠️  {name}: precio {price} sospechoso, omitiendo")
            continue
        prices[isin] = round(price, 5)
        print(f"  ✅ {name}: €{price}")
    except Exception as e:
        print(f"  ❌ {name} ({isin}): {e}")

# ── Tesla via Yahoo Finance (USD) ─────────────────────────────────────────
try:
    url = 'https://query1.finance.yahoo.com/v8/finance/chart/TSLA?interval=1d&range=1d'
    r = requests.get(url, headers=headers, timeout=10)
    data = r.json()
    raw = data['chart']['result'][0]['meta']['regularMarketPrice']
    price = round(raw * 0.92, 5)  # USD → EUR
    prices['US88160R1014'] = price
    print(f"  ✅ Tesla: ${raw} → €{price}")
except Exception as e:
    print(f"  ❌ Tesla: {e}")

# ── Bitcoin via CoinGecko ─────────────────────────────────────────────────
try:
    r = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=eur', timeout=10)
    btc = r.json()['bitcoin']['eur']
    prices['BTC'] = btc
    print(f"  ✅ Bitcoin: €{btc:,}")
except Exception as e:
    print(f"  ❌ Bitcoin: {e}")

# ── Calcular total cartera Marco ──────────────────────────────────────────
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
total = round(sum((prices.get(a['isin']) or fallback.get(a['isin'], 0)) * a['qty'] for a in portfolio), 2)
today = datetime.now().strftime('%Y-%m-%d')
print(f"\n  📊 Total Marco ({today}): €{total:,.2f}")

# ── Actualizar prices.json con historial ─────────────────────────────────
existing = json.load(open('prices.json')) if os.path.exists('prices.json') else {}
history = existing.get('history', [])
entry = next((h for h in history if h['date'] == today), None)
if entry: entry['total'] = total
else: history.append({'date': today, 'total': total})
history.sort(key=lambda x: x['date'])

output = {'updated': datetime.now().strftime('%Y-%m-%d %H:%M UTC'), 'prices': prices, 'history': history}
with open('prices.json', 'w') as f:
    json.dump(output, f, indent=2)
print(f'✅ prices.json: {len(prices)} precios, {len(history)} puntos historicos')
