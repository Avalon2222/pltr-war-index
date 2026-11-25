"""
muat_data.py - Membaca semua CSV di folder data/ dengan tipe kolom yang benar.

Harga saham bisa diambil langsung dari Yahoo Finance (live). Kalau gagal (internet
mati, Yahoo berubah, kena limit), aplikasi otomatis memakai snapshot data/harga_saham.csv
yang diperbarui GitHub Actions setiap minggu.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src import ambil_harga

DIR_DATA = Path(__file__).resolve().parent.parent / "data"

KATEGORI = {
    "perang_baru": "Perang baru pecah",
    "eskalasi": "Eskalasi",
    "keterlibatan_as": "Serangan AS",
    "deeskalasi": "Gencatan senjata / damai",
}
URUTAN_KATEGORI = list(KATEGORI)


def muat_harga_snapshot(path: Path = DIR_DATA / "harga_saham.csv") -> pd.DataFrame:
    df = pd.read_csv(path)
    # Tanggal rusak membuat seluruh kolom tanggal tetap teks; harga teks ("n.a.") membuat kolom close
    # jadi teks dan pivot harga gagal. Tanggal rusak dibuang, harga rusak jadi NaN (hari tanpa harga).
    df["tanggal"] = pd.to_datetime(df["tanggal"], errors="coerce")
    for kolom in ("close", "adj_close", "volume"):
        if kolom in df.columns:
            df[kolom] = pd.to_numeric(df[kolom], errors="coerce")
    return df.dropna(subset=["tanggal"]).reset_index(drop=True)


def muat_harga(live: bool = False) -> tuple[pd.DataFrame, str]:
    """Mengembalikan (harga, sumber). sumber = 'live' atau 'snapshot'."""
    if live:
        try:
            return ambil_harga.ambil_semua(jeda=0.2), "live"
        except Exception:  # noqa: BLE001 - apa pun errornya, jatuh ke snapshot
            pass
    return muat_harga_snapshot(), "snapshot"


def muat_peristiwa(path: Path = DIR_DATA / "peristiwa_perang.csv") -> pd.DataFrame:
    df = pd.read_csv(path)
    tanggal = pd.to_datetime(df["tanggal"], errors="coerce")
    if tanggal.isna().any():
        # Tanpa cek ini satu tanggal salah ketik (mis. 2023-13-01) membuat seluruh kolom jadi teks,
        # dan event study baru gagal jauh di belakang dengan pesan yang membingungkan.
        rusak = df.loc[tanggal.isna(), "peristiwa"].fillna("(tanpa nama)").tolist()
        raise ValueError(f"Tanggal peristiwa tidak valid di {Path(path).name}: {rusak}")
    df["tanggal"] = tanggal
    # " Eskalasi" atau "ESKALASI" dari suntingan manual tetap dikenali.
    df["kategori"] = df["kategori"].str.strip().str.lower()
    asing = sorted(set(df["kategori"].dropna()) - set(KATEGORI))
    if asing or df["kategori"].isna().any():
        # Tanpa cek ini, salah ketik kategori diam-diam jadi label kosong di grafik.
        raise ValueError(f"Kategori peristiwa tidak dikenal di {Path(path).name}: {asing or ['(kosong)']}. "
                         f"Pilihan: {URUTAN_KATEGORI}")
    df["label_kategori"] = df["kategori"].map(KATEGORI)
    # Sort stabil: peristiwa di tanggal yang sama tetap urut seperti di CSV, sehingga nomor
    # urutnya (dipakai sebagai id di event study) tidak berubah tiap kali data dimuat.
    return df.sort_values("tanggal", kind="mergesort").reset_index(drop=True)


def muat_konflik(path: Path = DIR_DATA / "konflik_harian.csv") -> pd.DataFrame:
    df = pd.read_csv(path)
    # Satu tanggal rusak membuat parse_dates diam-diam menyerah (kolom tetap teks), lalu resample
    # mingguan gagal untuk seluruh tabel. Baris itu dibuang saja, sama seperti muat_laporan.
    df["tanggal"] = pd.to_datetime(df["tanggal"], errors="coerce")
    return df.dropna(subset=["tanggal"]).reset_index(drop=True)


def muat_laporan(path: Path = DIR_DATA / "laporan_keuangan_pltr.csv") -> pd.DataFrame:
    df = pd.read_csv(path)
    # Baris dengan tanggal rusak atau kosong dibuang; kalau tidak, kolomnya jadi teks dan
    # pengecekan "ada laporan keuangan di jendela?" gagal untuk semua peristiwa.
    df["tanggal_rilis"] = pd.to_datetime(df["tanggal_rilis"], errors="coerce")
    return df.dropna(subset=["tanggal_rilis"]).reset_index(drop=True)
