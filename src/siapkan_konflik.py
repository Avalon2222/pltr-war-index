"""
siapkan_konflik.py - Meringkas data kekerasan bersenjata UCDP menjadi deret harian.

Sumber: Uppsala Conflict Data Program (UCDP), Universitas Uppsala.
  - GED 26.1 (final, 1989-2025):  https://ucdp.uu.se/downloads/ged/ged261-csv.zip
  - UCDP Candidate (awal, 2026):   https://ucdp.uu.se/downloads/candidateged/GEDEvent_v26_01_26_09.csv
    (data Candidate dirilis tiap bulan; skrip ini mencoba bulan-bulan berikutnya otomatis)

Satu baris GED = satu kejadian kekerasan dengan minimal satu korban jiwa, lengkap dengan
tanggal, negara, dan perkiraan korban (`best`). File mentahnya sekitar 290 MB, jadi
yang disimpan ke repo hanya ringkasan harian per "teater" konflik (beberapa ratus KB).

Cara pakai (butuh internet, sekitar 1-2 menit):
    python -m src.siapkan_konflik
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pandas as pd
import requests

URL_GED = "https://ucdp.uu.se/downloads/ged/ged261-csv.zip"
URL_KANDIDAT = "https://ucdp.uu.se/downloads/candidateged/GEDEvent_v26_01_26_{bulan:02d}.csv"
BULAN_KANDIDAT_AWAL = 9  # rilis Candidate terbaru yang sudah dicek
MULAI = "2020-01-01"

DIR_DATA = Path(__file__).resolve().parent.parent / "data"
DIR_MENTAH = DIR_DATA / "mentah"
PATH_CSV = DIR_DATA / "konflik_harian.csv"

# Negara (nama UCDP) -> teater konflik. Negara lain masuk "Lainnya".
TEATER = {
    "Ukraine": "Rusia-Ukraina",
    "Russia (Soviet Union)": "Rusia-Ukraina",
    "Israel": "Israel-Gaza-Lebanon",
    "Lebanon": "Israel-Gaza-Lebanon",
    "Iran": "Iran",
    "Yemen (North Yemen)": "Yaman",
    "Syria": "Suriah",
    "Sudan": "Sudan",
    "Ethiopia": "Etiopia",
    "Myanmar (Burma)": "Myanmar",
    "DR Congo (Zaire)": "RD Kongo",
    "Mali": "Sahel",
    "Burkina Faso": "Sahel",
    "Niger": "Sahel",
}
URUTAN_TEATER = [
    "Rusia-Ukraina", "Israel-Gaza-Lebanon", "Iran", "Yaman", "Suriah", "Sudan",
    "Etiopia", "Myanmar", "RD Kongo", "Sahel", "Lainnya",
]
KOLOM = ["date_start", "date_end", "country", "best"]


def _unduh(url: str) -> bytes:
    r = requests.get(url, timeout=300)
    r.raise_for_status()
    return r.content


def baca_ged(mentah: bytes) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(mentah)) as z:
        nama = next(n for n in z.namelist() if n.endswith(".csv"))
        with z.open(nama) as f:
            return pd.read_csv(f, usecols=KOLOM, low_memory=False)


def baca_kandidat() -> tuple[pd.DataFrame, str]:
    """Ambil rilis Candidate paling baru yang tersedia (coba bulan 12 turun ke bulan awal)."""
    for bulan in range(12, BULAN_KANDIDAT_AWAL - 1, -1):
        url = URL_KANDIDAT.format(bulan=bulan)
        r = requests.get(url, timeout=300)
        if r.ok:
            return pd.read_csv(io.BytesIO(r.content), usecols=KOLOM), url
    raise RuntimeError("Tidak ada rilis UCDP Candidate yang bisa diunduh")


def ringkas_harian(kejadian: pd.DataFrame, mulai: str = MULAI) -> pd.DataFrame:
    """Kejadian -> tabel harian lebar: tanggal, korban_<teater>..., korban_total, kejadian_total.

    Sebagian kejadian UCDP hanya diketahui rentang tanggalnya (misalnya "Agustus-Oktober 2022",
    puluhan ribu korban dari satu laporan). Kalau semua korban ditaruh di `date_start`, grafik
    mingguan akan punya paku palsu. Karena itu korban dibagi rata ke setiap hari antara
    `date_start` dan `date_end`. Hari tanpa kejadian tetap muncul dengan nilai 0.
    """
    df = kejadian.copy()
    df["mulai"] = pd.to_datetime(df["date_start"]).dt.normalize()
    akhir = df["date_end"] if "date_end" in df else df["date_start"]
    df["akhir"] = pd.to_datetime(akhir).dt.normalize().fillna(df["mulai"])
    df["hari"] = ((df["akhir"] - df["mulai"]).dt.days + 1).clip(lower=1)
    # Satu baris per (kejadian, hari) dengan korban dibagi rata.
    df = df.loc[df.index.repeat(df["hari"])].copy()
    df["tanggal"] = df["mulai"] + pd.to_timedelta(df.groupby(level=0).cumcount(), unit="D")
    df["best"] = df["best"] / df["hari"]
    df["kejadian"] = 1 / df["hari"]
    df = df[df["tanggal"] >= pd.Timestamp(mulai)]
    df["teater"] = df["country"].map(TEATER).fillna("Lainnya")

    korban = df.pivot_table(index="tanggal", columns="teater", values="best", aggfunc="sum", fill_value=0)
    korban = korban.reindex(columns=URUTAN_TEATER, fill_value=0)
    korban.columns = [f"korban_{c}" for c in korban.columns]

    hari = pd.date_range(df["tanggal"].min(), df["tanggal"].max(), freq="D")
    hasil = korban.reindex(hari, fill_value=0).round().astype("int64")
    hasil["korban_total"] = hasil.sum(axis=1)
    hasil["kejadian_total"] = df.groupby("tanggal")["kejadian"].sum().reindex(hari, fill_value=0).round().astype("int64")
    hasil.index.name = "tanggal"
    return hasil.reset_index()


def gabung_ged_kandidat(ged: pd.DataFrame, kandidat: pd.DataFrame, mulai: str = MULAI) -> pd.DataFrame:
    """GED final + Candidate -> tabel harian dengan kolom ``status`` ("final" atau "awal").

    Candidate hanya dipakai untuk tanggal setelah GED final berakhir, supaya tidak ada kejadian
    yang terhitung dua kali di masa transisi.
    """
    batas = pd.to_datetime(ged["date_start"]).max()
    kandidat = kandidat[pd.to_datetime(kandidat["date_start"]) > batas]
    semua = pd.concat([ged[KOLOM], kandidat[KOLOM]], ignore_index=True)
    hasil = ringkas_harian(semua, mulai)
    # Rentang yang melewati tanggal mulai kejadian terakhir dipotong, supaya ujung data tidak tampak "sepi".
    hasil = hasil[hasil["tanggal"] <= pd.to_datetime(semua["date_start"]).max()].copy()
    hasil["status"] = (hasil["tanggal"] > batas).map({True: "awal", False: "final"})
    return hasil.reset_index(drop=True)


def main() -> None:
    DIR_MENTAH.mkdir(parents=True, exist_ok=True)
    zip_ged = DIR_MENTAH / "ged261-csv.zip"
    if not zip_ged.exists():
        print("Mengunduh GED 26.1 ...")
        zip_ged.write_bytes(_unduh(URL_GED))
    ged = baca_ged(zip_ged.read_bytes())
    kandidat, url = baca_kandidat()
    print(f"Candidate dipakai: {url}")
    hasil = gabung_ged_kandidat(ged, kandidat)
    hasil.to_csv(PATH_CSV, index=False, date_format="%Y-%m-%d")
    print(f"OK: {len(hasil)} hari ({hasil['tanggal'].min():%Y-%m-%d} s/d {hasil['tanggal'].max():%Y-%m-%d}) -> {PATH_CSV}")

if __name__ == "__main__":
    main()
