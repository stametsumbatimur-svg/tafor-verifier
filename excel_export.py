import re
import pandas as pd
import io
from io import BytesIO
from datetime import datetime
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from verification_logic import hitung_angin_arah, hitung_angin_kec, hitung_vis, hitung_cuaca, hitung_awan_jml, hitung_awan_tgi, parse_sandi
from xlsxwriter.utility import xl_col_to_name, xl_rowcol_to_cell

def export_v_final_excel(df_vfinal, bulan, tahun, stasiun, nama_petugas, nip_petugas="[NIP PETUGAS]", nama_kepala="[NAMA KEPALA STASIUN]", nip_kepala="[NIP KEPALA]"):
    df_excel = df_vfinal.copy()
    
    # ==========================================
    # 1. KONVERSI BOOLEAN MENJADI STRING 'B' & 'S'
    # ==========================================
    kolom_skor = ['S_Arah', 'S_Kec', 'S_Vis', 'S_Wx', 'S_AwanJml', 'S_AwanTgi']
    for col in kolom_skor:
        if col in df_excel.columns:
            # Konversi: Jika aslinya False/Salah -> 'S', selain itu -> 'B'
            df_excel[col] = df_excel[col].apply(
                lambda x: 'S' if str(x).strip().upper() in ['FALSE', 'SALAH', 'S', '0', ''] else 'B'
            )

    if 'Tanggal' in df_excel.columns:
        df_excel.loc[df_excel['Tanggal'].duplicated(), 'Tanggal'] = ""

    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    workbook  = writer.book
    worksheet = workbook.add_worksheet('V_FINAL')
    
    # ==========================================
    # 2. FORMATTING STYLES
    # ==========================================
    format_title = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 12})
    format_subtitle = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_size': 11})
    format_bold_left = workbook.add_format({'bold': True, 'align': 'left', 'valign': 'vcenter', 'font_size': 11})
    
    format_req_header = workbook.add_format({'border': 1, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#D9D9D9', 'text_wrap': True, 'font_size': 10})
    format_req_text = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter', 'text_wrap': True, 'font_size': 10})
    format_req_center = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'bold': True, 'font_size': 10})
    format_req_bold = workbook.add_format({'border': 1, 'bold': True, 'align': 'left', 'valign': 'vcenter', 'font_size': 10})
    
    format_border_bold = workbook.add_format({'border': 1, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True, 'font_size': 10})
    format_persen = workbook.add_format({'border': 1, 'bold': True, 'align': 'center', 'num_format': '0.00%', 'font_size': 10})
    
    format_tabel_header = workbook.add_format({'border': 1, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#D9D9D9', 'font_size': 10})
    format_tabel_data = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 10})
    
    format_hijau = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100', 'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_size': 10})
    format_merah = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006', 'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_size': 10})
    
    # Format Nama TTD dengan Underline (Garis Bawah)
    format_ttd_nama = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 11, 'underline': True})

    # ==========================================
    # 3. MENCARI BATAS KOLOM
    # ==========================================
    if 'S_AwanTgi' in df_excel.columns:
        batas_col = df_excel.columns.get_loc('S_AwanTgi')
    else:
        batas_col = len(df_excel.columns) - 1
        
    batas_col = max(batas_col, 15)
    max_col_data = len(df_excel.columns) - 1

    # ==========================================
    # 4. MENULIS DATAFRAME MANUAL DENGAN BORDER TEPAT
    # ==========================================
    for col_num, value in enumerate(df_excel.columns):
        worksheet.write(12, col_num, value, format_tabel_header)
        
    for row_num, row_data in enumerate(df_excel.values):
        for col_num, value in enumerate(row_data):
            val = "" if pd.isna(value) else value
            worksheet.write(13 + row_num, col_num, val, format_tabel_data)

    # ==========================================
    # 5. HEADER & NARASI PERSYARATAN 
    # ==========================================
    worksheet.merge_range(0, 0, 0, batas_col, 'VERIFIKASI AERODROM FORECAST', format_title)
    worksheet.merge_range(1, 0, 1, batas_col, 'Sesuai Logika SIVETA (Berdasarkan Gambar Toleransi)', format_subtitle)
    worksheet.write(3, 0, 'PERSYARATAN / TOLERANSI KETELITIAN PRAKIRAAN :', format_bold_left)
    
    worksheet.merge_range(4, 0, 4, 1, 'UNSUR METEOROLOGI', format_req_header)
    worksheet.merge_range(4, 2, 4, 6, 'PERSYARATAN / TOLERANSI KETELITIAN', format_req_header)
    worksheet.write(4, 7, 'MINIMUM', format_req_header)
    worksheet.merge_range(4, 8, 4, 9, 'UNSUR METEOROLOGI', format_req_header)
    worksheet.merge_range(4, 10, 4, batas_col - 1, 'PERSYARATAN / TOLERANSI KETELITIAN', format_req_header)
    worksheet.write(4, batas_col, 'MINIMUM', format_req_header)
    
    worksheet.merge_range(5, 0, 5, 1, 'A. Arah Angin', format_req_bold)
    worksheet.merge_range(5, 2, 5, 6, 'Benar apabila arah sama, atau selisih ≤ 60°. Jika kecepatan angin <10 kt, atau VRB, atau kondisi CB/TS, dianggap benar.', format_req_text)
    worksheet.write(5, 7, '80%', format_req_center)
    worksheet.merge_range(5, 8, 5, 9, 'E. Jumlah Awan', format_req_bold)
    worksheet.merge_range(5, 10, 5, batas_col - 1, 'Benar apabila berada pada kelompok yang sama: FEW/SCT atau BKN/OVC. Jika tinggi awan > 5000 ft, dianggap benar.', format_req_text)
    worksheet.write(5, batas_col, '70%', format_req_center)
    
    worksheet.merge_range(6, 0, 6, 1, 'B. Kecepatan Angin', format_req_bold)
    worksheet.merge_range(6, 2, 6, 6, 'Selisih kecepatan dasar ≤ 10 knot. Status gust harus konsisten.', format_req_text)
    worksheet.write(6, 7, '80%', format_req_center)
    worksheet.merge_range(6, 8, 6, 9, 'F. Tinggi Dasar Awan', format_req_bold)
    worksheet.merge_range(6, 10, 6, batas_col - 1, 'Selisih ≤ 100 ft untuk <1000 ft. Untuk ≥ 1000 ft, selisih ≤ 30% dari tinggi awan Manual.', format_req_text)
    worksheet.write(6, batas_col, '70%', format_req_center)

    worksheet.merge_range(7, 0, 7, 1, 'C. Jarak Pandang', format_req_bold)
    worksheet.merge_range(7, 2, 7, 6, 'Benar apabila berada pada kelas visibility yang sama.', format_req_text)
    worksheet.write(7, 7, '80%', format_req_center)
    worksheet.merge_range(8, 8, 8, 9, '', format_req_bold)
    worksheet.merge_range(8, 10, 8, batas_col - 1, '', format_req_text)
    worksheet.write(8, batas_col, '', format_req_center)

    worksheet.merge_range(8, 0, 8, 1, 'D. Cuaca / Endapan', format_req_bold)
    worksheet.merge_range(8, 2, 8, 6, 'Benar apabila sama-sama mendeteksi atau tidak mendeteksi presipitasi sedang/lebat. Hujan ringan (-RA) tidak dihitung.', format_req_text)
    worksheet.write(8, 7, '80%', format_req_center)
    worksheet.merge_range(8, 8, 8, 9, '', format_req_bold)
    worksheet.merge_range(8, 10, 8, batas_col - 1, '', format_req_text)
    worksheet.write(8, batas_col, '', format_req_center)

    worksheet.set_row(5, 45)
    worksheet.set_row(6, 35)
    worksheet.set_row(7, 35)
    worksheet.set_row(8, 45)

    worksheet.write(10, 0, f"BULAN : {bulan}", format_bold_left)
    worksheet.write(10, 3, f"TAHUN : {tahun}", format_bold_left)
    worksheet.write(10, 6, "(SEMUA WAKTU DALAM GMT)", format_bold_left)
    worksheet.write(10, 11, f"STASIUN METEOROLOGI {stasiun}", format_bold_left)

    # ==========================================
    # 6. WARNA KONDISIONAL B/S, FILTER & FREEZE
    # ==========================================
    jumlah_baris_data = len(df_excel)
    excel_start_data_row = 14 
    excel_last_data_row = excel_start_data_row + jumlah_baris_data - 1
    
    data_range = f"A{excel_start_data_row}:{xl_col_to_name(max_col_data)}{excel_last_data_row}"
    
    worksheet.conditional_format(data_range, {'type': 'cell', 'criteria': '==', 'value': '"B"', 'format': format_hijau})
    worksheet.conditional_format(data_range, {'type': 'cell', 'criteria': '==', 'value': '"S"', 'format': format_merah})

    worksheet.autofilter(12, 0, 12 + jumlah_baris_data, max_col_data)
    worksheet.freeze_panes(13, 0) 

    # ==========================================
    # 7. FOOTER & RUMUS PERSENTASE (REVISI GIGI OMPONG)
    # ==========================================
    baris_jumlah_idx = 12 + jumlah_baris_data + 1 
    excel_baris_jumlah = baris_jumlah_idx + 1 
    baris_persen_idx = baris_jumlah_idx + 1
    excel_baris_persen = baris_persen_idx + 1 

    # 💡 PERBAIKAN MERGE: Cukup merge dari kolom 0 sampai 2 saja agar kolom sebelahnya tidak tertimpa
    worksheet.merge_range(baris_jumlah_idx, 0, baris_jumlah_idx, 2, 'JUMLAH', format_border_bold)
    worksheet.merge_range(baris_persen_idx, 0, baris_persen_idx, 2, 'PROSENTASE KEBENARAN', format_border_bold)

    # 💡 PERBAIKAN BORDER PONDASI: Tulis border penuh (string kosong) dari ujung ke ujung DULU
    for col_idx in range(3, max_col_data + 1):
        worksheet.write(baris_jumlah_idx, col_idx, jumlah_baris_data, format_border_bold)
        worksheet.write(baris_persen_idx, col_idx, "", format_border_bold) # Mencegah gigi ompong

    # 💡 MENIMPA BORDER DENGAN RUMUS PADA KOLOM SKOR TERTENTU
    for col_name in kolom_skor:
        if col_name in df_excel.columns:
            col_idx = df_excel.columns.get_loc(col_name)
            col_huruf = xl_col_to_name(col_idx) 
            rumus_persen = f'=IFERROR(COUNTIF({col_huruf}{excel_start_data_row}:{col_huruf}{excel_last_data_row}, "B") / {col_huruf}{excel_baris_jumlah}, 0)'
            # Timpa sel yang tadinya kosong dengan rumus persentase
            worksheet.write_formula(baris_persen_idx, col_idx, rumus_persen, format_persen)

    # ==========================================
    # 8. TANDA TANGAN (KIRI DAN KANAN)
    # ==========================================
    baris_ttd = baris_persen_idx + 4
    
    worksheet.merge_range(baris_ttd, 0, baris_ttd, 3, "Mengetahui,", format_subtitle)
    worksheet.merge_range(baris_ttd + 1, 0, baris_ttd + 1, 3, "Kepala Stasiun", format_subtitle)
    worksheet.merge_range(baris_ttd + 5, 0, baris_ttd + 5, 3, nama_kepala, format_ttd_nama)
    worksheet.merge_range(baris_ttd + 6, 0, baris_ttd + 6, 3, f"NIP. {nip_kepala}", format_subtitle)

    col_ttd_start = max(batas_col - 3, 4)
    col_ttd_end = batas_col
    worksheet.merge_range(baris_ttd, col_ttd_start, baris_ttd, col_ttd_end, "Petugas Pembuat Laporan", format_subtitle)
    worksheet.merge_range(baris_ttd + 5, col_ttd_start, baris_ttd + 5, col_ttd_end, nama_petugas, format_ttd_nama)
    worksheet.merge_range(baris_ttd + 6, col_ttd_start, baris_ttd + 6, col_ttd_end, f"NIP. {nip_petugas}", format_subtitle)

    # ==========================================
    # 9. SETUP PRINT
    # ==========================================
    worksheet.set_column(0, 0, 7.5)   
    worksheet.set_column(1, 1, 9.5)   
    worksheet.set_column(2, max_col_data, 7.5) 

    worksheet.set_landscape()            
    worksheet.set_paper(9)              
    worksheet.fit_to_pages(1, 0)        
    worksheet.set_margins(left=0.24, right=0.24, top=0.5, bottom=0.5)
    
    worksheet.repeat_rows(12, 12)       
    akhir_baris_print = baris_ttd + 7
    worksheet.print_area(0, 0, akhir_baris_print, max_col_data)

    writer.close()
    return output.getvalue()

