import json
import math
import ssl
import sys
import time
import urllib.request
from datetime import datetime

# ⚙️ PythonAnywhere 클라우드 환경 SSL 설정
SSL_CTX = ssl._create_unverified_context()
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# 📲 텔레그램 연동 정보
TELEGRAM_BOT_TOKEN = "8995639791:AAEw7MFhgjIOk0z4QtVMk6bv48PibFi8j1k"
TELEGRAM_CHAT_ID = "7191315709"

def send_telegram_message(message_text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ 텔레그램 설정이 올바르지 않습니다.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message_text,
        "parse_mode": "HTML"
    }).encode('utf-8')

    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=15.0):
            print("📲 텔레그램 리포트 전송 완료!")
    except Exception as e:
        print(f"❌ 텔레그램 전송 실패: {e}")

def get_binance_crypto_tickers():
    info_url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
    ticker_url = "https://fapi.binance.com/fapi/v1/ticker/24hr"

    NON_CRYPTO_BLACKLIST = {
        "ANTHROPIC", "OPENAI", "SPACEX", "STRIPE", "FIGMA", "DATABRICKS",
        "MU", "BE", "GLW", "SOXS", "SOXL", "ORCL", "SKDD", "CXMT", "PLTR", 
        "AMD", "NVDA", "TSLA", "AMZN", "SQ", "AAPL", "MSFT", "GOOG", "META", 
        "NFLX", "SPX", "NDX", "BTCDOM", "DEFI", "TLT", "TQQQ", "SQQQ", "BABA", 
        "COIN", "MSTR", "HOOD", "MARA", "RIOT", "XPT", "XPD", "XAU", "XAG", 
        "GOLD", "SILVER", "PLATINUM", "PALLADIUM", "BZ", "BRENT", "WTI", 
        "OIL", "NG", "GAS", "COPPER", "US500", "US100"
    }

    try:
        req_info = urllib.request.Request(info_url, headers=HEADERS)
        with urllib.request.urlopen(req_info, context=SSL_CTX, timeout=5) as resp:
            info_data = json.loads(resp.read().decode())

        valid_crypto_symbols = set()
        for s in info_data.get("symbols", []):
            symbol = s["symbol"]
            base_asset = s.get("baseAsset", "").upper()
            sub_types = [t.upper() for t in s.get("underlyingSubType", [])]
            sub_types.append(s.get("underlyingType", "").upper())

            is_non_crypto = any(t in ["EQUITY", "ETF", "INDEX", "COMMODITY", "STOCK", "PRE_MARKET", "PREMARKET"] for t in sub_types)
            clean_symbol = symbol.replace("USDT", "").replace(".P", "").upper()

            is_blacklisted = (
                base_asset in NON_CRYPTO_BLACKLIST
                or clean_symbol in NON_CRYPTO_BLACKLIST
                or any(b in clean_symbol for b in NON_CRYPTO_BLACKLIST)
                or clean_symbol.startswith(("XAU", "XAG", "XPT", "XPD", "BZ", "WTI", "NG"))
            )

            if s["status"] == "TRADING" and symbol.endswith("USDT") and not is_non_crypto and not is_blacklisted:
                valid_crypto_symbols.add(symbol)

        req_ticker = urllib.request.Request(ticker_url, headers=HEADERS)
        with urllib.request.urlopen(req_ticker, context=SSL_CTX, timeout=5) as resp:
            ticker_data = json.loads(resp.read().decode())

        return [i for i in ticker_data if i["symbol"] in valid_crypto_symbols and float(i["quoteVolume"]) >= 1500000]

    except Exception as e:
        print(f"❌ 데이터 수집 실패: {e}")
        return []

def fetch_klines(symbol, interval="1h", limit=48):
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=3.0) as resp:
            return json.loads(resp.read().decode())
    except:
        return None

def fetch_oi_change_15m(symbol):
    url = f"https://fapi.binance.com/futures/data/openInterestHist?symbol={symbol}&period=15m&limit=3"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=2.5) as resp:
            data = json.loads(resp.read().decode())
            if len(data) >= 2:
                oi_prev = float(data[-2]['sumOpenInterest'])
                oi_curr = float(data[-1]['sumOpenInterest'])
                if oi_prev > 0:
                    return ((oi_curr - oi_prev) / oi_prev) * 100
    except:
        pass
    return 0.0

def calc_atr_pct(highs, lows, closes, period=14):
    if len(closes) < period + 1: return 1.0
    trs = []
    for i in range(1, len(closes)):
        h, l, pc = highs[i], lows[i], closes[i-1]
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)
    atr = sum(trs[-period:]) / period
    return (atr / closes[-1]) * 100

def calc_ema(closes, period=20):
    if not closes or len(closes) < period:
        return closes[-1] if closes else 0
    ema = sum(closes[:period]) / period
    multiplier = 2 / (period + 1)
    for price in closes[period:]:
        ema = (price - ema) * multiplier + ema
    return ema

