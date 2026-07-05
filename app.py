import streamlit as st
import pandas as pd
import re
from datetime import datetime
from verification_logic import proses_verifikasi, parse_sandi, hitung_angin_arah, hitung_angin_kec, hitung_vis, hitung_cuaca, hitung_awan_jml, hitung_awan_tgi
from excel_export import generate_lapbul_excel, generate_form_2026

st.set_page_config(page_title="TAFOR Verifier", layout="wide")

def hitung_verifikasi_TAFOR(df_input):
    """Fungsi internal web untuk mengekstrak hitungan B/S Form 2026 bulanan"""
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
            parts = re.split(r'\b(BECMG|TEMPO)\b', str(taf_sandi))
            
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
                tipe = parts[i]
                isi = parts[i+1]
                time_match = re.search(r'(\d{2})(\d{2})/(\d{2})(\d{2})', isi)
                jam_target = 0
                if time_match: jam_target = int(time_match.group(2))
                    
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

st.title("✈️ TAFOR Verifier ✈️")
st.write("Unggah file CSV METAR dan TAFOR, lalu tentukan rentang tanggal verifikasi secara fleksibel.")

st.sidebar.header("🗓️ Filter Rentang Waktu")
hari_ini = datetime.now().date()
tanggal_pilihan = st.sidebar.date_input("Pilih Tanggal Mulai dan Selesai:", value=(hari_ini, hari_ini), key="rentang_tanggal")

col1, col2 = st.columns(2)
with col1:
    st.subheader("1. Unggah CSV METAR")
    file_metar = st.file_uploader("Pilih file gts_export_... (METAR)", type=["csv"], key="metar")
with col2:
    st.subheader("2. Unggah CSV TAF")
    file_taf = st.file_uploader("Pilih file gts_export_... (TAF)", type=["csv"], key="taf")

