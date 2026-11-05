# 🏋️ Latihan

Kerjakan berurutan; tiap latihan memakai apa yang dibangun latihan sebelumnya. ⭐ = 15–30 menit, ⭐⭐ = sekitar 1 jam,
⭐⭐⭐ = setengah hari. Kunci jawaban ada di bawah setiap soal; coba dulu tanpa membukanya.

---

### Latihan 1 — Tambah satu peristiwa ⭐

Pilih satu peristiwa militer yang belum ada di `data/peristiwa_perang.csv` (misalnya ledakan Jembatan Krimea,
8 Oktober 2022). Tambahkan barisnya, jalankan tes, lalu lihat CAR-nya di tab *Single event*.

<details><summary>Kunci</summary>

Tambahkan baris di posisi yang sesuai tanggalnya (tes memeriksa urutan):

```csv
2022-10-08,Jembatan Krimea meledak,eskalasi,Eropa & Kaukasus,Ledakan truk bom merusak jembatan Kerch.,https://en.wikipedia.org/wiki/2022_Crimean_Bridge_explosion
```

`python -m pytest tests/ -q` harus tetap hijau. Perhatikan: 8 Oktober 2022 hari Sabtu, jadi hari 0-nya Senin 10 Oktober,
sama dengan "Rudal Rusia menghantam kota-kota Ukraina". Dua peristiwa itu akan memberi CAR yang persis sama. Itu contoh
nyata masalah peristiwa bertumpuk.
</details>

---

### Latihan 2 — Bandingkan dengan Lockheed Martin ⭐

Tanpa mengubah kode: ganti "Saham yang diuji" ke LMT. Untuk jenis "Perang baru pecah", mana yang reaksinya lebih kuat,
PLTR atau LMT? Bagaimana dengan "Gencatan senjata / damai"?

<details><summary>Kunci</summary>

Dengan pengaturan default, LMT naik sekitar +14% setelah invasi Ukraina dan setelah serangan 7 Oktober, tetapi hampir
datar setelah perang Iran 2026. PLTR justru sebaliknya: datar setelah 7 Oktober, +22% setelah perang Iran. Gencatan
senjata cenderung negatif untuk keduanya. Kesimpulan: "saham perang" tidak bereaksi seragam; setiap perang punya cerita.
</details>

---

### Latihan 3 — CAR hari 0 sampai +5 di tabel ringkasan ⭐

`studi_semua` sudah menghitung kolom `car_0_5`. Tampilkan kolom ini di tab *All wars* sebagai grafik batang kedua,
lalu bandingkan dengan CAR jendela penuh. Apakah sebagian besar reaksi terjadi di minggu pertama?

<details><summary>Kunci</summary>

```python
urut = terpilih.sort_values("car_0_5")
fig = go.Figure(go.Bar(y=urut["peristiwa"], x=urut["car_0_5"] * 100, orientation="h",
                       marker_color=[WARNA_KATEGORI[k] for k in urut["kategori"]]))
st.plotly_chart(rapikan(fig, 19 * len(urut)), use_container_width=True)
```
</details>

---

### Latihan 4 — Fungsi baru + tes: CAR terbesar per kawasan ⭐⭐

Buat `ringkas_per_kawasan(ringkasan)` di `src/studi_peristiwa.py` yang mengembalikan rata-rata CAR, jumlah peristiwa,
dan peristiwa dengan CAR terbesar untuk setiap kawasan. Tulis tesnya dengan DataFrame kecil buatan sendiri.

<details><summary>Kunci</summary>

```python
def ringkas_per_kawasan(ringkasan: pd.DataFrame) -> pd.DataFrame:
    g = ringkasan.groupby("kawasan")
    hasil = g.agg(n=("car", "size"), car_rata=("car", "mean"))
    hasil["terbesar"] = g.apply(lambda d: d.loc[d["car"].idxmax(), "peristiwa"])
    return hasil.sort_values("car_rata", ascending=False).reset_index()


def test_ringkas_per_kawasan():
    df = pd.DataFrame({"kawasan": ["A", "A", "B"], "car": [0.1, 0.3, -0.2], "peristiwa": ["x", "y", "z"]})
    h = sp.ringkas_per_kawasan(df).set_index("kawasan")
    assert h.loc["A", "car_rata"] == pytest.approx(0.2)
    assert h.loc["A", "terbesar"] == "y"
    assert h.loc["B", "n"] == 1
```
</details>

