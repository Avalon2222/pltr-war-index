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
    return pd.read_csv(path, parse_dates=["tanggal"])


def muat_harga(live: bool = False) -> tuple[pd.DataFrame, str]:
    """Mengembalikan (harga, sumber). sumber = 'live' atau 'snapshot'."""
    if live:
        try:
            return ambil_harga.ambil_semua(jeda=0.2), "live"
        except Exception:  # noqa: BLE001 - apa pun errornya, jatuh ke snapshot
            pass
    return muat_harga_snapshot(), "snapshot"


def muat_peristiwa(path: Path = DIR_DATA / "peristiwa_perang.csv") -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["tanggal"])
    df["label_kategori"] = df["kategori"].map(KATEGORI)
    return df.sort_values("tanggal").reset_index(drop=True)


def muat_konflik(path: Path = DIR_DATA / "konflik_harian.csv") -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["tanggal"])


def muat_laporan(path: Path = DIR_DATA / "laporan_keuangan_pltr.csv") -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["tanggal_rilis"])
