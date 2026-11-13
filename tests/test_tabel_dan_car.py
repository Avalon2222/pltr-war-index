"""Tes tabel harga/return lebar dan rata-rata CAR di src/studi_peristiwa.py."""

import numpy as np
import pandas as pd

from src import studi_peristiwa as sp


def _harga_panjang():
    tgl = pd.to_datetime(["2024-01-03", "2024-01-02", "2024-01-04"] * 2)
    return pd.DataFrame({
        "tanggal": tgl,
        "ticker": ["PLTR"] * 3 + ["SPY"] * 3,
        "adj_close": [11.0, 10.0, 12.1, 101.0, 100.0, 100.0],
        "close": [11.0, 10.0, 12.1, 101.0, 100.0, 100.0],
    })


def test_tabel_return_urut_tanggal_dan_buang_baris_pertama():
    r = sp.tabel_return(_harga_panjang())
    assert list(r.columns) == ["PLTR", "SPY"]
    assert r.index.is_monotonic_increasing and len(r) == 2
    assert np.allclose(r["PLTR"].to_numpy(), [0.1, 0.1])


def test_tabel_harga_pilih_kolom():
    h = sp.tabel_harga(_harga_panjang(), "close")
    assert h.loc["2024-01-02", "SPY"] == 100.0 and h.shape == (3, 2)


def _hasil(car):
    tabel = pd.DataFrame({"hari_relatif": [-1, 0, 1], "car": car})
    return sp.HasilPeristiwa(tabel=tabel, alpha=0, beta=0, sigma=1, car=car[-1], t_stat=0, p_value=1,
                             hari_nol=pd.Timestamp("2024-01-02"))


def test_rata_rata_car_dan_interval():
    detail = {1: _hasil([0.0, 0.01, 0.02]), 2: _hasil([0.0, 0.03, 0.04])}
    r = sp.rata_rata_car(detail).set_index("hari_relatif")
    assert np.isclose(r.loc[1, "car_rata"], 0.03) and r.loc[1, "n"] == 2
    assert r.loc[1, "batas_bawah"] < r.loc[1, "car_rata"] < r.loc[1, "batas_atas"]


def test_rata_rata_car_id_tidak_dikenal_jadi_kosong():
    detail = {1: _hasil([0.0, 0.01, 0.02])}
    assert sp.rata_rata_car(detail, ids=[99]).empty
    assert sp.rata_rata_car(detail, ids=[1, 99])["n"].tolist() == [1, 1, 1]
