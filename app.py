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
    c.execute('''CREATE TABLE IF NOT EXISTS pegawai 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, nama TEXT, nip TEXT, jabatan TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS master_bandara 
                 (icao TEXT PRIMARY KEY, nama TEXT, heading_a INTEGER, heading_b INTEGER)''')
    
    c.execute("SELECT COUNT(*) FROM pegawai")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO pegawai (nama, nip, jabatan) VALUES ('TIM DATA & INFORMASI', 'Stasiun Meteorologi BMKG', 'Penyusun Laporan')")
    conn.commit()
    conn.close()

def auto_register_stasiun_baru(icao_code):
    conn = sqlite3.connect('verifier_db.sqlite')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM master_bandara WHERE icao=?", (str(icao_code).upper(),))
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO master_bandara VALUES (?, ?, 0, 180)", (str(icao_code).upper(), str(icao_code).upper()))
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

def ambil_semua_bandara():
    conn = sqlite3.connect('verifier_db.sqlite')
    df = pd.read_sql_query("SELECT * FROM master_bandara ORDER BY icao ASC", conn)
    conn.close()
    return df

def tambah_bandara(icao, nama, heading_a, heading_b):
    conn = sqlite3.connect('verifier_db.sqlite')
    c = conn.cursor()
    # Ubah int() menjadi str() agar SQLite bisa menyimpan deretan teks koma "90, 270"
    c.execute("INSERT OR REPLACE INTO master_bandara VALUES (?, ?, ?, ?)", (str(icao).upper(), str(nama).strip(), str(heading_a), str(heading_b)))
    conn.commit()
    conn.close()

def ambil_semua_pegawai():
    conn = sqlite3.connect('verifier_db.sqlite')
    df = pd.read_sql_query("SELECT * FROM pegawai ORDER BY id ASC", conn)
    conn.close()
    return df

def tambah_pegawai(nama, nip, jabatan):
    conn = sqlite3.connect('verifier_db.sqlite')
    c = conn.cursor()
    c.execute("INSERT INTO pegawai (nama, nip, jabatan) VALUES (?, ?, ?)", (nama, nip, jabatan))
    conn.commit()
    conn.close()

def edit_pegawai(id_peg, nama, nip, jabatan):
    conn = sqlite3.connect('verifier_db.sqlite')
    c = conn.cursor()
    c.execute("UPDATE pegawai SET nama=?, nip=?, jabatan=? WHERE id=?", (nama, nip, jabatan, id_peg))
    conn.commit()
    conn.close()

