import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import re
import os
import sqlite3
from datetime import datetime
from verification_logic import proses_verifikasi, parse_sandi, hitung_angin_arah, hitung_angin_kec, hitung_vis, hitung_cuaca, hitung_awan_jml, hitung_awan_tgi, hitung_verifikasi_TAFOR
from excel_export import generate_lapbul_excel, generate_form_2026, generate_logbook_excel, generate_klasik_31_sheet

st.set_page_config(page_title="SIVETA - BMKG", layout="wide")

# =========================================================================
# 🔒 INITIALIZATION MEMORI JAGA (ANTI-KEYERROR)
# =========================================================================
if 'diklik_proses' not in st.session_state: 
    st.session_state['diklik_proses'] = False
if 'df_hasil' not in st.session_state: 
    st.session_state['df_hasil'] = None
if 'df_speci_report' not in st.session_state: 
    st.session_state['df_speci_report'] = None

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
        button[data-baseweb="tab"] {
            font-weight: 600 !important;
            color: #64748B !important;
            font-size: 14px !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            color: #004B87 !important;
            border-bottom-color: #004B87 !important;
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
# 🗄️ DATABASE SYSTEM UNIVERSAL MURNI ICAO
# ==========================================
def init_db():
    conn = sqlite3.connect('verifier_db.sqlite')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS rekap_performa 
                 (stasiun TEXT, bulan_tahun TEXT, akurasi_tiap_jam REAL, akurasi_verifikasi_tafor REAL,
                  PRIMARY KEY (stasiun, bulan_tahun))''')
    c.execute('''CREATE TABLE IF NOT EXISTS master_bandara 
                 (icao TEXT PRIMARY KEY, nama TEXT, heading_a INTEGER, heading_b INTEGER)''')
    conn.commit()
    conn.close()

def simpan_rekap_db(stasiun, bulan_tahun, jam_score, tafor_score):
    try:
        conn = sqlite3.connect('verifier_db.sqlite')
        c = conn.cursor()
        
        # Jaga-jaga: Paksa buat tabel darurat jika tiba-tiba hilang di Cloud
        c.execute('''CREATE TABLE IF NOT EXISTS rekap_performa 
                     (stasiun TEXT, bulan_tahun TEXT, akurasi_tiap_jam REAL, akurasi_verifikasi_tafor REAL,
                      PRIMARY KEY (stasiun, bulan_tahun))''')
                      
        c.execute("SELECT COUNT(*) FROM rekap_performa WHERE stasiun=? AND bulan_tahun=?", (stasiun, bulan_tahun))
        data_ada = c.fetchone()[0]
        
        if data_ada > 0:
            c.execute('''UPDATE rekap_performa 
                         SET akurasi_tiap_jam=?, akurasi_verifikasi_tafor=? 
                         WHERE stasiun=? AND bulan_tahun=?''', 
                      (jam_score, tafor_score, stasiun, bulan_tahun))
        else:
            c.execute('''INSERT INTO rekap_performa (stasiun, bulan_tahun, akurasi_tiap_jam, akurasi_verifikasi_tafor)
                         VALUES (?, ?, ?, ?)''', 
                      (stasiun, bulan_tahun, jam_score, tafor_score))
                      
        conn.commit()
        conn.close()
    except Exception as e:
        # Jika database cloud sedang error, biarkan saja (jangan hancurkan aplikasinya)
        pass

def ambil_tren_db(stasiun):
    try:
        conn = sqlite3.connect('verifier_db.sqlite')
        df = pd.read_sql_query("SELECT bulan_tahun, akurasi_tiap_jam, akurasi_verifikasi_tafor FROM rekap_performa WHERE stasiun=? ORDER BY bulan_tahun ASC", conn, params=(stasiun,))
        conn.close()
        return df
    except Exception as e:
        # Jika database kosong/error, kembalikan tabel kosong tanpa membuat aplikasi crash
        return pd.DataFrame()

init_db()

# ==========================================
# 🗓️ SIDEBAR (HANYA UNTUK FILTER TANGGAL)
# ==========================================
st.sidebar.header("🗓️ Navigasi Laporan")
hari_ini = datetime.now().date()
tanggal_pilihan = st.sidebar.date_input("Filter Rentang Waktu:", value=(hari_ini, hari_ini), key="rentang_tanggal")

# ==========================================
# 🚀 1️⃣ KOTAK PENAHAN BANNER UTAMA (ANTI-ERROR)
# ==========================================
banner_container = st.container()

# ==========================================
# 📥 2️⃣ AREA UPLOADER (DI BAWAH BANNER)
# ==========================================
df_metar_raw, df_taf_raw, df_speci_raw = None, None, None


# --- KOTAK PANDUAN PENGGUNA (BUKU SAKU SIVETA) ---
with st.expander("📖 BUKU SAKU SIVETA: Panduan Penggunaan & Penjelasan Laporan (Klik untuk Buka)"):
    st.markdown("""
    ### Selamat Datang di SIVETA (Sistem Informasi Verifikasi TAFOR)
    Aplikasi ini dirancang untuk memproses ribuan baris sandi cuaca GTS menjadi laporan verifikasi TAFOR yang akurat dan bebas dari *human error*, hanya dalam hitungan detik.
    
    ---

    #### 🛠️ CARA PENGGUNAAN (4 LANGKAH MUDAH)
    **1. Persiapan Data (GTS)**
    Unduh riwayat sandi cuaca stasiun Anda dari sistem GTS dalam format `.csv`. Pastikan Anda mengunduh 3 file terpisah: **METAR, TAF, dan SPECI**.
    Melalui portal "https://bmkgsatu.bmkg.go.id/extractgts" atau menu "Output Data > Extract" pada web bmkgsatu, data yang digunakan memiliki status "SENT".
    
    **2. Unggah Data**
    Sistem sangat sensitif terhadap format sandi tetapi tidak ada aturan baku penamaan file, Masukkan file ke slot yang tepat:
    * **Slot 1:** Khusus untuk file `METAR.csv`
    * **Slot 2:** Khusus untuk file `TAF.csv`
    * **Slot 3:** Khusus untuk file `SPECI.csv`
    
    **3. Sesuaikan Rentang Waktu**
    Gunakan menu kalender di *sidebar* kiri. **Penting:** Pastikan rentang tanggal yang dipilih di kalender benar-benar ada di dalam file CSV yang Anda unggah.
    
    **4. Proses Data**
    Klik tombol biru **"🚀 PROSES DATA 🚀"**. Sistem akan otomatis membersihkan karakter *error* transmisi (GTS), menyingkronkan waktu, dan menghitung akurasi.

    ---

    #### 🖥️ MEMAHAMI TAMPILAN LAYAR (TAB MENU)
    Setelah data diproses, Anda akan melihat 2 Tab utama di layar:
    * 📊 **TAB 1 (Matriks Tiap Jam):** Menampilkan evaluasi cuaca secara *Time-Series* (per 30 menit / per jam). Cocok untuk menganalisa secara detail pada jam berapa prakiraan mulai meleset tebakannya.
    * 📋 **TAB 2 (Verifikasi TAF):** Menampilkan evaluasi berdasarkan **Grup TAF** (Base, TEMPO, BECMG).

    ---

    #### 📥 MEMAHAMI 4 TOMBOL UNDUH (EXCEL)
    SIVETA menjembatani masa transisi format laporan di stasiun Anda dengan menyediakan opsi unduhan yang lengkap:
    
    📄 **1. Matriks Jam (Excel):**
    Data mentah yang berisi rincian sandi TAF disandingkan dengan METAR per jamnya. Sangat berguna untuk bahan audit atau penelitian mendalam.

    📄 **2. Verifikasi TAF (Excel):**
    *Laporan Utama.* Mengevaluasi murni berbasis *Decision-Making* (Hanya menilai Grup TAF yang dirilis). **Nilainya lebih ketat, objektif, dan adil.**

    📄 **3. Format Klasik (Excel):**
    *Laporan Transisi.* Membentuk 31 *sheet* harian (format A-F). Mengevaluasi secara *Time-Series* (setiap setengah jam). 
    
    📝 **4. Logbook Perubahan:**
    Mencatat jejak rekam kapan sebuah TAF di-Amandemen (AMD) atau dibatalkan.
    
    
    #### ⚙️ PENGATURAN RUNWAY & CROSSWIND (ANGIN SILANG)
    SIVETA dilengkapi dengan algoritma penerbangan untuk menghitung komponen **Crosswind (Angin Potong/Silang)** secara otomatis. 
    Karena setiap bandara memiliki orientasi landasan pacu (*heading runway*) yang berbeda, Anda wajib memastikan data stasiun Anda telah dikonfigurasi:
    * Jika stasiun Anda memproses bandara baru yang belum terdaftar, hasil perhitungan angin silang bisa tidak akurat.
    * **Cara Konfigurasi:** Gulir ke bagian **paling bawah** aplikasi ini. Buka panel menu **"Manajemen"**, lalu masukkan kode ICAO stasiun dan arah derajat *Runway* bandara Anda (Misal: Runway 12/30, maka masukkan angka 120 dan 300). SIVETA akan mengunci pengaturan ini selamanya di dalam database!
    * Jika bandara Anda memiliki 2 landasan (misal Runway 09/27 dan Runway 10/28), masukkan semua angkanya dengan dipisahkan tanda koma, contoh: `90, 270, 100, 280`. SIVETA akan langsung mengunci dan memproses multi-runway tersebut dengan sempurna!
    """)

# --------------------------------------------

st.markdown("#### 📥 Unggah Berkas Sandi Extract GTS")
c_up1, c_up2, c_up3 = st.columns(3)
with c_up1:
    file_m = st.file_uploader("1. Unggah METAR.csv", type=["csv"], key="metar")
    if file_m: df_metar_raw = pd.read_csv(file_m)
with c_up2:
    file_t = st.file_uploader("2. Unggah TAF.csv", type=["csv"], key="taf")
    if file_t: df_taf_raw = pd.read_csv(file_t)
with c_up3:
    file_sp = st.file_uploader("3. Unggah SPECI.csv", type=["csv"], key="speci")
    if file_sp: df_speci_raw = pd.read_csv(file_sp)

stasiun_aktif = "Menunggu Berkas..."
if df_metar_raw is not None and 'cccc' in df_metar_raw.columns:
    stasiun_terdeteksi = df_metar_raw['cccc'].dropna().unique().tolist()
    if stasiun_terdeteksi:
        stasiun_aktif = str(stasiun_terdeteksi[0]).strip().upper()
      

st.sidebar.markdown("---")
st.sidebar.header("📍 Stasiun Terdeteksi")

# Mengisi Banner Biru Mewah (Logo + Jam Digital) ke dalam Container
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
                <div id="live_clock" style="font-size: 24px; font-weight: 800; color: #FFFFFF; font-family: monospace; letter-spacing: 2px;">
                    🕰️ Memuat...
                </div>
                <div id="live_date" style="font-size: 12px; color: #00A8E8; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-top: 2px;">
                    Memuat Tanggal...
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Injeksi Javascript Tak Terlihat (Berdetak Otomatis di Latar Belakang)
    components.html("""
        <script>
            function updateClock() {
                var doc = window.parent.document;
                var clockEl = doc.getElementById('live_clock');
                var dateEl = doc.getElementById('live_date');
                
                if (clockEl && dateEl) {
                    var now = new Date();
                    
                    // Format Jam:Menit:Detik
                    var h = String(now.getHours()).padStart(2, '0');
                    var m = String(now.getMinutes()).padStart(2, '0');
                    var s = String(now.getSeconds()).padStart(2, '0');
                    clockEl.innerHTML = '🕰️ ' + h + ':' + m + ':' + s;
                    
                    // Format Tanggal Indonesia
                    var days = ['Minggu', 'Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu'];
                    var months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Ags', 'Sep', 'Okt', 'Nov', 'Des'];
                    var dayName = days[now.getDay()];
                    var d = String(now.getDate()).padStart(2, '0');
                    var monthName = months[now.getMonth()];
                    var y = now.getFullYear();
                    
                    dateEl.innerHTML = dayName + ', ' + d + ' ' + monthName + ' ' + y;
                }
            }
            // Perintahkan komputer mengeksekusi updateClock setiap 1000 milidetik (1 Detik)
            setInterval(updateClock, 1000);
            updateClock();
        </script>
    """, height=0, width=0)

# 🚀 3️⃣ TOMBOL EKSEKUSI UTAMA (SPECI OPSIONAL & EKSEKUSI GANDA)
if df_metar_raw is not None and df_taf_raw is not None:
    if st.button("🚀 PROSES DATA 🚀", use_container_width=True, type="primary"):
        try:
            with st.spinner(f"Sedang menganalisa data stasiun {stasiun_aktif}..."):
                
                # 1. Jalankan Komputasi Jalur Utama (Dengan SPECI jika ada, Tanpa SPECI jika tidak diupload)
                df_speci_umpan = df_speci_raw if df_speci_raw is not None else pd.DataFrame(columns=df_metar_raw.columns)
                df_hasil, df_speci_report, _, _ = jalankan_komputasi_cached(df_metar_raw, df_taf_raw, df_speci_umpan)
                df_hasil['Datetime_Obj'] = pd.to_datetime(df_hasil['Waktu Aktual (UTC)']).dt.date
                
                if 'Waktu SPECI (UTC)' in df_speci_report.columns and not df_speci_report.empty:
                    df_speci_report['Datetime_Obj'] = pd.to_datetime(df_speci_report['Waktu SPECI (UTC)']).dt.date
                else:
                    df_speci_report['Waktu SPECI (UTC)'] = pd.Series(dtype='object')
                    df_speci_report['Datetime_Obj'] = pd.Series(dtype='object')
                
                st.session_state['df_hasil'] = df_hasil
                st.session_state['df_speci_report'] = df_speci_report
                
                # 2. JIKA SPECI ADA: Jalankan komputasi bayangan ke-2 (Khusus Tanpa SPECI)
                if df_speci_raw is not None and not df_speci_raw.empty:
                    df_speci_kosong = pd.DataFrame(columns=df_metar_raw.columns)
                    df_hasil_no_sp, _, _, _ = jalankan_komputasi_cached(df_metar_raw, df_taf_raw, df_speci_kosong)
                    df_hasil_no_sp['Datetime_Obj'] = pd.to_datetime(df_hasil_no_sp['Waktu Aktual (UTC)']).dt.date
                    st.session_state['df_hasil_no_sp'] = df_hasil_no_sp
                    st.session_state['ada_speci'] = True
                else:
                    st.session_state['ada_speci'] = False
                    
                st.session_state['diklik_proses'] = True
        except Exception as e: st.error(f"Gagal memproses data: {e}")
            
# INTERFACE DASHBOARD UTAMA
if st.session_state['diklik_proses'] and st.session_state['df_hasil'] is not None:
    df_hasil = st.session_state['df_hasil']
    df_speci_report = st.session_state['df_speci_report']
    
    if isinstance(tanggal_pilihan, tuple) and len(tanggal_pilihan) == 2: tgl_mulai, tgl_selesai = tanggal_pilihan
    else: tgl_mulai = tgl_selesai = tanggal_pilihan[0] if isinstance(tanggal_pilihan, list) else tanggal_pilihan
        
    df_filtered = df_hasil[(df_hasil['Datetime_Obj'] >= tgl_mulai) & (df_hasil['Datetime_Obj'] <= tgl_selesai) & (df_hasil['Kode_Stasiun'] == stasiun_aktif)].copy()
    df_speci_filtered = df_speci_report[(df_speci_report['Datetime_Obj'] >= tgl_mulai) & (df_speci_report['Datetime_Obj'] <= tgl_selesai)].copy()
    
    if df_filtered.empty:
        st.warning(f"⚠️ Berkas data kosong pada rentang tanggal {tgl_mulai} s.d {tgl_selesai}. Geser kalender filter di sidebar kiri ke waktu yang sesuai.")
    else:
        # HITUNG MATRIKS TIAP JAM
        total_b_g, total_data_global, rows_m = 0, 0, []
        p_headers = {'A':'A (Arah Wind)','B':'B (Kec Wind)','C':'C (Visibility)','D':'D (Cuaca)','E':'E (Jml Awan)','F':'F (Tgi Awan)'}
        for k, col_name in {'A':"S_Arah",'B':"S_Kec",'C':"S_Vis",'D':"S_Wx",'E':"S_AwanJml",'F':"S_AwanTgi"}.items():
            b, s = (df_filtered[col_name] == "B").sum(), (df_filtered[col_name] == "S").sum()
            tot = b + s
            pct = (b / tot * 100) if tot > 0 else 0
            total_b_g += b; total_data_global += tot
            rows_m.append({"Nama Parameter": p_headers[k], "Jumlah Benar (B)": int(b), "Jumlah Salah (S)": int(s), "Total Sampel Data (Tiap Jam)": int(tot), "Prosentase Ketelitian": f"{round(pct, 2)}%"})
        akurasi_global_matriks = round((total_b_g / total_data_global * 100), 1) if total_data_global > 0 else 0
        
        # HITUNG FORM BULANAN REGULASI SOP 2025
        rekapan_form = hitung_verifikasi_TAFOR(df_filtered)
        rows_f, total_b_f, total_d_f = [], 0, 0
        for k in ['A', 'B', 'C', 'D', 'E', 'F']:
            b_f, s_f = rekapan_form[k]['B'], rekapan_form[k]['S']
            tot_f = b_f + s_f
            pct_f = (b_f / tot_f * 100) if tot_f > 0 else 0
            total_b_f += b_f; total_d_f += tot_f
            rows_f.append({"Nama Parameter": p_headers[k], "Jumlah Benar (B)": int(b_f), "Jumlah Salah (S)": int(s_f), "Total Sampel Data (Grup TAF)": int(tot_f), "Prosentase Ketelitian": f"{round(pct_f, 2)}%"})
        akurasi_global_form = round((total_b_f / total_d_f * 100 if total_d_f > 0 else 0), 1)

        simpan_rekap_db(stasiun_aktif, tgl_mulai.strftime('%Y-%m'), akurasi_global_matriks, akurasi_global_form)

        # ==========================================
        # 📊 KOMPARASI AKURASI PER UNSUR CUACA (DUAL MODE)
        # ==========================================
        st.markdown("### 📊 Komparasi Akurasi per Unsur Cuaca")
        
        ada_speci = st.session_state.get('ada_speci', False)
        
        if ada_speci:
            # --- JIKA ADA SPECI: BUAT TABEL 5 KOLOM ---
            df_fil_nosp = st.session_state['df_hasil_no_sp']
            df_fil_nosp = df_fil_nosp[(df_fil_nosp['Datetime_Obj'] >= tgl_mulai) & (df_fil_nosp['Datetime_Obj'] <= tgl_selesai) & (df_fil_nosp['Kode_Stasiun'] == stasiun_aktif)].copy()
            
            # Hitung rincian parameter untuk versi Tanpa SPECI
            rows_m_nosp = []
            for k, col_name in {'A':"S_Arah",'B':"S_Kec",'C':"S_Vis",'D':"S_Wx",'E':"S_AwanJml",'F':"S_AwanTgi"}.items():
                b, s = (df_fil_nosp[col_name] == "B").sum(), (df_fil_nosp[col_name] == "S").sum()
                tot = b + s
                pct = (b / tot * 100) if tot > 0 else 0
                rows_m_nosp.append({"B": int(b), "T": int(tot), "Pct": f"{round(pct, 2)}%"})
                
            rek_nosp = hitung_verifikasi_TAFOR(df_fil_nosp)
            rows_f_nosp = []
            for k in ['A', 'B', 'C', 'D', 'E', 'F']:
                b_f, s_f = rek_nosp[k]['B'], rek_nosp[k]['S']
                tot_f = b_f + s_f
                pct_f = (b_f / tot_f * 100) if tot_f > 0 else 0
                rows_f_nosp.append({"B": int(b_f), "T": int(tot_f), "Pct": f"{round(pct_f, 2)}%"})
            
            # Header Tabel 7 Kolom (Dengan Kolom Selisih)
            c_head1, c_head2, c_head3, c_diff1, c_head4, c_head5, c_diff2 = st.columns([1.5, 1.1, 1.1, 0.9, 1.1, 1.1, 0.9])
            c_head1.write("📝 **Parameter**")
            c_head2.write("🌪️ **Klasik (+SPECI)**")
            c_head3.write("☀️ **Klasik (-SPECI)**")
            c_diff1.write("📉 **Selisih**")
            c_head4.write("🌪️ **SOP (+SPECI)**")
            c_head5.write("☀️ **SOP (-SPECI)**")
            c_diff2.write("📉 **Selisih**")
            st.markdown("---")
            
            # Looping 6 Parameter
            for i in range(6):
                c1, c2, c3, cd1, c4, c5, cd2 = st.columns([1.5, 1.1, 1.1, 0.9, 1.1, 1.1, 0.9])
                c1.write(f"**{rows_m[i]['Nama Parameter']}**")
                
                # --- KALKULASI SELISIH KLASIK ---
                val_k_sp = float(rows_m[i]['Prosentase Ketelitian'].replace('%', ''))
                val_k_nosp = float(rows_m_nosp[i]['Pct'].replace('%', ''))
                diff_k = round(val_k_sp - val_k_nosp, 2)
                simbol_k = "🟢" if diff_k > 0 else ("🔴" if diff_k < 0 else "⚪")
                
                # Cetak Barisan Klasik
                c2.code(f"{rows_m[i]['Prosentase Ketelitian']} ({rows_m[i]['Jumlah Benar (B)']}/{rows_m[i]['Total Sampel Data (Tiap Jam)']})")
                c3.code(f"{rows_m_nosp[i]['Pct']} ({rows_m_nosp[i]['B']}/{rows_m_nosp[i]['T']})")
                cd1.markdown(f"{simbol_k} **{diff_k}%**")
                
                # --- KALKULASI SELISIH SOP 2025 ---
                val_s_sp = float(rows_f[i]['Prosentase Ketelitian'].replace('%', ''))
                val_s_nosp = float(rows_f_nosp[i]['Pct'].replace('%', ''))
                diff_s = round(val_s_sp - val_s_nosp, 2)
                simbol_s = "🟢" if diff_s > 0 else ("🔴" if diff_s < 0 else "⚪")
                
                # Cetak Barisan SOP 2025
                c4.code(f"{rows_f[i]['Prosentase Ketelitian']} ({rows_f[i]['Jumlah Benar (B)']}/{rows_f[i]['Total Sampel Data (Grup TAF)']})")
                c5.code(f"{rows_f_nosp[i]['Pct']} ({rows_f_nosp[i]['B']}/{rows_f_nosp[i]['T']})")
                cd2.markdown(f"{simbol_s} **{diff_s}%**")
                
        st.markdown("---")
        
        # ==========================================
        # 🏆 KESIMPULAN TOTAL KESELURUHAN (DENGAN VS TANPA SPECI)
        # ==========================================
        st.subheader("🏆 TOTAL AKURASI KESELURUHAN")
        
        if st.session_state.get('ada_speci', False):
            # --- MESIN HITUNG CEPAT (VERSI TANPA SPECI) ---
            df_fil_nosp = st.session_state['df_hasil_no_sp']
            df_fil_nosp = df_fil_nosp[(df_fil_nosp['Datetime_Obj'] >= tgl_mulai) & (df_fil_nosp['Datetime_Obj'] <= tgl_selesai) & (df_fil_nosp['Kode_Stasiun'] == stasiun_aktif)].copy()
            
            # Kalkulasi Klasik 31 Tanpa SPECI
            tot_b_m_nosp = sum((df_fil_nosp[c] == "B").sum() for c in ["S_Arah","S_Kec","S_Vis","S_Wx","S_AwanJml","S_AwanTgi"])
            tot_s_m_nosp = sum((df_fil_nosp[c] == "S").sum() for c in ["S_Arah","S_Kec","S_Vis","S_Wx","S_AwanJml","S_AwanTgi"])
            tot_data_m_nosp = tot_b_m_nosp + tot_s_m_nosp
            ak_klasik_nosp = round((tot_b_m_nosp / tot_data_m_nosp * 100), 1) if tot_data_m_nosp > 0 else 0
            
            # Kalkulasi SOP 2025 Tanpa SPECI
            rek_nosp = hitung_verifikasi_TAFOR(df_fil_nosp)
            tot_b_f_nosp = sum(rek_nosp[k]['B'] for k in ['A','B','C','D','E','F'])
            tot_s_f_nosp = sum(rek_nosp[k]['S'] for k in ['A','B','C','D','E','F'])
            tot_data_f_nosp = tot_b_f_nosp + tot_s_f_nosp
            ak_sop_nosp = round((tot_b_f_nosp / tot_data_f_nosp * 100), 1) if tot_data_f_nosp > 0 else 0

            # Tampilkan 4 Kotak Metrik Komparasi
            st.info("💡 **Dampak SPECI:** Anda bisa melihat perbedaan nilai evaluasi ketika stasiun memperhitungkan cuaca ekstrem mendadak (SPECI) dibandingkan dengan mengabaikannya.")
            c_tot1, c_tot2, c_tot3, c_tot4 = st.columns(4)
            c_tot1.metric("🌪️ Klasik (+SPECI)", f"{akurasi_global_matriks}%")
            c_tot2.metric("🌪️ SOP 2025 (+SPECI)", f"{akurasi_global_form}%")
            c_tot3.metric("☀️ Klasik (Tanpa SPECI)", f"{ak_klasik_nosp}%")
            c_tot4.metric("☀️ SOP 2025 (Tanpa SPECI)", f"{ak_sop_nosp}%")
            
        else:
            # Jika SPECI tidak diupload, tampilkan 2 kotak standar
            c_tot1, c_tot2, c_tot3 = st.columns([2, 1.5, 1.5])
            c_tot1.write("**Data Murni (Tanpa SPECI)**")
            c_tot2.metric("Nilai IKU Klasik", f"{akurasi_global_matriks}%")
            c_tot3.metric("Nilai Audit SOP", f"{akurasi_global_form}%")
            
        st.markdown("---")

        # ==========================================
        # AREA DOWNLOAD BUTTONS (CERDAS & DINAMIS)
        # ==========================================
        str_m, str_s = tgl_mulai.strftime('%Y%m%d'), tgl_selesai.strftime('%Y%m%d')
        
        st.markdown("### 📥 Unduh Laporan Excel")
        if st.session_state.get('ada_speci', False):
            st.success("✨ **Berkas SPECI terdeteksi!** SIVETA secara otomatis membelah diri dan menghasilkan 2 versi laporan untuk Anda.")
            c_dl1, c_dl2 = st.columns(2)
            
            # --- VERSI DIPENGARUHI SPECI ---
            with c_dl1:
                st.write("**🌪️ VERSI LENGKAP (DIPENGARUHI SPECI)**")
                st.download_button("📄 Klasik 31 (+SPECI)", data=generate_klasik_31_sheet(df_filtered).getvalue(), file_name=f"KLASIK_SPECI_{stasiun_aktif}_{str_m}.xlsx", use_container_width=True)
                st.download_button("📄 Verifikasi SOP (+SPECI)", data=generate_form_2026(df_filtered, df_speci_filtered).getvalue(), file_name=f"SOP_SPECI_{stasiun_aktif}_{str_m}.xlsx", use_container_width=True)
            
            # --- VERSI TANPA SPECI ---
            with c_dl2:
                st.write("**☀️ VERSI MURNI (TANPA SPECI)**")
                df_fil_nosp = st.session_state['df_hasil_no_sp']
                df_fil_nosp = df_fil_nosp[(df_fil_nosp['Datetime_Obj'] >= tgl_mulai) & (df_fil_nosp['Datetime_Obj'] <= tgl_selesai) & (df_fil_nosp['Kode_Stasiun'] == stasiun_aktif)].copy()
                empty_sp = pd.DataFrame(columns=df_speci_filtered.columns)
                
                st.download_button("📄 Klasik 31 (Tanpa SPECI)", data=generate_klasik_31_sheet(df_fil_nosp).getvalue(), file_name=f"KLASIK_NOSPECI_{stasiun_aktif}_{str_m}.xlsx", use_container_width=True)
                st.download_button("📄 Verifikasi SOP (Tanpa SPECI)", data=generate_form_2026(df_fil_nosp, empty_sp).getvalue(), file_name=f"SOP_NOSPECI_{stasiun_aktif}_{str_m}.xlsx", use_container_width=True)
                
        else:
            st.info("ℹ️ Tidak ada berkas SPECI yang diunggah. Menghasilkan 1 versi laporan murni.")
            c_dl1, c_dl2 = st.columns(2)
            with c_dl1:
                st.download_button("📄 Unduh Klasik 31 Sheet", data=generate_klasik_31_sheet(df_filtered).getvalue(), file_name=f"KLASIK_{stasiun_aktif}_{str_m}.xlsx", use_container_width=True)
            with c_dl2:
                st.download_button("📄 Unduh Verifikasi SOP 2025", data=generate_form_2026(df_filtered, df_speci_filtered).getvalue(), file_name=f"SOP_{stasiun_aktif}_{str_m}.xlsx", use_container_width=True)
            