def generate_lapbul_excel(df_hasil, df_speci=None):
    tgl_jam = pd.DatetimeIndex(df_hasil['Waktu Aktual (UTC)'])
    df_hasil['Tanggal'] = tgl_jam.day
    df_hasil['Jam'] = tgl_jam.hour
    
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        workbook = writer.book
        fmt_h1 = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'bold': True, 'border': 1, 'bg_color': '#D9D9D9'})
        fmt_h2 = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'bold': True, 'border': 1, 'bg_color': '#F2F2F2', 'font_size': 9})
        fmt_jam = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'bold': True, 'border': 1, 'bg_color': '#D9D9D9'})
        fmt_data = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_size': 10})
        fmt_hit = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': True, 'font_color': '#006100', 'bg_color': '#C6EFCE'})
        fmt_miss = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': True, 'font_color': '#9C0006', 'bg_color': '#FFC7CE'})
        fmt_null = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#F2F2F2'})
        
        fmt_label_rekap = workbook.add_format({'align': 'right', 'valign': 'vcenter', 'bold': True})
        fmt_val_rekap = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'bold': True, 'border': 1, 'bg_color': '#D9D9D9'})
        fmt_pct_rekap = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'bold': True, 'border': 1, 'bg_color': '#C6EFCE', 'num_format': '0.00"%"'})

        peta_kolom = {
            'REKAP ARAH ANGIN': ('M_Arah', 'T_Arah', 'D_Arah', 'S_Arah'),
            'REKAP KEC ANGIN': ('M_Kec', 'T_Kec', 'D_Kec', 'S_Kec'),
            'REKAP VIS': ('M_Vis', 'T_Vis', 'D_Vis', 'S_Vis'),
            'REKAP CUACA': ('M_Wx', 'T_Wx', 'D_Wx', 'S_Wx'),
            'REKAP AWAN': ('M_AwanJml', 'T_AwanJml', 'D_AwanJml', 'S_AwanJml'),
            'REKAP TINGGI AWAN': ('M_AwanTgi', 'T_AwanTgi', 'D_AwanTgi', 'S_AwanTgi')
        }
        
        for sheet_name, (k_m, k_t, k_d, k_s) in peta_kolom.items():
            ws = workbook.add_worksheet(sheet_name)
            ws.merge_range(0, 0, 1, 0, "JAM UTC", fmt_h1)
            ws.set_column(0, 0, 10) 
            
            for tgl in range(1, 32):
                cs = 1 + (tgl - 1) * 4
                ws.merge_range(0, cs, 0, cs + 3, tgl, fmt_h1)
                ws.write(1, cs, "METAR", fmt_h2)
                ws.write(1, cs + 1, "TAFOR", fmt_h2)
                ws.write(1, cs + 2, "DEV", fmt_h2)
                ws.write(1, cs + 3, "B/S", fmt_h2)
                ws.set_column(cs, cs + 1, 7)
                ws.set_column(cs + 2, cs + 3, 5)

            for jam in range(24):
                r = jam + 2
                ws.write(r, 0, float(jam), fmt_jam) 
                for tgl in range(1, 32):
                    cs = 1 + (tgl - 1) * 4
                    data = df_hasil[(df_hasil['Tanggal'] == tgl) & (df_hasil['Jam'] == jam)]
                    if not data.empty:
                        baris = data.iloc[0]
                        ws.write(r, cs, baris[k_m], fmt_data)
                        ws.write(r, cs + 1, baris[k_t], fmt_data)
                        ws.write(r, cs + 2, baris[k_d], fmt_data)
                        ws.write(r, cs + 3, baris[k_s], fmt_hit if baris[k_s] == "B" else fmt_miss)
                    else:
                        for offset in range(4): ws.write(r, cs + offset, "-", fmt_null)
            
            r_rekap = 27  
            b_cnt, s_cnt = (df_hasil[k_s] == "B").sum(), (df_hasil[k_s] == "S").sum()
            tot = b_cnt + s_cnt
            pct = (b_cnt / tot * 100) if tot > 0 else 0
            
            for i, label in enumerate(["JUMLAH BENAR (B) : ", "JUMLAH SALAH (S) : ", "TOTAL DATA : ", "PROSENTASE KETELITIAN : "]):
                ws.merge_range(r_rekap + i, 0, r_rekap + i, 2, label, fmt_label_rekap)
            ws.merge_range(r_rekap, 3, r_rekap, 5, b_cnt, fmt_val_rekap)
            ws.merge_range(r_rekap + 1, 3, r_rekap + 1, 5, s_cnt, fmt_val_rekap)
            ws.merge_range(r_rekap + 2, 3, r_rekap + 2, 5, tot, fmt_val_rekap)
            ws.merge_range(r_rekap + 3, 3, r_rekap + 3, 5, pct, fmt_pct_rekap)
            
        if df_speci is not None and not df_speci.empty:
            _bikin_sheet_speci(workbook, df_speci)
            
    return buffer

