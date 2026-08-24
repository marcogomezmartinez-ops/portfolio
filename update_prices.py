import requests, json, os, time
try:
    from curl_cffi import requests as cfrequests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False
from datetime import datetime

prices = {}
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.morningstar.es/es/funds/',
    'Accept': 'application/json',
}

def morningstar(isin, name, retries=3):
    url = (f'https://tools.morningstar.es/api/rest.svc/timeseries_price/'
           f'2nhcdckzon?id={isin}&idtype=Isin&frequency=daily&outputType=JSON')
    try:
        r = None
        for attempt in range(retries):
            # curl_cffi imita la huella TLS de un navegador real (Chrome).
            # requests normal tiene una huella distinta que algunos WAF bloquean
            # aunque la cabecera User-Agent diga "navegador" — por eso los 202 persistentes.
            if HAS_CURL_CFFI:
                r = cfrequests.get(url, headers=headers, timeout=20, impersonate="chrome124")
            else:
                r = requests.get(url, headers=headers, timeout=20)
            if r.status_code == 200:
                break
            wait = 2 * (attempt + 1)
            print(f"  ⏳ {name}: HTTP {r.status_code}, reintento en {wait}s ({attempt+1}/{retries})")
            time.sleep(wait)
        if r is None or r.status_code != 200:
            print(f"  ❌ {name}: HTTP {r.status_code if r is not None else '???'} tras {retries} intentos")
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

YUA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def yahoo_fund(isin, name, known_price=None):
    """Resuelve el símbolo Yahoo por ISIN y obtiene el precio. Fuente primaria para fondos."""
    try:
        # 1) buscar símbolo por ISIN
        r = requests.get(f'https://query1.finance.yahoo.com/v1/finance/search?q={isin}',
                         headers=YUA, timeout=15)
        if r.status_code != 200:
            print(f"  ⏳ {name}: Yahoo search HTTP {r.status_code}")
            return None
        quotes = [q for q in r.json().get('quotes', []) if q.get('symbol')]
        if not quotes:
            print(f"  ⏳ {name}: sin símbolo Yahoo para {isin}")
            return None
        # preferir fondos; si no, primer resultado
        quotes.sort(key=lambda q: 0 if q.get('quoteType') == 'MUTUALFUND' else 1)
        sym = quotes[0]['symbol']
        # 2) precio vía chart API (la misma que Tesla/EURUSD)
        r2 = requests.get(f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=5d',
                          headers=YUA, timeout=15)
        meta = r2.json()['chart']['result'][0]['meta']
        price = meta.get('regularMarketPrice')
        curr = meta.get('currency', '')
        if not price or price <= 0:
            return None
        if curr and curr != 'EUR':
            print(f"  ⏳ {name}: Yahoo {sym} cotiza en {curr}, descartado")
            return None
        # 3) sanity check: proteger contra clase/serie equivocada
        if known_price and abs(price - known_price) / known_price > 0.40:
            print(f"  ⚠️ {name}: Yahoo {sym} €{price} difiere >40% del último conocido €{known_price}, descartado")
            return None
        print(f"  ✅ {name} (Yahoo {sym}): €{round(price, 5)}")
        return round(price, 5)
    except Exception as e:
        print(f"  ⏳ {name}: Yahoo error {e}")
        return None

print(f"🔄 Actualizando precios Marco v12... (curl_cffi: {'sí' if HAS_CURL_CFFI else 'NO disponible, usando requests'})\n")

# ── FONDOS vía Morningstar ────────────────────────────────────────────────────
funds = [
    ('IE000QAZP7L2', 'iShares Emerging Markets'),
    ('IE000ZYRH0Q7', 'iShares Developed World'),
    ('ES0112611001', 'Azvalor Internacional FI'),
    ('ES0146309002', 'Horos Value Internacional'),
    ('ES0175902008', 'Sigma Internacional FI'),
]
# fallback conocido para el sanity check (se define más abajo; duplicado mínimo aquí)
_known = {
    'IE000QAZP7L2': 13.554, 'IE000ZYRH0Q7': 12.071, 'ES0112611001': 337.44291,
    'ES0146309002': 217.2901, 'ES0175902008': 20.30,
}
for isin, name in funds:
    p = yahoo_fund(isin, name, _known.get(isin))          # 1ª fuente: Yahoo (funciona desde Actions)
    if not p:
        p = morningstar(isin, name, retries=1)            # 2ª fuente: Morningstar (suele dar 202 desde Actions)
    if p: prices[isin] = p
    time.sleep(1.0)

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

