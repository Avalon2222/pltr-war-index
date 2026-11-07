"""Tes untuk parsing Yahoo (src/ambil_harga.py), p-value plasebo, dan korelasi bergulir.

Semua offline: respons Yahoo dipalsukan, data harga dibuat dari angka acak dengan seed tetap.
"""

import numpy as np
import pandas as pd
import pytest

from src import ambil_harga, intensitas, studi_peristiwa


class _Respons:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


def test_ambil_satu_pakai_tanggal_new_york(monkeypatch):
    # 13:30 UTC = 09:30 New York (bursa buka). 03:00 UTC tanggal 3 = masih tanggal 2 di New York.
    ts = pd.to_datetime(["2024-01-02 14:30", "2024-01-03 03:00", "2024-01-03 14:30", "2024-01-04 14:30"], utc=True)
    data = {"chart": {"result": [{
        "timestamp": [int(t.timestamp()) for t in ts],
        "indicators": {
            "quote": [{"close": [10.0, 10.5, 11.0, 12.0], "volume": [100, 50, None, 300]}],
            "adjclose": [{"adjclose": [9.99999, 10.5, 11.0, None]}],
        },
    }]}}
    monkeypatch.setattr(ambil_harga.requests, "get", lambda *a, **k: _Respons(data))

    df = ambil_harga.ambil_satu("PLTR", mulai="2024-01-01")

    assert df["tanggal"].dt.strftime("%Y-%m-%d").tolist() == ["2024-01-02", "2024-01-03"]
    assert df.loc[0, "close"] == 10.5          # tanggal dobel: yang terakhir dipakai
    assert df.loc[1, "volume"] == 0            # volume kosong jadi 0
    assert (df["ticker"] == "PLTR").all()
    assert str(df["volume"].dtype) == "int64"


def test_p_plasebo_tengah_dan_ekstrem():
    distribusi = np.arange(100, dtype=float)
    assert studi_peristiwa.p_plasebo(50, distribusi) == pytest.approx(1.0)
    assert studi_peristiwa.p_plasebo(1000, distribusi) == 0.0
    assert studi_peristiwa.p_plasebo(-1000, distribusi) == 0.0
    assert studi_peristiwa.p_plasebo(4, distribusi) == pytest.approx(0.10)


def test_p_plasebo_input_tidak_valid_jadi_nan():
    assert np.isnan(studi_peristiwa.p_plasebo(1.0, np.array([])))
    assert np.isnan(studi_peristiwa.p_plasebo(float("nan"), np.arange(10.0)))


def test_korelasi_bergulir_kenal_kembaran_dan_kebalikan():
    rng = np.random.default_rng(1)
    acak = rng.normal(size=300)
    ret = pd.DataFrame({"PLTR": acak, "ITA": acak * 2, "QQQ": -acak},
                       index=pd.date_range("2024-01-01", periods=300, freq="B"))
    hasil = intensitas.korelasi_bergulir(ret, jendela=60)
    assert len(hasil) == 300 - 59               # baris awal tanpa jendela penuh dibuang
    assert np.allclose(hasil["ITA"], 1.0)
    assert np.allclose(hasil["QQQ"], -1.0)


def test_return_mingguan_jumat_ke_jumat():
    idx = pd.date_range("2024-01-01", "2024-01-19", freq="B")    # Senin 1 Jan - Jumat 19 Jan
    harga = pd.DataFrame({"PLTR": np.linspace(10, 12.8, len(idx))}, index=idx)
    r = intensitas.return_mingguan(harga)
    assert list(r.index.day_name().unique()) == ["Friday"]
    assert np.isnan(r["PLTR"].iloc[0])
    jumat = harga.loc[["2024-01-05", "2024-01-12"], "PLTR"]
    assert r["PLTR"].iloc[1] == pytest.approx(jumat.iloc[1] / jumat.iloc[0] - 1)
