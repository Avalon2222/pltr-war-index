"""Tes untuk src/intensitas.py, src/siapkan_konflik.py, dan integritas file di data/."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src import intensitas, muat_data, siapkan_konflik
from src.ambil_harga import TICKER

DATA = Path(__file__).resolve().parent.parent / "data"


def _konflik(n_hari=70):
    idx = pd.date_range("2024-01-01", periods=n_hari, freq="D")
    df = pd.DataFrame({"tanggal": idx})
    for t in intensitas.TEATER:
        df[f"korban_{t}"] = 1
    df["korban_total"] = len(intensitas.TEATER)
    return df


def test_konflik_mingguan_menjumlah_per_minggu_jumat():
    k = _konflik(14)  # 1-14 Januari 2024; Jumat = 5 dan 12 Januari
    m = intensitas.konflik_mingguan(k)
    assert m.index[0] == pd.Timestamp("2024-01-05")
    assert m["korban"].iloc[0] == 5 * len(intensitas.TEATER)
    m_ukr = intensitas.konflik_mingguan(k, ["Rusia-Ukraina"])
    assert m_ukr["korban"].iloc[1] == 7


def test_korelasi_lag_menemukan_hubungan_tertunda():
    rng = np.random.default_rng(1)
    x = rng.normal(size=300)
    df = pd.DataFrame({"perubahan_log": x, "return_lebih": np.roll(x, 2) + rng.normal(0, 0.1, 300)})
    lag = intensitas.korelasi_lag(df, lag_maks=3)
    assert list(lag["lag"]) == [-3, -2, -1, 0, 1, 2, 3]
    terbaik = lag.loc[lag["korelasi"].idxmax()]
    assert terbaik["lag"] == 2 and terbaik["korelasi"] > 0.9
    assert lag["batas"].iloc[0] == pytest.approx(1.96 / np.sqrt(297))


def test_minggu_terpanas_membagi_dua_kelompok():
    df = pd.DataFrame({"perubahan_log": np.arange(100), "return_lebih": np.r_[np.zeros(90), np.ones(10)]})
    hasil = intensitas.minggu_terpanas(df, 0.9)
    panas = hasil.set_index("kelompok").loc["Minggu lonjakan korban"]
    assert panas["jumlah_minggu"] == 10
    assert panas["rata_return_lebih"] == 1
    assert hasil["jumlah_minggu"].sum() == 100


def test_kinerja_relatif_mulai_dari_100():
    idx = pd.date_range("2024-01-01", periods=3)
    h = pd.DataFrame({"A": [10, 20, 5], "B": [2, 2, 4]}, index=idx)
    k = intensitas.kinerja_relatif(h)
    assert k.iloc[0].tolist() == [100, 100]
    assert k.iloc[-1].tolist() == [50, 200]
    assert intensitas.kinerja_relatif(h, "2024-01-02").iloc[0].tolist() == [100, 100]


def test_ringkas_harian_membagi_korban_rentang_tanggal():
    kejadian = pd.DataFrame({
        "date_start": ["2024-03-01"], "date_end": ["2024-03-04"], "country": ["Sudan"], "best": [400],
    })
    h = siapkan_konflik.ringkas_harian(kejadian)
    assert h["korban_Sudan"].tolist() == [100, 100, 100, 100]
    assert h["korban_total"].sum() == 400


def test_ringkas_harian_mengisi_hari_kosong_dan_memetakan_teater():
    kejadian = pd.DataFrame({
        "date_start": ["2024-01-01", "2024-01-01", "2024-01-03", "2019-05-05"],
        "country": ["Ukraine", "Atlantis", "Israel", "Ukraine"],
        "best": [10, 3, 7, 99],
    })
    h = siapkan_konflik.ringkas_harian(kejadian, mulai="2020-01-01")
    assert list(h["tanggal"].dt.day) == [1, 2, 3]
    assert h["korban_Rusia-Ukraina"].tolist() == [10, 0, 0]
    assert h["korban_Lainnya"].tolist() == [3, 0, 0]
    assert h["korban_total"].tolist() == [13, 0, 7]
    assert h["kejadian_total"].tolist() == [2, 0, 1]


# --- Integritas data snapshot -------------------------------------------------

def test_peristiwa_perang_valid():
    ev = muat_data.muat_peristiwa()
    assert len(ev) >= 40
    assert ev["kategori"].isin(muat_data.KATEGORI).all()
    assert ev["sumber"].str.startswith("https://").all()
    assert ev["tanggal"].is_monotonic_increasing
    assert not ev.duplicated(["tanggal", "peristiwa"]).any()
    assert ev["peristiwa"].str.len().max() < 70


def test_harga_saham_lengkap():
    h = muat_data.muat_harga_snapshot()
    assert set(h["ticker"]) == set(TICKER)
    assert h["tanggal"].min() == pd.Timestamp("2020-09-30")
    per_ticker = h.groupby("ticker").size()
    assert per_ticker.nunique() == 1, "semua ticker harus punya jumlah hari bursa yang sama"
    assert (h["adj_close"] > 0).all()


def test_konflik_harian_konsisten():
    k = muat_data.muat_konflik()
    kolom_teater = [f"korban_{t}" for t in intensitas.TEATER]
    assert (k[kolom_teater].sum(axis=1) == k["korban_total"]).all()
    assert k["tanggal"].diff().dropna().eq(pd.Timedelta(days=1)).all()
    assert set(k["status"]) <= {"final", "awal"}


def test_laporan_keuangan_kuartalan():
    lap = muat_data.muat_laporan()
    assert lap["tanggal_rilis"].is_monotonic_increasing
    jarak = lap["tanggal_rilis"].diff().dropna().dt.days
    assert jarak.between(70, 110).all()


def _harga_lebar(n_hari=70):
    idx = pd.date_range("2024-01-01", periods=n_hari, freq="D")
    return pd.DataFrame({"PLTR": np.linspace(20, 34, n_hari), "SPY": np.linspace(400, 420, n_hari)}, index=idx)


def test_gabung_mingguan_return_lebih_dikurangi_patokan():
    df = intensitas.gabung_mingguan(_konflik(), _harga_lebar())
    assert len(df) > 0
    assert df["return_lebih"].to_numpy() == pytest.approx((df["return_saham"] - df["SPY"]).to_numpy())
    assert df[["perubahan_log", "return_saham"]].notna().all().all()   # minggu pertama (NaN) dibuang


def test_gabung_mingguan_tanpa_patokan():
    df = intensitas.gabung_mingguan(_konflik(), _harga_lebar(), patokan=None)
    assert "SPY" not in df.columns
    assert df["return_lebih"].to_numpy() == pytest.approx(df["return_saham"].to_numpy())