def calc_efficiency_ratio(klines_15m, period=8):
    if not klines_15m or len(klines_15m) < period: return 0.5
    net_change = abs(float(klines_15m[-1][4]) - float(klines_15m[-period][1]))
    total_range = sum(float(k[2]) - float(k[3]) for k in klines_15m[-period:])
    if total_range == 0: return 0.5
    er = net_change / total_range
    return max(0.1, min(1.0, er))

def check_btc_trend():
    klines_1h = fetch_klines("BTCUSDT", "1h", limit=30)
    if not klines_1h: return True, "BTC 데이터 미수집 (일반 스캔 진행)"
    closes = [float(k[4]) for k in klines_1h]
    ema20 = calc_ema(closes, 20)
    curr_btc = closes[-1]
    
    if curr_btc >= ema20:
        return True, f"🪙 BTC 상승 추세 유지 (${curr_btc:.1f} >= EMA20 ${ema20:.1f})"
    else:
        return False, f"⚠️ BTC 하락 추세 경고 (${curr_btc:.1f} < EMA20 ${ema20:.1f})"

def evaluate_coin_v23(symbol):
    klines_1d = fetch_klines(symbol, "1d", limit=30)
    if not klines_1d or len(klines_1d) < 20: return None
    closes_1d = [float(k[4]) for k in klines_1d]
    current_price = closes_1d[-1]
    sma20_1d = sum(closes_1d[-20:]) / 20

    if current_price < sma20_1d * 0.95: return None

    klines_4h = fetch_klines(symbol, "4h", limit=30)
    if not klines_4h or len(klines_4h) < 20: return None

    highs_4h = [float(k[2]) for k in klines_4h]
    lows_4h = [float(k[3]) for k in klines_4h]
    wave_high_4h = max(highs_4h)
    wave_low_4h = min(lows_4h)
    wave_range_4h = wave_high_4h - wave_low_4h

    if wave_range_4h <= 0 or current_price <= wave_low_4h: return None
    retrace_ratio_4h = (wave_high_4h - current_price) / wave_range_4h

    klines_1h = fetch_klines(symbol, "1h", limit=48)
    klines_15m = fetch_klines(symbol, "15m", limit=30)
    if not klines_1h or len(klines_1h) < 30 or not klines_15m: return None

    closes_1h = [float(k[4]) for k in klines_1h]
    highs_1h = [float(k[2]) for k in klines_1h]
    lows_1h = [float(k[3]) for k in klines_1h]
    vols_1h = [float(k[5]) for k in klines_1h]
    opens_15m = [float(k[1]) for k in klines_15m]
    closes_15m = [float(k[4]) for k in klines_15m]

    ema20_15m = calc_ema(closes_15m, 20)
    if closes_15m[-1] < ema20_15m: return None 
    
    bodies_15m = [abs(opens_15m[i] - closes_15m[i]) for i in range(len(closes_15m)-11, len(closes_15m)-1)]
    avg_body = sum(bodies_15m) / len(bodies_15m) if bodies_15m else 0
    p_open, p_close = opens_15m[-2], closes_15m[-2]
    if p_open > p_close and (p_open - p_close) > (avg_body * 2.0): return None 
    
    if closes_15m[-1] <= opens_15m[-1]: return None 

    score = 0
    reasons = []

    if current_price >= sma20_1d:
        score += 20
        reasons.append("일봉 20선 안착")

    if 0.382 <= retrace_ratio_4h <= 0.618:
        score += 30
        reasons.append(f"🎯 피보나치 황금구역(Fib {retrace_ratio_4h*100:.1f}%)")
    elif 0.236 <= retrace_ratio_4h < 0.382:
        score += 20
        reasons.append(f"4파 얕은 수렴(Fib {retrace_ratio_4h*100:.1f}%)")

    recent_1h_high = max(highs_1h[-6:-1])
    is_breakout = current_price >= recent_1h_high
    if is_breakout:
        score += 25
        reasons.append("🚀 3파 돌파 점화")

    fib_618_support = wave_high_4h - (wave_range_4h * 0.618)
    candidate_retest = min(ema20_15m, fib_618_support)
    
    if candidate_retest >= current_price:
        entry_retest = current_price * 0.990
    else:
        entry_retest = candidate_retest

    oi_change_pct = fetch_oi_change_15m(symbol)
    if oi_change_pct >= 2.0:
        score += 25
        reasons.append(f"📈 롱 매집 유입(OI: +{oi_change_pct:.1f}%)")

    avg_vol_24 = sum(vols_1h[-25:-1]) / 24
    if avg_vol_24 <= 0: return None
    vol_ratio = vols_1h[-1] / avg_vol_24
    if vol_ratio >= 2.5:
        score += 25
        reasons.append(f"💥 거래량 스파이크({vol_ratio:.1f}배)")

    raw_sl = min(lows_1h[-10:])
    if raw_sl >= current_price: raw_sl = current_price * 0.975
    buffered_sl = raw_sl * 0.995

    risk = current_price - buffered_sl
    sl_pct = (risk / current_price) * 100

    if 2.5 <= sl_pct <= 5.0:
        score += 20
        reasons.append(f"🛡️ 적정 손절유격(SL: -{sl_pct:.2f}%)")

    tp1 = current_price + (risk * 1.5)
    tp1_pct = ((tp1 - current_price) / current_price) * 100
    
    tp2 = current_price + (risk * 3.0)
    tp2_pct = ((tp2 - current_price) / current_price) * 100

    if current_price >= sma20_1d * 1.02:
        tp3 = current_price + (risk * 4.5)
        tp3_pct = ((tp3 - current_price) / current_price) * 100
        tp3_str = f"${format_price(tp3)} (+{tp3_pct:.2f}%)"
    else:
        tp3_str = "N/A (대세 파동 미확정)"

    atr_pct = calc_atr_pct(highs_1h, lows_1h, closes_1h, 14)
    if atr_pct < 0.1: atr_pct = 0.1
    recent_3h_vol = sum(vols_1h[-3:]) / 3
    accel_factor = recent_3h_vol / avg_vol_24 if avg_vol_24 > 0 else 1.0

    er = calc_efficiency_ratio(klines_15m, period=8)
    accel_scale = 1.0 + math.log(max(1.0, accel_factor))

    est_hours = tp1_pct / (atr_pct * er * accel_scale)
    est_hours = max(0.2, min(48.0, est_hours))

    if est_hours <= 2.0:
        fast_tag = " ⚡ [초단기 타점]"
        score += 2
    else:
        fast_tag = ""

    est_time_str = f"약 {int(est_hours * 60)}분 내" if est_hours < 1.0 else f"약 {est_hours:.1f}시간 내"

    return {
        "symbol": symbol, "score": score, "price": current_price,
        "entry_retest": entry_retest,
        "vol_ratio": round(vol_ratio, 1), "reasons": reasons, 
        "sl": buffered_sl, "sl_pct": round(sl_pct, 2),
        "tp1": tp1, "tp1_pct": round(tp1_pct, 2), 
        "tp2": tp2, "tp2_pct": round(tp2_pct, 2),
        "tp3_str": tp3_str,
        "est_hours": est_hours, "est_time": est_time_str,
        "fast_tag": fast_tag
    }

