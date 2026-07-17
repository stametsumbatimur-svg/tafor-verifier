import streamlit as st
import pandas as pd
from datetime import datetime

# Impor fungsi-fungsi dari file logika dan export Kapten
from verification_logic import proses_verifikasi, buat_tabel_laporan_excel
from excel_export import generate_excel_vfinal

# Konfigurasi Halaman Web
st.set_page_config(page_title="SIVETA - Verifikasi TAFOR", page_icon="✈️", layout="wide")

st.title("SIVETA: Sistem Verifikasi TAFOR ✈️")
st.markdown("Aplikasi pintar untuk memverifikasi TAFOR terhadap METAR dengan hasil format **V FINAL BMKG**.")
st.markdown("---")

# ==========================================
# 1. SIDEBAR (PENGATURAN & UPLOAD FILE)
# ==========================================
with st.sidebar:
    st.header("⚙️ Pengaturan Laporan")
    nama_stasiun = st.text_input("Nama Stasiun", value="UMBU MEHANG KUNDA")
    
    # Deteksi waktu saat ini untuk default dropdown
    bulan_sekarang = datetime.now().month - 1
    tahun_sekarang = datetime.now().year
    
    daftar_bulan = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", 
                    "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    
    bulan_pilih = st.selectbox("Pilih Bulan", daftar_bulan, index=bulan_sekarang)
    tahun_pilih = st.number_input("Pilih Tahun", min_value=2000, max_value=2100, value=tahun_sekarang)

    st.markdown("---")
    st.header("📂 Upload Data")
    file_metar = st.file_uploader("1. Upload METAR (Excel/CSV)", type=['xlsx', 'xls', 'csv'])
    file_taf = st.file_uploader("2. Upload TAFOR (Excel/CSV)", type=['xlsx', 'xls', 'csv'])
    file_speci = st.file_uploader("3. Upload SPECI (Opsional)", type=['xlsx', 'xls', 'csv'])

# ==========================================
# 2. MAIN AREA (PROSES VERIFIKASI)
# ==========================================
# Fungsi untuk membaca data sesuai ekstensi (di-cache agar cepat)
@st.cache_data
def load_data(file):
    if file.name.endswith('.csv'):
        return pd.read_csv(file)
    return pd.read_excel(file)

if st.button("🚀 Jalankan Verifikasi", type="primary", use_container_width=True):
    if file_metar is None or file_taf is None:
        st.error("⚠️ Mohon upload file METAR dan TAFOR di panel sebelah kiri terlebih dahulu!")
    else:
        with st.spinner("Membaca sandi dan menghitung akurasi... Mohon tunggu..."):
            try:
                # Muat DataFrame
                df_metar = load_data(file_metar)
                df_taf = load_data(file_taf)
                df_speci = load_data(file_speci) if file_speci else pd.DataFrame()

                # Jalankan Mesin Logika Utama
                df_analisis_final, df_speci_final, _, _ = proses_verifikasi(df_metar, df_taf, df_speci)
                
                st.success("✅ Verifikasi berhasil diselesaikan dengan kilat!")
                
                # Tampilkan cuplikan data di layar untuk meyakinkan User
                st.subheader("Cuplikan Hasil Analisis Internal")
                st.dataframe(df_analisis_final.head(10), use_container_width=True)

                # ==========================================
                # 3. GENERATE EXCEL (FORMAT V FINAL)
                # ==========================================
                # Pecah data menjadi baris-baris Base, TEMPO, BECMG
                df_siap_cetak = buat_tabel_laporan_excel(df_analisis_final)
                
                # Gambar ke dalam Excel secara virtual (Binary)
                file_excel_binary = generate_excel_vfinal(
                    df_evaluasi=df_siap_cetak, 
                    bulan_nama=bulan_pilih, 
                    tahun=str(tahun_pilih),
                    nama_stasiun=nama_stasiun
                )
                
                st.markdown("---")
                st.subheader("📥 Unduh Laporan")
                st.info("Laporan sudah disusun menyesuaikan Instruksi Met./No.029/I/88 (Format V FINAL).")
                
                # Tombol Download
                st.download_button(
                    label=f"Unduh Laporan {bulan_pilih} {tahun_pilih} (.xlsx)",
                    data=file_excel_binary,
                    file_name=f"Laporan_Verifikasi_TAF_{bulan_pilih}_{tahun_pilih}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )

            except Exception as e:
                st.error(f"❌ Terjadi kesalahan saat memproses data. Detail Error: {e}")
                st.info("Pastikan format kolom Excel yang diupload sudah sesuai dengan standar sistem.")
