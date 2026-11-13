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
