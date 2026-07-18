# 🔥 SIVETA - Excel Export Engine (Ultra-Clean Streamlined Version)
import io
import re
import pandas as pd
from datetime import datetime
import openpyxl
from openpyxl.styles import Font
from xlsxwriter.utility import xl_col_to_name

def export_v_final_excel(df_vfinal, bulan, tahun, stasiun, nama_petugas, nip_petugas="[NIP PETUGAS]", nama_kepala="[NAMA KEPALA STASIUN]", nip_kepala="[NIP KEPALA]"):
    df_excel = df_vfinal.copy()
    
    # ==========================================
    # 1. KONVERSI BOOLEAN MENJADI STRING 'B' & 'S'
    # ==========================================
    kolom_skor = ['S_Arah', 'S_Kec', 'S_Vis', 'S_Wx', 'S_AwanJml', 'S_AwanTgi']
    for col in kolom_skor:
        if col in df_excel.columns:
            df_excel[col] = df_excel[col].apply(
                lambda x: 'S' if str(x).strip().upper() in ['FALSE', 'SALAH', 'S', '0', ''] else 'B'
            )

    if 'Tanggal' in df_excel.columns:
        df_excel.loc[df_excel['Tanggal'].duplicated(), 'Tanggal'] = ""

    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    workbook  = writer.book
    worksheet = workbook.add_worksheet('VERIFIKASI TAFOR')
    
    # ==========================================
    # 2. OPTIMASI FORMATTING STYLES (PORTRAIT MODE)
    # ==========================================
    format_title = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 11})
    format_subtitle = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'font_size': 9})
    format_bold_left = workbook.add_format({'bold': True, 'align': 'left', 'valign': 'vcenter', 'font_size': 9.5})
    
    format_req_header = workbook.add_format({'border': 1, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#D9D9D9', 'text_wrap': True, 'font_size': 8.5})
    format_req_text = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter', 'text_wrap': True, 'font_size': 8})
    format_req_bold = workbook.add_format({'border': 1, 'bold': True, 'align': 'left', 'valign': 'vcenter', 'font_size': 8.5})
    
    format_border_bold = workbook.add_format({'border': 1, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True, 'font_size': 8.5})
    format_persen = workbook.add_format({'border': 1, 'bold': True, 'align': 'center', 'num_format': '0.00%', 'font_size': 8.5})
    
    format_tabel_header = workbook.add_format({'border': 1, 'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#D9D9D9', 'text_wrap': True, 'font_size': 8.5})
    format_tabel_data = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 8.5, 'text_wrap': True})
    
    format_hijau = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100', 'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_size': 8.5})
    format_merah = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006', 'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_size': 8.5})
    
    format_ttd_nama = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 9.5, 'underline': True})

    # ==========================================
    # 3. MENCARI BATAS KOLOM & NAMA HEADER
    # ==========================================
    if 'S_AwanTgi' in df_excel.columns:
        batas_col = df_excel.columns.get_loc('S_AwanTgi')
    else:
        batas_col = len(df_excel.columns) - 1
        
    batas_col = max(batas_col, 15)
    max_col_data = len(df_excel.columns) - 1

    nama_kolom_cantik = [
        "Tgl", "Jangka Waktu", "Perubahan",
        "Arah\n(T)", "Kec\n(T)", "Vis\n(T)", "Cuaca\n(T)", "Jml\nAwan\n(T)", "Tgi\nAwan\n(T)",
        "Arah\n(M)", "Skor", "Kec\n(M)", "Skor", "Vis\n(M)", "Skor", 
        "Cuaca\n(M)", "Skor", "Jml\nAwan\n(M)", "Skor", "Tgi\nAwan\n(M)", "Skor"
    ]

    # ==========================================
    # 4. MENULIS HEADER & DATAFRAME MANUAL
    # ==========================================
    worksheet.set_row(12, 38) # Ruang ekstra untuk kompresi teks header vertical
    for col_num, col_name in enumerate(nama_kolom_cantik):
        worksheet.write(12, col_num, col_name, format_tabel_header)
        
    for row_num, row_data in enumerate(df_excel.values):
        for col_num, value in enumerate(row_data):
            val = "" if pd.isna(value) else value
            worksheet.write(13 + row_num, col_num, val, format_tabel_data)

    # ==========================================
    # 5. HEADER & NARASI KRITERIA (DISTRIBUSI TINGGI ROW BARU)
    # ==========================================
    worksheet.merge_range(0, 0, 0, batas_col, 'VERIFIKASI AERODROM FORECAST', format_title)
    worksheet.write(3, 0, 'PERSYARATAN / TOLERANSI KETELITIAN PRAKIRAAN :', format_bold_left)
    
    worksheet.merge_range(4, 0, 4, 1, 'UNSUR METEOROLOGI', format_req_header)
    worksheet.merge_range(4, 2, 4, 7, 'PERSYARATAN / TOLERANSI KETELITIAN', format_req_header) 
    worksheet.merge_range(4, 8, 4, 10, 'UNSUR METEOROLOGI', format_req_header) 
    worksheet.merge_range(4, 11, 4, batas_col, 'PERSYARATAN / TOLERANSI KETELITIAN', format_req_header) 
    
    worksheet.merge_range(5, 0, 5, 1, 'A. Arah Angin', format_req_bold)
    worksheet.merge_range(5, 2, 5, 7, 'Benar apabila arah sama, atau selisih <= 60 derajat. Jika kecepatan angin <10 kt, atau VRB, atau kondisi CB/TS, dianggap benar.', format_req_text)
    worksheet.merge_range(5, 8, 5, 10, 'E. Jumlah Awan', format_req_bold) 
    worksheet.merge_range(5, 11, 5, batas_col, 'Benar apabila berada pada kelompok yang sama: FEW/SCT atau BKN/OVC. Jika tinggi awan > 5000 ft, dianggap benar.', format_req_text)
    
    worksheet.merge_range(6, 0, 6, 1, 'B. Kecepatan Angin', format_req_bold)
    worksheet.merge_range(6, 2, 6, 7, 'Selisih kecepatan dasar <= 10 knot. Status gust harus konsisten.', format_req_text)
    worksheet.merge_range(6, 8, 6, 10, 'F. Tinggi Dasar Awan', format_req_bold) 
    worksheet.merge_range(6, 11, 6, batas_col, 'Selisih <= 100 ft untuk <1000 ft. Untuk >= 1000 ft, selisih <= 30% dari tinggi awan Manual.', format_req_text)

    worksheet.merge_range(7, 0, 7, 1, 'C. Jarak Pandang', format_req_bold)
    worksheet.merge_range(7, 2, 7, 7, 'Benar apabila berada pada kelas visibility yang sama.', format_req_text)
    worksheet.merge_range(7, 8, 7, 10, '', format_req_bold) 
    worksheet.merge_range(7, 11, 7, batas_col, '', format_req_text)

    worksheet.merge_range(8, 0, 8, 1, 'D. Cuaca / Endapan', format_req_bold)
    worksheet.merge_range(8, 2, 8, 7, 'Benar apabila sama-sama mendeteksi atau tidak mendeteksi presipitasi sedang/lebat. Hujan ringan (-RA) tidak dihitung.', format_req_text)
    worksheet.merge_range(8, 8, 8, 10, '', format_req_bold) 
    worksheet.merge_range(8, 11, 8, batas_col, '', format_req_text)

    # Ditinggikan signifikan karena kolom portrait sempit membuat teks kriteria melipat ke bawah
    worksheet.set_row(5, 68)
    worksheet.set_row(6, 52)
    worksheet.set_row(7, 35)
    worksheet.set_row(8, 68)
    
    worksheet.write(10, 0, f"BULAN : {bulan}", format_bold_left)
    worksheet.write(10, 3, f"TAHUN : {tahun}", format_bold_left)
    worksheet.write(10, 6, "(GMT)", format_bold_left)
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
    # 7. FOOTER & RUMUS PERSENTASE
    # ==========================================
    baris_jumlah_idx = 12 + jumlah_baris_data + 1 
    excel_baris_jumlah = baris_jumlah_idx + 1 
    baris_persen_idx = baris_jumlah_idx + 1
    excel_baris_persen = baris_persen_idx + 1 

    worksheet.merge_range(baris_jumlah_idx, 0, baris_jumlah_idx, 2, 'JUMLAH', format_border_bold)
    worksheet.merge_range(baris_persen_idx, 0, baris_persen_idx, 2, 'PROSENTASE KEBENARAN', format_border_bold)

    for col_idx in range(3, max_col_data + 1):
        worksheet.write(baris_jumlah_idx, col_idx, jumlah_baris_data, format_border_bold)
        worksheet.write(baris_persen_idx, col_idx, "", format_border_bold)

    for col_name in kolom_skor:
        if col_name in df_excel.columns:
            col_idx = df_excel.columns.get_loc(col_name)
            col_huruf = xl_col_to_name(col_idx) 
            rumus_persen = f'=IFERROR(COUNTIF({col_huruf}{excel_start_data_row}:{col_huruf}{excel_last_data_row}, "B") / {col_huruf}{excel_baris_jumlah}, 0)'
            worksheet.write_formula(baris_persen_idx, col_idx, rumus_persen, format_persen)

    # ==========================================
    # 8. TANDA TANGAN (POSISI KOMPRES)
    # ==========================================
    baris_ttd = baris_persen_idx + 4 
    
    worksheet.merge_range(baris_ttd, 0, baris_ttd, 3, "Mengetahui,", format_subtitle)
    worksheet.merge_range(baris_ttd + 1, 0, baris_ttd + 1, 3, "Kepala Stasiun", format_subtitle)
    worksheet.merge_range(baris_ttd + 5, 0, baris_ttd + 5, 3, nama_kepala, format_ttd_nama)
    worksheet.merge_range(baris_ttd + 6, 0, baris_ttd + 6, 3, f"NIP. {nip_kepala}", format_subtitle)

    col_ttd_start = max(batas_col - 4, 4)
    col_ttd_end = batas_col
    worksheet.merge_range(baris_ttd, col_ttd_start, baris_ttd, col_ttd_end, "Petugas Pembuat Laporan", format_subtitle)
    worksheet.merge_range(baris_ttd + 5, col_ttd_start, baris_ttd + 5, col_ttd_end, nama_petugas, format_ttd_nama)
    worksheet.merge_range(baris_ttd + 6, col_ttd_start, baris_ttd + 6, col_ttd_end, f"NIP. {nip_petugas}", format_subtitle)

    # ==========================================
    # 9. SETUP HINGGA COCOK PADA CETAK PORTRAIT
    # ==========================================
    worksheet.set_column('A:A', 4.5)   # Tanggal ringkas
    worksheet.set_column('B:C', 9.5)   # Jangka Waktu & Perubahan
    worksheet.set_column('D:E', 5.5)   # Arah & Kec TAF
    worksheet.set_column('F:I', 6.5)   # Vis, Wx, Awan TAF
    worksheet.set_column('J:J', 5.5)   # Arah METAR
    worksheet.set_column('K:K', 4.0)   # Skor Arah (Ultra Slim)
    worksheet.set_column('L:L', 5.5)   # Kec METAR
    worksheet.set_column('M:M', 4.0)   # Skor Kec (Ultra Slim)
    worksheet.set_column('N:N', 6.5)   # Vis METAR
    worksheet.set_column('O:O', 4.0)   # Skor Vis (Ultra Slim)
    worksheet.set_column('P:P', 6.5)   # Wx METAR
    worksheet.set_column('Q:Q', 4.0)   # Skor Wx (Ultra Slim)
    worksheet.set_column('R:R', 6.5)   # Awan Jml METAR
    worksheet.set_column('S:S', 4.0)   # Skor Awan Jml (Ultra Slim)
    worksheet.set_column('T:T', 6.5)   # Awan Tgi METAR
    worksheet.set_column('U:U', 4.0)   # Skor Awan Tgi (Ultra Slim)

    worksheet.set_portrait()            # 🟢 AKTOR UTAMA: UBAH JADI PORTRAIT
    worksheet.set_paper(9)              # Kertas A4             
    worksheet.fit_to_pages(1, 0)        # Paksa lebar tabel pas total 1 halaman Portrait
    worksheet.set_margins(left=0.15, right=0.15, top=0.4, bottom=0.4) # Margin ultra tipis
    
    worksheet.repeat_rows(12, 12)       
    
    akhir_baris_print = baris_ttd + 7
    worksheet.print_area(0, 0, akhir_baris_print, max_col_data)

    writer.close()
    return output.getvalue()


def generate_klasik_31_sheet(df_filtered):
    output = io.BytesIO()
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

    # Rekap 1 Bulan Singkat 
    ws_rekap = wb.create_sheet(title="REKAP 1 BULAN", index=0)
    ws_rekap.column_dimensions['A'].width = 35
    ws_rekap.column_dimensions['B'].width = 20
    ws_rekap["A1"] = f"VERIFIKASI TAF BULAN {nama_bulan} {tahun}"
    ws_rekap["A1"].font = Font(bold=True)
    ws_rekap.append([""])
    ws_rekap.append(["UNSUR METEOROLOGI", "PROSENTASE (%)"])
    ws_rekap["A3"].font = Font(bold=True); ws_rekap["B3"].font = Font(bold=True)
    
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