if file_metar is not None and file_taf is not None:
    try:
        df_metar = pd.read_csv(file_metar)
        df_taf = pd.read_csv(file_taf)
        if "metar" not in df_metar['type_message'].iloc[0].lower(): df_metar, df_taf = df_taf, df_metar 
            
        df_hasil, _, _, _ = proses_verifikasi(df_metar, df_taf)
        df_hasil['Datetime_Obj'] = pd.to_datetime(df_hasil['Waktu Aktual (UTC)']).dt.date
        
        if isinstance(tanggal_pilihan, tuple) and len(tanggal_pilihan) == 2: tgl_mulai, tgl_selesai = tanggal_pilihan
        else: tgl_mulai = tgl_selesai = tanggal_pilihan[0] if isinstance(tanggal_pilihan, list) else tanggal_pilihan
            
        df_filtered = df_hasil[(df_hasil['Datetime_Obj'] >= tgl_mulai) & (df_hasil['Datetime_Obj'] <= tgl_selesai)].copy()
        
        if df_filtered.empty:
            st.warning(f"⚠️ Tidak ada data cuaca ditemukan pada rentang {tgl_mulai} s.d {tgl_selesai}.")
        else:
            st.success(f"✅ Data Berhasil Difilter: {tgl_mulai} s.d {tgl_selesai}")
            
            p_headers = {
                'A': 'A (Arah Wind)', 'B': 'B (Kec Wind)', 'C': 'C (Visibility)',
                'D': 'D (Cuaca)',     'E': 'E (Jml Awan)',  'F': 'F (Tgi Awan)'
            }
            
            # --- 1. HITUNGAN AKURASI MATRIKS (TIAP JAM) ---
            total_b_global = 0
            total_data_global = 0
            p_akurasi = {}
            rows_matriks_web = []
            p_mapping = {
                'A': "S_Arah", 'B': "S_Kec", 'C': "S_Vis",
                'D': "S_Wx", 'E': "S_AwanJml", 'F': "S_AwanTgi"
            }
            for k, col_name in p_mapping.items():
                b_cnt = (df_filtered[col_name] == "B").sum()
                s_cnt = (df_filtered[col_name] == "S").sum()
                tot = b_cnt + s_cnt
                pct = (b_cnt / tot * 100) if tot > 0 else 0
                p_akurasi[p_headers[k]] = round(pct, 1)
                total_b_global += b_cnt
                total_data_global += tot
                
                # Masukkan ke list tabel matriks web
                rows_matriks_web.append({
                    "Nama Parameter": p_headers[k],
                    "Jumlah Benar (B)": b_cnt,
                    "Jumlah Salah (S)": s_cnt,
                    "Total Sampel Data (Jam)": tot,
                    "Prosentase Ketelitian": f"{round(pct, 2)}%"
                })
            df_rekap_matriks_tampil = pd.DataFrame(rows_matriks_web)
            akurasi_global_matriks = round((total_b_global / total_data_global * 100), 1) if total_data_global > 0 else 0
            
            # --- 2. HITUNGAN AKURASI VERIFIKASI TAFOR (BERDASARKAN GRUP TREND TAF) ---
            rekapan_form = hitung_verifikasi_TAFOR(df_filtered)
            rows_form_web = []
            total_b_form, total_data_form = 0, 0
            for k in ['A', 'B', 'C', 'D', 'E', 'F']:
                b_f = rekapan_form[k]['B']
                s_f = rekapan_form[k]['S']
                tot_f = b_f + s_f
                pct_f = (b_f / tot_f * 100) if tot_f > 0 else 0
                total_b_form += b_f
                total_data_form += tot_f
                rows_form_web.append({
                    "Nama Parameter": p_headers[k],
                    "Jumlah Benar (B)": b_f,
                    "Jumlah Salah (S)": s_f,
                    "Total Sampel Data (Grup TAF)": tot_f,
                    "Prosentase Ketelitian": f"{round(pct_f, 2)}%"
                })
            df_rekap_form_tampil = pd.DataFrame(rows_form_web)
            akurasi_global_form = round((total_b_form / total_data_form * 100), 1) if total_data_form > 0 else 0

            # --- PANEL TAB INTERAKTIF ---
            st.subheader(f"📊 Panel Analisis Akurasi Periode ({tgl_mulai} s.d {tgl_selesai})")
            tab_matriks, tab_form = st.tabs(["📊 Akurasi Matriks (Tiap Jam)", "📄 Rekapitulasi Verifikasi TAFOR"])
            
            with tab_matriks:
                st.info(f"### 📈 TOTAL AKURASI MATRIKS TIAP JAM: {akurasi_global_matriks}%")
                cols = st.columns(6)
                for idx, (label, score) in enumerate(p_akurasi.items()):
                    cols[idx].metric(label, f"{score}%")
                
                st.write("")
                st.write("**🔥 BARU: Tabel Detail Perhitungan Rangkuman Matriks (Tiap Jam):**")
                st.dataframe(df_rekap_matriks_tampil, use_container_width=True, hide_index=True)
                
                st.write("")
                st.write("**Tren Fluktuasi Akurasi Harian:**")
                df_grafik = df_filtered.copy()
                df_grafik['Tanggal_Chart'] = pd.to_datetime(df_grafik['Waktu Aktual (UTC)']).dt.date
                df_harian = df_grafik.groupby('Tanggal_Chart').apply(lambda x: (len(x[x['Hasil Akhir'] == 'ACCURATE']) / len(x)) * 100).reset_index(name='Akurasi (%)')
                df_harian.set_index('Tanggal_Chart', inplace=True)
                st.line_chart(df_harian, use_container_width=True)
                
            with tab_form:
                st.success(f"### 🎯 TOTAL AKURASI VERIFIKASI TAFOR: {akurasi_global_form}%")
                st.write("Tabel ringkasan administrasi bulanan berbasis grup TAFOR (BASE/TEMPO/BECMG) secara proporsional:")
                st.dataframe(df_rekap_form_tampil, use_container_width=True, hide_index=True)
            
            # --- PANDUAN PENTING ---
            with st.expander("📖 PANDUAN PENTING: Ketentuan Rentang Data & Logika Verifikasi Harian", expanded=False):
                st.markdown("""
                * **1. Aturan Batasan Rentang Waktu:** Berkas Excel yang Anda unduh dirancang patuh pada **Instruksi Met No.029 (Format Bulanan: Tanggal 1 s.d 31)**. Pastikan rentang tanggal yang Anda pilih di sidebar berada dalam 1 bulan kalender yang sama agar tidak tumpang tindih.
                * **2. Aturan Data Sehari Utuh & Logika Amandemen (Time Slicing):** Penilaian dihitung berdasarkan **Masa Berlaku Aktif TAFOR**. Jika dalam satu hari terbit TAF Rutin dan TAF Amandemen, komputer akan memotong jam penilaian secara adil dan kronologis. TAFOR Amandemen akan tercetak berjejer ke bawah dalam kotak tanggal yang sama pada berkas **Form 2026**.
                """)
            
            # --- EXPORT ---
            str_mulai, str_selesai = tgl_mulai.strftime('%Y%m%d'), tgl_selesai.strftime('%Y%m%d')
            st.subheader("📥 Export Dokumen Verifikasi Sesuai Range")
            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                st.download_button(label=f"1️⃣ Unduh Matriks Tiap Jam ({str_mulai} - {str_selesai})", data=generate_lapbul_excel(df_filtered).getvalue(), file_name=f"REKAP_MATRIKS_TAFOR_{str_mulai}_TO_{str_selesai}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            with col_dl2:
                st.download_button(label=f"2️⃣ Unduh Verifikasi TAFOR ({str_mulai} - {str_selesai})", data=generate_form_2026(df_filtered).getvalue(), file_name=f"FORM_2026_TAFOR_{str_mulai}_TO_{str_selesai}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                
            with st.expander("🔍 Klik di sini untuk melihat Pratinjau Log Data Terfilter (Audit Trail)"):
                st.dataframe(df_filtered.drop(columns=['Datetime_Obj']).head(50), use_container_width=True)
            
    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")
