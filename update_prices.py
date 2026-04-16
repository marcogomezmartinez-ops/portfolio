import requests, json
from datetime import datetime

prices = {}
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
EUR_GBP = 1.17  # GBP → EUR

def yahoo_to_eur(raw, currency, ticker):
    """Convert Yahoo Finance price to EUR, handling GBp/GBP ambiguity."""
    if currency == 'USD':
        return raw * 0.92
    
    if ticker.endswith('.L'):
        # Yahoo Finance .L stocks: sometimes returns GBp labeled as GBP
        # Heuristic: if price > 50, it's in GBp (pence) → divide by 100
        if currency == 'GBp' or (currency == 'GBP' and raw > 50):
            return (raw / 100) * EUR_GBP
        else:
            return raw * EUR_GBP
    
    return raw  # fallback

# ── ETFs y acciones via Yahoo Finance ────────────────────────────────────
yahoo_map = {
    'IE000QAZP7L2': 'EIMI.L',   # iShares Emerging Markets
    'IE000ZYRH0Q7': 'SWDA.L',   # iShares Developed World
    'IE00B4ND3602': 'IGLN.L',   # iShares Physical Gold
    'US88160R1014': 'TSLA',     # Tesla
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
        print(f"  ✅ {ticker}: raw={raw} curr={curr} → €{price:.5f}")
        prices[isin] = round(price, 5)
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
            print(f"  ⚠️  {name}: {price} parece incorrecto, omitiendo")
            continue
        prices[isin] = round(price, 5)
        print(f"  ✅ {name}: €{price}")
    except Exception as e:
        print(f"  ❌ {name}: {e}")

# ── Bitcoin via CoinGecko ────────────────────────────────────────────────
try:
    r = requests.get(
        'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=eur',
        timeout=10
    )
    btc = r.json()['bitcoin']['eur']
    prices['BTC'] = btc
    print(f"  ✅ Bitcoin: €{btc:,}")
except Exception as e:
    print(f"  ❌ Bitcoin: {e}")

# ── Guardar prices.json ──────────────────────────────────────────────────
output = {'updated': datetime.now().strftime('%Y-%m-%d %H:%M UTC'), 'prices': prices}
with open('prices.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f'\n✅ prices.json actualizado con {len(prices)} precios:')
for k, v in prices.items():
    print(f'   {k}: €{v}')
