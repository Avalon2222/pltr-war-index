# 🎓 Belajar dari PLTR War Index

Panduan ini menjelaskan konsep di balik aplikasi, dari "apa itu return" sampai uji plasebo, dengan potongan kode
dari `src/`. Bacalah berurutan; setiap bagian memakai bagian sebelumnya.

---

## 1. Return: bahasa yang dipakai pasar

Harga saham sendiri sulit dibandingkan: PLTR $10 dan LMT $450 tidak bisa diadu langsung. Yang dibandingkan adalah
**return**, yaitu perubahan harga dalam persen:

```
return hari t = harga_t / harga_(t-1) - 1
```

Di `src/studi_peristiwa.py`:

```python
def tabel_return(harga: pd.DataFrame) -> pd.DataFrame:
    lebar = harga.pivot_table(index="tanggal", columns="ticker", values="adj_close").sort_index()
    return lebar.pct_change().iloc[1:]
```

- `pivot_table` mengubah format panjang (satu baris per tanggal × ticker) menjadi format lebar (satu kolom per ticker).
- `adj_close` dipakai, bukan `close`, karena sudah memperhitungkan dividen. Lockheed Martin membagi dividen sekitar 2,5%
  per tahun; tanpa penyesuaian, return-nya terlihat lebih kecil daripada yang diterima pemegang saham.
- `pct_change()` menghitung return untuk semua kolom sekaligus.

> 💡 Simpangan baku return harian PLTR sejak IPO sekitar **4,4%**, tiga kali lipat S&P 500 (1,0%). Ini penting nanti:
> saham yang biasa naik-turun 4% sehari butuh gerakan yang sangat besar agar terlihat "tidak normal".

---

## 2. Masalah: bagaimana tahu sebuah kenaikan disebabkan perang?

Misalkan PLTR naik 10% sehari setelah invasi Ukraina. Apakah karena perang? Belum tentu. Mungkin hari itu seluruh pasar
juga naik 3%, dan PLTR memang biasanya naik dua kali lipat pasar. Kalau begitu, "jatah normal" PLTR adalah 6%, dan
hanya 4% sisanya yang bisa dikaitkan dengan peristiwa.

Itulah inti **event study**: pisahkan bagian gerakan yang bisa dijelaskan pasar dari bagian yang tidak.

---

## 3. Market model: belajar perilaku normal

Ambil 120 hari bursa **sebelum** peristiwa (hari −130 sampai −11). Di periode itu, cari garis lurus yang paling cocok:

```
R_PLTR = α + β × R_pasar + ε
```

- **β (beta)**: seberapa kuat saham ikut pasar. β = 2 berarti kalau S&P 500 naik 1%, PLTR biasanya naik 2%.
- **α (alpha)**: return rata-rata PLTR di luar efek pasar.
- **ε (residual)**: sisa yang tidak dijelaskan. Simpangan bakunya disebut **σ**.

```python
def market_model(r_saham, r_pasar):
    x, y = r_pasar.to_numpy(), r_saham.to_numpy()
    beta = np.cov(x, y, ddof=1)[0, 1] / np.var(x, ddof=1)
    alpha = y.mean() - beta * x.mean()
    resid = y - (alpha + beta * x)
    sigma = np.sqrt(np.sum(resid**2) / (len(resid) - 2))
    return alpha, beta, sigma
```

Rumus beta di atas adalah regresi OLS satu variabel: kovarians dibagi varians. Pembaginya `n - 2` karena dua parameter
(α dan β) sudah "memakan" dua derajat kebebasan.

**Mengapa berhenti di hari −11, bukan −1?** Banyak perang punya tanda-tanda sebelumnya (pasukan Rusia menumpuk di
perbatasan sejak November 2021). Jeda 10 hari mencegah kabar awal itu ikut membentuk "perilaku normal".

---

## 4. Abnormal return dan CAR

Di jendela peristiwa (default hari −1 sampai +10):

```
return normal_t   = α + β × R_pasar_t
abnormal return_t = R_PLTR_t − return normal_t          (AR)
CAR               = AR_−1 + AR_0 + ... + AR_+10          (cumulative abnormal return)
```

Contoh nyata dari aplikasi, invasi Ukraina (hari 0 = 24 Februari 2022): β terhadap S&P 500 = 2,02, AR hari 0 = +10,9%,
CAR hari −1 s/d +10 = **+22,1%**. Artinya PLTR naik 22 poin persen lebih tinggi daripada yang bisa dijelaskan oleh pasar.

```python
normal = alpha + beta * jen[patokan]
ar = jen[saham] - normal
tabel["car"] = tabel["ar"].cumsum()
```

---

## 5. Uji t: besar, tapi apakah istimewa?

CAR +22% terdengar besar, tetapi PLTR memang liar. Uji t membandingkan CAR dengan goyangan normalnya:

```
t = CAR / (σ × √L)
```

L adalah panjang jendela (12 hari untuk −1 s/d +10). Kalau AR harian saling bebas dengan simpangan baku σ, maka jumlah
L hari punya simpangan baku σ × √L. Nilai |t| > 1,96 berarti kira-kira hanya 5% kemungkinan muncul secara kebetulan.

```python
t = car / (sigma * math.sqrt(len(tabel)))
p = math.erfc(abs(t) / math.sqrt(2))      # p-value dua sisi, pendekatan distribusi normal
```

Invasi Ukraina: t = 2,50, p = 0,013, **signifikan**.

> ⚠️ **Jebakan uji banyak.** Dari 45 peristiwa, 6 signifikan. Kalau perang sama sekali tidak berpengaruh, kita tetap
> akan berharap sekitar 2 sampai 3 peristiwa "signifikan" hanya karena kebetulan (5% × 45). Jadi 6 itu menarik, tetapi
> belum bukti kuat. Inilah alasan bagian berikutnya ada.