def generate_form_2026(df_hasil, df_speci=None):
    # 🟢 BYPASS BULLETPROOF: Gunakan DatetimeIndex murni (Bebas dari error .dt accessor)
    tgl_jam = pd.DatetimeIndex(df_hasil['Waktu Aktual (UTC)'])
    df_hasil['Tanggal'] = tgl_jam.day
    df_hasil['Jam'] = tgl_jam.hour
    
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        workbook = writer.book
        ws = workbook.add_worksheet('FORM VERIFIKASI')
        
        fmt_title = workbook.add_format({'bold': True, 'font_size': 11})
        fmt_h = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'bold': True, 'border': 1, 'bg_color': '#D9D9D9', 'font_size': 10})
        fmt_tgl = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': True, 'font_size': 11}) 
        fmt_base = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_size': 10, 'bg_color': '#F8FAFC'})
        fmt_tempo = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_size': 10, 'bg_color': '#FFF9E6'})
        fmt_becmg = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_size': 10, 'bg_color': '#F4EBF7'})
        fmt_prob = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_size': 10, 'bg_color': '#E8F0FE'})
        
        fmt_hit = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': True, 'font_color': '#006100', 'bg_color': '#C6EFCE'})
        fmt_miss = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': True, 'font_color': '#9C0006', 'bg_color': '#FFC7CE'})
        
        fmt_label_rekap = workbook.add_format({'align': 'right', 'valign': 'vcenter', 'bold': True})
        fmt_val_rekap = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'bold': True, 'border': 1, 'bg_color': '#D9D9D9'})
        fmt_pct_rekap = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'bold': True, 'border': 1, 'bg_color': '#C6EFCE', 'num_format': '0.00"%"'})

        ws.write("A1", "VERIFIKASI AERODROM FORECAST", fmt_title)
        ws.merge_range("A4:A5", "TGL", fmt_h)
        ws.merge_range("B4:B5", "WAKTU", fmt_h)
        ws.merge_range("C4:H4", "P R A K I R A A N (TAFOR)", fmt_h)
        ws.write_row("C5", ["A", "B", "C", "D", "E", "F"], fmt_h)
        ws.merge_range("I4:T4", "K E N Y A T A A N (METAR)", fmt_h)
        ws.write_row("I5", ["A", "H", "B", "H", "C", "H", "D", "H", "E", "H", "F", "H"], fmt_h)
        
        ws.set_column("A:A", 5)
        ws.set_column("B:B", 12)
        ws.set_column("C:H", 7)
        ws.set_column("I:T", 6)
        
        rekapan = {k: {'B': 0, 'S': 0} for k in ['A', 'B', 'C', 'D', 'E', 'F']}
        row_idx = 5
        
        for tgl in range(1, 32):
            data_tgl = df_hasil[df_hasil['Tanggal'] == tgl]
            if data_tgl.empty:
                ws.write(row_idx, 0, str(tgl).zfill(2), fmt_tgl)
                ws.write(row_idx, 1, "-", fmt_base)
                ws.write_row(row_idx, 2, ["-"]*18, fmt_base)
                row_idx += 1
                continue
            
            data_tgl_sorted = data_tgl.sort_values('Jam')
            tafs_hari_ini = []
            for _, row in data_tgl_sorted.iterrows():
                sandi = row['Sandi TAF Prakiraan']
                if sandi != "-" and sandi not in tafs_hari_ini: tafs_hari_ini.append(sandi)
            if not tafs_hari_ini: continue
                
            start_row_tgl = row_idx
            for taf_sandi in tafs_hari_ini:
                baris_m_base = data_tgl_sorted[data_tgl_sorted['Sandi TAF Prakiraan'] == taf_sandi].iloc[0]
                parts = re.split(r'\b(BECMG|TEMPO|PROB30 TEMPO|PROB40 TEMPO|PROB30|PROB40)\b', str(taf_sandi))
                
                base_time_match = re.search(r'(\d{2})(\d{2})/(\d{2})(\d{2})', parts[0])
                w_base = f"{base_time_match.group(2)} - {base_time_match.group(4)}" if base_time_match else "00 - 24"
                if w_base.endswith("00"): w_base = w_base[:-2] + "24"
                
                b_ar, b_ke, b_vi, b_wx, b_aj, b_at = parse_sandi(parts[0])
                cur_ar, cur_ke, cur_vi, cur_wx, cur_aj, cur_at = b_ar, b_ke, b_vi, b_wx, b_aj, b_at
                
                _tulis_baris_form(ws, row_idx, w_base, b_ar, b_ke, b_vi, b_wx, b_aj, b_at, baris_m_base, rekapan, fmt_base, fmt_hit, fmt_miss)
                row_idx += 1
                
                for i in range(1, len(parts), 2):
                    tipe, isi = parts[i], parts[i+1]
                    time_match = re.search(r'(\d{2})(\d{2})/(\d{2})(\d{2})', isi)
                    
                    short_tipe = "B" if tipe=='BECMG' else ("T" if tipe=='TEMPO' else ("P30" if '30' in tipe else "P40"))
                    label_w = f"{short_tipe}.{time_match.group(2)}-{time_match.group(4)}" if time_match else f"{short_tipe}.??"
                    if label_w.endswith("00"): label_w = label_w[:-2] + "24"
                    
                    t_ar, t_ke, t_vi, t_wx, t_aj, t_at = parse_sandi(isi)
                    if t_ar == "-": t_ar = cur_ar
                    if t_ke == "-": t_ke = cur_ke
                    if t_vi == "-": t_vi = cur_vi
                    if t_wx == "NIL" and not re.search(r'\b(HZ|RA|TSRA|BR|DZ|FG|VCTS|TS|SHRA|MIFG|SQ|FC)\b', isi) and "CAVOK" not in isi: t_wx = cur_wx
                    if t_aj == "-": t_aj = cur_aj
                    if t_at == "-": t_at = cur_at
                    
                    data_jam = data_tgl_sorted[(data_tgl_sorted['Jam'] == int(time_match.group(2))) & (data_tgl_sorted['Sandi TAF Prakiraan'] == taf_sandi)] if time_match else pd.DataFrame()
                    
                    fmt_warna = fmt_tempo if tipe=='TEMPO' else (fmt_becmg if tipe=='BECMG' else fmt_prob)
                    
                    _tulis_baris_form(ws, row_idx, label_w, t_ar, t_ke, t_vi, t_wx, t_aj, t_at, data_jam.iloc[0] if not data_jam.empty else baris_m_base, rekapan, fmt_warna, fmt_hit, fmt_miss, base_data=(cur_ar, cur_ke, cur_vi, cur_wx, cur_aj, cur_at), is_prob=('PROB' in tipe))
                    row_idx += 1
                    if tipe == 'BECMG': cur_ar, cur_ke, cur_vi, cur_wx, cur_aj, cur_at = t_ar, t_ke, t_vi, t_wx, t_aj, t_at
            
            if row_idx - start_row_tgl > 1: ws.merge_range(start_row_tgl, 0, row_idx - 1, 0, str(tgl).zfill(2), fmt_tgl)
            else: ws.write(start_row_tgl, 0, str(tgl).zfill(2), fmt_tgl)
            
        row_idx += 1
        ws.merge_range(row_idx, 0, row_idx, 7, "NAMA PARAMETER : ", fmt_label_rekap)
        for idx, pk in enumerate(['A', 'B', 'C', 'D', 'E', 'F']):
            ws.merge_range(row_idx, 8 + idx*2, row_idx, 9 + idx*2, pk, fmt_h)
            
        row_idx += 1
        total_b_g, total_data_global = 0, 0
        for i, lbl in enumerate(["JUMLAH BENAR (B) : ", "JUMLAH SALAH (S) : ", "TOTAL DATA : ", "PROSENTASE KETELITIAN : "]):
            ws.merge_range(row_idx+i, 0, row_idx+i, 7, lbl, fmt_label_rekap)
            
        for idx, k in enumerate(['A', 'B', 'C', 'D', 'E', 'F']):
            b, s = rekapan[k]['B'], rekapan[k]['S']
            tot = b + s
            pct = (b / tot * 100) if tot > 0 else 0
            total_b_g += b
            total_data_global += tot  
            ws.merge_range(row_idx, 8 + idx*2, row_idx, 9 + idx*2, b, fmt_val_rekap)
            ws.merge_range(row_idx+1, 8 + idx*2, row_idx+1, 9 + idx*2, s, fmt_val_rekap)
            ws.merge_range(row_idx+2, 8 + idx*2, row_idx+2, 9 + idx*2, tot, fmt_val_rekap)
            ws.merge_range(row_idx+3, 8 + idx*2, row_idx+3, 9 + idx*2, pct, fmt_pct_rekap)
            
        row_idx += 5
        ws.merge_range(row_idx, 0, row_idx, 7, "🔥 TOTAL AKURASI PRAKIRAAN GLOBAL (ALL PARAMETERS) : ", fmt_label_rekap)
        ws.merge_range(row_idx, 8, row_idx, 19, (total_b_g / total_data_global * 100 if total_data_global > 0 else 0), workbook.add_format({'align': 'center', 'valign': 'vcenter', 'bold': True, 'border': 1, 'bg_color': '#DEEBF7', 'num_format': '0.00"%"'}))
        
        row_idx += 3
        fmt_leg_title = workbook.add_format({'bold': True, 'underline': True, 'font_size': 10})
        fmt_leg_text = workbook.add_format({'font_size': 9, 'italic': True})
        ws.write(row_idx, 0, "KETERANGAN KODE PARAMETER:", fmt_leg_title)
        
        legenda_items = [
            "A = Arah Angin (Wind Direction)", "B = Kecepatan Angin (Wind Speed)",
            "C = Visibility (Jarak Pandang Mendatar)", "D = Cuaca Signifikan (Weather Phenomena)",
            "E = Jumlah Awan (Cloud Amount)", "F = Tinggi Dasar Awan (Cloud Base Height)"
        ]
        for item in legenda_items:
            row_idx += 1
            ws.merge_range(row_idx, 0, row_idx, 7, item, fmt_leg_text)
        
        if df_speci is not None and not df_speci.empty:
            _bikin_sheet_speci(workbook, df_speci)
            
    return buffer

