import pandas as pd
import io
import re

# Mengimpor rumus otak dari verification_logic agar bisa menguji secara mandiri
from verification_logic import parse_sandi, hitung_angin_arah, hitung_angin_kec, hitung_vis, hitung_cuaca, hitung_awan_jml, hitung_awan_tgi

def generate_lapbul_excel(df_hasil):
    """
    Fungsi pengisi Excel Matriks (Jam x Tanggal) yang dilengkapi dengan 
    Rekapitulasi otomatis yang sudah diperlebar di bagian bawah jam ke-23.
    """
    df_hasil['Datetime'] = pd.to_datetime(df_hasil['Waktu Aktual (UTC)'], errors='coerce')
    df_hasil['Tanggal'] = df_hasil['Datetime'].dt.day
    df_hasil['Jam'] = df_hasil['Datetime'].dt.hour
    df_hourly = df_hasil
    
    buffer = io.BytesIO()
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
                    data = df_hourly[(df_hourly['Tanggal'] == tgl) & (df_hourly['Jam'] == jam)]
                    
                    if not data.empty:
                        baris = data.iloc[0]
                        v_m, v_t, v_d, stat = baris[k_m], baris[k_t], baris[k_d], baris[k_s]
                        f_stat = fmt_hit if stat == "B" else fmt_miss
                        ws.write(r, cs, v_m, fmt_data)
                        ws.write(r, cs + 1, v_t, fmt_data)
                        ws.write(r, cs + 2, v_d, fmt_data)
                        ws.write(r, cs + 3, stat, f_stat)
                    else:
                        for offset in range(4): ws.write(r, cs + offset, "-", fmt_null)
            
            r_rekap = 27  
            b_cnt = (df_hourly[k_s] == "B").sum()
            s_cnt = (df_hourly[k_s] == "S").sum()
            tot = b_cnt + s_cnt
            pct = (b_cnt / tot * 100) if tot > 0 else 0
            
            labels = [
                "JUMLAH BENAR (B) : ", 
                "JUMLAH SALAH (S) : ", 
                "TOTAL DATA : ", 
                "PROSENTASE KETELITIAN : "
            ]
            
            for i, label in enumerate(labels):
                ws.merge_range(r_rekap + i, 0, r_rekap + i, 2, label, fmt_label_rekap)
                
            ws.merge_range(r_rekap, 3, r_rekap, 5, b_cnt, fmt_val_rekap)
            ws.merge_range(r_rekap + 1, 3, r_rekap + 1, 5, s_cnt, fmt_val_rekap)
            ws.merge_range(r_rekap + 2, 3, r_rekap + 2, 5, tot, fmt_val_rekap)
            ws.merge_range(r_rekap + 3, 3, r_rekap + 3, 5, pct, fmt_pct_rekap)
                            
    return buffer


