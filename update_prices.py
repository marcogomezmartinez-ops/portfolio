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

print("🔄 Actualizando precios Marco v10.6...\n")

# ── FONDOS vía Morningstar ────────────────────────────────────────────────────
funds = [
    ('IE000QAZP7L2', 'iShares Emerging Markets'),
    ('IE000ZYRH0Q7', 'iShares Developed World'),
    ('ES0140794001', 'Gamma Global FI'),
    ('ES0175902008', 'Sigma Internacional'),
    ('ES0112611001', 'Azvalor Internacional FI'),
    ('LU1598719752', 'Cobas International Fund'),
    # Nueva Expresion Textil → Yahoo Finance NXT.MC
]
for isin, name in funds:
    p = morningstar(isin, name)
    if p: prices[isin] = p
    time.sleep(1.5)

# ── Tasa EUR/USD vía Yahoo Finance (para convertir buy de Plata USD→EUR) ─────
try:
    r_fx = requests.get('https://query1.finance.yahoo.com/v8/finance/chart/EURUSD=X?interval=1d&range=1d',
                     headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
    eur_usd = r_fx.json()['chart']['result'][0]['meta']['regularMarketPrice']
    prices['EURUSD'] = round(eur_usd, 5)
    print(f"  ✅ EUR/USD: {round(eur_usd, 5)}")
except Exception as e:
    print(f"  ❌ EUR/USD: {e}")

# ── Invesco Physical Silver vía SI=F (futuros CME, USD/oz) ──────────────────
try:
    r_xag = requests.get('https://query1.finance.yahoo.com/v8/finance/chart/SI=F?interval=1d&range=5d',
                     headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
    xag_usd = r_xag.json()['chart']['result'][0]['meta']['regularMarketPrice']
    eur_usd = prices.get('EURUSD', 1.12)
    price_silver_eur = round(xag_usd * 0.9482 / eur_usd, 5)
    prices['IE00B43VDT70'] = price_silver_eur
    print(f"  ✅ Invesco Physical Silver: ${xag_usd}/oz → €{price_silver_eur}")
except Exception as e:
    print(f"  ❌ Invesco Physical Silver: {e}")


# ── Nueva Expresion Textil vía Yahoo Finance (NXT.MC — EUR, Madrid) ──────────
try:
    r_nxt = requests.get('https://query1.finance.yahoo.com/v8/finance/chart/NXT.MC?interval=1d&range=1d',
                     headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
    price_nxt = r_nxt.json()['chart']['result'][0]['meta']['regularMarketPrice']
    prices['ES0126962069'] = round(price_nxt, 5)
    print(f"  ✅ Nueva Expresion Textil: €{round(price_nxt, 5)}")
except Exception as e:
    print(f"  ❌ Nueva Expresion Textil: {e}")

# ── Tesla vía Yahoo Finance Xetra (TL0.DE — EUR directo, sin conversión) ─────
try:
    r_tsla = requests.get('https://query1.finance.yahoo.com/v8/finance/chart/TL0.DE?interval=1d&range=1d',
                     headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
    price_tsla_eur = r_tsla.json()['chart']['result'][0]['meta']['regularMarketPrice']
    prices['US88160R1014'] = round(price_tsla_eur, 5)
    print(f"  ✅ Tesla (Xetra TL0.DE): €{round(price_tsla_eur, 5)}")
except Exception as e:
    print(f"  ❌ Tesla Xetra: {e}")

# ── Bitcoin vía CoinGecko (EUR) ───────────────────────────────────────────────
try:
    r = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=eur', timeout=10)
    btc = r.json()['bitcoin']['eur']
    prices['BTC'] = btc
    print(f"  ✅ Bitcoin: €{btc:,}")
except Exception as e:
    print(f"  ❌ Bitcoin: {e}")

# ── Cálculo total cartera Marco (v10.5) ───────────────────────────────────────
portfolio = [
    {'isin': 'ES0140794001', 'qty': 290.210066},   # Gamma Global FI
    {'isin': 'LU1598719752', 'qty': 17.7714},       # Cobas International Fund
    {'isin': 'IE000ZYRH0Q7', 'qty': 124.03},        # iShares Developed World
    {'isin': 'IE000QAZP7L2', 'qty': 27.85},         # iShares Emerging Markets
    {'isin': 'ES0175902008', 'qty': 17.913204},     # Sigma Internacional FI
    {'isin': 'IE00B43VDT70', 'qty': 80},            # Invesco Physical Silver
    {'isin': 'ES0112611001', 'qty': 14.525463},     # Azvalor Internacional FI
    {'isin': 'US88160R1014', 'qty': 0.543552},      # Tesla (Xetra EUR)
    {'isin': 'ES0126962069', 'qty': 5000},          # Nueva Expresion Textil ✅ corregido
    {'isin': 'BTC',          'qty': 0.00884963},    # Bitcoin
]

fallback = {
    'ES0140794001': 13.8546,  'LU1598719752': 178.90,
    'IE000ZYRH0Q7': 11.416,   'IE000QAZP7L2': 13.65,
    'ES0175902008': 20.55209, 'IE00B4NCWG09': 66.33,
    'ES0112611001': 346.7784, 'US88160R1014': 385.95,
    'ES0126962069': 0.922,    'BTC': 68222,
}

total = round(sum((prices.get(a['isin']) or fallback.get(a['isin'], 0)) * a['qty'] for a in portfolio), 2)
today = datetime.now().strftime('%Y-%m-%d')
print(f"\n📊 Total Marco ({today}): €{total:,.2f} ({len(prices)}/10 precios)")

existing = json.load(open('prices.json')) if os.path.exists('prices.json') else {}
history = existing.get('history', [])
entry = next((h for h in history if h['date'] == today), None)
if entry: entry['total'] = total
else: history.append({'date': today, 'total': total})
history.sort(key=lambda x: x['date'])

with open('prices.json', 'w') as f:
    json.dump({'updated': datetime.now().strftime('%Y-%m-%d %H:%M UTC'), 'prices': prices, 'history': history}, f, indent=2)
print(f'✅ prices.json: {len(prices)} precios, {len(history)} puntos')
