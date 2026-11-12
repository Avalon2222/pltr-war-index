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


def _kejadian(baris):
    import pandas as pd

    return pd.DataFrame(baris, columns=["date_start", "date_end", "country", "best"])


def test_gabung_candidate_hanya_setelah_ged_berakhir():
    ged = _kejadian([("2024-01-01", "2024-01-01", "Ukraine", 10), ("2024-01-03", "2024-01-03", "Sudan", 6)])
    kandidat = _kejadian([
        ("2024-01-03", "2024-01-03", "Sudan", 999),  # tumpang tindih dengan GED -> dibuang
        ("2024-01-05", "2024-01-05", "Ukraine", 4),
    ])
    h = siapkan_konflik.gabung_ged_kandidat(ged, kandidat, mulai="2024-01-01")
    assert h["korban_total"].sum() == 20
    status = dict(zip(h["tanggal"].dt.strftime("%Y-%m-%d"), h["status"]))
    assert status["2024-01-03"] == "final"
    assert status["2024-01-04"] == "awal" and status["2024-01-05"] == "awal"


def test_gabung_potong_ujung_rentang():
    ged = _kejadian([("2024-01-01", "2024-01-01", "Ukraine", 1)])
    kandidat = _kejadian([("2024-01-02", "2024-01-10", "Sudan", 9)])  # rentang 9 hari, 1 korban per hari
    h = siapkan_konflik.gabung_ged_kandidat(ged, kandidat, mulai="2024-01-01")
    assert h["tanggal"].max().strftime("%Y-%m-%d") == "2024-01-02"
    assert list(h.index) == list(range(len(h)))


def test_main_tanpa_jaringan(tmp_path, monkeypatch):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("GEDEvent_v26_1.csv", "id,date_start,date_end,country,best\n1,2024-01-01,2024-01-01,Ukraine,12\n")
    mentah = tmp_path / "mentah"
    monkeypatch.setattr(siapkan_konflik, "DIR_MENTAH", mentah)
    monkeypatch.setattr(siapkan_konflik, "PATH_CSV", tmp_path / "konflik_harian.csv")
    monkeypatch.setattr(siapkan_konflik, "_unduh", lambda url: buf.getvalue())
    monkeypatch.setattr(siapkan_konflik, "baca_kandidat",
                        lambda: (_kejadian([("2024-01-02", "2024-01-02", "Sudan", 3)]), "https://contoh/kandidat.csv"))
    siapkan_konflik.main()
    assert (mentah / "ged261-csv.zip").exists()
    isi = (tmp_path / "konflik_harian.csv").read_text().splitlines()
    assert isi[0].startswith("tanggal,")
    assert len(isi) == 3 and isi[1].startswith("2024-01-01") and isi[2].endswith("awal")
