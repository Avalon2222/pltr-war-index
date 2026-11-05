"""
ambil_harga.py - Mengunduh harga saham harian dari Yahoo Finance.

Yang diambil:
  PLTR  Palantir Technologies (bintang utama, IPO 30 September 2020)
  SPY   S&P 500 ETF, patokan "pasar secara umum"
  QQQ   Nasdaq-100 ETF, patokan saham teknologi
  ITA   iShares U.S. Aerospace & Defense ETF, sekeranjang saham pertahanan
  LMT, NOC, RTX, GD  kontraktor pertahanan klasik untuk pembanding

Yahoo Finance gratis dan tidak butuh API key. Kolom `adj_close` sudah
memperhitungkan dividen dan stock split, jadi return dihitung dari kolom itu.

Cara pakai dari terminal (memperbarui data/harga_saham.csv):
    python -m src.ambil_harga
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

URL_YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
# Yahoo menolak request tanpa User-Agent yang mirip browser.
HEADER = {"User-Agent": "Mozilla/5.0 (pltr-war-index)"}
PATH_CSV = Path(__file__).resolve().parent.parent / "data" / "harga_saham.csv"

TICKER = {
    "PLTR": "Palantir",
    "SPY": "S&P 500 (SPY)",
    "QQQ": "Nasdaq-100 (QQQ)",
    "ITA": "ETF pertahanan (ITA)",
    "LMT": "Lockheed Martin",
    "NOC": "Northrop Grumman",
    "RTX": "RTX (Raytheon)",
    "GD": "General Dynamics",
}
MULAI = "2020-09-30"  # hari pertama PLTR diperdagangkan


def _ke_unix(tanggal: str) -> int:
    dt = datetime.strptime(tanggal, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def ambil_satu(ticker: str, mulai: str = MULAI) -> pd.DataFrame:
    """Harga harian satu ticker. Kolom: tanggal, ticker, close, adj_close, volume."""
    params = {
        "interval": "1d",
        "period1": _ke_unix(mulai),
        "period2": int(datetime.now(tz=timezone.utc).timestamp()),
        "events": "div,split",
    }
    r = requests.get(URL_YAHOO.format(ticker=ticker), params=params, headers=HEADER, timeout=30)
    r.raise_for_status()
    hasil = r.json()["chart"]["result"][0]
    ind = hasil["indicators"]
    df = pd.DataFrame(
        {
            # Timestamp Yahoo = jam buka bursa New York; tanggal lokalnya yang dipakai.
            "tanggal": pd.to_datetime(hasil["timestamp"], unit="s", utc=True)
            .tz_convert("America/New_York")
            .tz_localize(None)
            .normalize(),
            "ticker": ticker,
            "close": ind["quote"][0]["close"],
            "adj_close": ind["adjclose"][0]["adjclose"],
            "volume": ind["quote"][0]["volume"],
        }
    )
    df = df.dropna(subset=["adj_close"]).drop_duplicates("tanggal", keep="last")
    df["close"] = df["close"].astype(float).round(4)
    df["adj_close"] = df["adj_close"].astype(float).round(4)
    df["volume"] = df["volume"].fillna(0).astype("int64")
    return df.sort_values("tanggal").reset_index(drop=True)


def ambil_semua(tickers: list[str] | None = None, jeda: float = 1.0) -> pd.DataFrame:
    """Unduh semua ticker lalu gabungkan dalam format panjang (satu baris per tanggal x ticker)."""
    potongan = []
    for t in tickers or list(TICKER):
        potongan.append(ambil_satu(t))
        time.sleep(jeda)
    return pd.concat(potongan, ignore_index=True)


def perbarui_csv(path: Path = PATH_CSV) -> pd.DataFrame:
    df = ambil_semua()
    df.to_csv(path, index=False, date_format="%Y-%m-%d")
    return df


if __name__ == "__main__":
    data = perbarui_csv()
    print(f"OK: {len(data)} baris disimpan ke {PATH_CSV}")
    print(data.groupby("ticker")["tanggal"].agg(["min", "max", "count"]).to_string())