def format_price(val):
    if val >= 10: return f"{val:.2f}"
    elif val >= 1: return f"{val:.4f}"
    else: return f"{val:.6f}"

# ==============================================================================
# 🚀 메인 실행부
# ==============================================================================
if __name__ == "__main__":
    print("⏳ [PythonAnywhere 스캔 가동 중...]")
    btc_ok, btc_msg = check_btc_trend()
    tickers = get_binance_crypto_tickers()

    results = []
    for item in tickers:
        try:
            res = evaluate_coin_v23(item["symbol"])
            if res and res["score"] > 0:
                results.append(res)
            time.sleep(0.01)
        except:
            continue

    results.sort(key=lambda x: x["score"], reverse=True)
    top_results = results[:7]

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    msg_lines = [f"📊 <b>[알트코인 파동 현황 Top 7 (v23)]</b>"]
    msg_lines.append(f"⏰ 스캔 시각: {now_str}")
    msg_lines.append(f"🪙 시장 상태: {btc_msg}\n")

    if top_results:
        for idx, coin in enumerate(top_results, 1):
            symbol = coin['symbol']
            msg_lines.append(f"<b>{idx}. [{symbol}]</b> (점수: {coin['score']}점)")
            msg_lines.append(f"• 💵 현재가: <code>${format_price(coin['price'])}</code>")
            msg_lines.append(f"• 🎯 <b>추천 눌림목 진입가</b>: <code>${format_price(coin['entry_retest'])}</code>")
            msg_lines.append(f"• ⏱️ 도달 예상: <b>{coin['est_time']}{coin['fast_tag']}</b>")
            msg_lines.append(f"• 💡 진단: {', '.join(coin['reasons'])}")
            msg_lines.append(f"• 🎯 TP1: <code>${format_price(coin['tp1'])}</code> (+{coin['tp1_pct']}%)")
            msg_lines.append(f"• 🚀 TP2: <code>${format_price(coin['tp2'])}</code> (+{coin['tp2_pct']}%)")
            msg_lines.append(f"• 🌕 TP3: <b>{coin['tp3_str']}</b>")
            msg_lines.append(f"• 🛡️ SL: <code>${format_price(coin['sl'])}</code> (-{coin['sl_pct']}%)\n")

        send_telegram_message("\n".join(msg_lines))
    else:
        print("💡 조건 충족 종목 없음")