# ── iShares Physical Gold vía GC=F (futuros oro CME, calibrado 15/07/2026) ───
try:
    r_xau = requests.get('https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=1d&range=5d',
                     headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
    xau_usd = r_xau.json()['chart']['result'][0]['meta']['regularMarketPrice']
    eur_usd = prices.get('EURUSD', 1.167)
    # factor 0.019738 calibrado: 68.68 EUR con oro $4060.66 y EURUSD 1.167 (15/07/2026)
    price_gold_eur = round(xau_usd / eur_usd * 0.019738, 5)
    prices['IE00B4ND3602'] = price_gold_eur
    print(f"  ✅ iShares Physical Gold: ${xau_usd}/oz → €{price_gold_eur}")
except Exception as e:
    print(f"  ❌ iShares Physical Gold: {e}")

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

# ── Bitcoin, Ethereum y Hyperliquid vía CoinGecko (EUR) ───────────────────────
try:
    r = requests.get(
        'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,hyperliquid&vs_currencies=eur',
        timeout=10)
    data = r.json()
    btc = data.get('bitcoin', {}).get('eur')
    eth = data.get('ethereum', {}).get('eur')
    hype = data.get('hyperliquid', {}).get('eur')
    if btc:
        prices['BTC'] = btc
        print(f"  ✅ Bitcoin: €{btc:,}")
    if eth:
        prices['ETH'] = eth
        print(f"  ✅ Ethereum: €{eth:,}")
    if hype:
        prices['HYPE'] = hype
        print(f"  ✅ Hyperliquid: €{hype:,}")
except Exception as e:
    print(f"  ❌ Cripto (CoinGecko): {e}")

# ── Cálculo total cartera Marco (v12 — MyInvestor + cripto 24/08/2026) ────────
portfolio = [
    {'isin': 'IE000ZYRH0Q7', 'qty': 63.5},           # iShares Developed World ✅ 02/07
    {'isin': 'IE000QAZP7L2', 'qty': 22.21},          # iShares Emerging Markets ✅ 02/07
    {'isin': 'IE00B43VDT70', 'qty': 80},             # Invesco Physical Silver
    {'isin': 'IE000UL6CLP7', 'qty': 272},            # Global X Silver Miners ✅ 261→272
    {'isin': 'ES0146309002', 'qty': 0.46021425},     # Horos Value Internacional ✅ 21/07
    {'isin': 'ES0175902008', 'qty': 0.591133},       # Sigma Internacional ✅ 21/07 (provisional)
    {'isin': 'ES0112611001', 'qty': 14.525463},      # Azvalor Internacional FI
    {'isin': 'US88160R1014', 'qty': 0.543552},       # Tesla (Xetra EUR)
    {'isin': 'ES0126962069', 'qty': 5500},           # Nueva Expresion Textil ✅ 02/07
    {'isin': 'BTC',          'qty': 0.04282313},     # Bitcoin ✅ 15/07
    {'isin': 'ETH',          'qty': 0.12575517},     # Ethereum ✅ 24/08
    {'isin': 'HYPE',         'qty': 7.93650794},     # Hyperliquid ✅ 24/08
    {'isin': 'IE00B4ND3602', 'qty': 2},              # iShares Physical Gold ✅ 15/07
]

fallback = {
    'IE000ZYRH0Q7': 12.071,   'IE000QAZP7L2': 13.554,
    'IE00B43VDT70': 48.042,   'IE000UL6CLP7': 31.15,
    'ES0112611001': 337.44291, 'US88160R1014': 356.60,
    'ES0126962069': 1.066,    'BTC': 56524,
    'ETH': 2106.1,            'HYPE': 69.963,
    'IE00B4ND3602': 68.68,
    'ES0146309002': 217.2901, 'ES0175902008': 20.30,
}

total = round(sum((prices.get(a['isin']) or fallback.get(a['isin'], 0)) * a['qty'] for a in portfolio), 2)
today = datetime.now().strftime('%Y-%m-%d')
print(f"\n📊 Total Marco ({today}): €{total:,.2f} ({len(prices)}/12 precios)")

existing = json.load(open('prices.json')) if os.path.exists('prices.json') else {}
history = existing.get('history', [])
entry = next((h for h in history if h['date'] == today), None)
if entry: entry['total'] = total
else: history.append({'date': today, 'total': total})
history.sort(key=lambda x: x['date'])

with open('prices.json', 'w') as f:
    json.dump({'updated': datetime.now().strftime('%Y-%m-%d %H:%M UTC'), 'prices': prices, 'history': history}, f, indent=2)
print(f'✅ prices.json: {len(prices)} precios, {len(history)} puntos')