def generate_logbook_excel(df_hasil):
    df_log = df_hasil.copy()
    df_log = df_log[df_log['Sandi TAF Prakiraan'] != df_log['Sandi TAF Prakiraan'].shift()]
    
    stn = "WATU"
    if 'Kode_Stasiun' in df_log.columns and not df_log.empty:
        stn = str(df_log['Kode_Stasiun'].iloc[0]).strip().upper()
        
    if stn in ['WIII', 'WIRR', 'WARR', 'WIHH', 'WICC', 'WIIB']:
        tz_label = "WIB"
        hours_offset = 7
    elif stn in ['WADD', 'WAAA', 'WALL', 'WATU']:
        tz_label = "WITA"
        hours_offset = 8
    else:
        tz_label = "WIT"
        hours_offset = 9
        
    # 🟢 BYPASS BULLETPROOF LOGBOOK
    dt_col = pd.to_datetime(df_log['Waktu Aktual (UTC)'])
    df_log['Dt_Lokal'] = dt_col + pd.Timedelta(hours=hours_offset)
    df_log['Tanggal_Lokal'] = df_log['Dt_Lokal'].dt.strftime('%Y-%m-%d')
    df_log['Jam_Lokal'] = df_log['Dt_Lokal'].dt.strftime('%H:%M:%S')
    
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        workbook = writer.book
        ws = workbook.add_worksheet('LOGBOOK RAW GTS')
        
        fmt_h = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'bold': True, 'border': 1, 'bg_color': '#36454F', 'font_color': '#FFFFFF', 'font_size': 10})
        fmt_c = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_size': 10})
        fmt_l = workbook.add_format({'align': 'left', 'valign': 'vcenter', 'border': 1, 'font_size': 9, 'font_name': 'Courier New'})
        
        headers = [f"TANGGAL ({tz_label})", f"JAM ({tz_label})", "SANDI METAR AKTUAL (RAW GTS)", "SANDI TAFOR PRAKIRAAN (RAW GTS)"]
        ws.write_row(0, 0, headers, fmt_h)
        ws.set_column("A:A", 16)
        ws.set_column("B:B", 14)
        ws.set_column("C:C", 55)
        ws.set_column("D:D", 65)
        
        for idx, row in df_log.reset_index(drop=True).iterrows():
            r_num = idx + 1
            ws.write(r_num, 0, row['Tanggal_Lokal'], fmt_c)
            ws.write(r_num, 1, row['Jam_Lokal'], fmt_c)
            ws.write(r_num, 2, str(row['Sandi METAR Aktual']).strip(), fmt_l)
            ws.write(r_num, 3, str(row['Sandi TAF Prakiraan']).strip(), fmt_l)
            
    return buffer

