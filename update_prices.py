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

print("🔄 Actualizando precios Marco v11...\n")

# ── FONDOS vía Morningstar ────────────────────────────────────────────────────
funds = [
    ('IE000QAZP7L2', 'iShares Emerging Markets'),
    ('IE000ZYRH0Q7', 'iShares Developed World'),
    ('ES0112611001', 'Azvalor Internacional FI'),
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

# ── Invesco Physical Silver vía SI=F (futuros plata CME, calibrado 15/05/2026)
try:
    r_xag = requests.get('https://query1.finance.yahoo.com/v8/finance/chart/SI=F?interval=1d&range=5d',
                     headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
    xag_usd = r_xag.json()['chart']['result'][0]['meta']['regularMarketPrice']
    eur_usd = prices.get('EURUSD', 1.12)
    price_silver_eur = round(xag_usd * 0.9393 / eur_usd, 5)
    prices['IE00B43VDT70'] = price_silver_eur
    print(f"  ✅ Invesco Physical Silver: ${xag_usd}/oz → €{price_silver_eur}")
except Exception as e:
    print(f"  ❌ Invesco Physical Silver: {e}")

# ── Global X Silver Miners UCITS vía SIL (NYSE USD, mismo índice) / EUR/USD ──
try:
    r_silv = requests.get('https://query1.finance.yahoo.com/v8/finance/chart/SIL?interval=1d&range=5d',
                     headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
    price_sil_usd = r_silv.json()['chart']['result'][0]['meta']['regularMarketPrice']
    eur_usd = prices.get('EURUSD', 1.12)
    price_silv_eur = round(price_sil_usd / eur_usd * 0.4773, 5)
    prices['IE000UL6CLP7'] = price_silv_eur
    print(f"  ✅ Global X Silver Miners: ${price_sil_usd} → €{price_silv_eur}")
except Exception as e:
    print(f"  ❌ Global X Silver Miners: {e}")


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

# ── Cálculo total cartera Marco (v11 — MyInvestor 01/06/2026) ─────────────────
portfolio = [
    {'isin': 'IE000ZYRH0Q7', 'qty': 63.5},           # iShares Developed World ✅ 02/07
    {'isin': 'IE000QAZP7L2', 'qty': 22.21},          # iShares Emerging Markets ✅ 02/07
    {'isin': 'IE00B43VDT70', 'qty': 80},             # Invesco Physical Silver
    {'isin': 'IE000UL6CLP7', 'qty': 272},            # Global X Silver Miners ✅ 261→272
    {'isin': 'ES0112611001', 'qty': 14.525463},      # Azvalor Internacional FI
    {'isin': 'US88160R1014', 'qty': 0.543552},       # Tesla (Xetra EUR)
    {'isin': 'ES0126962069', 'qty': 5500},           # Nueva Expresion Textil ✅ 02/07
    {'isin': 'BTC',          'qty': 0.03558006},     # Bitcoin ✅ 02/07
]

fallback = {
    'IE000ZYRH0Q7': 11.999,   'IE000QAZP7L2': 14.125,
    'IE00B43VDT70': 50.80,    'IE000UL6CLP7': 33.51,
    'ES0112611001': 323.46471, 'US88160R1014': 351.30,
    'ES0126962069': 0.978,    'BTC': 54042,
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
