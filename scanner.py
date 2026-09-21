import json
import math
import ssl
import sys
import time
import urllib.request
from datetime import datetime

# ⚙️ SSL 및 요청 헤더 설정 (차단 방지)
SSL_CTX = ssl.create_unverified_context()
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache"
}

# 📱 텔레그램 연동 정보
TELEGRAM_BOT_TOKEN = "8995639791:AAEw7MFhgjI0kE"  # 사용자의 토큰 정보
TELEGRAM_CHAT_ID = "7191315709"

def send_telegram_message(message_text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ 텔레그램 설정이 올바르지 않습니다.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": message_text, "parse_mode": "HTML"}).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, context=SSL_CTX) as resp:
            print("📲 텔레그램 리포트 전송 완료!")
    except Exception as e:
        print(f"❌ 텔레그램 전송 실패: {e}")

def get_binance_crypto_tickers():
    # 🌐 바이낸스 우회 주소 (.me) 사용
    info_url = "https://fapi.binance.me/fapi/v1/exchangeInfo"
    ticker_url = "https://fapi.binance.me/fapi/v1/ticker/24hr"

    NON_CRYPTO_BLACKLIST = {
        "ANTHROPIC", "OPENAI", "STRIPE", "FIGMA", "DATABRICKS",
        "SOXS", "SOXL", "ORCL", "SKDD", "CXMT", "PLTR",
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

            is_stock_or_index = any(t in ["EQUITY", "ETF", "INDEX", "COMMODITY"] for t in sub_types)
            clean_base = symbol.replace("USDT", "").replace(".P", "").upper()

            if is_stock_or_index or clean_base in NON_CRYPTO_BLACKLIST or base_asset in NON_CRYPTO_BLACKLIST:
                continue
            valid_crypto_symbols.add(symbol)

        req_ticker = urllib.request.Request(ticker_url, headers=HEADERS)
        with urllib.request.urlopen(req_ticker, context=SSL_CTX, timeout=5) as resp:
            ticker_data = json.loads(resp.read().decode())

        filtered_tickers = [t for t in ticker_data if t["symbol"] in valid_crypto_symbols]
        return filtered_tickers

    except Exception as e:
        print(f"❌ 데이터 수집 실패: {e}")
        return []

# 스캐너 실행 구문
if __name__ == "__main__":
    print("⏳ [GitHub Actions 스캔 가동 중...]")
    tickers = get_binance_crypto_tickers()
    if tickers:
        msg = f"<b>[코인 스캐너 리포트]</b>\n\n총 {len(tickers)}개 종목 수집 완료 🚀"
        send_telegram_message(msg)
    else:
        print("💡 조건 충족 종목 없음")