---

### Latihan 5 — Uji plasebo khusus perang ⭐⭐

Di tab *All wars*, uji plasebo memakai semua jenis yang dipilih. Tambahkan uji kedua yang hanya memakai "Perang baru
pecah" + "Eskalasi". Berapa p-value-nya, dan mengapa berbeda dari uji gabungan?

<details><summary>Kunci</summary>

```python
perang = terpilih[terpilih["kategori"].isin(["perang_baru", "eskalasi"])]
dist = hitung_plasebo(harga, len(perang), saham, patokan, jendela)
st.metric("p plasebo (hanya perang)", f"{sp.p_plasebo(perang['car'].mean(), dist):.2f}")
```

Hasil default sekitar 0,12. Gencatan senjata cenderung negatif, jadi mencampurnya dengan perang membuat rata-rata
mendekati nol. Memisahkan keduanya memperjelas pola, meskipun masih belum melewati batas 0,05.
</details>

---

### Latihan 6 — Jendela estimasi yang bisa diatur ⭐⭐

Jendela estimasi saat ini tetap (−130 s/d −11). Tambahkan slider di sidebar untuk mengubahnya, lalu teruskan nilainya
ke `studi_semua` dan `uji_plasebo`. Apa yang terjadi pada beta PLTR kalau jendela estimasi hanya 30 hari?

<details><summary>Kunci</summary>

Tambahkan parameter `estimasi` ke `studi_semua` dan `uji_plasebo` (sudah ada di `studi_satu`), ganti semua pemakaian
`JENDELA_ESTIMASI` di dalam fungsi dengan parameter itu, dan sertakan nilainya di argumen fungsi `@st.cache_data` agar
cache ikut berubah. Dengan 30 hari, beta jauh lebih tidak stabil (bisa 1 di satu peristiwa dan 3 di peristiwa lain)
karena regresi hanya punya sedikit titik.
</details>

---

### Latihan 7 — Model dua faktor ⭐⭐⭐

Market model hanya memakai satu patokan. Ganti dengan regresi dua faktor:

```
R_PLTR = α + β1 × R_SPY + β2 × (R_QQQ − R_SPY) + ε
```

Faktor kedua menangkap "kelebihan teknologi". Implementasikan dengan `np.linalg.lstsq`, lalu bandingkan rata-rata
CAR dengan versi satu faktor.

<details><summary>Kunci</summary>

```python
def model_dua_faktor(y, x1, x2):
    X = np.column_stack([np.ones(len(y)), x1, x2])
    koef, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ koef
    sigma = np.sqrt(np.sum(resid**2) / (len(y) - 3))
    return koef, sigma
```

Di jendela peristiwa: `normal = koef[0] + koef[1] * spy + koef[2] * (qqq - spy)`. Biasanya CAR sedikit mengecil karena
sebagian gerakan PLTR yang tadinya "abnormal" ternyata dijelaskan oleh sektor teknologi.
</details>

---

### Latihan 8 — Peristiwa kontrak Palantir ⭐⭐⭐

Buat file `data/kontrak_pltr.csv` berisi 10-15 kontrak besar Palantir (misalnya Army Vantage, Project Maven, NHS
Federated Data Platform, TITAN) dengan tanggal pengumuman dan sumbernya. Tambahkan tab yang menjalankan event study
yang sama untuk kontrak. Mana yang lebih menggerakkan saham: perang atau kontrak?

<details><summary>Petunjuk</summary>

Format kolomnya bisa sama dengan `peristiwa_perang.csv` (kategori diganti instansi: militer, intelijen, kesehatan,
sipil). `studi_semua` hanya butuh kolom `tanggal`, `peristiwa`, `kategori`, dan `kawasan`, jadi fungsi yang ada bisa
langsung dipakai ulang. Data kontrak federal AS tersedia di <https://www.usaspending.gov> (cari penerima "Palantir").
</details>
