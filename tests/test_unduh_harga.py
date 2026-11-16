"""Tes pengunduh harga (src/ambil_harga.py) dan fallback snapshot di src/muat_data.py, tanpa internet."""

import pandas as pd

from src import ambil_harga, muat_data


def test_ke_unix_tengah_malam_utc():
    assert ambil_harga._ke_unix("1970-01-02") == 86_400
    assert ambil_harga._ke_unix("2020-01-01") == 1_577_836_800


def _harga_palsu(ticker, mulai=None):
    return pd.DataFrame({"tanggal": pd.to_datetime(["2024-01-02", "2024-01-03"]), "ticker": ticker,
                         "close": [10.0, 11.0], "adj_close": [10.0, 11.0], "volume": [100, 120]})


def test_ambil_semua_gabung_format_panjang(monkeypatch):
    monkeypatch.setattr(ambil_harga, "ambil_satu", _harga_palsu)
    df = ambil_harga.ambil_semua(["PLTR", "SPY"], jeda=0)
    assert len(df) == 4 and set(df["ticker"]) == {"PLTR", "SPY"}
    assert df.index.tolist() == [0, 1, 2, 3]


def test_perbarui_csv_tulis_tanggal_rapi(monkeypatch, tmp_path):
    monkeypatch.setattr(ambil_harga, "ambil_satu", _harga_palsu)
    monkeypatch.setattr(ambil_harga, "TICKER", {"PLTR": "Palantir"})
    monkeypatch.setattr(ambil_harga.time, "sleep", lambda s: None)
    path = tmp_path / "harga.csv"
    ambil_harga.perbarui_csv(path)
    baris = path.read_text().splitlines()
    assert baris[0].startswith("tanggal,ticker")
    assert baris[1].startswith("2024-01-02,PLTR")


def test_muat_harga_live_gagal_jatuh_ke_snapshot(monkeypatch):
    def gagal(**kwargs):
        raise ConnectionError("tidak ada internet")

    monkeypatch.setattr(muat_data.ambil_harga, "ambil_semua", gagal)
    df, sumber = muat_data.muat_harga(live=True)
    assert sumber == "snapshot" and not df.empty


def test_muat_harga_live_berhasil(monkeypatch):
    monkeypatch.setattr(muat_data.ambil_harga, "ambil_semua", lambda **kw: _harga_palsu("PLTR"))
    df, sumber = muat_data.muat_harga(live=True)
    assert sumber == "live" and len(df) == 2


class _Respons:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


def test_ambil_satu_tanpa_adjclose_pakai_close(monkeypatch):
    data = {"chart": {"result": [{
        "timestamp": [1_704_205_800, 1_704_292_200],  # 2 & 3 Jan 2024, 09:30 New York
        "indicators": {"quote": [{"close": [10.123456, 11.0], "volume": [100, None]}]},
    }]}}
    monkeypatch.setattr(ambil_harga.requests, "get", lambda *a, **k: _Respons(data))
    df = ambil_harga.ambil_satu("^VIX")
    assert df["tanggal"].dt.strftime("%Y-%m-%d").tolist() == ["2024-01-02", "2024-01-03"]
    assert df["adj_close"].tolist() == [10.1235, 11.0]
    assert df["volume"].tolist() == [100, 0]
