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


def test_muat_konflik_buang_tanggal_rusak(tmp_path):
    f = tmp_path / "konflik.csv"
    f.write_text(
        "tanggal,korban_total,kejadian_total,status\n2024-01-05,10,2,final\n2024-13-40,5,1,final\n2024-01-06,7,1,final\n",
        encoding="utf-8",
    )
    df = muat_data.muat_konflik(f)
    assert pd.api.types.is_datetime64_any_dtype(df["tanggal"])
    assert df["korban_total"].tolist() == [10, 7]
    assert intensitas.konflik_mingguan(df)["korban"].sum() == 17


def test_muat_harga_snapshot_tanggal_dan_harga_rusak(tmp_path):
    f = tmp_path / "harga.csv"
    f.write_text(
        "tanggal,ticker,close,adj_close,volume\n"
        "2024-01-02,PLTR,17.0,17.0,100\n2024-01-03,PLTR,n.a.,n.a.,0\nkemarin,PLTR,18.0,18.0,100\n",
        encoding="utf-8",
    )
    df = muat_data.muat_harga_snapshot(f)
    assert pd.api.types.is_datetime64_any_dtype(df["tanggal"])
    assert pd.api.types.is_float_dtype(df["close"])
    assert len(df) == 2
    assert pd.isna(df.loc[1, "close"])
