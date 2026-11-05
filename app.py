"""
app.py - PLTR War Index
=======================
Jalankan dengan:   streamlit run app.py

Pertanyaan besarnya: apakah saham Palantir (PLTR) naik setiap kali perang pecah?

Alur file ini (baca dari atas ke bawah):
  1. Konfigurasi halaman + gaya grafik
  2. Muat data: harga saham (Yahoo Finance), daftar peristiwa perang, korban konflik (UCDP)
  3. Sidebar: saham, patokan pasar, jendela peristiwa, kategori
  4. Hitung event study (src/studi_peristiwa.py) dan intensitas konflik (src/intensitas.py)
  5. Tampilkan tab: grafik, satu peristiwa, semua perang, intensitas, pertahanan vs teknologi, data, cara kerja

Penjelasan istilah (abnormal return, CAR, market model) ada di docs/BELAJAR.md.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from src import intensitas, muat_data
from src import studi_peristiwa as sp
from src.ambil_harga import TICKER

# ----------------------------------------------------------------------------
# 0. KONFIGURASI HALAMAN
# ----------------------------------------------------------------------------
st.set_page_config(page_title="PLTR War Index", page_icon="🛰️", layout="wide")

TEMPLATE = "plotly_dark"
AMBER = "#f5b544"
ABU = "#8b93a7"
WARNA_KATEGORI = {
    "perang_baru": "#f87171",
    "eskalasi": "#fb923c",
    "keterlibatan_as": "#60a5fa",
    "deeskalasi": "#34d399",
}
WARNA_TICKER = {
    "PLTR": AMBER, "SPY": "#9ca3af", "QQQ": "#a78bfa", "ITA": "#34d399",
    "LMT": "#60a5fa", "NOC": "#22d3ee", "RTX": "#f472b6", "GD": "#facc15",
}
WARNA_TEATER = {
    "Rusia-Ukraina": "#60a5fa", "Israel-Gaza-Lebanon": "#f87171", "Iran": "#fb923c", "Yaman": "#facc15",
    "Suriah": "#a78bfa", "Sudan": "#f472b6", "Etiopia": "#34d399", "Myanmar": "#22d3ee",
    "RD Kongo": "#c084fc", "Sahel": "#fdba74", "Lainnya": "#4b5563",
}
DISCLAIMER = (
    "ℹ️ Harga saham dari **Yahoo Finance**, korban konflik dari **UCDP** (Uppsala Conflict Data Program), dan "
    "daftar peristiwa dikurasi manual dengan tautan sumber. Ini proyek analisis data untuk edukasi, **bukan "
    "saran investasi**, dan tidak berafiliasi dengan Palantir Technologies."
)


def rapikan(fig: go.Figure, tinggi: int = 420, legenda_bawah: bool = False) -> go.Figure:
    """Gaya seragam semua grafik: latar gelap transparan, grid tipis, legenda di atas."""
    fig.update_layout(
        template=TEMPLATE,
        height=tinggi,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=20, t=70, b=10),
        title=dict(y=0.97, yanchor="top", x=0, xanchor="left", font=dict(size=15)),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0, title=None),
        font=dict(family="system-ui, -apple-system, Segoe UI, sans-serif"),
        hoverlabel=dict(font_size=12),
    )
    if legenda_bawah:
        fig.update_layout(legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="left", x=0, title=None),
                          margin=dict(l=10, r=20, t=50, b=10))
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="#262b3a", zeroline=False)
    return fig


def persen(x: float, desimal: int = 1, tanda: bool = True) -> str:
    if x is None or not np.isfinite(x):
        return "–"
    teks = f"{x * 100:+.{desimal}f}%" if tanda else f"{x * 100:.{desimal}f}%"
    return teks.replace(".", ",")


def ribuan(angka: float) -> str:
    return f"{int(round(angka)):,}".replace(",", ".")


BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


def tanggal_id(ts) -> str:
    """Timestamp -> '24 Feb 2022' dengan nama bulan Indonesia."""
    if pd.isna(ts):
        return "–"
    ts = pd.Timestamp(ts)
    return f"{ts.day:02d} {BULAN[ts.month - 1]} {ts.year}"


def bulan_tahun(seri: pd.Series) -> pd.Series:
    return seri.map(lambda t: f"{BULAN[t.month - 1]} {t.year}")


def belajar(teks: str) -> None:
    """Kotak penjelasan yang hanya muncul saat Mode belajar aktif."""
    if st.session_state.get("mode_belajar"):
        st.info(teks, icon="🎓")


# ----------------------------------------------------------------------------
# 1. MUAT DATA
# ----------------------------------------------------------------------------
@st.cache_data(ttl=6 * 3600, show_spinner="Mengambil harga saham terbaru...")
def ambil_harga(live: bool):
    return muat_data.muat_harga(live)


@st.cache_data
def ambil_lainnya():
    return muat_data.muat_peristiwa(), muat_data.muat_konflik(), muat_data.muat_laporan()


@st.cache_data(show_spinner="Menjalankan event study...")
def hitung_studi(harga: pd.DataFrame, peristiwa: pd.DataFrame, laporan: pd.DataFrame, saham: str,
                 patokan: str | None, jendela: tuple[int, int]):
    ret = sp.tabel_return(harga)
    return sp.studi_semua(ret, peristiwa, saham, patokan, jendela, laporan)


@st.cache_data(show_spinner="Membuat 1.000 tanggal acak untuk uji plasebo...")
def hitung_plasebo(harga: pd.DataFrame, n: int, saham: str, patokan: str | None, jendela: tuple[int, int]):
    return sp.uji_plasebo(sp.tabel_return(harga), n, saham, patokan, jendela, n_ulang=1000)


peristiwa_semua, konflik, laporan = ambil_lainnya()

# ----------------------------------------------------------------------------
# 2. SIDEBAR
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Pengaturan")
    saham = st.selectbox(
        "Saham yang diuji", list(TICKER), index=0, format_func=lambda t: f"{t} · {TICKER[t]}",
        help="Default PLTR. Coba ganti ke LMT atau ITA untuk membandingkan dengan saham pertahanan klasik.",
    )
    pilihan_patokan = {"SPY": "S&P 500 (SPY)", "QQQ": "Nasdaq-100 (QQQ)", "ITA": "ETF pertahanan (ITA)",
                       None: "Tanpa patokan (rata-rata saham itu sendiri)"}
    patokan = st.selectbox(
        "Patokan pasar (market model)", list(pilihan_patokan), index=0, format_func=lambda k: pilihan_patokan[k],
        help="Return 'normal' dihitung dari hubungan saham dengan patokan ini selama 120 hari bursa sebelum peristiwa.",
    )
    if patokan == saham:
        st.warning("Saham dan patokan sama; patokan diganti ke SPY.")
        patokan = "SPY" if saham != "SPY" else "QQQ"
    jendela = st.slider("Jendela peristiwa (hari bursa)", -10, 40, (-1, 10),
                        help="Hari 0 = hari bursa pertama pada/setelah peristiwa. (-1, 10) = sehari sebelum s/d 10 hari sesudah.")
    if jendela[0] > 0:
        jendela = (0, jendela[1])
    if jendela[1] < 1:
        jendela = (jendela[0], 1)
    kategori = st.multiselect(
        "Jenis peristiwa", muat_data.URUTAN_KATEGORI, default=muat_data.URUTAN_KATEGORI,
        format_func=lambda k: muat_data.KATEGORI[k],
    )
    buang_laporan = st.checkbox(
        "Buang peristiwa yang bertabrakan dengan laporan keuangan PLTR", value=False,
        help="Laporan kuartalan sering menggerakkan PLTR 10-30% dalam sehari. Kalau jatuh di jendela yang sama, "
             "gerakannya sulit dipisahkan dari efek perang.",
    )
    live = st.toggle("Harga live dari Yahoo Finance", value=True,
                     help="Kalau gagal, otomatis memakai snapshot mingguan di data/harga_saham.csv.")
    st.toggle("🎓 Mode belajar", key="mode_belajar", help="Tampilkan penjelasan singkat di setiap bagian.")
    st.divider()
    st.caption("Kode: [github.com/Avalon2222/pltr-war-index](https://github.com/Avalon2222/pltr-war-index)")

harga, sumber_harga = ambil_harga(live)
harga_lebar = sp.tabel_harga(harga, "close")
harga_adj = sp.tabel_harga(harga, "adj_close")
ret = sp.tabel_return(harga)

peristiwa = peristiwa_semua[peristiwa_semua["kategori"].isin(kategori)]
ringkasan, detail = hitung_studi(harga, peristiwa_semua, laporan, saham, patokan, jendela)
if not ringkasan.empty:
    ringkasan["label_kategori"] = ringkasan["kategori"].map(muat_data.KATEGORI)
terpilih = ringkasan[ringkasan["kategori"].isin(kategori)]
if buang_laporan:
    terpilih = terpilih[terpilih["laporan_keuangan"].isna()]

# ----------------------------------------------------------------------------
# 3. HEADER + ANGKA RINGKASAN
# ----------------------------------------------------------------------------
st.markdown(
    f"<h1 style='margin-bottom:0'>🛰️ PLTR War Index</h1>"
    f"<p style='color:{ABU};font-size:1.05rem;margin-top:4px'>Does war pay? Saham Palantir diuji terhadap "
    f"{len(peristiwa_semua)} peristiwa perang dan gencatan senjata sejak IPO 2020.</p>",
    unsafe_allow_html=True,
)
st.caption(DISCLAIMER)

if terpilih.empty:
    st.warning("Tidak ada peristiwa yang cocok dengan filter. Tambahkan jenis peristiwa di sidebar.")
    st.stop()

plasebo = hitung_plasebo(harga, len(terpilih), saham, patokan, jendela)
car_rata = float(terpilih["car"].mean())
p_acak = sp.p_plasebo(car_rata, plasebo)
# Reaksi terbesar/terburuk diambil dari peristiwa yang TIDAK bertabrakan dengan laporan keuangan,
# supaya yang tampil benar-benar efek perang (kalau semuanya bertabrakan, pakai semua).
bersih = terpilih[terpilih["laporan_keuangan"].isna()]
bersih = bersih if not bersih.empty else terpilih
terbaik = bersih.loc[bersih["car"].idxmax()]
terburuk = bersih.loc[bersih["car"].idxmin()]
nama_patokan = pilihan_patokan[patokan].split(" (")[0] if patokan else "rata-rata sendiri"

k1, k2, k3, k4 = st.columns(4)
k1.metric(f"Rata-rata CAR {saham}", persen(car_rata),
          help=f"Rata-rata abnormal return kumulatif hari {jendela[0]} s/d +{jendela[1]} di {len(terpilih)} peristiwa.")
k2.metric("Peristiwa signifikan (p < 0,05)", f"{int((terpilih['p_value'] < 0.05).sum())} dari {len(terpilih)}",
          help="Secara kebetulan saja, sekitar 5% peristiwa akan terlihat 'signifikan'.")
k3.metric("p-value vs tanggal acak", f"{p_acak:.2f}".replace(".", ","),
          help="Uji plasebo: seberapa sering 1.000 kumpulan tanggal acak menghasilkan rata-rata CAR seekstrem ini.")
k4.metric("Reaksi terbesar", persen(terbaik["car"]), terbaik["peristiwa"], delta_color="off",
          help="Tanpa peristiwa yang bertabrakan dengan laporan keuangan PLTR.")

if p_acak >= 0.05:
    vonis = (f"**Vonis:** secara rata-rata, {saham} **tidak** bergerak lebih aneh setelah perang dibanding hari-hari acak "
             f"(p = {p_acak:.2f}). Tapi beberapa perang besar memang membuatnya melonjak; lihat tab *All wars*.")
else:
    arah = "naik" if car_rata > 0 else "turun"
    vonis = (f"**Vonis:** dengan pengaturan ini, {saham} cenderung **{arah}** setelah peristiwa perang, dan pola ini "
             f"jarang muncul dari tanggal acak (p = {p_acak:.2f}).")
st.markdown(vonis.replace("0.", "0,"))
sumber_teks = "live dari Yahoo Finance" if sumber_harga == "live" else "snapshot mingguan (Yahoo Finance)"
st.caption(f"Harga {sumber_teks}, terakhir {tanggal_id(harga['tanggal'].max())}. "
           f"Korban konflik UCDP sampai {tanggal_id(konflik['tanggal'].max())}.")

tab_grafik, tab_satu, tab_semua, tab_intensitas, tab_tech, tab_data, tab_cara = st.tabs(
    ["📈 War chart", "🎯 Single event", "📊 All wars", "🔥 War intensity", "🛡️ Defense or tech?",
     "🗂️ Data & sources", "⚙️ How it works"]
)

# ----------------------------------------------------------------------------
# 4a. GRAFIK HARGA + PERISTIWA
# ----------------------------------------------------------------------------
with tab_grafik:
    belajar("Garis oranye adalah harga penutupan saham. Setiap titik berwarna adalah satu peristiwa perang. "
            "Arahkan kursor ke titik untuk melihat nama peristiwanya, lalu lihat apakah harganya naik setelah itu. "
            "Grafik bawah menunjukkan korban konflik dunia per minggu menurut UCDP.")
    c1, c2 = st.columns([3, 1])
    with c2:
        skala_log = st.toggle("Skala logaritmik", value=True,
                              help="PLTR naik ~18x sejak IPO. Skala log membuat kenaikan 10% terlihat sama besar di 2021 maupun 2026.")
        bandingkan = st.multiselect("Bandingkan dengan", [t for t in TICKER if t != saham], default=["ITA"])
        tampil_teater = st.toggle("Pecah korban per teater konflik", value=True)
    with c1:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.68, 0.32], vertical_spacing=0.04)
        seri = harga_lebar[saham].dropna()
        fig.add_trace(go.Scatter(x=seri.index, y=seri, name=saham, line=dict(color=WARNA_TICKER.get(saham, AMBER), width=2),
                                 hovertemplate="%{x|%d %b %Y}<br>$%{y:,.2f}<extra>" + saham + "</extra>"), row=1, col=1)
        for t in bandingkan:
            # Pembanding dinormalisasi supaya mulai dari harga yang sama dengan saham utama.
            s = harga_adj[t].dropna()
            s = s / s.iloc[0] * harga_adj[saham].dropna().iloc[0]
            fig.add_trace(go.Scatter(x=s.index, y=s, name=f"{t} (dinormalisasi)", line=dict(color=WARNA_TICKER[t], width=1.2),
                                     opacity=0.8, hovertemplate="%{x|%d %b %Y}<extra>" + t + "</extra>"), row=1, col=1)
        for kat in kategori:
            ev = peristiwa[peristiwa["kategori"] == kat].copy()
            ev = ev[ev["tanggal"] >= seri.index.min()]
            if ev.empty:
                continue
            pos = [sp.posisi_hari_nol(seri.index, t) for t in ev["tanggal"]]
            ev["hari_nol"] = [seri.index[p] if p is not None else pd.NaT for p in pos]
            ev["harga"] = [seri.iloc[p] if p is not None else np.nan for p in pos]
            ev = ev.dropna(subset=["harga"])
            fig.add_trace(go.Scatter(
                x=ev["hari_nol"], y=ev["harga"], mode="markers", name=muat_data.KATEGORI[kat],
                marker=dict(color=WARNA_KATEGORI[kat], size=10, line=dict(color="#0e1117", width=1.5)),
                customdata=np.stack([ev["peristiwa"], ev["tanggal"].map(tanggal_id)], axis=-1),
                hovertemplate="<b>%{customdata[0]}</b><br>%{customdata[1]}<br>" + saham + " $%{y:,.2f}<extra></extra>",
            ), row=1, col=1)

        mingguan = konflik.set_index("tanggal").resample("W-FRI").sum(numeric_only=True)
        mingguan = mingguan[mingguan.index >= seri.index.min() - pd.Timedelta(days=7)]
        if tampil_teater:
            for teater in intensitas.TEATER:
                fig.add_trace(go.Bar(x=mingguan.index, y=mingguan[f"korban_{teater}"], name=teater,
                                     marker_color=WARNA_TEATER[teater], showlegend=False,
                                     hovertemplate="%{x|%d %b %Y}<br>" + teater + ": %{y:,.0f}<extra></extra>"), row=2, col=1)
            fig.update_layout(barmode="stack", bargap=0)
        else:
            fig.add_trace(go.Bar(x=mingguan.index, y=mingguan["korban_total"], name="Korban per minggu",
                                 marker_color="#f87171", showlegend=False,
                                 hovertemplate="%{x|%d %b %Y}<br>%{y:,.0f} korban<extra></extra>"), row=2, col=1)
        if skala_log:
            fig.update_yaxes(type="log", tickvals=[5, 10, 20, 50, 100, 200, 500], tickprefix="$", row=1, col=1)
        fig.update_yaxes(title_text="Harga (USD)", row=1, col=1)
        fig.update_yaxes(title_text="Korban/minggu", row=2, col=1)
        fig.update_layout(title=f"{TICKER[saham]} vs perang dunia", hovermode="closest")
        st.plotly_chart(rapikan(fig, 660, legenda_bawah=True), use_container_width=True)
    st.caption("Korban = perkiraan terbaik (best estimate) UCDP untuk kekerasan bersenjata terorganisasi. "
               "Data 2026 masih rilis awal (UCDP Candidate) dan bisa direvisi.")

# ----------------------------------------------------------------------------
# 4b. SATU PERISTIWA
# ----------------------------------------------------------------------------
with tab_satu:
    belajar("**Abnormal return (AR)** = return asli dikurangi return yang 'seharusnya' terjadi kalau saham hanya "
            "mengikuti pasar. **CAR** adalah jumlah AR dari hari ke hari. CAR +20% berarti saham naik 20 poin persen "
            "lebih tinggi daripada yang bisa dijelaskan oleh gerakan pasar.")
    pilihan = terpilih.sort_values("tanggal", ascending=False)
    default_id = int(pilihan.loc[pilihan["peristiwa"].str.contains("menginvasi Ukraina")].iloc[0]["id"]) \
        if pilihan["peristiwa"].str.contains("menginvasi Ukraina").any() else int(pilihan.iloc[0]["id"])
    ids = pilihan["id"].astype(int).tolist()
    pid = st.selectbox(
        "Pilih peristiwa", ids, index=ids.index(default_id),
        format_func=lambda i: f"{tanggal_id(peristiwa_semua.loc[i, 'tanggal'])} · {peristiwa_semua.loc[i, 'peristiwa']}",
    )
    p = peristiwa_semua.loc[pid]
    h = detail[pid]
    baris = terpilih.set_index("id").loc[pid]

    st.markdown(f"#### {p['peristiwa']}")
    st.markdown(f"<span style='color:{WARNA_KATEGORI[p['kategori']]}'>● {muat_data.KATEGORI[p['kategori']]}</span> · "
                f"{p['kawasan']} · {tanggal_id(p['tanggal'])} (hari 0 = {tanggal_id(h.hari_nol)}) · "
                f"[sumber]({p['sumber']})", unsafe_allow_html=True)
    st.caption(p["keterangan"])
    if isinstance(baris["laporan_keuangan"], str):
        st.warning(f"⚠️ Laporan keuangan PLTR **{baris['laporan_keuangan']}** jatuh di dalam jendela ini. "
                   "Sebagian (bisa juga sebagian besar) gerakan harga kemungkinan berasal dari laporan itu, bukan dari perang.")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(f"CAR hari {jendela[0]} s/d +{jendela[1]}", persen(h.car))
    m2.metric("Abnormal return hari 0", persen(baris["ar_hari0"]))
    m3.metric("t-stat / p-value", f"{h.t_stat:.2f} / {h.p_value:.3f}".replace(".", ","),
              "signifikan" if h.signifikan else "tidak signifikan", delta_color="normal" if h.signifikan else "off")
    m4.metric(f"Beta terhadap {patokan or '—'}", f"{h.beta:.2f}".replace(".", ","),
              help="Beta 1,5 = kalau pasar naik 1%, saham ini biasanya naik 1,5%.")

    # Saham pembanding dihitung dengan pengaturan yang sama.
    pembanding = [t for t in ["PLTR", "ITA", "LMT", "QQQ"] if t not in (saham, patokan)]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.06)
    tab = h.tabel
    fig.add_trace(go.Scatter(x=tab["hari_relatif"], y=tab["car"] * 100, name=f"CAR {saham}",
                             line=dict(color=WARNA_TICKER.get(saham, AMBER), width=3), mode="lines+markers",
                             hovertemplate="Hari %{x}<br>CAR %{y:.1f}%<extra>" + saham + "</extra>"), row=1, col=1)
    for t in pembanding:
        hp = sp.studi_satu(ret, p["tanggal"], t, patokan, jendela)
        if hp is not None:
            fig.add_trace(go.Scatter(x=hp.tabel["hari_relatif"], y=hp.tabel["car"] * 100, name=f"CAR {t}",
                                     line=dict(color=WARNA_TICKER[t], width=1.5, dash="dot"),
                                     hovertemplate="Hari %{x}<br>CAR %{y:.1f}%<extra>" + t + "</extra>"), row=1, col=1)
    fig.add_trace(go.Bar(x=tab["hari_relatif"], y=tab["ar"] * 100, name=f"AR harian {saham}",
                         marker_color=[AMBER if v >= 0 else "#f87171" for v in tab["ar"]], opacity=0.8, showlegend=False,
                         hovertemplate="Hari %{x}<br>AR %{y:.2f}%<extra></extra>"), row=2, col=1)
    for n_baris in (1, 2):
        fig.add_vline(x=0, line_dash="dash", line_color=ABU, row=n_baris, col=1)
        fig.add_hline(y=0, line_color="#3a4152", row=n_baris, col=1)
    fig.update_xaxes(title_text="Hari bursa relatif terhadap peristiwa (garis putus-putus = hari 0)", row=2, col=1)
    fig.update_yaxes(title_text="CAR (%)", row=1, col=1)
    fig.update_yaxes(title_text="AR harian (%)", row=2, col=1)
    fig.update_layout(title=f"Abnormal return kumulatif di sekitar peristiwa (patokan: {nama_patokan})")
    st.plotly_chart(rapikan(fig, 520), use_container_width=True)

    with st.expander("Tabel harian"):
        tampil = tab.assign(tanggal=tab["tanggal"].dt.strftime("%Y-%m-%d"))
        for kol in ["return", "return_normal", "ar", "car"]:
            tampil[kol] = (tampil[kol] * 100).round(2)
        st.dataframe(tampil.rename(columns={"return": "return (%)", "return_normal": "return normal (%)",
                                            "ar": "AR (%)", "car": "CAR (%)"}), hide_index=True, use_container_width=True)
        st.caption(f"Market model dari 120 hari bursa ({sp.JENDELA_ESTIMASI[0]} s/d {sp.JENDELA_ESTIMASI[1]}): "
                   f"return normal = {h.alpha * 100:.3f}% + {h.beta:.2f} × return {patokan or '—'}. "
                   f"Simpangan baku residual {h.sigma * 100:.2f}% per hari.")

# ----------------------------------------------------------------------------
# 4c. SEMUA PERANG
# ----------------------------------------------------------------------------
with tab_semua:
    belajar("Satu peristiwa bisa kebetulan. Di sini semua peristiwa digabung: kalau perang memang menguntungkan "
            "Palantir, rata-rata CAR-nya harus jelas di atas nol **dan** lebih ekstrem dibanding tanggal acak. "
            "Itulah gunanya uji plasebo di bagian bawah.")
    c1, c2 = st.columns([1.15, 1])
    with c1:
        fig = go.Figure()
        for kat in kategori:
            ids_kat = terpilih.loc[terpilih["kategori"] == kat, "id"].tolist()
            if not ids_kat:
                continue
            rr = sp.rata_rata_car(detail, ids_kat)
            warna = WARNA_KATEGORI[kat]
            if len(ids_kat) > 2:
                fig.add_trace(go.Scatter(
                    x=np.concatenate([rr["hari_relatif"], rr["hari_relatif"][::-1]]),
                    y=np.concatenate([rr["batas_atas"], rr["batas_bawah"][::-1]]) * 100,
                    fill="toself", fillcolor=warna, opacity=0.12, line=dict(width=0), hoverinfo="skip", showlegend=False))
            fig.add_trace(go.Scatter(x=rr["hari_relatif"], y=rr["car_rata"] * 100,
                                     name=f"{muat_data.KATEGORI[kat]} (n={len(ids_kat)})", line=dict(color=warna, width=2.5),
                                     hovertemplate="Hari %{x}<br>CAR rata-rata %{y:.1f}%<extra></extra>"))
        semua = sp.rata_rata_car(detail, terpilih["id"].tolist())
        fig.add_trace(go.Scatter(x=semua["hari_relatif"], y=semua["car_rata"] * 100, name=f"Semua (n={len(terpilih)})",
                                 line=dict(color="#e8e8e8", width=2, dash="dash")))
        fig.add_vline(x=0, line_dash="dash", line_color=ABU)
        fig.add_hline(y=0, line_color="#3a4152")
        fig.update_xaxes(title_text="Hari bursa relatif")
        fig.update_yaxes(title_text="CAR rata-rata (%)")
        fig.update_layout(title=f"Rata-rata CAR {saham} per jenis peristiwa (pita = interval kepercayaan 95%)")
        st.plotly_chart(rapikan(fig, 480, legenda_bawah=True), use_container_width=True)
    with c2:
        per_kat = (terpilih.groupby("kategori")
                   .agg(n=("car", "size"), car_rata=("car", "mean"), median=("car", "median"),
                        porsi_naik=("car", lambda s: (s > 0).mean()), signifikan=("p_value", lambda s: (s < 0.05).sum()))
                   .reindex([k for k in muat_data.URUTAN_KATEGORI if k in kategori]).dropna(subset=["n"]))
        st.markdown("##### Ringkasan per jenis")
        st.dataframe(
            pd.DataFrame({
                "Jenis": [muat_data.KATEGORI[k] for k in per_kat.index],
                "n": per_kat["n"].astype(int),
                "CAR rata-rata": per_kat["car_rata"].map(persen),
                "Median": per_kat["median"].map(persen),
                "Porsi naik": per_kat["porsi_naik"].map(lambda x: persen(x, 0, False)),
                "Signifikan": per_kat["signifikan"].astype(int),
            }), hide_index=True, use_container_width=True)
        tanpa_lap = terpilih[terpilih["laporan_keuangan"].isna()]
        st.markdown(
            f"- **Perang baru pecah** dan **eskalasi** rata-rata membuat {saham} bergerak "
            f"{persen(terpilih.loc[terpilih['kategori'].isin(['perang_baru', 'eskalasi']), 'car'].mean())}, "
            f"sedangkan **gencatan senjata** {persen(terpilih.loc[terpilih['kategori'] == 'deeskalasi', 'car'].mean())}.\n"
            f"- Tanpa peristiwa yang bertabrakan dengan laporan keuangan ({len(tanpa_lap)} peristiwa), rata-rata CAR "
            f"menjadi {persen(tanpa_lap['car'].mean())}.\n"
            f"- Reaksi terbesar tanpa gangguan laporan keuangan: **{terbaik['peristiwa']}** ({persen(terbaik['car'])}). "
            f"Terburuk: **{terburuk['peristiwa']}** ({persen(terburuk['car'])})."
        )

    urut = terpilih.sort_values("car")
    teks_lap = np.where(urut["laporan_keuangan"].notna(), " ⚠️ laporan " + urut["laporan_keuangan"].fillna(""), "")
    fig = go.Figure(go.Bar(
        y=urut["peristiwa"] + " (" + bulan_tahun(urut["tanggal"]) + ")", x=urut["car"] * 100, orientation="h",
        marker=dict(color=[WARNA_KATEGORI[k] for k in urut["kategori"]],
                    line=dict(color=["#ffffff" if p < 0.05 else "rgba(0,0,0,0)" for p in urut["p_value"]], width=1.5)),
        customdata=np.stack([urut["p_value"], teks_lap], axis=-1),
        hovertemplate="<b>%{y}</b><br>CAR %{x:.1f}%<br>p = %{customdata[0]:.3f}%{customdata[1]}<extra></extra>",
    ))
    fig.add_vline(x=0, line_color="#3a4152")
    fig.update_xaxes(title_text=f"CAR hari {jendela[0]} s/d +{jendela[1]} (%)")
    fig.update_layout(title="CAR setiap peristiwa (garis tepi putih = signifikan p < 0,05)")
    st.plotly_chart(rapikan(fig, max(420, 19 * len(urut))), use_container_width=True)

    st.markdown("##### 🎲 Uji plasebo: perang vs tanggal acak")
    c1, c2 = st.columns([2, 1])
    with c1:
        fig = go.Figure(go.Histogram(x=plasebo * 100, nbinsx=50, marker_color="#4b5563", name="Tanggal acak",
                                     hovertemplate="CAR %{x:.1f}%<br>%{y} kali<extra></extra>"))
        fig.add_vline(x=car_rata * 100, line_color=AMBER, line_width=3,
                      annotation_text=f"Perang sungguhan: {persen(car_rata)}", annotation_position="top right")
        fig.update_xaxes(title_text=f"Rata-rata CAR dari {len(terpilih)} tanggal acak (%)")
        fig.update_yaxes(title_text="Frekuensi")
        fig.update_layout(title="1.000 kali memilih tanggal acak", showlegend=False)
        st.plotly_chart(rapikan(fig, 340), use_container_width=True)
    with c2:
        st.metric("p-value plasebo", f"{p_acak:.2f}".replace(".", ","))
        st.markdown(
            f"Dari 1.000 kumpulan berisi {len(terpilih)} tanggal acak, "
            f"**{persen(np.mean(plasebo >= car_rata), 0, False)}** menghasilkan rata-rata CAR setinggi atau lebih tinggi "
            f"daripada tanggal perang sungguhan. "
            + ("Artinya hasil perang **tidak istimewa**: hari biasa pun sering seperti itu."
               if p_acak >= 0.05 else "Artinya pola di tanggal perang **jarang** muncul secara kebetulan.")
        )
        belajar("PLTR adalah saham yang sangat bergejolak (sering naik-turun 5% sehari). Karena itu, gerakan "
                "besar setelah satu perang belum tentu istimewa. Uji plasebo membandingkannya dengan hari-hari biasa.")

    unduh = terpilih.drop(columns=["id"]).assign(tanggal=lambda d: d["tanggal"].dt.date, hari_nol=lambda d: d["hari_nol"].dt.date)
    st.download_button("⬇️ Unduh hasil event study (CSV)", unduh.to_csv(index=False).encode("utf-8"),
                       file_name=f"event_study_{saham}_{patokan or 'mean'}.csv", mime="text/csv")

# ----------------------------------------------------------------------------
# 4d. INTENSITAS PERANG
# ----------------------------------------------------------------------------
with tab_intensitas:
    belajar("Event study hanya melihat tanggal tertentu. Di sini kita melihat setiap minggu: apakah minggu dengan "
            "lonjakan korban konflik juga minggu ketika saham naik lebih tinggi dari pasar? Kalau korelasinya di dalam "
            "pita abu-abu, hubungannya tidak bisa dibedakan dari kebetulan.")
    teater = st.multiselect("Teater konflik", intensitas.TEATER, default=[],
                            placeholder="Semua teater (dunia)", help="Kosongkan untuk korban seluruh dunia.")
    gab = intensitas.gabung_mingguan(konflik, harga_adj, saham, patokan, teater or None)
    lag = intensitas.korelasi_lag(gab)

    c1, c2 = st.columns([1.3, 1])
    with c1:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=gab.index, y=gab["korban"], name="Korban per minggu", marker_color="#f87171", opacity=0.55,
                             hovertemplate="%{x|%d %b %Y}<br>%{y:,.0f} korban<extra></extra>"))
        s = harga_lebar[saham].resample("W-FRI").last().reindex(gab.index)
        fig.add_trace(go.Scatter(x=s.index, y=s, name=f"Harga {saham}", line=dict(color=WARNA_TICKER.get(saham, AMBER), width=2),
                                 hovertemplate="%{x|%d %b %Y}<br>$%{y:,.2f}<extra></extra>"), secondary_y=True)
        fig.update_yaxes(title_text="Korban", secondary_y=False)
        fig.update_yaxes(title_text="Harga (USD)", secondary_y=True, showgrid=False, rangemode="tozero",
                         tickprefix="$", tickformat=",.0f")
        fig.update_layout(title=f"Korban konflik ({', '.join(teater) if teater else 'dunia'}) vs {saham}")
        st.plotly_chart(rapikan(fig, 420), use_container_width=True)
    with c2:
        fig = go.Figure()
        batas = float(lag["batas"].iloc[0])
        fig.add_hrect(y0=-batas, y1=batas, fillcolor="#4b5563", opacity=0.25, line_width=0)
        fig.add_trace(go.Bar(x=lag["lag"], y=lag["korelasi"],
                             marker_color=[AMBER if abs(r) > b else "#6b7280" for r, b in zip(lag["korelasi"], lag["batas"])],
                             hovertemplate="Lag %{x} minggu<br>r = %{y:.3f}<extra></extra>"))
        fig.update_xaxes(title_text="Lag (minggu); positif = return sesudah lonjakan", dtick=1)
        fig.update_yaxes(title_text="Korelasi", range=[-0.35, 0.35])
        fig.update_layout(title=f"Korelasi lonjakan korban vs return lebih {saham}", showlegend=False)
        st.plotly_chart(rapikan(fig, 420), use_container_width=True)

    panas = intensitas.minggu_terpanas(gab)
    c1, c2 = st.columns([1, 1.3])
    with c1:
        st.markdown("##### Minggu 10% paling 'panas' vs minggu lainnya")
        st.dataframe(pd.DataFrame({
            "Kelompok": panas["kelompok"],
            "Minggu": panas["jumlah_minggu"],
            "Rata-rata return lebih": panas["rata_return_lebih"].map(persen),
            "Median": panas["median_return_lebih"].map(persen),
            "Porsi minggu naik": panas["porsi_naik"].map(lambda x: persen(x, 0, False)),
        }), hide_index=True, use_container_width=True)
        r0 = float(lag.loc[lag["lag"] == 0, "korelasi"].iloc[0])
        st.caption(f"Korelasi di minggu yang sama r = {r0:.3f}; batas kebetulan ±{batas:.3f}. "
                   f"'Return lebih' = return {saham} dikurangi return {patokan or '0'} di minggu yang sama.")
    with c2:
        fig = go.Figure(go.Scatter(
            x=gab["perubahan_log"], y=gab["return_lebih"] * 100, mode="markers",
            marker=dict(color=AMBER, size=6, opacity=0.55), text=[tanggal_id(t) for t in gab.index],
            hovertemplate="Minggu %{text}<br>Perubahan log korban %{x:.2f}<br>Return lebih %{y:.1f}%<extra></extra>"))
        fig.update_xaxes(title_text="Perubahan log korban dibanding minggu sebelumnya")
        fig.update_yaxes(title_text=f"Return lebih {saham} (%)")
        fig.update_layout(title="Setiap titik = satu minggu", showlegend=False)
        st.plotly_chart(rapikan(fig, 360), use_container_width=True)

# ----------------------------------------------------------------------------
# 4e. PERTAHANAN ATAU TEKNOLOGI?
# ----------------------------------------------------------------------------
with tab_tech:
    belajar("Kalau Palantir benar-benar 'saham perang', harganya seharusnya bergerak bersama Lockheed Martin dan "
            "ETF pertahanan. Korelasi 1 = selalu bergerak searah, 0 = tidak ada hubungan.")
    c1, c2 = st.columns([1.4, 1])
    with c1:
        mulai = st.date_input("Mulai dari", value=harga_adj.index.min().date(),
                              min_value=harga_adj.index.min().date(), max_value=harga_adj.index.max().date())
        pilih = st.multiselect("Saham", list(TICKER), default=["PLTR", "ITA", "LMT", "QQQ", "SPY"])
        kin = intensitas.kinerja_relatif(harga_adj[pilih], mulai) if pilih else pd.DataFrame()
        fig = go.Figure()
        for t in pilih:
            fig.add_trace(go.Scatter(x=kin.index, y=kin[t], name=t, line=dict(color=WARNA_TICKER[t], width=2.5 if t == "PLTR" else 1.5),
                                     hovertemplate="%{x|%d %b %Y}<br>%{y:,.0f}<extra>" + t + "</extra>"))
        fig.update_yaxes(type="log", title_text="Nilai (awal = 100, skala log)",
                         tickvals=[25, 50, 100, 200, 500, 1000, 2000, 5000])
        fig.update_layout(title="Kinerja sejak tanggal mulai (termasuk dividen)")
        st.plotly_chart(rapikan(fig, 430), use_container_width=True)
        if pilih:
            akhir = kin.iloc[-1].sort_values(ascending=False)
            st.caption(" · ".join(f"**{t}** {akhir[t] / 100:,.1f}x".replace(".", ",") for t in akhir.index))
    with c2:
        kor = ret[list(TICKER)].corr()
        fig = go.Figure(go.Heatmap(z=kor.values, x=kor.columns, y=kor.index, zmin=-1, zmax=1,
                                   colorscale=[[0, "#1e3a8a"], [0.5, "#111827"], [1, AMBER]],
                                   text=np.round(kor.values, 2), texttemplate="%{text:.2f}", textfont=dict(size=11), hovertemplate="%{y} × %{x}: %{z:.2f}<extra></extra>"))
        fig.update_layout(title="Korelasi return harian sejak IPO PLTR")
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(rapikan(fig, 470), use_container_width=True)

    kb = intensitas.korelasi_bergulir(ret, saham if saham != "ITA" else "PLTR", ("ITA", "LMT", "QQQ"), 120)
    fig = go.Figure()
    for t in kb.columns:
        fig.add_trace(go.Scatter(x=kb.index, y=kb[t], name=f"vs {t}", line=dict(color=WARNA_TICKER[t], width=2)))
    for _, ev in peristiwa_semua[peristiwa_semua["kategori"] == "perang_baru"].iterrows():
        if ev["tanggal"] >= kb.index.min():
            fig.add_vline(x=ev["tanggal"], line_dash="dot", line_color="#f87171", opacity=0.6)
    fig.update_yaxes(title_text="Korelasi 120 hari", range=[-0.3, 1])
    fig.update_layout(title=f"Korelasi bergulir {saham if saham != 'ITA' else 'PLTR'} dengan saham pertahanan dan teknologi "
                            "(garis merah = perang baru pecah)")
    st.plotly_chart(rapikan(fig, 380), use_container_width=True)
    st.markdown(
        f"Sejak IPO, korelasi harian PLTR dengan **QQQ** {kor.loc['PLTR', 'QQQ']:.2f}, dengan **ITA** "
        f"{kor.loc['PLTR', 'ITA']:.2f}, dan dengan **Lockheed Martin** hanya {kor.loc['PLTR', 'LMT']:.2f}. "
        "Pasar memperlakukan Palantir sebagai saham software/AI, bukan kontraktor senjata, meskipun pelanggan "
        "terbesarnya adalah militer.".replace("0.", "0,")
    )

# ----------------------------------------------------------------------------
# 4f. DATA & SUMBER
# ----------------------------------------------------------------------------
with tab_data:
    st.markdown("##### Peristiwa perang yang diuji")
    tampil = peristiwa_semua.assign(tanggal=peristiwa_semua["tanggal"].dt.date)[
        ["tanggal", "peristiwa", "label_kategori", "kawasan", "keterangan", "sumber"]]
    st.dataframe(tampil.rename(columns={"label_kategori": "jenis"}), hide_index=True, use_container_width=True,
                 column_config={"sumber": st.column_config.LinkColumn("sumber", display_text="buka")})
    c1, c2, c3 = st.columns(3)
    c1.download_button("⬇️ peristiwa_perang.csv", peristiwa_semua.drop(columns=["label_kategori"]).to_csv(index=False).encode(),
                       "peristiwa_perang.csv", "text/csv")
    c2.download_button("⬇️ harga_saham.csv", harga.to_csv(index=False).encode(), "harga_saham.csv", "text/csv")
    c3.download_button("⬇️ konflik_harian.csv", konflik.to_csv(index=False).encode(), "konflik_harian.csv", "text/csv")

    st.markdown(f"""
