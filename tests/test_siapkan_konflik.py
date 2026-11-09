"""Tes pembaca data UCDP di src/siapkan_konflik.py, offline (zip dibuat di memori, unduhan dipalsukan)."""

import io
import zipfile

import pytest

from src import siapkan_konflik

CSV_UCDP = (
    "id,date_start,date_end,country,best,region\n"
    "1,2024-01-01,2024-01-01,Ukraine,12,Europe\n"
    "2,2024-01-02,2024-01-04,Sudan,30,Africa\n"
)


class _Respons:
    def __init__(self, ok=True, isi=b""):
        self.ok = ok
        self.content = isi


def test_baca_ged_dari_zip_hanya_kolom_penting():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("LICENSE.txt", "bukan csv")
        z.writestr("GEDEvent_v26_1.csv", CSV_UCDP)
    df = siapkan_konflik.baca_ged(buf.getvalue())
    assert list(df.columns) == siapkan_konflik.KOLOM
    assert len(df) == 2 and df["best"].sum() == 42


def test_baca_kandidat_ambil_rilis_terbaru(monkeypatch):
    dicoba = []

    def palsu(url, timeout):
        dicoba.append(url)
        return _Respons(ok="_10.csv" in url, isi=CSV_UCDP.encode())

    monkeypatch.setattr(siapkan_konflik.requests, "get", palsu)
    df, url = siapkan_konflik.baca_kandidat()
    assert url.endswith("_10.csv")
    assert [u[-6:-4] for u in dicoba] == ["12", "11", "10"]  # turun dari Desember
    assert list(df.columns) == siapkan_konflik.KOLOM


def test_baca_kandidat_gagal_semua(monkeypatch):
    monkeypatch.setattr(siapkan_konflik.requests, "get", lambda url, timeout: _Respons(ok=False))
    with pytest.raises(RuntimeError):
        siapkan_konflik.baca_kandidat()
