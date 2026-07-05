import streamlit as st
import pandas as pd
import re
import sqlite3
from datetime import datetime
from verification_logic import proses_verifikasi, parse_sandi, hitung_angin_arah, hitung_angin_kec, hitung_vis, hitung_cuaca, hitung_awan_jml, hitung_awan_tgi
from excel_export import generate_lapbul_excel, generate_form_2026

st.set_page_config(page_title="TAFOR Verifier BMKG", layout="wide")
st.title("✈️ TAFOR Verifier ✈️")
st.write("Sistem Verifikasi Sinkronisasi Dokumen METAR, SPECI, dan TAFOR Kontinu (GTS BMKG).")

# ==========================================
# 1. DATABASE SQLITE PERMANEN
# ==========================================
def init_db():
    conn = sqlite3.connect('verifier_db.sqlite')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS rekap_performa 
                 (bulan_tahun TEXT PRIMARY KEY, akurasi_tiap_jam REAL, akurasi_verifikasi_tafor REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS pegawai 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, nama TEXT, nip TEXT, jabatan TEXT)''')
    c.execute("SELECT COUNT(*) FROM pegawai")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO pegawai (nama, nip, jabatan) VALUES ('TIM DATA & INFORMASI', 'Stasiun Meteorologi WGP', 'Penyusun Laporan')")
    conn.commit()
    conn.close()

def simpan_rekap_db(bulan_tahun, jam_score, tafor_score):
    conn = sqlite3.connect('verifier_db.sqlite')
    c = conn.cursor()
    c.execute('''INSERT INTO rekap_performa (bulan_tahun, akurasi_tiap_jam, akurasi_verifikasi_tafor)
                 VALUES (?, ?, ?) ON CONFLICT(bulan_tahun) DO UPDATE SET
                 akurasi_tiap_jam=excluded.akurasi_tiap_jam, akurasi_verifikasi_tafor=excluded.akurasi_verifikasi_tafor''', 
              (bulan_tahun, jam_score, tafor_score))
    conn.commit()
    conn.close()

def ambil_tren_db():
    conn = sqlite3.connect('verifier_db.sqlite')
    df = pd.read_sql_query("SELECT * FROM rekap_performa ORDER BY bulan_tahun ASC", conn)
    conn.close()
    return df

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
# 2. GENERATOR NOTA DINAS RESMI
# ==========================================
def generate_nota_dinas_html(tgl_m, tgl_s, acc_jam, acc_form, table_jam, table_form, total_speci, nama_ttd, nip_ttd, jab_ttd):
    str_tgl = datetime.now().strftime('%d %B %Y')
    param_terendah = "Visibility (Jarak Pandang)"
    min_score = 100.0
    for r in table_form:
        score_val = float(r['Prosentase Ketelitian'].replace('%',''))
        if score_val < min_score:
            min_score = score_val
            param_terendah = r['Nama Parameter']

    html_content = f"""
    <html>
    <head>
    <style>
        body {{ font-family: 'Arial', sans-serif; margin: 40px; color: #000; line-height: 1.4; }}
        .kop {{ text-align: center; font-weight: bold; border-bottom: 3px double #000; padding-bottom: 10px; margin-bottom: 20px; }}
        .kop h2 {{ margin: 0; font-size: 16px; letter-spacing: 1px; }}
        .kop h1 {{ margin: 5px 0; font-size: 18px; letter-spacing: 1px; }}
        .kop p {{ margin: 0; font-size: 11px; font-weight: normal; font-style: italic; }}
        .judul {{ text-align: center; font-weight: bold; text-decoration: underline; font-size: 14px; margin-top: 15px; text-transform: uppercase; }}
        .nomor {{ text-align: center; font-size: 12px; margin-bottom: 25px; }}
        .meta-table {{ width: 100%; margin-bottom: 20px; font-size: 13px; }}
        .meta-table td {{ padding: 3px 0; vertical-align: top; }}
        .divider {{ border-top: 1px solid #000; margin: 15px 0; }}
        .isi {{ font-size: 13px; text-align: justify; }}
        table.data {{ width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 12px; }}
        table.data th, table.data td {{ border: 1px solid #000; padding: 6px; text-align: center; }}
        table.data th {{ background-color: #F2F2F2; font-weight: bold; }}
        .ttd-container {{ float: right; width: 280px; margin-top: 40px; font-size: 13px; text-align: center; page-break-inside: avoid; }}
        @media print {{ border: none; @page {{ margin: 1.5cm; }} }}
    </style>
    </head>
    <body>
        <div class="kop">
            <h2>BADAN METEOROLOGI, KLIMATOLOGI, DAN GEOFISIKA</h2>
            <h1>STASIUN METEOROLOGI UMBU MEHANG KUNDA</h1>
            <p>Jl. Adam Malik No. 1 Waingapu - Nusa Tenggara Timur, Telp: (0387) 61318</p>
        </div>
        <div class="judul">NOTA DINAS LINGKUP INTERNAL</div>
        <div class="nomor">NOMOR: ME.02.01 / 029 / WGP / {datetime.now().strftime('%m/%Y')}</div>
        <table class="meta-table">
            <tr><td style="width: 80px;"><b>Kepada</b></td><td style="width: 15px;">:</td><td>Kepala Stasiun Meteorologi Umbu Mehang Kunda</td></tr>
            <tr><td><b>Dari</b></td><td>:</td><td>Senior Forecaster / Koordinator Data dan Informasi</td></tr>
            <tr><td><b>Tanggal</b></td><td>:</td><td>{str_tgl}</td></tr>
            <tr><td><b>Hal</b></td><td>:</td><td>Laporan Ringkasan Eksekutif Hasil Verifikasi Ketelitian TAFOR Periode {tgl_m} s.d {tgl_s}</td></tr>
        </table>
        <div class="divider"></div>
        <div class="isi">
            <p>Bersama nota dinas ini dilaporkan bahwa sistem komputasi otomatis telah menyelesaikan perhitungan akurasi dokumen prakiraan cuaca bandara <b>(TAFOR)</b> kontinu terhadap dokumen kenyataan aktual <b>(METAR)</b> serta didukung penyelarasan data letupan perubahan cuaca mendadak <b>(SPECI)</b> sebanyak <b>{total_speci} kejadian</b> terhitung pada masa rentang evaluasi target.</p>
            <p>Berdasarkan rumusan matematis verifikasi operasional penerbangan, diperoleh capaian <b>Indikator Mutu Utama Stasiun</b> sebagai berikut:</p>
            <ul>
                <li><b>Total Akurasi Akumulatif Tiap Jam (Sains Linier):</b> <b>{acc_jam}%</b></li>
                <li><b>Total Akurasi Resmi Verifikasi TAFOR (Administrasi Bulanan):</b> <b>{acc_form}%</b></li>
            </ul>
            <p>Berikut diurai rincian ketelitian per parameter meteorologi penerbangan sebagai bahan evaluasi teknis operasional:</p>
            <table class="data">
                <thead><tr><th>Nama Unsur Parameter Cuaca</th><th>Sampel Data Tiap Jam (B / S)</th><th>Akurasi Tiap Jam</th><th>Sampel Grup TAF (B / S)</th><th>Akurasi Resmi Bulanan</th></tr></thead>
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
            <p><b>REKOMENDASI TEKNIS DAN CATATAN FORECASTER:</b><br>
            Berdasarkan hasil rekapitulasi di atas, ketelitian terendah berada pada parameter <b>{param_terendah}</b> dengan skor <b>{min_score}%</b>. Disarankan kepada seluruh jajaran prakirawan stasiun untuk lebih mempertegas pemanfaatan pemodelan cuaca numerik jarak pendek serta menjaga kewaspadaan pengamatan unsur tersebut guna meminimalisir deviasi prakiraan pada periode amandemen berikutnya.</p>
            <p>Demikian nota dinas ringkasan eksekutif ini dibuat untuk menjadi periksa dan arahan kebijakan pimpinan selanjutnya.</p>
        </div>
        <div class="ttd-container">
            <p>Waingapu, {str_tgl}<br>{jab_ttd},</p><br><br><br><br>
            <p><b><u>{nama_ttd}</u></b><br>{nip_ttd}</p>
        </div>
    </body>
    </html>
    """
    return html_content

# ==========================================
# 3. VERIFIKASI TAFOR CONTROLLER FORM BULANAN
# ==========================================
def hitung_verifikasi_TAFOR(df_input):
    df_work = df_input.copy()
    df_work['Tanggal'] = pd.to_datetime(df_work['Waktu Aktual (UTC)']).dt.day
    df_work['Jam'] = pd.to_datetime(df_work['Waktu Aktual (UTC)']).dt.hour
    rekapan = {k: {'B': 0, 'S': 0} for k in ['A', 'B', 'C', 'D', 'E', 'F']}
    
    for tgl in range(1, 32):
        data_tgl = df_work[df_work['Tanggal'] == tgl]
        if data_tgl.empty: continue
        data_tgl_sorted = data_tgl.sort_values('Jam')
        tafs_hari_ini = []
        for _, row in data_tgl_sorted.iterrows():
            sandi = row['Sandi TAF Prakiraan']
            if sandi != "-" and sandi not in tafs_hari_ini: tafs_hari_ini.append(sandi)
        if not tafs_hari_ini: continue
            
        for taf_sandi in tafs_hari_ini:
            baris_m_base = data_tgl_sorted[data_tgl_sorted['Sandi TAF Prakiraan'] == taf_sandi].iloc[0]
            parts = re.split(r'\b(BECMG|TEMPO|PROB30 TEMPO|PROB40 TEMPO|PROB30|PROB40)\b', str(taf_sandi))
            base_str = parts[0]
            b_ar, b_ke, b_vi, b_wx, b_aj, b_at = parse_sandi(base_str)
            cur_ar, cur_ke, cur_vi, cur_wx, cur_aj, cur_at = b_ar, b_ke, b_vi, b_wx, b_aj, b_at
            
            for k, func, m_col, tar in [
                ('A', hitung_angin_arah, 'M_Arah', b_ar), ('B', hitung_angin_kec, 'M_Kec', b_ke),
                ('C', hitung_vis, 'M_Vis', b_vi), ('D', hitung_cuaca, 'M_Wx', b_wx),
                ('E', hitung_awan_jml, 'M_AwanJml', b_aj), ('F', hitung_awan_tgi, 'M_AwanTgi', b_at)
            ]:
                _, stat = func(baris_m_base[m_col], tar)
                if stat in ['B', 'S']: rekapan[k][stat] += 1
                    
            for i in range(1, len(parts), 2):
                tipe, isi = parts[i], parts[i+1]
                time_match = re.search(r'(\d{2})(\d{2})/(\d{2})(\d{2})', isi)
                jam_target = int(time_match.group(2)) if time_match else 0
                    
                t_ar, t_ke, t_vi, t_wx, t_aj, t_at = parse_sandi(isi)
                if t_ar == "-": t_ar = cur_ar
                if t_ke == "-": t_ke = cur_ke
                if t_vi == "-": t_vi = cur_vi
                if t_wx == "NIL" and not re.search(r'\b(HZ|RA|TSRA|BR|DZ|FG|VCTS|TS|SHRA|MIFG|SQ|FC)\b', isi) and "CAVOK" not in isi: t_wx = cur_wx
                if t_aj == "-": t_aj = cur_aj
                if t_at == "-": t_at = cur_at
                
                data_jam = data_tgl_sorted[(data_tgl_sorted['Jam'] == jam_target) & (data_tgl_sorted['Sandi TAF Prakiraan'] == taf_sandi)]
                baris_m_trend = data_jam.iloc[0] if not data_jam.empty else baris_m_base
                
                for k, func, m_col, tar in [
                    ('A', hitung_angin_arah, 'M_Arah', t_ar), ('B', hitung_angin_kec, 'M_Kec', t_ke),
                    ('C', hitung_vis, 'M_Vis', t_vi), ('D', hitung_cuaca, 'M_Wx', t_wx),
                    ('E', hitung_awan_jml, 'M_AwanJml', t_aj), ('F', hitung_awan_tgi, 'M_AwanTgi', t_at)
                ]:
                    _, stat = func(baris_m_trend[m_col], tar)
                    if stat in ['B', 'S']: rekapan[k][stat] += 1
                if tipe == 'BECMG': cur_ar, cur_ke, cur_vi, cur_wx, cur_aj, cur_at = t_ar, t_ke, t_vi, t_wx, t_aj, t_at
    return rekapan

# SESSION STATE
if 'diklik_proses' not in st.session_state: st.session_state['diklik_proses'] = False
if 'df_hasil' not in st.session_state: st.session_state['df_hasil'] = None
if 'df_speci_report' not in st.session_state: st.session_state['df_speci_report'] = None

# TAMPILKAN HISTORIS
df_tren_historis = ambil_tren_db()
if not df_tren_historis.empty:
    st.subheader("📈 Tren Performa Stasiun Antar-Bulan (Memory Database)")
    st.line_chart(df_tren_historis.copy().set_index('bulan_tahun'), use_container_width=True)

# SIDEBAR CALENDAR
st.sidebar.header("🗓️ Filter Rentang Waktu")
hari_ini = datetime.now().date()
tanggal_pilihan = st.sidebar.date_input("Pilih Tanggal Mulai dan Selesai:", value=(hari_ini, hari_ini), key="rentang_tanggal")

col1, col2, col3 = st.columns(3)
with col1: file_metar = st.file_uploader("1. Unggah CSV METAR", type=["csv"], key="metar")
with col2: file_taf = st.file_uploader("2. Unggah CSV TAF", type=["csv"], key="taf")
with col3: file_speci = st.file_uploader("3. Unggah CSV SPECI", type=["csv"], key="speci")

if file_metar is not None and file_taf is not None and file_speci is not None:
    st.markdown("---")
    if st.button("🚀 JALANKAN PROSES VERIFIKASI SEKARANG", use_container_width=True, type="primary"):
        try:
            with st.spinner("Mengevaluasi ribuan baris data, menyisir letupan SPECI, dan mengunci database..."):
                df_hasil, df_speci_report, _, _ = proses_verifikasi(pd.read_csv(file_metar), pd.read_csv(file_taf), pd.read_csv(file_speci))
                df_hasil['Datetime_Obj'] = pd.to_datetime(df_hasil['Waktu Aktual (UTC)']).dt.date
                df_speci_report['Datetime_Obj'] = pd.to_datetime(df_speci_report['Waktu SPECI (UTC)']).dt.date
                st.session_state['df_hasil'] = df_hasil
                st.session_state['df_speci_report'] = df_speci_report
                st.session_state['diklik_proses'] = True
        except Exception as e:
            st.error(f"Gagal memproses data: {e}")

# RENDER INTERFACE
if st.session_state['diklik_proses'] and st.session_state['df_hasil'] is not None:
    df_hasil = st.session_state['df_hasil']
    df_speci_report = st.session_state['df_speci_report']
    
    if isinstance(tanggal_pilihan, tuple) and len(tanggal_pilihan) == 2: tgl_mulai, tgl_selesai = tanggal_pilihan
    else: tgl_mulai = tgl_selesai = tanggal_pilihan[0] if isinstance(tanggal_pilihan, list) else tanggal_pilihan
        
    df_filtered = df_hasil[(df_hasil['Datetime_Obj'] >= tgl_mulai) & (df_hasil['Datetime_Obj'] <= tgl_selesai)].copy()
    df_speci_filtered = df_speci_report[(df_speci_report['Datetime_Obj'] >= tgl_mulai) & (df_speci_report['Datetime_Obj'] <= tgl_selesai)].copy()
    
    if df_filtered.empty:
        st.warning(f"⚠️ Tidak ditemukan data cuaca pada rentang kalender aktif ({tgl_mulai} s.d {tgl_selesai}).")
    else:
        st.success(f"✅ Sinkronisasi Sukses! Menampilkan Rentang: {tgl_mulai} s.d {tgl_selesai}")
        
        # PERHITUNGAN MATRIKS TIAP JAM
        total_b_g, total_data_global, rows_m = 0, 0, []
        p_headers = {'A':'A (Arah Wind)','B':'B (Kec Wind)','C':'C (Visibility)','D':'D (Cuaca)','E':'E (Jml Awan)','F':'F (Tgi Awan)'}
        for k, col_name in {'A':"S_Arah",'B':"S_Kec",'C':"S_Vis",'D':"S_Wx",'E':"S_AwanJml",'F':"S_AwanTgi"}.items():
            b, s = (df_filtered[col_name] == "B").sum(), (df_filtered[col_name] == "S").sum()
            tot = b + s
            pct = (b / tot * 100) if tot > 0 else 0
            total_b_g += b; total_data_global += tot
            rows_m.append({"Nama Parameter": p_headers[k], "Jumlah Benar (B)": b, "Jumlah Salah (S)": s, "Total Sampel Data (Tiap Jam)": tot, "Prosentase Ketelitian": f"{round(pct, 2)}%"})
        akurasi_global_matriks = round((total_b_g / total_data_global * 100), 1) if total_data_global > 0 else 0
        
        # PERHITUNGAN VERIFIKASI TAFOR
        rekapan_form = hitung_verifikasi_TAFOR(df_filtered)
        rows_f, total_b_f, total_d_f = [], 0, 0
        for k in ['A', 'B', 'C', 'D', 'E', 'F']:
            b_f, s_f = rekapan_form[k]['B'], rekapan_form[k]['S']
            tot_f = b_f + s_f
            pct_f = (b_f / tot_f * 100) if tot_f > 0 else 0
            total_b_f += b_f; total_d_f += tot_f
            rows_f.append({"Nama Parameter": p_headers[k], "Jumlah Benar (B)": b_f, "Jumlah Salah (S)": s_f, "Total Sampel Data (Grup TAF)": tot_f, "Prosentase Ketelitian": f"{round(pct_f, 2)}%"})
        akurasi_global_form = round((total_b_f / total_d_f * 100 if total_d_f > 0 else 0), 1)

        simpan_rekap_db(tgl_mulai.strftime('%Y-%m'), akurasi_global_matriks, akurasi_global_form)

        st.subheader(f"📊 Panel Analisis Akurasi Periode ({tgl_mulai} s.d {tgl_selesai})")
        
        tab_matriks, tab_form, tab_speci, tab_error = st.tabs([
            "📊 Akurasi Matriks (Tiap Jam)", 
            "📄 Rekapitulasi Verifikasi TAFOR (Standar Bulanan)", 
            "🟧 Audit Trail SPECI (Letupan Ekstrem)",
            "🎯 📊 Evaluasi & Performa Forecaster"
        ])
        
        with tab_matriks:
            st.info(f"### 📈 TOTAL AKURASI MATRIKS TIAP JAM: {akurasi_global_matriks}%")
            st.dataframe(pd.DataFrame(rows_m), use_container_width=True, hide_index=True)
            df_grafik = df_filtered.copy()
            df_grafik['Tanggal_Chart'] = pd.to_datetime(df_grafik['Waktu Aktual (UTC)']).dt.date
            df_harian = df_grafik.groupby('Tanggal_Chart').apply(lambda x: (len(x[x['Hasil Akhir'] == 'ACCURATE']) / len(x)) * 100).reset_index(name='Akurasi (%)')
            st.line_chart(df_harian.set_index('Tanggal_Chart'), use_container_width=True)
            
        with tab_form:
            st.success(f"### 🎯 TOTAL AKURASI GLOBAL VERIFIKASI TAFOR (STANDAR 029): {akurasi_global_form}%")
            st.dataframe(pd.DataFrame(rows_f), use_container_width=True, hide_index=True)
            
        with tab_form:
            st.success(f"### 🎯 TOTAL AKURASI GLOBAL VERIFIKASI TAFOR (STANDAR 029): {akurasi_global_form}%")
            st.dataframe(pd.DataFrame(rows_f), use_container_width=True, hide_index=True)
            
        with tab_speci:
            st.warning(f"### ⚡ Total Sampel Kejadian SPECI Terdeteksi: {len(df_speci_filtered)} baris")
            st.dataframe(df_speci_filtered.drop(columns=['Datetime_Obj']), use_container_width=True, hide_index=True)
            
        with tab_error:
            # 🔥 UPGRADE AKBAR TAB 4: DUET DIAGNOSTIK PARAMETER & SHIFT JAGA (WITA)
            st.subheader("🎯 Analisis Karakteristik Deviasi Prakiraan Stasiun")
            
            # --- BLOK ATAS: DISTRIBUSI UNSUR CUACA ---
            st.write("#### 1. Rangking Frekuensi Parameter yang Paling Sering Meleset")
            p_err_mapping = {
                'Parameter A (Arah Angin / Wind Direction)': 'S_Arah',
                'Parameter B (Kecepatan Angin / Wind Speed + Gusts)': 'S_Kec',
                'Parameter C (Visibility / Jarak Pandang)': 'S_Vis',
                'Parameter D (Cuaca Signifikan / Weather Phenomena)': 'S_Wx',
                'Parameter E (Jumlah Awan / Cloud Amount)': 'S_AwanJml',
                'Parameter F (Tinggi Awan / Cloud Base Height)': 'S_AwanTgi'
            }
            err_rows = []
            for label, col_name in p_err_mapping.items():
                s_count = (df_filtered[col_name] == 'S').sum()
                err_rows.append({"Parameter Cuaca": label, "Jumlah Frekuensi Meleset (Kali)": int(s_count)})
                
            df_err_chart = pd.DataFrame(err_rows).set_index("Parameter Cuaca")
            col_c1, col_c2 = st.columns([2, 3])
            with col_c1:
                st.dataframe(pd.DataFrame(err_rows).sort_values(by="Jumlah Frekuensi Meleset (Kali)", ascending=False), use_container_width=True, hide_index=True)
            with col_c2:
                st.bar_chart(df_err_chart, use_container_width=True)
                
            st.markdown("---")
            
            # --- BLOK BAWAH: ANALISIS SHIFT JAGA OPERASIONAL (WITA) ---
            st.write("#### 2. Distribusi Akurasi Berdasarkan Regu Shift Jaga Lokal (WITA)")
            st.caption("Penerapan pembagian jam kerja internal stasiun Waingapu: Pagi (06:30-13:30 WITA), Siang (13:30-20:30 WITA), dan Malam (20:30-06:30 WITA). Catatan: Jam kerja forecaster reguler (07:30-16:00 WITA) terdistribusi secara proporsional di dalam shift pagi dan siang.")
            
            # Konversi waktu UTC di file menjadi waktu WITA (UTC + 8)
            df_shift = df_filtered.copy()
            df_shift['Dt_UTC'] = pd.to_datetime(df_shift['Waktu Aktual (UTC)'])
            df_shift['Jam_WITA'] = (df_shift['Dt_UTC'].dt.hour + 8) + (df_shift['Dt_UTC'].dt.minute / 60.0)
            df_shift['Jam_WITA'] = df_shift['Jam_WITA'] % 24
            
            def klasifikasi_shift(wita_val):
                if 6.5 <= wita_val < 13.5:
                    return "🌅 Shift Pagi (06:30 - 13:30 WITA)"
                elif 13.5 <= wita_val < 20.5:
                    return "🌆 Shift Siang (13:30 - 20:30 WITA)"
                else:
                    return "🌌 Shift Malam (20:30 - 06:30 WITA)"
                    
            df_shift['Regu Jaga'] = df_shift['Jam_WITA'].apply(klasifikasi_shift)
            
            shift_rows = []
            for name_s in ["🌅 Shift Pagi (06:30 - 13:30 WITA)", "🌆 Shift Siang (13:30 - 20:30 WITA)", "🌌 Shift Malam (20:30 - 06:30 WITA)"]:
                sub_s = df_shift[df_shift['Regu Jaga'] == name_s]
                if not sub_s.empty:
                    b_s = (sub_s['Hasil Akhir'] == 'ACCURATE').sum()
                    tot_s = len(sub_s)
                    pct_s = round((b_s / tot_s * 100), 2)
                else:
                    b_s, tot_s, pct_s = 0, 0, 0.0
                shift_rows.append({"Regu Jaga / Shift": name_s, "Akurasi (%)": pct_s, "Total Sampel Jam": tot_s})
                
            df_shift_chart = pd.DataFrame(shift_rows).set_index("Regu Jaga / Shift")[["Akurasi (%)"]]
            col_s1, col_s2 = st.columns([2, 3])
            with col_s1:
                st.dataframe(pd.DataFrame(shift_rows), use_container_width=True, hide_index=True)
            with col_s2:
                st.bar_chart(df_shift_chart, use_container_width=True)
        
        # --- EXPORT PACK ZONE ---
        str_m, str_s = tgl_mulai.strftime('%Y%m%d'), tgl_selesai.strftime('%Y%m%d')
        st.subheader("📥 Export Paket Dokumen Verifikasi Resmi Stasiun")
        
        df_peg_list = ambil_semua_pegawai()
        opsi_pegawai = [f"{r['nama']} ({r['jabatan']})" for _, r in df_peg_list.iterrows()]
        pegawai_terpilih = st.selectbox("✒️ Pilih Pegawai Penandatangan Nota Dinas PDF:", opsi_pegawai)
        row_peg_terpilih = df_peg_list.iloc[opsi_pegawai.index(pegawai_terpilih)]
        
        c_dl1, c_dl2, c_dl3 = st.columns(3)
        with c_dl1:
            st.download_button(label="1️⃣ Unduh Matriks Tiap Jam (Excel)", data=generate_lapbul_excel(df_filtered, df_speci_filtered).getvalue(), file_name=f"REKAP_MATRIKS_TAFOR_{str_m}_TO_{str_s}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        with c_dl2:
            st.download_button(label="2️⃣ Unduh Verifikasi TAFOR (Excel)", data=generate_form_2026(df_filtered, df_speci_filtered).getvalue(), file_name=f"VERIFIKASI_TAFOR_{str_m}_TO_{str_s}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
        with c_dl3:
            html_nota = generate_nota_dinas_html(str_m, str_s, akurasi_global_matriks, akurasi_global_form, rows_m, rows_f, len(df_speci_filtered), row_peg_terpilih['nama'], row_peg_terpilih['nip'], row_peg_terpilih['jabatan'])
            st.download_button(label="📄 3️⃣ Cetak Ringkasan Eksekutif (Nota Dinas PDF)", data=html_nota, file_name=f"NOTA_DINAS_VERIFIKASI_TAFOR_{str_m}.html", mime="text/html", use_container_width=True)

# ==========================================
# 5. PANEL UTAMA CRUD MANAJEMEN DATA PEGAWAI
# ==========================================
st.markdown("---")
with st.expander("👥 ⚙️ PANEL UTAMA: Manajemen Data Pegawai Pembuat Laporan (Tambah / Edit / Hapus)"):
    df_peg_crud = ambil_semua_pegawai()
    st.write("Daftar Pegawai Aktif Saat Ini di Database:")
    st.dataframe(df_peg_crud, use_container_width=True, hide_index=True)
    
    tab_add, tab_edit, tab_del = st.tabs(["➕ Tambah Pegawai", "✏️ Edit Data Pegawai", "❌ Hapus Data Pegawai"])
    with tab_add:
        with st.form("form_tambah"):
            n_nama = st.text_input("Nama Lengkap & Gelar:")
            n_nip = st.text_input("NIP / Identitas Stasiun:")
            n_jab = st.text_input("Jabatan Struktural / Fungsional:", value="Prakirawan / Forecaster")
            if st.form_submit_button("Simpan Pegawai Baru"):
                if n_nama and n_nip:
                    tambah_pegawai(n_nama, n_nip, n_jab)
                    st.success("✅ Pegawai baru berhasil ditambahkan! Silakan refresh halaman.")
                else: st.error("Nama dan NIP wajib diisi!")
                
    with tab_edit:
        if len(df_peg_crud) > 0:
            opsi_edit = [f"ID {r['id']} - {r['nama']}" for _, r in df_peg_crud.iterrows()]
            edit_sel = st.selectbox("Pilih Pegawai yang Ingin Diedit:", opsi_edit)
            row_edit = df_peg_crud.iloc[opsi_edit.index(edit_sel)]
            with st.form("form_edit"):
                e_nama = st.text_input("Ubah Nama Lengkap:", value=row_edit['nama'])
                e_nip = st.text_input("Ubah NIP:", value=row_edit['nip'])
                e_jab = st.text_input("Ubah Jabatan:", value=row_edit['jabatan'])
                if st.form_submit_button("Simpan Perubahan Data"):
                    edit_pegawai(int(row_edit['id']), e_nama, e_nip, e_jab)
                    st.success("✅ Perubahan data berhasil disimpan! Silakan refresh halaman.")
        else: st.info("Belum ada data pegawai untuk diedit.")
                    
    with tab_del:
        if len(df_peg_crud) > 1:
            opsi_del = [f"ID {r['id']} - {r['nama']}" for _, r in df_peg_crud.iterrows()]
            del_sel = st.selectbox("Pilih Pegawai yang Ingin Dihapus:", opsi_del)
            row_del = df_peg_crud.iloc[opsi_del.index(del_sel)]
            if st.button("🚨 HAPUS PEGAWAI SEARA PERMANEN", type="primary"):
                hapus_pegawai(int(row_del['id']))
                st.success("❌ Pegawai berhasil dihapus dari database stasiun! Silakan refresh halaman.")
        else: st.info("Data default stasiun tidak boleh dihapus demi keselamatan sistem.")
