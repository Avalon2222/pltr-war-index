# Sumber data

Semua file di folder ini bisa dibangun ulang dari sumber publik tanpa API key, kecuali `peristiwa_perang.csv`
dan `laporan_keuangan_pltr.csv` yang dikurasi manual.

## `harga_saham.csv`

- **Sumber:** Yahoo Finance chart API (`query1.finance.yahoo.com/v8/finance/chart/<TICKER>`), tanpa key.
- **Dibangun oleh:** `python -m src.ambil_harga`
- **Rentang:** 30 September 2020 (hari pertama PLTR diperdagangkan) sampai pembaruan terakhir.
- **Ticker:** PLTR (Palantir), SPY (S&P 500), QQQ (Nasdaq-100), ITA (iShares U.S. Aerospace & Defense ETF),
  LMT (Lockheed Martin), NOC (Northrop Grumman), RTX (RTX/Raytheon), GD (General Dynamics).

| Kolom | Arti |
|---|---|
| `tanggal` | Tanggal bursa New York |
| `ticker` | Kode saham |
| `close` | Harga penutupan (USD) |
| `adj_close` | Harga penutupan yang disesuaikan dividen dan stock split; return dihitung dari kolom ini |
| `volume` | Jumlah saham yang diperdagangkan |

Data Yahoo Finance hanya untuk penggunaan pribadi dan edukasi.

## `konflik_harian.csv`

- **Sumber:** [UCDP Georeferenced Event Dataset (GED) 26.1](https://ucdp.uu.se/downloads/) untuk 1989-2025 dan
  **UCDP Candidate Events** (rilis bulanan, data awal) untuk 2026. Uppsala Conflict Data Program, Universitas Uppsala.
- **Lisensi:** CC BY 4.0. Sitasi: Sundberg & Melander (2013), *Introducing the UCDP Georeferenced Event Dataset*,
  Journal of Peace Research 50(4); Davies et al. (2025), *Organized violence 1989-2024*.
- **Dibangun oleh:** `python -m src.siapkan_konflik` (mengunduh zip GED 39 MB dan CSV Candidate terbaru).
- **Cakupan:** kekerasan bersenjata terorganisasi dengan minimal satu korban jiwa: konflik negara, konflik
  non-negara, dan kekerasan sepihak terhadap warga sipil.

| Kolom | Arti |
|---|---|
| `tanggal` | Hari (1 Januari 2020 s/d rilis Candidate terakhir) |
| `korban_<teater>` | Jumlah korban (perkiraan terbaik UCDP, `best`) hari itu di teater tersebut |
| `korban_total` | Jumlah semua teater |
| `kejadian_total` | Jumlah kejadian kekerasan (dibulatkan setelah pembagian rentang tanggal) |
| `status` | `final` (GED) atau `awal` (Candidate, bisa direvisi) |

Teater dipetakan dari negara UCDP: Rusia-Ukraina (Ukraina, Rusia), Israel-Gaza-Lebanon (Israel termasuk Gaza dan Tepi
Barat, Lebanon), Iran, Yaman, Suriah, Sudan, Etiopia, Myanmar, RD Kongo, Sahel (Mali, Burkina Faso, Niger), dan Lainnya.

Sebagian kejadian UCDP hanya diketahui rentang tanggalnya (misalnya satu laporan untuk Agustus-Oktober 2022 di
Etiopia). Korbannya dibagi rata ke setiap hari dalam rentang itu agar grafik mingguan tidak memiliki lonjakan palsu.

## `peristiwa_perang.csv`

Dikurasi manual. Satu baris per peristiwa, masing-masing dengan tautan sumber.

| Kolom | Arti |
|---|---|
| `tanggal` | Tanggal peristiwa (waktu setempat). Hari 0 analisis = hari bursa AS pertama pada/setelah tanggal ini |
| `peristiwa` | Nama singkat |
| `kategori` | `perang_baru` (perang baru pecah), `eskalasi`, `keterlibatan_as` (serangan langsung militer AS), `deeskalasi` (gencatan senjata/kesepakatan damai) |
| `kawasan` | Timur Tengah, Eropa & Kaukasus, Asia, Afrika, Amerika |
| `keterangan` | Satu kalimat konteks |
| `sumber` | Tautan sumber (sebagian besar artikel Wikipedia berbahasa Inggris yang mengutip sumber primer) |

Kriteria pemilihan: peristiwa militer besar yang diberitakan luas secara internasional dan punya tanggal yang jelas,
sejak IPO Palantir. Peristiwa 2026 berasal dari pemberitaan yang masih berkembang; tanggalnya mengikuti sumber yang
ditautkan. Tiga peristiwa paling awal (sebelum April 2021) tidak masuk analisis karena belum ada 130 hari data harga
sebelumnya untuk jendela estimasi.

Untuk menambah peristiwa, tambahkan satu baris dengan format yang sama. Tes `test_peristiwa_perang_valid` memastikan
kategorinya valid, sumbernya berupa tautan https, dan urutannya menurut tanggal.

## `laporan_keuangan_pltr.csv`

Tanggal rilis laporan keuangan kuartalan Palantir (`tanggal_rilis`, `kuartal`). Palantir merilis setelah bursa tutup,
sehingga reaksi pasar terjadi di hari bursa berikutnya. Tanggal diambil dari kalender rilis publik dan dicek dengan
lonjakan volume perdagangan PLTR di hari berikutnya. Dipakai untuk menandai peristiwa yang jendelanya bertabrakan
dengan laporan keuangan.