def _tulis_baris_form(ws, r, lbl, tar, tke, tvi, twx, taj, tat, m_row, rekapan, fmt_f, fmt_b, fmt_s, base_data=None, is_prob=False):
    ws.write(r, 1, lbl, fmt_f)
    ws.write_row(r, 2, [tar, tke, tvi, twx, taj, tat], fmt_f)
    
    # ⚙️ PERBAIKAN: Menambahkan parameter kecepatan (M_Kec dan tke) untuk evaluasi Arah Angin SOP 2025
    _, s_ar = hitung_angin_arah(m_row['M_Arah'], tar, m_row['M_Kec'], tke)
    _, s_ke = hitung_angin_kec(m_row['M_Kec'], tke)
    _, s_vi = hitung_vis(m_row['M_Vis'], tvi)
    _, s_wx = hitung_cuaca(m_row['M_Wx'], twx)
    _, s_aj = hitung_awan_jml(m_row['M_AwanJml'], taj, m_row['M_AwanTgi'])
    _, s_at = hitung_awan_tgi(m_row['M_AwanTgi'], tat)
    
    if base_data is not None:
        # ⚙️ PERBAIKAN: Menambahkan parameter kecepatan base_data[1] untuk evaluasi Arah Angin Base Group
        _, b_ar = hitung_angin_arah(m_row['M_Arah'], base_data[0], m_row['M_Kec'], base_data[1])
        _, b_ke = hitung_angin_kec(m_row['M_Kec'], base_data[1])
        _, b_vi = hitung_vis(m_row['M_Vis'], base_data[2])
        _, b_wx = hitung_cuaca(m_row['M_Wx'], base_data[3])
        _, b_aj = hitung_awan_jml(m_row['M_AwanJml'], base_data[4], m_row['M_AwanTgi'])
        _, b_at = hitung_awan_tgi(m_row['M_AwanTgi'], base_data[5])
        
        if s_ar == "S" and b_ar == "B": s_ar = "B"
        if s_ke == "S" and b_ke == "B": s_ke = "B"
        if s_vi == "S" and b_vi == "B": s_vi = "B"
        if s_wx == "S" and b_wx == "B": s_wx = "B"
        if s_aj == "S" and b_aj == "B": s_aj = "B"
        if s_at == "S" and b_at == "B": s_at = "B"

    for idx, (val, stat) in enumerate([(m_row.get('M_Arah', '-'), s_ar), 
                                       (m_row.get('M_Kec', '-'), s_ke), 
                                       (m_row.get('M_Vis', '-'), s_vi), 
                                       (m_row.get('M_Wx', '-'), s_wx), 
                                       (m_row.get('M_AwanJml', '-'), s_aj), 
                                       (m_row.get('M_AwanTgi', '-'), s_at)]):
        ws.write(r, 8 + idx*2, val, fmt_f)
        ws.write(r, 9 + idx*2, stat, fmt_b if stat == "B" else fmt_s)
        
        if stat in ['B', 'S']: 
            rekapan[['A','B','C','D','E','F'][idx]][stat] += 1