def hapus_pegawai(id_peg):
    conn = sqlite3.connect('verifier_db.sqlite')
    c = conn.cursor()
    c.execute("DELETE FROM pegawai WHERE id=?", (id_peg,))
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 📄 GENERATOR NOTA DINAS ADM SIAP CETAK
# ==========================================
def generate_nota_dinas_html(tgl_m, tgl_s, acc_jam, acc_form, table_jam, table_form, total_speci, nama_ttd, nip_ttd, jab_ttd, st_name):
    str_tgl = datetime.now().strftime('%d %B %Y')
    param_terendah = "Visibility (Jarak Pandang)"
    min_score = 100.0
    for r in table_form:
        score_val = float(str(r['Prosentase Ketelitian']).replace('%',''))
        if score_val < min_score:
            min_score = score_val
            param_terendah = r['Nama Parameter']

    html_content = f"""
    <html>
    <head><style>
        body {{ font-family: 'Arial', sans-serif; margin: 40px; color: #000; line-height: 1.4; }}
        .kop {{ text-align: center; font-weight: bold; border-bottom: 3px double #000; padding-bottom: 10px; margin-bottom: 20px; }}
        .kop h2 {{ margin: 0; font-size: 14px; }}
        .kop h1 {{ margin: 5px 0; font-size: 16px; text-transform: uppercase; }}
        .judul {{ text-align: center; font-weight: bold; text-decoration: underline; font-size: 14px; margin-top: 15px; }}
        .nomor {{ text-align: center; font-size: 12px; margin-bottom: 25px; }}
        .meta-table {{ width: 100%; margin-bottom: 20px; font-size: 13px; }}
        table.data {{ width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 12px; }}
        table.data th, table.data td {{ border: 1px solid #000; padding: 6px; text-align: center; }}
        table.data th {{ background-color: #F2F2F2; }}
        .ttd-container {{ float: right; width: 280px; margin-top: 40px; font-size: 13px; text-align: center; }}
    </style></head>
    <body>
        <div class="kop">
            <h2>BADAN METEOROLOGI, KLIMATOLOGI, DAN GEOFISIKA</h2>
            <h1>STASIUN METEOROLOGI {st_name}</h1>
        </div>
        <div class="judul">NOTA DINAS RESMI INTERNAL</div>
        <div class="nomor">NOMOR: ME.02.01 / ND / REGIONAL / {datetime.now().strftime('%m/%Y')}</div>
        <table class="meta-table">
            <tr><td style="width: 80px;"><b>Kepada</b></td><td>: Kepala Stasiun Meteorologi</td></tr>
            <tr><td><b>Dari</b></td><td>: Koordinator Data dan Informasi / Senior Forecaster</td></tr>
            <tr><td><b>Tanggal</b></td><td>: {str_tgl}</td></tr>
            <tr><td><b>Hal</b></td><td>: Laporan Hasil Audit Kepatuhan Verifikasi TAFOR SOP 2025 Periode {tgl_m} s.d {tgl_s}</td></tr>
        </table>
        <div class="isi" style="font-size:13px; text-align:justify;">
            <p>Dilaporkan dengan hormat bahwa sistem komputasi otomatis <b>SIVETA</b> telah merampungkan perhitungan akurasi dokumen prakiraan cuaca bandara <b>(TAFOR)</b> terhadap kondisi riil <b>(METAR)</b> serta menyelaraskan data letupan cuaca mendadak <b>(SPECI)</b> sebanyak <b>{total_speci} lembar</b> berdasarkan aturan baku SOP Meteorologi Penerbangan BMKG Edisi Terbaru 2025.</p>
            <p>Capaian Indikator Kinerja Utama stasiun pada periode ini adalah:</p>
            <ul>
                <li><b>Total Akurasi Matriks Tiap Jam:</b> <b>{acc_jam}%</b></li>
                <li><b>Total Akurasi Verifikasi TAFOR:</b> <b>{acc_form}%</b></li>
            </ul>
            <table class="data">
                <thead><tr><th>Nama Unsur Parameter Cuaca</th><th>Sampel Jam (B / S)</th><th>Akurasi Jam</th><th>Sampel Grup TAF (B / S)</th><th>Akurasi Bulanan</th></tr></thead>
                <tbody>
    """
    for j, f in zip(table_jam, table_form):
        html_content += f"""
                    <tr>
                        <td style="text-align:left;"><b>{f['Nama Parameter']}</b></td>
                        <td>{j['Jumlah Benar (B)']} / {j['Jumlah Salah (S)']}</td>
                        <td>{j['Prosentase Ketelitian']}</td>
                        <td>{f['Jumlah Benar (B)']} / {f['Jumlah Salah (S)']}</td>
                        <td>{f['Prosentase Ketelitian']}</td>
                    </tr>
        """
    html_content += f"""
                </tbody>
            </table>
            <p>Catatan Evaluasi: Unsur dengan ketelitian terendah berada pada parameter <b>{param_terendah}</b> dengan skor <b>{min_score}%</b>. Disarankan evaluasi internal forecaster dilakukan untuk meminimalisir deviasi tersebut.</p>
        </div>
        <div class="ttd-container">
            <p>{str_tgl}<br>{jab_ttd},</p><br><br><br>
            <p><b><u>{nama_ttd}</u></b><br>{nip_ttd}</p>
        </div>
    </body>
    </html>
    """
    return html_content

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
    
    🟢 **1. Matriks Jam (Excel):**
    Data mentah yang berisi rincian sandi TAF disandingkan dengan METAR per jamnya. Sangat berguna untuk bahan audit atau penelitian mendalam.

    🔵 **2. Verifikasi TAF (Excel):**
    *Laporan Utama.* Mengevaluasi murni berbasis *Decision-Making* (Hanya menilai Grup TAF yang dirilis). **Nilainya lebih ketat, objektif, dan adil.**

    🗂️ **3. Format Klasik (Excel):**
    *Laporan Transisi.* Membentuk 31 *sheet* harian (format A-F). Mengevaluasi secara *Time-Series* (setiap setengah jam). 
    
    📝 **4. Logbook Perubahan:**
    Mencatat jejak rekam kapan sebuah TAF di-Amandemen (AMD) atau dibatalkan.
    
    
    #### ⚙️ PENGATURAN RUNWAY & CROSSWIND (ANGIN SILANG)
    SIVETA dilengkapi dengan algoritma penerbangan untuk menghitung komponen **Crosswind (Angin Potong/Silang)** secara otomatis. 
    Karena setiap bandara memiliki orientasi landasan pacu (*heading runway*) yang berbeda, Anda wajib memastikan data stasiun Anda telah dikonfigurasi:
    * Jika stasiun Anda memproses bandara baru yang belum terdaftar, hasil perhitungan angin silang bisa tidak akurat.
    * **Cara Konfigurasi:** Gulir ke bagian **paling bawah** aplikasi ini. Buka panel menu **"Database Pegawai & Runway"**, lalu masukkan kode ICAO stasiun dan arah derajat *Runway* bandara Anda (Misal: Runway 12/30, maka masukkan angka 120 dan 300). SIVETA akan mengunci pengaturan ini selamanya di dalam database!
    ---
        **Bagaimana jika bandara memiliki LEBIH DARI 1 Landasan?**
    * Secara operasional penerbangan, pesawat akan selalu diarahkan ke landasan dengan angin silang terkecil. 
    * SIVETA mengadopsi aturan ini: Jika Anda memasukkan lebih dari satu landasan, sistem akan menghitung crosswind untuk **semua** landasan tersebut secara paralel, lalu otomatis mengambil **nilai crosswind terkecil (paling aman)** sebagai hasil laporan operasional.
    * **Cara Input Banyak Landasan:** Gulir ke panel **"Database Pegawai & Runway"** di bagian bawah. Jika bandara Anda memiliki 2 landasan (misal Runway 09/27 dan Runway 10/28), masukkan semua angkanya dengan dipisahkan tanda koma, contoh: `90, 270, 100, 280`. SIVETA akan langsung mengunci dan memproses multi-runway tersebut dengan sempurna!
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
        auto_register_stasiun_baru(stasiun_aktif)

