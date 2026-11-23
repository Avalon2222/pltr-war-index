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


def test_kinerja_relatif_lewati_harga_nol_di_awal():
    idx = pd.date_range("2024-01-01", periods=3, freq="D")
    harga = pd.DataFrame({"PLTR": [0.0, 20.0, 30.0], "SPY": [100.0, 110.0, 120.0]}, index=idx)
    hasil = intensitas.kinerja_relatif(harga)
    assert hasil["PLTR"].iloc[1:].tolist() == [100.0, 150.0]
    assert hasil["SPY"].iloc[0] == 100.0


def test_muat_peristiwa_tanggal_sama_tetap_urutan_csv(tmp_path):
    baris = [{"tanggal": f"2024-01-0{i % 3 + 1}", "peristiwa": f"E{i:02d}", "kategori": "eskalasi",
              "kawasan": "x", "keterangan": "", "sumber": ""} for i in range(60)]
    csv = tmp_path / "peristiwa.csv"
    pd.DataFrame(baris).to_csv(csv, index=False)
    df = muat_data.muat_peristiwa(csv)
    hari_pertama = df[df["tanggal"] == "2024-01-01"]["peristiwa"].tolist()
    assert hari_pertama == sorted(hari_pertama)