def _bikin_sheet_speci(workbook, df_speci):
    ws = workbook.add_worksheet('AUDIT TRAIL SPECI')
    fmt_h = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'bold': True, 'border': 1, 'bg_color': '#D9D9D9', 'font_size': 10})
    fmt_sp = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#FFEAD2', 'font_size': 10})
    fmt_b = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': True, 'font_color': '#006100', 'bg_color': '#C6EFCE'})
    fmt_s = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': True, 'font_color': '#9C0006', 'bg_color': '#FFC7CE'})
    
    headers = ["WAKTU SPECI (UTC)", "SANDI SPECI", "TAFOR BERLAKU", "M_AR", "T_AR", "S_AR", "M_KE", "T_KE", "S_KE", "M_VI", "T_VI", "S_VI", "M_WX", "T_WX", "S_WX", "M_AJ", "T_AJ", "S_AJ", "M_AT", "T_AT", "S_AT", "HASIL"]
    ws.write_row(0, 0, headers, fmt_h)
    ws.set_column("A:A", 20)
    ws.set_column("B:C", 35)
    
    for idx, r in df_speci.reset_index(drop=True).iterrows():
        row_num = idx + 1
        ws.write_row(row_num, 0, [r['Waktu SPECI (UTC)'], r['Sandi SPECI'], r['TAFOR Berlaku']], fmt_sp)
        cols_mapping = [
            ('M_Arah', 'T_Arah', 'S_Arah'), ('M_Kec', 'T_Kec', 'S_Kec'),
            ('M_Vis', 'T_Vis', 'S_Vis'), ('M_Wx', 'T_Wx', 'S_Wx'),
            ('M_AwanJml', 'T_AwanJml', 'S_AwanJml'), ('M_AwanTgi', 'T_AwanTgi', 'S_AwanTgi')
        ]
        c_idx = 3
        for m, t, s in cols_mapping:
            ws.write(row_num, c_idx, r[m], fmt_sp)
            ws.write(row_num, c_idx+1, r[t], fmt_sp)
            ws.write(row_num, c_idx+2, r[s], fmt_b if r[s]=='B' else fmt_s)
            c_idx += 3
        ws.write(row_num, 21, r['Hasil Akhir'], fmt_b if r['Hasil Akhir']=='ACCURATE' else fmt_s)
        