| Data | Sumber | Isi | Pembaruan |
|---|---|---|---|
| Harga saham | [Yahoo Finance](https://finance.yahoo.com/quote/PLTR/) (chart API, tanpa key) | Harga harian {", ".join(TICKER)} sejak {tanggal_id(harga["tanggal"].min())} ({ribuan(len(harga))} baris) | Live + snapshot mingguan |
| Korban konflik | [UCDP GED 26.1 + Candidate](https://ucdp.uu.se/downloads/) (Universitas Uppsala) | Korban harian per teater konflik, {tanggal_id(konflik["tanggal"].min())} s/d {tanggal_id(konflik["tanggal"].max())} | GED tahunan, Candidate bulanan |
| Peristiwa perang | Kurasi manual, tiap baris bertautan ke sumber | {len(peristiwa_semua)} peristiwa: perang baru, eskalasi, serangan AS, gencatan senjata | Manual |
| Laporan keuangan PLTR | Kalender rilis publik, dicek dengan lonjakan volume | {len(laporan)} tanggal rilis kuartalan | Manual |
""")
    st.caption("Catatan: peristiwa 2026 berasal dari pemberitaan yang masih berkembang; tanggalnya mengikuti sumber yang "
               "ditautkan. Korban UCDP 2026 adalah rilis awal dan biasanya bertambah saat revisi.")

# ----------------------------------------------------------------------------
# 4g. CARA KERJA
# ----------------------------------------------------------------------------
with tab_cara:
    st.markdown(f"""
#### Alur analisis

1. **Harga** 8 ticker diambil dari Yahoo Finance. Return harian dihitung dari *adjusted close* (sudah memperhitungkan dividen).
2. **Hari 0** setiap peristiwa = hari bursa pertama pada atau setelah tanggalnya. Perang yang pecah di akhir pekan baru
   tercermin hari Senin.
3. **Market model.** Pada 120 hari bursa sebelum peristiwa (hari {sp.JENDELA_ESTIMASI[0]} s/d {sp.JENDELA_ESTIMASI[1]}),
   dicari garis lurus `R_saham = α + β × R_patokan` dengan regresi OLS. Jeda 10 hari sebelum hari 0 memastikan
   kabar awal perang tidak ikut "mengajari" model.
4. **Abnormal return** di jendela peristiwa = return asli − (α + β × return patokan hari itu). Dijumlahkan menjadi **CAR**.
5. **Uji t** per peristiwa: `t = CAR / (σ × √L)`, dengan σ simpangan baku residual di jendela estimasi dan L panjang jendela.
6. **Uji plasebo.** CAR dihitung untuk setiap hari bursa yang mungkin, lalu 1.000 kali diambil {len(terpilih)} hari acak dan
   dirata-rata. Distribusi ini menjawab: seberapa sering hari biasa menghasilkan rata-rata seekstrem perang sungguhan?
7. **Intensitas konflik.** Korban UCDP dijumlah per minggu (Jumat ke Jumat), diubah menjadi perubahan log, lalu
   dikorelasikan dengan return lebih saham pada lag −4 s/d +4 minggu.

#### Keterbatasan yang perlu diingat

- **Peristiwa bertumpuk.** Beberapa peristiwa jatuh berdekatan (misalnya serangan AS ke Iran 22 Juni 2025 dan gencatan
  senjata dua hari kemudian), sehingga jendelanya saling menimpa.
- **Laporan keuangan dan berita perusahaan.** PLTR sering melonjak 20-30% setelah laporan kuartalan atau kontrak besar.
  Gunakan opsi "Buang peristiwa yang bertabrakan dengan laporan keuangan" di sidebar.
- **Pasar bisa tahu duluan.** Invasi Ukraina sudah diperingatkan berminggu-minggu sebelumnya. Sebagian reaksi bisa
  terjadi sebelum hari 0, jadi coba geser jendela ke −10.
- **Pemilihan peristiwa itu subjektif.** Daftar ini dikurasi; semua sumbernya bisa diperiksa di tab *Data & sources*.
- **Korelasi bukan sebab-akibat.** Bahkan CAR yang signifikan belum membuktikan perang *menyebabkan* kenaikan.

Penjelasan langkah demi langkah ada di [docs/BELAJAR.md](https://github.com/Avalon2222/pltr-war-index/blob/main/docs/BELAJAR.md).
""")
