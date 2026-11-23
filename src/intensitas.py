"""
intensitas.py - Menghubungkan "seberapa panas dunia" (korban konflik UCDP) dengan return saham.

Event study melihat tanggal-tanggal tertentu. Modul ini melihat semuanya sekaligus:
setiap minggu, berapa korban konflik di dunia, dan berapa return PLTR minggu itu?

Catatan penting: korelasi bukan sebab-akibat. Korban konflik juga tercatat dengan jeda
(laporan menyusul), dan harga saham digerakkan banyak hal lain (suku bunga, laporan
keuangan, hype AI). Hasilnya dibaca sebagai petunjuk, bukan bukti.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TEATER = [
    "Rusia-Ukraina", "Israel-Gaza-Lebanon", "Iran", "Yaman", "Suriah", "Sudan",
    "Etiopia", "Myanmar", "RD Kongo", "Sahel", "Lainnya",
]


def konflik_mingguan(konflik: pd.DataFrame, teater: list[str] | None = None) -> pd.DataFrame:
    """Korban harian -> mingguan (minggu berakhir Jumat, sama seperti minggu bursa).

    `teater` None berarti semua teater (korban_total).
    """
    df = konflik.set_index("tanggal")
    if isinstance(teater, str):   # satu teater sebagai teks, bukan daftar huruf
        teater = [teater]
    if teater:
        seri = df[[f"korban_{t}" for t in teater]].sum(axis=1)
    else:
        seri = df["korban_total"]
    mingguan = seri.resample("W-FRI")
    hasil = mingguan.sum().to_frame("korban")
    hasil["log_korban"] = np.log1p(hasil["korban"])
    # Minggu pertama/terakhir sering terpotong (data berakhir Rabu, misalnya). Korbannya jadi
    # terlihat turun padahal harinya saja yang kurang, jadi perubahan_log hanya dihitung
    # antara dua minggu yang sama-sama lengkap 7 hari.
    lengkap = mingguan.size() == 7
    hasil["perubahan_log"] = hasil["log_korban"].diff().where(lengkap & lengkap.shift(1, fill_value=False))
    return hasil


def return_mingguan(harga_lebar: pd.DataFrame) -> pd.DataFrame:
    """Harga penutupan harian (kolom = ticker) -> return mingguan (Jumat ke Jumat)."""
    return harga_lebar.resample("W-FRI").last().pct_change()


def gabung_mingguan(konflik: pd.DataFrame, harga_lebar: pd.DataFrame, saham: str = "PLTR",
                    patokan: str | None = "SPY", teater: list[str] | None = None) -> pd.DataFrame:
    """Tabel mingguan: korban, perubahan_log, return saham, return lebih (saham - patokan)."""
    k = konflik_mingguan(konflik, teater)
    r = return_mingguan(harga_lebar)
    # Patokan sama dengan saham: kolomnya jangan dipilih dua kali. Kalau dipilih dua kali, keduanya
    # ikut diganti nama jadi return_saham, lalu df[patokan] melempar KeyError.
    df = k.join(r[list(dict.fromkeys([saham] + ([patokan] if patokan else [])))], how="inner")
    df["return_saham"] = df[saham]
    df["return_lebih"] = df["return_saham"] - (df[patokan] if patokan else 0.0)
    if saham != patokan:
        df = df.drop(columns=saham)
    return df.dropna(subset=["perubahan_log", "return_saham"])


def korelasi_lag(df: pd.DataFrame, kolom_x: str = "perubahan_log", kolom_y: str = "return_lebih",
                 lag_maks: int = 4) -> pd.DataFrame:
    """Korelasi Pearson x(t) dengan y(t + lag).

    lag positif: lonjakan korban minggu ini vs return beberapa minggu SESUDAHNYA.
    lag negatif: return minggu-minggu SEBELUM lonjakan (pasar "tahu duluan"?).
    Batas ±1.96/sqrt(n) = kira-kira batas korelasi yang masih bisa terjadi karena kebetulan.
    """
    baris = []
    # lag_maks negatif dibaca sebagai jangkauannya (|-4| = 4); range(4, -3) kosong tanpa ini.
    lag_maks = abs(int(lag_maks))
    for lag in range(-lag_maks, lag_maks + 1):
        y = df[kolom_y].shift(-lag)
        ok = df[kolom_x].notna() & y.notna()
        n = int(ok.sum())
        r = float(np.corrcoef(df.loc[ok, kolom_x], y[ok])[0, 1]) if n > 2 else float("nan")
        baris.append({"lag": lag, "korelasi": r, "n": n, "batas": 1.96 / np.sqrt(n) if n else np.nan})
    # Kolom tetap ada walau tidak ada lag sama sekali, supaya grafik tidak KeyError.
    return pd.DataFrame(baris, columns=["lag", "korelasi", "n", "batas"])


def minggu_terpanas(df: pd.DataFrame, persentil: float = 0.9) -> pd.DataFrame:
    """Bandingkan return lebih di minggu dengan lonjakan korban terbesar vs minggu lainnya.

    Lonjakan = perubahan_log di atas persentil tertentu (default 10% teratas).
    """
    if not 0 < persentil < 1:
        raise ValueError("persentil harus di antara 0 dan 1, misalnya 0.9")
    batas = df["perubahan_log"].quantile(persentil)
    ada = df["perubahan_log"].notna()  # minggu tanpa angka korban tidak masuk kelompok mana pun
    panas = ada & (df["perubahan_log"] >= batas)
    ringkas = []
    for label, maska in [("Minggu lonjakan korban", panas), ("Minggu lainnya", ada & ~panas)]:
        x = df.loc[maska, "return_lebih"]
        ringkas.append({
            "kelompok": label,
            "jumlah_minggu": int(maska.sum()),
            "rata_return_lebih": float(x.mean()),
            "median_return_lebih": float(x.median()),
            "porsi_naik": float((x > 0).mean()),
        })
    return pd.DataFrame(ringkas)


def korelasi_bergulir(ret_harian: pd.DataFrame, saham: str = "PLTR", pembanding=("ITA", "QQQ"),
                      jendela: int = 120) -> pd.DataFrame:
    """Korelasi bergulir return harian saham dengan beberapa pembanding.

    Dipakai untuk menjawab: PLTR lebih mirip saham pertahanan (ITA) atau saham teknologi (QQQ)?
    """
    # Pembanding yang tidak ada di data (mis. unduhan live gagal untuk satu ticker) dilewati,
    # dan baris hanya dibuang bila SEMUA korelasinya kosong; dengan dropna() biasa, satu
    # pembanding yang kosong total membuat seluruh grafik ikut kosong.
    # Satu ticker sebagai teks ("ITA") jangan sampai diiterasi per huruf ("I", "T", "A").
    if isinstance(pembanding, str):
        pembanding = (pembanding,)
    hasil = {p: ret_harian[saham].rolling(jendela).corr(ret_harian[p]) for p in pembanding if p in ret_harian}
    return pd.DataFrame(hasil, index=ret_harian.index).dropna(how="all")


def kinerja_relatif(harga_lebar: pd.DataFrame, mulai=None) -> pd.DataFrame:
    """Harga dinormalisasi: nilai 100 di tanggal mulai.

    Tiap kolom dibagi harga pertamanya yang tersedia. Saham yang baru melantai setelah `mulai`
    (misalnya PLTR, IPO 30 September 2020) mulai dari 100 di hari pertamanya, bukan NaN semua.
    """
    df = harga_lebar if mulai is None else harga_lebar[harga_lebar.index >= pd.Timestamp(mulai)]
    df = df.dropna(how="all")
    if df.empty:
        return df.copy()  # tanggal mulai setelah data terakhir: tidak ada yang dinormalisasi
    # Harga 0 atau negatif (baris rusak dari sumber data) tidak boleh jadi pembagi: hasilnya
    # inf dan seluruh garis saham itu hilang dari grafik. Pakai harga positif pertama.
    pertama = df.where(df > 0).bfill().iloc[0]
    return df / pertama * 100
