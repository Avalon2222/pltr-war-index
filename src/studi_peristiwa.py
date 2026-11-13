"""
studi_peristiwa.py - Event study: apakah saham bergerak "tidak normal" setelah perang pecah?

Ide dasarnya (metode klasik keuangan, MacKinlay 1997):
  1. Ambil 120 hari bursa SEBELUM peristiwa (jendela estimasi). Di situ kita belajar
     hubungan normal saham dengan pasar:  R_saham = alpha + beta * R_pasar  (market model).
  2. Di sekitar peristiwa (jendela peristiwa, misalnya hari -5 s/d +20) kita hitung
     return yang "seharusnya" terjadi menurut model itu.
  3. Abnormal return (AR) = return asli - return seharusnya.
     Cumulative abnormal return (CAR) = jumlah AR dari awal jendela sampai hari ke-t.
  4. Kalau CAR jauh dari nol dibanding "goyangan normal" saham itu, gerakannya
     kemungkinan besar bukan kebetulan.

Hari 0 = hari bursa pertama PADA atau SETELAH tanggal peristiwa. Perang yang pecah
hari Sabtu (misalnya 7 Oktober 2023) baru bisa direspons pasar hari Senin.

Semua fungsi di sini murni (tanpa Streamlit), jadi mudah dites.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

JENDELA_ESTIMASI = (-130, -11)  # hari relatif terhadap hari 0, dua-duanya inklusif


# ---------------------------------------------------------------------------
# Persiapan data
# ---------------------------------------------------------------------------

def tabel_return(harga: pd.DataFrame) -> pd.DataFrame:
    """Harga format panjang -> return harian format lebar (kolom = ticker, index = tanggal)."""
    lebar = harga.pivot_table(index="tanggal", columns="ticker", values="adj_close").sort_index()
    return lebar.pct_change().iloc[1:]


def tabel_harga(harga: pd.DataFrame, kolom: str = "close") -> pd.DataFrame:
    return harga.pivot_table(index="tanggal", columns="ticker", values=kolom).sort_index()


def posisi_hari_nol(index: pd.DatetimeIndex, tanggal) -> int | None:
    """Posisi hari bursa pertama pada/setelah `tanggal`. None kalau di luar data."""
    pos = int(index.searchsorted(pd.Timestamp(tanggal), side="left"))
    return pos if pos < len(index) else None


# ---------------------------------------------------------------------------
# Satu peristiwa
# ---------------------------------------------------------------------------

@dataclass
class HasilPeristiwa:
    tabel: pd.DataFrame      # hari_relatif, tanggal, return, return_normal, ar, car
    alpha: float
    beta: float
    sigma: float             # simpangan baku residual di jendela estimasi
    car: float               # CAR di akhir jendela
    t_stat: float
    p_value: float
    hari_nol: pd.Timestamp

    @property
    def signifikan(self) -> bool:
        return self.p_value < 0.05


def p_dua_sisi(t: float) -> float:
    """p-value dua sisi dari statistik t (pendekatan distribusi normal)."""
    if not np.isfinite(t):
        return float("nan")
    return math.erfc(abs(t) / math.sqrt(2))


def market_model(r_saham: pd.Series, r_pasar: pd.Series | None) -> tuple[float, float, float]:
    """Regresi OLS sederhana R_saham = alpha + beta * R_pasar. Mengembalikan (alpha, beta, sigma).

    Kalau r_pasar None, modelnya "mean-adjusted": return normal = rata-rata return saham.
    """
    y = r_saham.to_numpy(dtype=float)
    if r_pasar is None:
        y = y[np.isfinite(y)]      # hari tanpa harga (NaN) tidak boleh membuat sigma ikut NaN
        alpha, beta = float(np.mean(y)), 0.0
        resid = y - alpha
        ddof = 1
    else:
        x = r_pasar.to_numpy(dtype=float)
        ok = np.isfinite(x) & np.isfinite(y)
        x, y = x[ok], y[ok]
        beta = float(np.cov(x, y, ddof=1)[0, 1] / np.var(x, ddof=1))
        alpha = float(y.mean() - beta * x.mean())
        resid = y - (alpha + beta * x)
        ddof = 2
    sigma = float(np.sqrt(np.sum(resid**2) / (len(resid) - ddof)))
    return alpha, beta, sigma


def studi_satu(
    ret: pd.DataFrame,
    tanggal,
    saham: str = "PLTR",
    patokan: str | None = "SPY",
    jendela: tuple[int, int] = (-5, 20),
    estimasi: tuple[int, int] = JENDELA_ESTIMASI,
) -> HasilPeristiwa | None:
    """Event study untuk satu tanggal. None kalau data sebelum/sesudahnya tidak cukup."""
    nol = posisi_hari_nol(ret.index, tanggal)
    if nol is None:
        return None
    e0, e1 = nol + estimasi[0], nol + estimasi[1]
    j0, j1 = nol + jendela[0], nol + jendela[1]
    if e0 < 0 or j1 >= len(ret) or j0 < 0:
        return None

    est = ret.iloc[e0 : e1 + 1]
    alpha, beta, sigma = market_model(est[saham], est[patokan] if patokan else None)

    jen = ret.iloc[j0 : j1 + 1]
    normal = alpha + beta * jen[patokan] if patokan else pd.Series(alpha, index=jen.index)
    ar = jen[saham] - normal
    tabel = pd.DataFrame(
        {
            "hari_relatif": np.arange(jendela[0], jendela[1] + 1),
            "tanggal": jen.index,
            "return": jen[saham].to_numpy(),
            "return_normal": normal.to_numpy(),
            "ar": ar.to_numpy(),
        }
    )
    tabel["car"] = tabel["ar"].cumsum()
    car = float(tabel["car"].iloc[-1])
    t = car / (sigma * math.sqrt(len(tabel)))
    return HasilPeristiwa(tabel, alpha, beta, sigma, car, t, p_dua_sisi(t), ret.index[nol])


# ---------------------------------------------------------------------------
# Banyak peristiwa
# ---------------------------------------------------------------------------

def ada_laporan_keuangan(hari_nol: pd.Timestamp, index: pd.DatetimeIndex, tanggal_laporan,
                         jendela: tuple[int, int]) -> str | None:
    """Kuartal laporan keuangan PLTR yang reaksinya jatuh di dalam jendela, kalau ada.

    Palantir merilis laporan setelah bursa tutup, jadi reaksi pasarnya di hari bursa berikutnya.
    """
    nol = index.get_loc(hari_nol)
    awal = index[max(nol + jendela[0], 0)]
    akhir = index[min(nol + jendela[1], len(index) - 1)]
    for tgl, kuartal in tanggal_laporan:
        pos = posisi_hari_nol(index, pd.Timestamp(tgl) + pd.Timedelta(days=1))
        if pos is not None and awal <= index[pos] <= akhir:
            return kuartal
    return None


def studi_semua(
    ret: pd.DataFrame,
    peristiwa: pd.DataFrame,
    saham: str = "PLTR",
    patokan: str | None = "SPY",
    jendela: tuple[int, int] = (-5, 20),
    laporan: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, dict[int, HasilPeristiwa]]:
    """Jalankan studi_satu untuk setiap baris peristiwa.

    Mengembalikan (ringkasan, detail). Ringkasan punya satu baris per peristiwa yang datanya cukup.
    """
    daftar_laporan = []
    if laporan is not None:
        daftar_laporan = list(zip(laporan["tanggal_rilis"], laporan["kuartal"]))
    baris, detail = [], {}
    for i, p in peristiwa.iterrows():
        h = studi_satu(ret, p["tanggal"], saham, patokan, jendela)
        if h is None:
            continue
        detail[i] = h
        ar_hari = h.tabel.set_index("hari_relatif")["ar"]
        baris.append(
            {
                "id": i,
                "tanggal": p["tanggal"],
                "hari_nol": h.hari_nol,
                "peristiwa": p["peristiwa"],
                "kategori": p["kategori"],
                "kawasan": p["kawasan"],
                "ar_hari0": float(ar_hari.get(0, np.nan)),
                "car_0_5": float(ar_hari.loc[0 : min(5, jendela[1])].sum()),
                "car": h.car,
                "t_stat": h.t_stat,
                "p_value": h.p_value,
                "beta": h.beta,
                "laporan_keuangan": ada_laporan_keuangan(h.hari_nol, ret.index, daftar_laporan, jendela),
            }
        )
    return pd.DataFrame(baris), detail


def rata_rata_car(detail: dict[int, HasilPeristiwa], ids=None) -> pd.DataFrame:
    """Rata-rata jalur CAR lintas peristiwa + interval kepercayaan 95%.

    Kolom: hari_relatif, car_rata, batas_bawah, batas_atas, n.
    """
    ids = list(detail) if ids is None else [i for i in ids if i in detail]
    if not ids:
        return pd.DataFrame(columns=["hari_relatif", "car_rata", "batas_bawah", "batas_atas", "n"])
    jalur = pd.concat({i: detail[i].tabel.set_index("hari_relatif")["car"] for i in ids}, axis=1)
    rata = jalur.mean(axis=1)
    n = jalur.notna().sum(axis=1)
    se = jalur.std(axis=1, ddof=1) / np.sqrt(n)
    return pd.DataFrame(
        {
            "hari_relatif": jalur.index,
            "car_rata": rata.to_numpy(),
            "batas_bawah": (rata - 1.96 * se).to_numpy(),
            "batas_atas": (rata + 1.96 * se).to_numpy(),
            "n": n.to_numpy(),
        }
    )


def uji_plasebo(
    ret: pd.DataFrame,
    n_peristiwa: int,
    saham: str = "PLTR",
    patokan: str | None = "SPY",
    jendela: tuple[int, int] = (-5, 20),
    n_ulang: int = 500,
    seed: int = 7,
) -> np.ndarray:
    """Distribusi rata-rata CAR dari tanggal ACAK (tanpa perang).

    Setiap ulangan memilih `n_peristiwa` hari bursa acak lalu menghitung rata-rata CAR-nya.
    Kalau rata-rata CAR perang sungguhan biasa saja dibanding distribusi ini, berarti
    perang tidak membuat saham bergerak lebih aneh daripada hari-hari biasa.
    """
    rng = np.random.default_rng(seed)
    awal = -JENDELA_ESTIMASI[0]
    akhir = len(ret) - 1 - jendela[1]
    if akhir <= awal or n_peristiwa < 1:
        return np.array([])

    # Pra-hitung CAR untuk semua kandidat hari 0 sekali saja, lalu ambil sampel.
    kandidat = np.arange(awal, akhir + 1)
    y = ret[saham].to_numpy(dtype=float)
    x = ret[patokan].to_numpy(dtype=float) if patokan else None
    car_semua = np.empty(len(kandidat))
    for k, nol in enumerate(kandidat):
        e = slice(nol + JENDELA_ESTIMASI[0], nol + JENDELA_ESTIMASI[1] + 1)
        j = slice(nol + jendela[0], nol + jendela[1] + 1)
        if x is None:
            alpha, beta = y[e].mean(), 0.0
            normal = alpha
        else:
            xe, ye = x[e], y[e]
            beta = np.cov(xe, ye, ddof=1)[0, 1] / np.var(xe, ddof=1)
            alpha = ye.mean() - beta * xe.mean()
            normal = alpha + beta * x[j]
        car_semua[k] = np.sum(y[j] - normal)

    sampel = rng.choice(len(kandidat), size=(n_ulang, n_peristiwa), replace=True)
    return car_semua[sampel].mean(axis=1)


def p_plasebo(nilai: float, distribusi: np.ndarray) -> float:
    """p-value dua sisi berbasis persentil: seberapa ekstrem nilai asli di dalam distribusi acak."""
    if len(distribusi) == 0 or not np.isfinite(nilai):
        return float("nan")
    bawah = np.mean(distribusi <= nilai)
    atas = np.mean(distribusi >= nilai)
    return float(min(1.0, 2 * min(bawah, atas)))
