"""Tes untuk src/studi_peristiwa.py memakai data sintetis yang hasilnya bisa ditebak."""

import numpy as np
import pandas as pd
import pytest

from src import studi_peristiwa as sp


def _data_sintetis(n=400, beta=1.5, lonjakan=None, seed=0):
    """Return pasar acak + saham = beta * pasar + noise kecil. `lonjakan` = {posisi: return tambahan}."""
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2021-01-04", periods=n)
    pasar = rng.normal(0, 0.01, n)
    saham = 0.0005 + beta * pasar + rng.normal(0, 0.002, n)
    for pos, tambah in (lonjakan or {}).items():
        saham[pos] += tambah
    return pd.DataFrame({"PLTR": saham, "SPY": pasar}, index=idx)


def test_tabel_return_dari_harga_panjang():
    harga = pd.DataFrame({
        "tanggal": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"] * 2),
        "ticker": ["PLTR"] * 3 + ["SPY"] * 3,
        "adj_close": [10.0, 11.0, 9.9, 100.0, 101.0, 101.0],
    })
    ret = sp.tabel_return(harga)
    assert list(ret.columns) == ["PLTR", "SPY"]
    assert len(ret) == 2
    assert ret["PLTR"].iloc[0] == pytest.approx(0.10)
    assert ret["PLTR"].iloc[1] == pytest.approx(-0.10)
    assert ret["SPY"].iloc[1] == pytest.approx(0.0)


def test_hari_nol_akhir_pekan_pindah_ke_senin():
    idx = pd.bdate_range("2023-10-02", "2023-10-13")
    # 7 Oktober 2023 hari Sabtu -> hari bursa pertama Senin 9 Oktober
    pos = sp.posisi_hari_nol(idx, "2023-10-07")
    assert idx[pos] == pd.Timestamp("2023-10-09")
    assert sp.posisi_hari_nol(idx, "2023-10-04") == 2
    assert sp.posisi_hari_nol(idx, "2030-01-01") is None


def test_market_model_menemukan_beta():
    ret = _data_sintetis(beta=1.5)
    alpha, beta, sigma = sp.market_model(ret["PLTR"], ret["SPY"])
    assert beta == pytest.approx(1.5, abs=0.05)
    assert alpha == pytest.approx(0.0005, abs=0.0005)
    assert sigma == pytest.approx(0.002, rel=0.15)


def test_market_model_tanpa_patokan_pakai_rata_rata():
    s = pd.Series([0.01, 0.03, 0.02])
    alpha, beta, sigma = sp.market_model(s, None)
    assert alpha == pytest.approx(0.02)
    assert beta == 0
    assert sigma == pytest.approx(0.01)


def test_tanpa_lonjakan_car_mendekati_nol():
    ret = _data_sintetis()
    h = sp.studi_satu(ret, ret.index[250], jendela=(-1, 10))
    assert abs(h.car) < 0.02
    assert not h.signifikan


def test_lonjakan_terdeteksi_sebagai_abnormal_return():
    ret = _data_sintetis(lonjakan={250: 0.15})
    h = sp.studi_satu(ret, ret.index[250], jendela=(-1, 10))
    ar0 = h.tabel.set_index("hari_relatif").loc[0, "ar"]
    assert ar0 == pytest.approx(0.15, abs=0.01)
    assert h.car == pytest.approx(0.15, abs=0.02)
    assert h.signifikan
    assert h.p_value < 0.001
    # CAR sebelum hari 0 belum terpengaruh
    assert abs(h.tabel.set_index("hari_relatif").loc[-1, "car"]) < 0.01


def test_gerakan_pasar_tidak_dihitung_abnormal():
    """Kalau pasar anjlok dan saham ikut anjlok sesuai beta, itu bukan abnormal."""
    ret = _data_sintetis(beta=1.5)
    ret.iloc[250] = [1.5 * -0.05, -0.05]
    h = sp.studi_satu(ret, ret.index[250], jendela=(0, 0))
    assert abs(h.car) < 0.005


def test_tabel_peristiwa_lengkap_dan_car_kumulatif():
    ret = _data_sintetis()
    h = sp.studi_satu(ret, ret.index[200], jendela=(-5, 20))
    assert list(h.tabel["hari_relatif"]) == list(range(-5, 21))
    assert h.tabel["car"].iloc[-1] == pytest.approx(h.tabel["ar"].sum())
    assert h.hari_nol == ret.index[200]


def test_data_tidak_cukup_mengembalikan_none():
    ret = _data_sintetis(n=200)
    assert sp.studi_satu(ret, ret.index[50]) is None      # estimasi butuh 130 hari ke belakang
    assert sp.studi_satu(ret, ret.index[195], jendela=(-1, 10)) is None  # jendela lewat ujung data


