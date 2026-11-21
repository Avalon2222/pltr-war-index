"""Tes pemuat data saat CSV hasil suntingan manual tidak rapi."""

import pandas as pd
import pytest

from src import intensitas, muat_data


def test_muat_peristiwa_tolak_tanggal_rusak(tmp_path):
    csv = tmp_path / "peristiwa.csv"
    csv.write_text(
        "tanggal,peristiwa,kategori,kawasan\n"
        "2023-10-07,Serangan 7 Oktober,perang_baru,Timur Tengah\n"
        "2023-13-01,Salah ketik,eskalasi,Eropa & Kaukasus\n"
    )
    with pytest.raises(ValueError, match="Salah ketik"):
        muat_data.muat_peristiwa(csv)


def test_muat_laporan_buang_tanggal_rusak(tmp_path):
    csv = tmp_path / "laporan.csv"
    csv.write_text("tanggal_rilis,kuartal\n2024-02-05,Q4 2023\nbelum diumumkan,Q1 2024\n,Q2 2024\n")
    lap = muat_data.muat_laporan(csv)
    assert pd.api.types.is_datetime64_any_dtype(lap["tanggal_rilis"])
    assert lap["kuartal"].tolist() == ["Q4 2023"]
