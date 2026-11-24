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


def test_konflik_mingguan_abaikan_minggu_terpotong():
    k = _konflik(31)  # Senin 1 Jan s.d. Rabu 31 Jan 2024: minggu pertama & terakhir tidak lengkap
    m = intensitas.konflik_mingguan(k)
    assert m["perubahan_log"].iloc[0:2].isna().all()   # minggu terpotong + minggu sesudahnya
    assert m["perubahan_log"].iloc[2:4].notna().all()  # 19 & 26 Jan: dua minggu lengkap
    assert np.isnan(m["perubahan_log"].iloc[-1])       # 2 Feb: hanya 5 hari (27-31 Jan)
    assert m["korban"].iloc[-1] == 5 * len(intensitas.TEATER)


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


def test_ringkas_harian_tidak_kehilangan_korban_kecil_yang_dibagi():
    kejadian = pd.DataFrame({
        "date_start": ["2024-03-01"], "date_end": ["2024-03-30"], "country": ["Sudan"], "best": [10],
    })
    h = siapkan_konflik.ringkas_harian(kejadian)
    assert len(h) == 30
    assert h["korban_Sudan"].sum() == 10        # sebelumnya 0: 0,33 per hari dibulatkan ke 0
    assert h["korban_total"].sum() == 10
    assert h["kejadian_total"].sum() == 1
    assert (h["korban_Sudan"] >= 0).all()


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


def test_kinerja_relatif_saham_yang_baru_melantai():
    idx = pd.date_range("2020-09-28", periods=4)
    h = pd.DataFrame({"PLTR": [np.nan, np.nan, 10.0, 12.0], "ITA": [80.0, 82.0, 84.0, 88.0]}, index=idx)
    k = intensitas.kinerja_relatif(h)
    assert k["PLTR"].iloc[:2].isna().all()
    assert k["PLTR"].iloc[2:].tolist() == [100, 120]
    assert k["ITA"].iloc[0] == 100 and k["ITA"].iloc[-1] == pytest.approx(110)


@pytest.mark.parametrize("kategori", ["eskalsi", ""])
def test_muat_peristiwa_tolak_kategori_salah(tmp_path, kategori):
    csv = tmp_path / "peristiwa.csv"
    csv.write_text("tanggal,peristiwa,kategori,kawasan,keterangan,sumber\n"
                   "2024-01-01,Uji,eskalasi,Asia,,\n"
                   f"2024-01-02,Uji salah,{kategori},Asia,,\n")
    with pytest.raises(ValueError, match="Kategori peristiwa tidak dikenal"):
        muat_data.muat_peristiwa(csv)


def test_minggu_terpanas_abaikan_minggu_tanpa_angka():
    df = pd.DataFrame({"perubahan_log": [np.nan] + list(range(10)), "return_lebih": [5.0] + [0.0] * 10})
    hasil = intensitas.minggu_terpanas(df, 0.9).set_index("kelompok")
    assert hasil["jumlah_minggu"].sum() == 10
    assert hasil.loc["Minggu lainnya", "rata_return_lebih"] == 0


def test_kinerja_relatif_tanggal_mulai_setelah_data_habis():
    idx = pd.date_range("2024-01-01", periods=3)
    h = pd.DataFrame({"A": [10, 20, 5]}, index=idx)
    assert intensitas.kinerja_relatif(h, "2025-01-01").empty


@pytest.mark.parametrize("persentil", [0, 1, 90, -0.1])
def test_minggu_terpanas_menolak_persentil_di_luar_0_1(persentil):
    df = pd.DataFrame({"perubahan_log": np.arange(10.0), "return_lebih": np.zeros(10)})
    with pytest.raises(ValueError):
        intensitas.minggu_terpanas(df, persentil)


def test_muat_peristiwa_kategori_huruf_besar_dan_spasi(tmp_path):
    csv = tmp_path / "peristiwa.csv"
    csv.write_text("tanggal,peristiwa,kategori,kawasan,keterangan,sumber\n"
                   "2024-01-01,Uji,Eskalasi ,Asia,,\n"
                   "2024-01-02,Uji dua, PERANG_BARU,Asia,,\n")
    df = muat_data.muat_peristiwa(csv)
    assert list(df["kategori"]) == ["eskalasi", "perang_baru"]
    assert list(df["label_kategori"]) == ["Eskalasi", "Perang baru pecah"]


def test_korelasi_bergulir_pembanding_hilang_atau_kosong():
    rng = np.random.default_rng(3)
    idx = pd.bdate_range("2024-01-01", periods=60)
    ret = pd.DataFrame({"PLTR": rng.normal(0, 0.02, 60), "QQQ": rng.normal(0, 0.01, 60), "ITA": np.nan}, index=idx)
    hasil = intensitas.korelasi_bergulir(ret, pembanding=("ITA", "QQQ", "XLK"), jendela=20)
    assert list(hasil.columns) == ["ITA", "QQQ"]
    assert len(hasil) == 41 and hasil["QQQ"].notna().all()


def test_gabung_mingguan_patokan_sama_dengan_saham():
    df = intensitas.gabung_mingguan(_konflik(), _harga_lebar(), saham="SPY", patokan="SPY")
    assert len(df) > 0
    assert (df["return_lebih"] == 0).all()   # saham dikurangi dirinya sendiri


def test_korelasi_lag_tabel_kosong_tetap_punya_kolom():
    kosong = pd.DataFrame({"perubahan_log": pd.Series(dtype=float), "return_lebih": pd.Series(dtype=float)})
    hasil = intensitas.korelasi_lag(kosong, lag_maks=-1)
    assert list(hasil.columns) == ["lag", "korelasi", "n", "batas"]


def test_korelasi_lag_maks_negatif_dibaca_mutlak():
    df = pd.DataFrame({"perubahan_log": np.arange(20.0), "return_lebih": np.arange(20.0) ** 2})
    assert intensitas.korelasi_lag(df, lag_maks=-2)["lag"].tolist() == [-2, -1, 0, 1, 2]


def test_konflik_mingguan_satu_teater_sebagai_teks():
    k = _konflik(14)
    m = intensitas.konflik_mingguan(k, "Rusia-Ukraina")
    assert m["korban"].iloc[1] == 7


def test_minggu_terpanas_return_kosong_tidak_dihitung_turun():
    # Dua minggu lonjakan tanpa return patokan: porsi_naik dihitung dari minggu yang ada angkanya saja.
    df = pd.DataFrame({"perubahan_log": np.arange(20.0),
                       "return_lebih": [0.0] * 16 + [0.02, 0.03, np.nan, np.nan]})
    panas = intensitas.minggu_terpanas(df, 0.8).set_index("kelompok").loc["Minggu lonjakan korban"]
    assert panas["jumlah_minggu"] == 2
    assert panas["porsi_naik"] == 1.0