def generate_form_2026(df_hasil):
    """
    Fungsi penyusun Form Verifikasi 2026 yang mendeteksi seluruh TAF secara dinamis
    dan kini dilengkapi PEWARNAAN KHUSUS (Soft Tint) untuk unsur BASE, TEMPO, dan BECMG.
    """
    df_hasil['Datetime'] = pd.to_datetime(df_hasil['Waktu Aktual (UTC)'], errors='coerce')
    df_hasil['Tanggal'] = df_hasil['Datetime'].dt.day
    df_hasil['Jam'] = df_hasil['Datetime'].dt.hour
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        workbook = writer.book
        ws = workbook.add_worksheet('FORM VERIFIKASI')
        
        fmt_title = workbook.add_format({'bold': True, 'font_size': 11})
        fmt_h = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'bold': True, 'border': 1, 'bg_color': '#D9D9D9', 'font_size': 10})
        fmt_tgl = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': True, 'font_size': 11}) 
        
        # --- AMUNISI BARU: PALETTE WARNA SOFT BERDASARKAN GRUP TAF ---
        fmt_base = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_size': 10, 'bg_color': '#F8FAFC'}) # Putih/Slate Soft
        fmt_tempo = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_size': 10, 'bg_color': '#FFF9E6'}) # Kuning Pastel Soft
        fmt_becmg = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_size': 10, 'bg_color': '#F4EBF7'}) # Ungu Pastel Soft
        
        # Format Status B/S (Tetap dipertahankan warnanya agar kontras)
        fmt_hit = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': True, 'font_color': '#006100', 'bg_color': '#C6EFCE'})
        fmt_miss = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': True, 'font_color': '#9C0006', 'bg_color': '#FFC7CE'})
        
        ws.write("A1", "VERIFIKASI AERODROM FORECAST", fmt_title)
        ws.write("A2", "Instruksi Met./No.029/Verifikasi Prakiraan/I/88", fmt_title)
        
        ws.merge_range("A4:A5", "TGL", fmt_h)
        ws.merge_range("B4:B5", "WAKTU", fmt_h)
        ws.merge_range("C4:H4", "P R A K I R A A N (TAFOR)", fmt_h)
        ws.write_row("C5", ["A", "B", "C", "D", "E", "F"], fmt_h)
        ws.merge_range("I4:T4", "K E N Y A T A A N (METAR)", fmt_h)
        ws.write_row("I5", ["A", "H", "B", "H", "C", "H", "D", "H", "E", "H", "F", "H"], fmt_h)
        
        ws.set_column("A:A", 5)
        ws.set_column("B:B", 10)
        ws.set_column("C:H", 7)
        ws.set_column("I:T", 6)
        
        rekapan = {k: {'B': 0, 'S': 0} for k in ['A', 'B', 'C', 'D', 'E', 'F']}
        
        def tulis_baris(r_idx, label_wkt, tar, tke, tvi, twx, taj, tat, m_baris):
            # LOGIKA PEMILIHAN WARNA DINAMIS
            if label_wkt.startswith('T.'):
                fmt_aktif = fmt_tempo
            elif label_wkt.startswith('B.'):
                fmt_aktif = fmt_becmg
            else:
                fmt_aktif = fmt_base
                
            ws.write(r_idx, 1, label_wkt, fmt_aktif)
            ws.write_row(r_idx, 2, [tar, tke, tvi, twx, taj, tat], fmt_aktif)
            
            _, bs_ar = hitung_angin_arah(m_baris['M_Arah'], tar)
            _, bs_ke = hitung_angin_kec(m_baris['M_Kec'], tke)
            _, bs_vi = hitung_vis(m_baris['M_Vis'], tvi)
            _, bs_wx = hitung_cuaca(m_baris['M_Wx'], twx)
            _, bs_aj = hitung_awan_jml(m_baris['M_AwanJml'], taj)
            _, bs_at = hitung_awan_tgi(m_baris['M_AwanTgi'], tat)
            
            for k, s in zip(['A', 'B', 'C', 'D', 'E', 'F'], [bs_ar, bs_ke, bs_vi, bs_wx, bs_aj, bs_at]):
                if s in ['B', 'S']:
                    rekapan[k][s] += 1
            
            col_m = 8
            for val, stat in [
                (m_baris['M_Arah'], bs_ar), (m_baris['M_Kec'], bs_ke),
                (m_baris['M_Vis'], bs_vi), (m_baris['M_Wx'], bs_wx),
                (m_baris['M_AwanJml'], bs_aj), (m_baris['M_AwanTgi'], bs_at)
            ]:
                ws.write(r_idx, col_m, val, fmt_aktif)
                ws.write(r_idx, col_m+1, stat, fmt_hit if stat == "B" else fmt_miss)
                col_m += 2

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
                if sandi != "-" and sandi not in tafs_hari_ini:
                    tafs_hari_ini.append(sandi)
            
            if not tafs_hari_ini:
                ws.write(row_idx, 0, str(tgl).zfill(2), fmt_tgl)
                ws.write(row_idx, 1, "-", fmt_base)
                ws.write_row(row_idx, 2, ["-"]*18, fmt_base)
                row_idx += 1
                continue
                
            start_row_tgl = row_idx  
            
            for taf_sandi in tafs_hari_ini:
                baris_m_base = data_tgl_sorted[data_tgl_sorted['Sandi TAF Prakiraan'] == taf_sandi].iloc[0]
                
                parts = re.split(r'\b(BECMG|TEMPO)\b', str(taf_sandi))
                base_str = parts[0]
                base_time_match = re.search(r'(\d{2})(\d{2})/(\d{2})(\d{2})', base_str)
                if base_time_match:
                    s_hr = base_time_match.group(2)
                    e_hr = base_time_match.group(4)
                    if e_hr == "00" and base_time_match.group(1) != base_time_match.group(3):
                        e_hr = "24"
                    w_base = f"{s_hr} - {e_hr}"
                else:
                    w_base = "00 - 24"
                
                b_ar, b_ke, b_vi, b_wx, b_aj, b_at = parse_sandi(base_str)
                cur_ar, cur_ke, cur_vi, cur_wx, cur_aj, cur_at = b_ar, b_ke, b_vi, b_wx, b_aj, b_at
                
                tulis_baris(row_idx, w_base, b_ar, b_ke, b_vi, b_wx, b_aj, b_at, baris_m_base)
                row_idx += 1
                
                for i in range(1, len(parts), 2):
                    tipe = parts[i]
                    isi = parts[i+1]
                    
                    time_match = re.search(r'(\d{2})(\d{2})/(\d{2})(\d{2})', isi)
                    jam_target = 0
                    if time_match:
                        s_hr = time_match.group(2)
                        e_hr = time_match.group(4)
                        if e_hr == "00" and time_match.group(1) != time_match.group(3):
                            e_hr = "24"
                        label_w = f"{'B' if tipe=='BECMG' else 'T'}.{s_hr}-{e_hr}"
                        jam_target = int(s_hr)
                    else:
                        label_w = f"{'B' if tipe=='BECMG' else 'T'}.??"
                        
                    t_ar, t_ke, t_vi, t_wx, t_aj, t_at = parse_sandi(isi)
                    
                    if t_ar == "-": t_ar = cur_ar
                    if t_ke == "-": t_ke = cur_ke
                    if t_vi == "-": t_vi = cur_vi
                    if t_wx == "NIL" and not re.search(r'\b(HZ|RA|TSRA|BR|DZ|FG|VCTS|TS|SHRA|MIFG|SQ|FC)\b', isi) and "CAVOK" not in isi:
                        t_wx = cur_wx
                    if t_aj == "-": t_aj = cur_aj
                    if t_at == "-": t_at = cur_at
                    
                    data_jam = data_tgl_sorted[(data_tgl_sorted['Jam'] == jam_target) & (data_tgl_sorted['Sandi TAF Prakiraan'] == taf_sandi)]
                    baris_m_trend = data_jam.iloc[0] if not data_jam.empty else baris_m_base
                    
                    tulis_baris(row_idx, label_w, t_ar, t_ke, t_vi, t_wx, t_aj, t_at, baris_m_trend)
                    row_idx += 1
                    
                    if tipe == 'BECMG':
                        cur_ar, cur_ke, cur_vi, cur_wx, cur_aj, cur_at = t_ar, t_ke, t_vi, t_wx, t_aj, t_at
                        
            if row_idx - start_row_tgl > 1:
                ws.merge_range(start_row_tgl, 0, row_idx - 1, 0, str(tgl).zfill(2), fmt_tgl)
            else:
                ws.write(start_row_tgl, 0, str(tgl).zfill(2), fmt_tgl)
                
        # --- BLOK REKAPITULASI BAWAH ---
        row_idx += 1 
        
        fmt_label_rekap = workbook.add_format({'align': 'right', 'valign': 'vcenter', 'bold': True})
        fmt_val_rekap = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'bold': True, 'border': 1, 'bg_color': '#D9D9D9'})
        fmt_pct_rekap = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'bold': True, 'border': 1, 'bg_color': '#C6EFCE', 'num_format': '0.00"%"'})
        fmt_h_rekap = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'bold': True, 'border': 1, 'bg_color': '#F2F2F2', 'font_size': 9})
        fmt_total_final = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'bold': True, 'border': 1, 'bg_color': '#DEEBF7', 'num_format': '0.00"%"', 'font_size': 11})

        ws.merge_range(row_idx, 0, row_idx, 7, "NAMA PARAMETER : ", fmt_label_rekap)
        p_headers = {
            'A': 'A (Arah Wind)', 'B': 'B (Kec Wind)', 'C': 'C (Visibility)',
            'D': 'D (Cuaca)',     'E': 'E (Jml Awan)',  'F': 'F (Tgi Awan)'
        }
        col_m = 8
        for k in ['A', 'B', 'C', 'D', 'E', 'F']:
            ws.merge_range(row_idx, col_m, row_idx, col_m+1, p_headers[k], fmt_h_rekap)
            col_m += 2
            
        row_idx += 1 
        
        labels = ["JUMLAH BENAR (B) : ", "JUMLAH SALAH (S) : ", "TOTAL DATA : ", "PROSENTASE KETELITIAN : "]
        for i, label in enumerate(labels):
            ws.merge_range(row_idx + i, 0, row_idx + i, 7, label, fmt_label_rekap)
            
        total_benar_global = 0
        total_data_global = 0
            
        col_m = 8
        for k in ['A', 'B', 'C', 'D', 'E', 'F']:
            b_cnt = rekapan[k]['B']
            s_cnt = rekapan[k]['S']
            tot = b_cnt + s_cnt
            pct = (b_cnt / tot * 100) if tot > 0 else 0
            
            total_benar_global += b_cnt
            total_data_global += tot
            
            ws.merge_range(row_idx, col_m, row_idx, col_m+1, b_cnt, fmt_val_rekap)
            ws.merge_range(row_idx+1, col_m, row_idx+1, col_m+1, s_cnt, fmt_val_rekap)
            ws.merge_range(row_idx+2, col_m, row_idx+2, col_m+1, tot, fmt_val_rekap)
            ws.merge_range(row_idx+3, col_m, row_idx+3, col_m+1, pct, fmt_pct_rekap)
            
            col_m += 2
            
        row_idx += 5 
        ws.merge_range(row_idx, 0, row_idx, 7, "🔥 TOTAL AKURASI PRAKIRAAN GLOBAL (ALL PARAMETERS) : ", fmt_label_rekap)
        
        akurasi_global_final = (total_benar_global / total_data_global * 100) if total_data_global > 0 else 0
        ws.merge_range(row_idx, 8, row_idx, 19, akurasi_global_final, fmt_total_final)
                
    return buffer