---

## 6. Uji plasebo: bandingkan dengan hari biasa

Pertanyaan yang lebih jujur: *apakah rata-rata CAR di 45 tanggal perang lebih ekstrem daripada rata-rata CAR di 45
tanggal acak?*

```python
# Hitung CAR untuk SETIAP hari bursa yang mungkin, sekali saja
for k, nol in enumerate(kandidat):
    ...
    car_semua[k] = np.sum(y[j] - normal)

# 1.000 kali: ambil 45 hari acak, rata-ratakan
sampel = rng.choice(len(kandidat), size=(n_ulang, n_peristiwa), replace=True)
distribusi = car_semua[sampel].mean(axis=1)
```

Trik pra-hitung membuat 1.000 ulangan selesai dalam kurang dari satu detik: CAR setiap hari hanya dihitung sekali,
lalu sampelnya cukup diambil dengan indeks.

p-value plasebo dihitung dari posisi nilai asli di distribusi itu (`p_plasebo`). Hasil default: **p = 0,67**. Rata-rata
CAR perang (+1,0%) berada di tengah-tengah distribusi tanggal acak. Secara rata-rata, perang tidak istimewa bagi PLTR.

---

## 7. Pengganggu terbesar: laporan keuangan

PLTR sering naik atau turun 10-30% sehari setelah laporan kuartalan. Kalau laporan jatuh di dalam jendela perang,
efeknya tercampur. `ada_laporan_keuangan` memeriksa hal itu:

```python
for tgl, kuartal in tanggal_laporan:
    pos = posisi_hari_nol(index, pd.Timestamp(tgl) + pd.Timedelta(days=1))   # reaksi = hari bursa berikutnya
    if pos is not None and awal <= index[pos] <= akhir:
        return kuartal
```

Contoh: "Serangan drone Tower 22" (28 Januari 2024) tampak memberi CAR +38%, tetapi laporan Q4 2023 rilis 5 Februari
dan PLTR naik 31% keesokan harinya. Hampir semua lonjakan itu milik laporan keuangan, bukan perang. Tanpa peristiwa yang
bertabrakan, rata-rata CAR menjadi −1,0%.

---

## 8. Intensitas konflik: semua minggu sekaligus

Event study hanya melihat tanggal terpilih. Pendekatan kedua memakai **semua** minggu:

1. Korban UCDP harian dijumlah per minggu (Jumat ke Jumat, sama dengan minggu bursa).
2. Diubah menjadi **perubahan log**: `log(1 + korban_minggu_ini) − log(1 + korban_minggu_lalu)`. Log dipakai karena
   lonjakan 1.000 → 2.000 korban dan 10.000 → 20.000 sama-sama "dua kali lipat".
3. Dikorelasikan dengan **return lebih** PLTR (return PLTR − return S&P 500) di minggu yang sama, sampai 4 minggu
   sebelum dan sesudahnya (lag).

```python
for lag in range(-lag_maks, lag_maks + 1):
    y = df["return_lebih"].shift(-lag)
    r = np.corrcoef(df["perubahan_log"][ok], y[ok])[0, 1]
```

Batas "kebetulan" kira-kira ±1,96/√n. Dengan ~310 minggu, batasnya ±0,11. Hasilnya: hampir semua lag berada di dalam
batas. Satu lag (+2 minggu) melewatinya tipis (0,116), dan dari 9 lag yang diuji, satu yang melewati batas memang wajar
terjadi karena kebetulan.

---

## 9. Saham perang atau saham AI?

Korelasi return harian menjawab pertanyaan yang lebih mendasar. Kalau PLTR saham pertahanan, ia harus bergerak bersama
Lockheed Martin. Ternyata:

| Pasangan | Korelasi |
|---|---|
| PLTR – QQQ (teknologi) | 0,51 |
| PLTR – ITA (ETF pertahanan) | 0,33 |
| PLTR – LMT | 0,02 |
| LMT – ITA | 0,52 |

Korelasi PLTR dengan Lockheed hampir nol. Pasar menilai Palantir dengan kacamata software dan AI (pertumbuhan pendapatan,
suku bunga, sentimen AI), meskipun pelanggan terbesarnya militer. `korelasi_bergulir` memperlihatkan hal ini konsisten
dari tahun ke tahun.

---

## 10. Struktur kode

| File | Tugas | Boleh pakai Streamlit? |
|---|---|---|
| `src/studi_peristiwa.py` | Market model, AR/CAR, t-test, plasebo | Tidak (murni, mudah dites) |
| `src/intensitas.py` | Agregasi mingguan, korelasi | Tidak |
| `src/ambil_harga.py`, `src/siapkan_konflik.py` | Unduh dan bersihkan data | Tidak |
| `src/muat_data.py` | Baca CSV, harga live dengan cadangan | Tidak |
| `app.py` | Tampilan | Ya |

Logika yang dipisah dari tampilan bisa dites dengan data sintetis. Contoh dari `tests/test_studi_peristiwa.py`: buat
saham palsu yang selalu bergerak 1,5 × pasar, sisipkan lonjakan +15% di satu hari, lalu pastikan event study menemukan
AR ≈ +15% tepat di hari itu dan beta ≈ 1,5.

---

## Bacaan lanjutan

- MacKinlay, A. C. (1997). *Event Studies in Economics and Finance.* Journal of Economic Literature 35(1). Rujukan
  klasik metode ini.
- Brune, A., Hens, T., Rieger, M. O., & Wang, M. (2015). *The war puzzle: contradictory effects of international
  conflicts on stock markets.* Pasar sering naik saat perang benar-benar pecah, bukan turun.
- Dokumentasi dan codebook UCDP GED: <https://ucdp.uu.se/downloads/>
