import streamlit as st
import pandas as pd
from datetime import datetime
from verification_logic import proses_verifikasi
from excel_export import generate_lapbul_excel, generate_form_2026

st.set_page_config(page_title="TAFOR Verifier BMKG", layout="wide")

st.title("✈️ Sistem Verifikasi TAFOR Kontinu (GTS BMKG)")
st.write("Unggah file CSV METAR dan TAFOR, lalu tentukan rentang tanggal verifikasi secara fleksibel.")

# --- PANEL FILTER TANGGAL DI SIDEBAR ---
st.sidebar.header("🗓️ Filter Rentang Waktu")
st.sidebar.write("Tentukan periode cuaca yang ingin diverifikasi:")

hari_ini = datetime.now().date()
tanggal_pilihan = st.sidebar.date_input(
    "Pilih Tanggal Mulai dan Selesai:",
    value=(hari_ini, hari_ini),
    key="rentang_tanggal"
)

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
        
        if "metar" not in df_metar['type_message'].iloc[0].lower():
            df_metar, df_taf = df_taf, df_metar 
            
        df_hasil, _, _, _ = proses_verifikasi(df_metar, df_taf)
        
        # --- PROSES FILTER RENTANG TANGGAL ---
        df_hasil['Datetime_Obj'] = pd.to_datetime(df_hasil['Waktu Aktual (UTC)']).dt.date
        
        if isinstance(tanggal_pilihan, tuple) and len(tanggal_pilihan) == 2:
            tgl_mulai, tgl_selesai = tanggal_pilihan
        else:
            tgl_mulai = tgl_selesai = tanggal_pilihan[0] if isinstance(tanggal_pilihan, list) else tanggal_pilihan
            
        df_filtered = df_hasil[(df_hasil['Datetime_Obj'] >= tgl_mulai) & (df_hasil['Datetime_Obj'] <= tgl_selesai)].copy()
        
        if df_filtered.empty:
            st.warning(f"⚠️ Tidak ada data cuaca ditemukan pada rentang {tgl_mulai} s.d {tgl_selesai}. Silakan cek kembali file ekspor GTS Anda.")
        else:
            st.success(f"✅ Data Berhasil Difilter: {tgl_mulai} s.d {tgl_selesai}")
            
            # --- PERHITUNGAN BARU: AKURASI PROPORSIONAL (SAMA SEPERTI EXCEL) ---
            total_b_global = 0
            total_data_global = 0
            p_akurasi = {}
            
            p_mapping = {
                "A (Arah Angin)": "S_Arah",
                "B (Kec Angin)": "S_Kec",
                "C (Visibility)": "S_Vis",
                "D (Cuaca)": "S_Wx",
                "E (Jumlah Awan)": "S_AwanJml",
                "F (Tinggi Awan)": "S_AwanTgi"
            }
            
            for label, col_name in p_mapping.items():
                b_cnt = (df_filtered[col_name] == "B").sum()
                s_cnt = (df_filtered[col_name] == "S").sum()
                tot = b_cnt + s_cnt
                
                pct = (b_cnt / tot * 100) if tot > 0 else 0
                p_akurasi[label] = round(pct, 1)
                
                total_b_global += b_cnt
                total_data_global += tot
                
            akurasi_global_final = round((total_b_global / total_data_global * 100), 1) if total_data_global > 0 else 0
            
            # --- TAMPILAN BARU: TOTAL AKURASI GLOBAL SPERTI EXCEL ---
            st.subheader(f"📊 Ringkasan Akurasi Periode ({tgl_mulai} s.d {tgl_selesai})")
            
            # Menampilkan Nilai Akurasi Global secara besar dan mencolok
            st.info(f"### 🔥 TOTAL AKURASI PRAKIRAAN GLOBAL (ALL PARAMETERS): {akurasi_global_final}%")
            
            # Menampilkan 6 Parameter Unsur Cuaca Berjejer di bawahnya
            st.write("**Rincian Ketelitian Per Parameter (Standar Instruksi Met No.029):**")
            cols = st.columns(6)
            for idx, (label, score) in enumerate(p_akurasi.items()):
                cols[idx].metric(label, f"{score}%")
            
            # --- GRAFIK TREN ---
            st.subheader("📈 Tren Akurasi Harian")
            df_grafik = df_filtered.copy()
            df_grafik['Tanggal_Chart'] = pd.to_datetime(df_grafik['Waktu Aktual (UTC)']).dt.date
            df_harian = df_grafik.groupby('Tanggal_Chart').apply(
                lambda x: (len(x[x['Hasil Akhir'] == 'ACCURATE']) / len(x)) * 100
            ).reset_index(name='Akurasi (%)')
            df_harian.set_index('Tanggal_Chart', inplace=True)
            st.line_chart(df_harian, use_container_width=True)
            
            # --- FORMAT NAMA FILE EXCEL ---
            str_mulai = tgl_mulai.strftime('%Y%m%d')
            str_selesai = tgl_selesai.strftime('%Y%m%d')
            nama_file_matriks = f"REKAP_MATRIKS_TAFOR_{str_mulai}_TO_{str_selesai}.xlsx"
            nama_file_form = f"FORM_2026_TAFOR_{str_mulai}_TO_{str_selesai}.xlsx"
            
            st.subheader("📥 Export Dokumen Verifikasi Sesuai Range")
            st.write("Unduh berkas excel dengan penamaan otomatis sesuai rentang tanggal inputan.")
            
            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                excel_matriks = generate_lapbul_excel(df_filtered)
                st.download_button(
                    label=f"1️⃣ Unduh Matriks ({str_mulai} - {str_selesai})",
                    data=excel_matriks.getvalue(),
                    file_name=nama_file_matriks,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            with col_dl2:
                excel_form = generate_form_2026(df_filtered)
                st.download_button(
                    label=f"2️⃣ Unduh Form 2026 ({str_mulai} - {str_selesai})",
                    data=excel_form.getvalue(),
                    file_name=nama_file_form,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
            # Menggunakan expander (Laci lipat) agar web terlihat bersih dan ringkas
            with st.expander("🔍 Klik di sini untuk melihat Pratinjau Log Data Terfilter (Audit Trail)"):
                st.write("Menampilkan 50 baris data teratas untuk pengecekan kecocokan sandi harian:")
                st.dataframe(df_filtered.drop(columns=['Datetime_Obj']).head(50), use_container_width=True)
            
    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")