def generate_klasik_31_sheet(df_filtered):
    output = BytesIO()
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    
    if df_filtered.empty:
        wb.create_sheet("Kosong")
        wb.save(output)
        output.seek(0)
        return output

    contoh_waktu = pd.to_datetime(df_filtered.iloc[0]['Waktu Aktual (UTC)'])
    nama_bulan = contoh_waktu.strftime("%B").upper()
    tahun = contoh_waktu.strftime("%Y")

    # Loop maksimal 31 Hari untuk Cetak Form Harian
    for hari in range(1, 32):
        tgl_str = f"{tahun}-{contoh_waktu.strftime('%m')}-{str(hari).zfill(2)}"
        try:
            start_time = datetime.strptime(f"{tgl_str} 00:00", "%Y-%m-%d %H:%M")
        except ValueError:
            break 
            
        ws = wb.create_sheet(title=str(hari))
        ws.merge_cells("A1:AD1")
        ws["C3"] = f"BULAN : {nama_bulan}"
        ws["E3"] = f"TAHUN : {tahun}"
        ws["M3"] = "( SEMUA WAKTU DALAM UTC )"
        
        headers_atas = ["", "Tanggal", "Jangka waktu", "Prakiraan :", "", "", "", "", "", "", "", "", "KENYATAAN (METAR DAN SPECI):"]
        headers_bawah = ["", "", "Change Group", "Change Group Time (UTC)", "A", "B1", "B2", "C", "D", "E", "F", "DATA METAR", "A", "H", "B1", "H", "B2", "H", "C", "H", "D", "H", "E", "H", "F", "H"]
        ws.append(headers_atas)
        ws.append(headers_bawah)
        
        df_hari_ini = df_filtered[df_filtered['Waktu Aktual (UTC)'].str.startswith(tgl_str)]
        
        # Isi form 48 baris (grid kaku)
        for i in range(48):
            jam_sekarang = (start_time + pd.Timedelta(minutes=30*i)).strftime("%H:%M:%S")
            df_jam = df_hari_ini[df_hari_ini['Waktu Aktual (UTC)'].str.contains(jam_sekarang)]
            
            if not df_jam.empty:
                row_data = df_jam.iloc[0]
                h_a = 1 if row_data.get('S_Arah', 'S') == 'B' else 0
                h_b = 1 if row_data.get('S_Kec', 'S') == 'B' else 0
                h_c = 1 if row_data.get('S_Vis', 'S') == 'B' else 0
                h_d = 1 if row_data.get('S_Wx', 'S') == 'B' else 0
                h_e = 1 if row_data.get('S_AwanJml', 'S') == 'B' else 0
                h_f = 1 if row_data.get('S_AwanTgi', 'S') == 'B' else 0

                baris = [
                    "", hari if i == 0 else "", jam_sekarang, 
                    row_data.get('Sandi TAF Prakiraan', '-'), "", 
                    row_data.get('T_Arah', '-'), row_data.get('T_Kec', '-'), 0, row_data.get('T_Vis', '-'), row_data.get('T_Wx', '-'), row_data.get('T_AwanJml', '-'), row_data.get('T_AwanTgi', '-'),
                    row_data.get('Sandi METAR Aktual', '-'),
                    row_data.get('M_Arah', '-'), h_a,
                    row_data.get('M_Kec', '-'), h_b,
                    0, 1, 
                    row_data.get('M_Vis', '-'), h_c,
                    row_data.get('M_Wx', '-'), h_d,
                    row_data.get('M_AwanJml', '-'), h_e,
                    row_data.get('M_AwanTgi', '-'), h_f
                ]
            else:
                baris = ["", hari if i == 0 else "", jam_sekarang] + [""]*23
                
            baris_bersih = [re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', item) if isinstance(item, str) else item for item in baris]
            ws.append(baris_bersih)

    # ==============================================================
    # 🟢 SINKRONISASI TOTAL AKURASI REKAP DENGAN WEB DASHBOARD
    # ==============================================================
    ws_rekap = wb.create_sheet(title="REKAP 1 BULAN", index=0)
    ws_rekap.column_dimensions['A'].width = 35
    ws_rekap.column_dimensions['B'].width = 20
    ws_rekap["A1"] = f"VERIFIKASI TAF BULAN {nama_bulan} {tahun}"
    ws_rekap["A1"].font = Font(bold=True)
    ws_rekap.append([""])
    ws_rekap.append(["UNSUR METEOROLOGI", "PROSENTASE (%)"])
    ws_rekap["A3"].font = Font(bold=True); ws_rekap["B3"].font = Font(bold=True)
    
    # Menghitung Nilai B dan S dari Populasi Data Global (Persis Cara Kerja Web)
    def hitung_persen_unsur(kolom):
        b = (df_filtered[kolom] == "B").sum()
        s = (df_filtered[kolom] == "S").sum()
        tot = b + s
        pct = round((b / tot * 100), 2) if tot > 0 else 0
        return pct, b, tot

    p_a, b_a, tot_a = hitung_persen_unsur('S_Arah')
    p_b, b_b, tot_b = hitung_persen_unsur('S_Kec')
    p_c, b_c, tot_c = hitung_persen_unsur('S_Vis')
    p_d, b_d, tot_d = hitung_persen_unsur('S_Wx')
    p_e, b_e, tot_e = hitung_persen_unsur('S_AwanJml')
    p_f, b_f, tot_f = hitung_persen_unsur('S_AwanTgi')
    
    # Rata-rata Total GLOBAL (Sama dengan Akurasi Matriks di Web)
    total_b_global = b_a + b_b + b_c + b_d + b_e + b_f
    total_data_global = tot_a + tot_b + tot_c + tot_d + tot_e + tot_f
    rata_rata = round((total_b_global / total_data_global * 100), 1) if total_data_global > 0 else 0
    
    ws_rekap.append(["A. Arah Angin", p_a])
    ws_rekap.append(["B. Kecepatan Angin", p_b])
    ws_rekap.append(["C. Jarak Pandang (Visibility)", p_c])
    ws_rekap.append(["D. Cuaca / Endapan", p_d])
    ws_rekap.append(["E. Jumlah Awan", p_e])
    ws_rekap.append(["F. Tinggi Dasar Awan", p_f])
    ws_rekap.append(["", ""])
    ws_rekap.append(["RATA-RATA TOTAL", rata_rata])
    
    ws_rekap.cell(row=11, column=1).font = Font(bold=True)
    ws_rekap.cell(row=11, column=2).font = Font(bold=True)

    wb.save(output)
    output.seek(0)
    return output