st.sidebar.markdown("---")
st.sidebar.header("📍 Stasiun Terdeteksi")
st.sidebar.info(f"Kode ICAO Aktif: **{stasiun_aktif}**")

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

# 🚀 3️⃣ TOMBOL EKSEKUSI UTAMA
if df_metar_raw is not None and df_taf_raw is not None and df_speci_raw is not None:
    if st.button("🚀 PROSES DATA 🚀", use_container_width=True, type="primary"):
        try:
            with st.spinner(f"Sedang menganalisa data stasiun {stasiun_aktif}..."):
                df_hasil, df_speci_report, _, _ = jalankan_komputasi_cached(df_metar_raw, df_taf_raw, df_speci_raw)
                df_hasil['Datetime_Obj'] = pd.to_datetime(df_hasil['Waktu Aktual (UTC)']).dt.date
                df_speci_report['Datetime_Obj'] = pd.to_datetime(df_speci_report['Waktu SPECI (UTC)']).dt.date
                st.session_state['df_hasil'] = df_hasil
                st.session_state['df_speci_report'] = df_speci_report
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

        # WIDGET METRIC PREMIUM
        m1, m2 = st.columns(2)
        m1.metric(f"📊 Akurasi Matriks {stasiun_aktif}", f"{akurasi_global_matriks}%")
        m2.metric(f"🎯 Akurasi Verifikasi {stasiun_aktif}", f"{akurasi_global_form}%")

        # AREA DOWNLOAD BUTTONS 
        str_m, str_s = tgl_mulai.strftime('%Y%m%d'), tgl_selesai.strftime('%Y%m%d')
        
        c_dl1, c_dl2 = st.columns(2)
        with c_dl1: 
            st.download_button(label="📄 1️⃣ Unduh Matriks Jam (Excel)", data=generate_lapbul_excel(df_filtered, df_speci_filtered).getvalue(), file_name=f"MATRIKS_{stasiun_aktif}_{str_m}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            
            st.download_button(label="📄 3️⃣ Unduh Format Klasik 31 Sheet (Excel)", data=generate_klasik_31_sheet(df_filtered).getvalue(), file_name=f"KLASIK_31_SHEET_{stasiun_aktif}_{str_m}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            
        with c_dl2: 
            st.download_button(label="📄 2️⃣ Unduh Verifikasi TAF (Excel SOP 2025)", data=generate_form_2026(df_filtered, df_speci_filtered).getvalue(), file_name=f"VERIFIKASI_TAF_{stasiun_aktif}_{str_m}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            
            st.download_button(label="📝 4️⃣ Unduh Logbook (Excel)", data=generate_logbook_excel(df_filtered).getvalue(), file_name=f"LOGBOOK_TAF_SIVETA_{stasiun_aktif}_{str_m}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        st.markdown("---")
        
        # TAB DETAIL VISUALISASI DATA (TIDAK ADA KARAKTER FORECASTER)
        tab_m, tab_f, tab_sp, tab_min = st.tabs(["📄 Matriks Jam", "📄 Verifikasi TAF", "📄 Log SPECI", "📄 Kritis & Crosswind"])
        
        with tab_m: 
            st.dataframe(pd.DataFrame(rows_m), use_container_width=True, hide_index=True)
            st.write("---")
            st.write("📈 **Grafik Performa Akurasi Harian (Rentang Terpilih)**")
            df_grafik = df_filtered.copy()
            df_grafik['Tanggal_Chart'] = pd.to_datetime(df_grafik['Waktu Aktual (UTC)']).dt.date
            df_harian = df_grafik.groupby('Tanggal_Chart').apply(lambda x: (len(x[x['Hasil Akhir'] == 'ACCURATE']) / len(x)) * 100).reset_index(name='Akurasi (%)')
            st.line_chart(df_harian.set_index('Tanggal_Chart'), use_container_width=True)
            
            df_tren_historis = ambil_tren_db(stasiun_aktif)
            if not df_tren_historis.empty:
                st.write("---")
                st.write(f"📈 **Tren Historis Akurasi Verifikasi {stasiun_aktif} (Multi-Bulan)**")
                st.line_chart(df_tren_historis.set_index('bulan_tahun'), use_container_width=True)
                
        with tab_f: 
            st.dataframe(pd.DataFrame(rows_f), use_container_width=True, hide_index=True)
        with tab_sp: 
            st.dataframe(df_speci_filtered.drop(columns=['Datetime_Obj']), use_container_width=True, hide_index=True)
            
        with tab_min:
            max_m_cw = df_filtered['M_Crosswind_Knot'].max()
            max_t_cw = df_filtered['T_Crosswind_Knot'].max()
            st.write(f"**Crosswind Maksimum Runway {stasiun_aktif}:** Aktual {max_m_cw} Kt | Ramalan {max_t_cw} Kt")
            df_cw_chart = df_filtered.copy().set_index("Waktu Aktual (UTC)")[["M_Crosswind_Knot", "T_Crosswind_Knot"]]
            st.line_chart(df_cw_chart, use_container_width=True)

# ==========================================
# EXPANDER CONFIGURATION PANELS
# ==========================================
st.write("")
with st.expander("✈️ ⚙️ Panel Manajemen Heading Runway"):
    st.write("Gunakan menu ini untuk mengatur sudut landasan pacu (*Runway*) jika Anda memproses stasiun baru agar perhitungan angin potong (*Crosswind*) akurat.")
    df_all_rw = ambil_semua_bandara()
    st.dataframe(df_all_rw, use_container_width=True, hide_index=True)
    with st.form("form_bandara"):
        add_icao = st.text_input("Kode ICAO Stasiun target (4 Huruf):", value=stasiun_aktif if stasiun_aktif != "Menunggu Berkas..." else "").upper()
        add_nama = st.text_input("Nama Bandara/Stasiun:", value=stasiun_aktif if stasiun_aktif != "Menunggu Berkas..." else "")
        
        # --- INPUT TEXT KHUSUS MULTI RUNWAY (ANTI-MEMBULAT) ---
        add_rw_a = st.text_input("Heading Runway Set 1 (Misal tunggal: 120, atau multi: 120, 090):", value="120")
        add_rw_b = st.text_input("Heading Runway Set 2 (Misal tunggal: 300, atau multi: 300, 270):", value="300")
        
        if st.form_submit_button("Update Sudut Runway"):
            if len(add_icao) == 4:
                # Bersihkan spasi hantu sebelum disetor ke database
                rw_a_bersih = ",".join([x.strip() for x in add_rw_a.split(",") if x.strip()])
                rw_b_bersih = ",".join([x.strip() for x in add_rw_b.split(",") if x.strip()])
                
                tambah_bandara(add_icao, add_nama, rw_a_bersih, rw_b_bersih)
                st.success(f"🎉 Sudut landasan pacu MULTI-RUNWAY stasiun {add_icao} sukses diperbarui!")