def test_p_dua_sisi():
    assert sp.p_dua_sisi(0) == pytest.approx(1.0)
    assert sp.p_dua_sisi(1.96) == pytest.approx(0.05, abs=0.001)
    assert sp.p_dua_sisi(-1.96) == pytest.approx(0.05, abs=0.001)
    assert np.isnan(sp.p_dua_sisi(float("nan")))


def _peristiwa(ret, posisi):
    return pd.DataFrame({
        "tanggal": [ret.index[p] for p in posisi],
        "peristiwa": [f"Perang {i}" for i in range(len(posisi))],
        "kategori": ["eskalasi"] * len(posisi),
        "kawasan": ["Uji"] * len(posisi),
    })


def test_studi_semua_dan_rata_rata():
    ret = _data_sintetis(n=500, lonjakan={200: 0.10, 300: 0.10, 400: 0.10})
    ev = _peristiwa(ret, [200, 300, 400])
    ringkas, detail = sp.studi_semua(ret, ev, jendela=(-1, 5))
    assert len(ringkas) == 3 and set(detail) == {0, 1, 2}
    assert (ringkas["car"] > 0.08).all()
    assert ringkas["car_0_5"].iloc[0] == pytest.approx(ringkas["car"].iloc[0] - detail[0].tabel["ar"].iloc[0])
    rr = sp.rata_rata_car(detail)
    assert rr["n"].eq(3).all()
    akhir = rr.iloc[-1]
    assert akhir["batas_bawah"] < akhir["car_rata"] < akhir["batas_atas"]
    assert akhir["car_rata"] == pytest.approx(ringkas["car"].mean())


def test_studi_semua_melewati_peristiwa_tanpa_data():
    ret = _data_sintetis(n=300)
    ev = _peristiwa(ret, [10, 200])
    ringkas, detail = sp.studi_semua(ret, ev, jendela=(-1, 5))
    assert list(ringkas["id"]) == [1]


def test_tanda_laporan_keuangan_dalam_jendela():
    ret = _data_sintetis(n=400)
    hari_nol = ret.index[250]
    # Rilis setelah bursa tutup sehari sebelum hari 3 -> reaksi di hari 3 -> di dalam jendela (-1, 10)
    rilis = ret.index[252]
    laporan = [(rilis, "Q9 2099")]
    assert sp.ada_laporan_keuangan(hari_nol, ret.index, laporan, (-1, 10)) == "Q9 2099"
    assert sp.ada_laporan_keuangan(hari_nol, ret.index, laporan, (-1, 1)) is None
    jauh = [(ret.index[300], "Q1 2000")]
    assert sp.ada_laporan_keuangan(hari_nol, ret.index, jauh, (-1, 10)) is None


def test_plasebo_berpusat_di_nol_dan_lonjakan_terlihat_ekstrem():
    ret = _data_sintetis(n=600, seed=3)
    dist = sp.uji_plasebo(ret, n_peristiwa=5, jendela=(-1, 5), n_ulang=400)
    assert len(dist) == 400
    assert abs(np.mean(dist)) < 0.003
    assert sp.p_plasebo(0.10, dist) < 0.01
    assert sp.p_plasebo(float(np.median(dist)), dist) > 0.8


def test_plasebo_sama_dengan_studi_satu():
    """CAR yang dihitung cepat di uji_plasebo harus sama dengan studi_satu untuk hari yang sama."""
    ret = _data_sintetis(n=300, seed=5)
    dist = sp.uji_plasebo(ret, n_peristiwa=1, jendela=(-1, 3), n_ulang=1, seed=11)
    rng = np.random.default_rng(11)
    kandidat = np.arange(130, len(ret) - 1 - 3 + 1)
    nol = kandidat[rng.choice(len(kandidat), size=(1, 1), replace=True)[0, 0]]
    h = sp.studi_satu(ret, ret.index[nol], jendela=(-1, 3))
    assert dist[0] == pytest.approx(h.car)


def test_tabel_harga_dari_format_panjang():
    panjang = pd.DataFrame({
        "tanggal": pd.to_datetime(["2024-01-03", "2024-01-02", "2024-01-02", "2024-01-03"]),
        "ticker": ["PLTR", "PLTR", "SPY", "SPY"],
        "close": [11.0, 10.0, 470.0, 472.0],
    })
    lebar = sp.tabel_harga(panjang)
    assert list(lebar.columns) == ["PLTR", "SPY"]
    assert lebar.index.is_monotonic_increasing
    assert lebar.loc["2024-01-03", "PLTR"] == 11.0


def test_market_model_tanpa_patokan_abaikan_nan():
    s = pd.Series([0.01, np.nan, 0.03, 0.02, np.nan, 0.02])
    alpha, beta, sigma = sp.market_model(s, None)
    assert alpha == pytest.approx(0.02) and beta == 0.0
    assert np.isfinite(sigma)
    assert sigma == pytest.approx(np.std([0.01, 0.03, 0.02, 0.02], ddof=1))
