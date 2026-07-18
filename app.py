# 🔥 SIVETA - Sistem Informasi Verifikasi TAFOR
import importlib
import verification_logic
importlib.reload(verification_logic)
import excel_export
importlib.reload(excel_export)
import streamlit as st
import pandas as pd
from datetime import datetime
from verification_logic import buat_tabel_laporan_excel, proses_verifikasi
from excel_export import generate_klasik_31_sheet, export_v_final_excel

st.set_page_config(page_title="SIVETA - BMKG", layout="wide")

# =========================================================================
# 🔒 INITIALIZATION MEMORI JAGA
# =========================================================================
if 'diklik_proses' not in st.session_state: 
    st.session_state['diklik_proses'] = False
if 'df_hasil' not in st.session_state: 
    st.session_state['df_hasil'] = None

# =========================================================================
# 🎨 PORTAL THEME INJECTION (PORTAL BMKG STYLE)
# =========================================================================
st.markdown("""
    <style>
        html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background-color: #F4F7FA !important;
            font-family: 'Inter', 'Segoe UI', Helvetica, Arial, sans-serif;
        }
        [data-testid="stSidebar"] {
            background-color: #FFFFFF !important;
            border-right: 1px solid #E2E8F0;
        }
        .bmkg-portal-header {
            background: linear-gradient(135deg, #004B87 0%, #002244 100%);
            padding: 24px;
            border-radius: 12px;
            color: #FFFFFF;
            margin-bottom: 25px;
            box-shadow: 0 4px 15px rgba(0, 75, 135, 0.15);
            border-left: 6px solid #00A8E8;
        }
        [data-testid="stMetricValue"] {
            font-size: 32px !important;
            font-weight: 800 !important;
            color: #004B87 !important;
        }
        [data-testid="stMetricLabel"] {
            font-size: 13px !important;
            font-weight: 600 !important;
            color: #334155 !important;
        }
        [data-testid="stMetric"] {
            background-color: #FFFFFF;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid #E2E8F0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# ⚡ OPTIMASI MEMORI CACHING (ANTI-LAG)
# ==========================================
@st.cache_data(show_spinner=False)
def jalankan_komputasi_cached(df_m_raw, df_t_raw, df_sp_raw):
    return proses_verifikasi(df_m_raw, df_t_raw, df_sp_raw)

# ==========================================
# 🗓️ SIDEBAR (HANYA UNTUK FILTER TANGGAL)
# ==========================================
st.sidebar.header("🗓️ Navigasi Laporan")
hari_ini = datetime.now().date()
tanggal_pilihan = st.sidebar.date_input("Filter Rentang Waktu:", value=(hari_ini, hari_ini), key="rentang_tanggal")

if isinstance(tanggal_pilihan, tuple) and len(tanggal_pilihan) == 2:
    tgl_mulai, tgl_selesai = tanggal_pilihan
elif isinstance(tanggal_pilihan, tuple) and len(tanggal_pilihan) == 1:
    tgl_mulai = tgl_selesai = tanggal_pilihan[0]
else:
    tgl_mulai = tgl_selesai = tanggal_pilihan[0] if isinstance(tanggal_pilihan, list) else tanggal_pilihan

banner_container = st.container()

# ==========================================
# 📥 AREA UPLOADER
# ==========================================
df_metar_raw, df_taf_raw, df_speci_raw = None, None, None

with st.expander("📖 BUKU SAKU SIVETA: Panduan Penggunaan Baru (Klik untuk Buka)"):
    st.markdown("""
    ### ⚡ Alur Kerja Baru SIVETA yang Disederhanakan
    Aplikasi kini berjalan lebih cepat dan ringkas dengan berfokus penuh pada **Laporan Verifikasi TAFOR**.

    ---
    #### 🛠️ CARA PENGGUNAAN
    1. **Unggah Berkas Wajib:** Masukkan file `METAR.csv` dan `TAF.csv` dari GTS.
    2. **Unggah Berkas Opsional:** Masukkan `SPECI.csv` jika stasiun Anda memilikinya. Jika dimasukkan, logika verifikasi otomatis melebur data SPECI ke dalam hasil akhir tanpa memisahkan tabel di web.
    3. **Tentukan Rentang Waktu:** Gunakan filter kalender di *sidebar* kiri.
    4. **Proses:** Tekan tombol **"🚀 PROSES DATA 🚀"**.
    """)

st.markdown("#### 📥 Unggah Berkas Sandi Extract GTS")
c_up1, c_up2, c_up3 = st.columns(3)
with c_up1:
    file_m = st.file_uploader("1. Unggah METAR.csv", type=["csv"], key="metar")
    if file_m: 
        df_m = pd.read_csv(file_m)
        if 'id' in df_m.columns: df_m = df_m.sort_values('id')
        df_metar_raw = df_m.drop_duplicates(subset=['data_timestamp'], keep='last')

with c_up2:
    file_t = st.file_uploader("2. Unggah TAF.csv", type=["csv"], key="taf")
    if file_t: 
        df_t = pd.read_csv(file_t)
        if 'id' in df_t.columns: df_t = df_t.sort_values('id')
        df_taf_raw = df_t.drop_duplicates(subset=['data_timestamp'], keep='last')

with c_up3:
    file_sp = st.file_uploader("3. Unggah SPECI.csv (Opsional)", type=["csv"], key="speci")
    if file_sp: 
        df_sp = pd.read_csv(file_sp)
        if 'id' in df_sp.columns: df_sp = df_sp.sort_values('id')
        df_speci_raw = df_sp.drop_duplicates(subset=['data_timestamp'], keep='last')

stasiun_aktif = "Menunggu Berkas..."
if df_metar_raw is not None and 'cccc' in df_metar_raw.columns:
    stasiun_terdeteksi = df_metar_raw['cccc'].dropna().unique().tolist()
    if stasiun_terdeteksi:
        stasiun_aktif = str(stasiun_terdeteksi[0]).strip().upper()

# Inject Banner
with banner_container:
    st.markdown(f"""
        <div class="bmkg-portal-header" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px;">
            <div style="display: flex; align-items: center;">
                <img src="https://upload.wikimedia.org/wikipedia/commons/1/12/Logo_BMKG_%282010%29.png" width="75" style="margin-right: 20px; filter: drop-shadow(0px 4px 6px rgba(0,0,0,0.3));">
                <div>
                    <h1 style="color: #FFFFFF !important; font-size: 26px !important; margin: 0 !important; font-weight: 700 !important;">SIVETA — SISTEM INFORMASI VERIFIKASI TAFOR</h1>
                    <p style="margin: 6px 0 0 0 !important; font-size: 13px !important; color: #E2E8F0 !important; text-transform: uppercase; letter-spacing: 1px;">
                        Kode ICAO Stasiun: <b style="color: #00A8E8; font-size: 14px;">{stasiun_aktif}</b>
                    </p>
                </div>
            </div>
            <div style="text-align: right; background: rgba(0,0,0,0.25); padding: 10px 20px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1);">
                <div style="font-size: 24px; font-weight: 800; color: #FFFFFF; font-family: monospace; letter-spacing: 2px;">
                    #️⃣ ACTIVE MODE
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

# ==========================================
# 🚀 TOMBOL EKSEKUSI
# ==========================================
if df_metar_raw is not None and df_taf_raw is not None:
    if st.button("🚀 PROSES DATA VERIFIKASI TAFOR 🚀", use_container_width=True, type="primary"):
        try:
            with st.spinner(f"Sedang memproses Verifikasi TAFOR stasiun {stasiun_aktif}..."):
                st.session_state['excel_ready'] = False
                
                df_speci_umpan = df_speci_raw if df_speci_raw is not None else pd.DataFrame(columns=df_metar_raw.columns)
                # 💡 Menggunakan '_' untuk mengabaikan output logbook/speci report yang tidak lagi dicetak di app.py
                df_hasil, _, _, _ = jalankan_komputasi_cached(df_metar_raw, df_taf_raw, df_speci_umpan)
                df_hasil['Datetime_Obj'] = pd.to_datetime(df_hasil['Waktu Aktual (UTC)']).dt.date
                
                st.session_state['df_hasil'] = df_hasil
                st.session_state['diklik_proses'] = True
        except Exception as e: 
            st.error(f"Gagal memproses data: {e}")

# ==========================================
# 📊 PRESENTASI METRIKS DASHBOARD UTAMA
# ==========================================
if st.session_state['diklik_proses'] and st.session_state['df_hasil'] is not None:
    df_hasil = st.session_state['df_hasil']
    df_filtered = df_hasil[(df_hasil['Datetime_Obj'] >= tgl_mulai) & (df_hasil['Datetime_Obj'] <= tgl_selesai) & (df_hasil['Kode_Stasiun'] == stasiun_aktif)].copy()
    
    if df_filtered.empty:
        st.warning(f"⚠️ Berkas data kosong pada rentang tanggal {tgl_mulai} s.d {tgl_selesai}. Silakan sesuaikan filter tanggal.")
    else:
        rows_tafor = []
        total_b_global = 0
        total_sampel_global = 0
        
        p_headers = {
            'S_Arah': 'A. Arah Angin (Wind Direction)',
            'S_Kec': 'B. Kecepatan Angin (Wind Speed)',
            'S_Vis': 'C. Jarak Pandang (Visibility)',
            'S_Wx': 'D. Cuaca / Endapan (Significant Weather)',
            'S_AwanJml': 'E. Jumlah Awan (Cloud Amount)',
            'S_AwanTgi': 'F. Tinggi Dasar Awan (Cloud Base)'
        }
        
        for col_name, label in p_headers.items():
            b = (df_filtered[col_name] == "B").sum()
            s = (df_filtered[col_name] == "S").sum()
            tot = b + s
            pct = (b / tot * 100) if tot > 0 else 0.0
            total_b_global += b
            total_sampel_global += tot
            rows_tafor.append({"param": label, "b": int(b), "s": int(s), "tot": int(tot), "pct": pct})
            
        total_accuracy_global = (total_b_global / total_sampel_global * 100) if total_sampel_global > 0 else 0.0
        
        st.markdown("### 📊 VERIFIKASI TAFOR: Komparasi Akurasi per Unsur Cuaca")
        
        c_head1, c_head2, c_head3 = st.columns([3, 2, 2])
        c_head1.write("📝 **Unsur Meteorologi**")
        c_head2.write("🎯 **Persentase Ketelitian**")
        c_head3.write("🔢 **Proporsi Data (Benar / Total)**")
        st.markdown("---")
        
        for item in rows_tafor:
            c1, c2, c3 = st.columns([3, 2, 2])
            c1.write(f"**{item['param']}**")
            c2.code(f" {round(item['pct'], 2)} % ")
            c3.write(f"⭐ {item['b']} dari {item['tot']} sampel")
            
        st.markdown("---")
        
        st.subheader("🏆 TOTAL AKURASI KESELURUHAN")
        st.metric(label="Total Akurasi Verifikasi TAFOR", value=f"{round(total_accuracy_global, 1)}%")
        st.markdown("---")
        
        # ==========================================
        # 📥 AREA UNDUH LAPORAN EXCEL
        # ==========================================
        str_m = tgl_mulai.strftime('%Y%m%d')
        nama_bulan = tgl_mulai.strftime('%B').upper()
        tahun_str = tgl_mulai.strftime('%Y')
        
        st.markdown("### 📥 Unduh Laporan Excel")
        
        c_ttd1, c_ttd2 = st.columns(2)
        with c_ttd1:
            nama_kepala = st.text_input("Nama Kepala Stasiun:", value="[NAMA KEPALA STASIUN]")
            nip_kepala = st.text_input("NIP Kepala Stasiun:", value="[NIP KEPALA]")
        with c_ttd2:
            nama_forecaster = st.text_input("Nama Petugas Pembuat Laporan:", value="KAPTEN METEO")
            nip_forecaster = st.text_input("NIP Petugas:", value="[NIP PETUGAS]")
            
        st.markdown("---")
        
        opsi_klasik = st.checkbox("Sertakan Laporan Format KLASIK (31 Sheet Harian)")
        
        if st.button("⚙️ SIAPKAN FILE EXCEL UNTUK DIUNDUH", use_container_width=True):
            with st.spinner("Mesin sedang merakit data ke format Excel... Mohon tunggu sebentar..."):
                
                st.session_state['dl_verifikasi_tafor'] = export_v_final_excel(
                    df_vfinal = buat_tabel_laporan_excel(df_filtered), 
                    bulan = nama_bulan, 
                    tahun = tahun_str, 
                    stasiun = stasiun_aktif, 
                    nama_petugas = nama_forecaster,
                    nip_petugas = nip_forecaster,
                    nama_kepala = nama_kepala,
                    nip_kepala = nip_kepala
                )
                
                if opsi_klasik:
                    st.session_state['dl_klasik'] = generate_klasik_31_sheet(df_filtered).getvalue()
                else:
                    st.session_state['dl_klasik'] = None
                    
                st.session_state['excel_ready'] = True

        if st.session_state.get('excel_ready', False):
            st.success("✅ Berkas Excel telah selesai dirakit dan siap untuk diunduh!")
            
            if opsi_klasik and st.session_state.get('dl_klasik') is not None:
                c_dl1, c_dl2 = st.columns(2)
                with c_dl1:
                    st.download_button("📊 Unduh Laporan VERIFIKASI TAFOR", data=st.session_state['dl_verifikasi_tafor'], file_name=f"VERIFIKASI_TAFOR_{stasiun_aktif}_{str_m}.xlsx", use_container_width=True, type="primary")
                with c_dl2:
                    st.download_button("📄 Unduh Laporan Format KLASIK 31", data=st.session_state['dl_klasik'], file_name=f"KLASIK_{stasiun_aktif}_{str_m}.xlsx", use_container_width=True)
            else:
                st.download_button("📊 Unduh Laporan VERIFIKASI TAFOR", data=st.session_state['dl_verifikasi_tafor'], file_name=f"VERIFIKASI_TAFOR_{stasiun_aktif}_{str_m}.xlsx", use_container_width=True, type="primary")
                
        st.markdown("---")
