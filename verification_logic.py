import pandas as pd
import numpy as np
import re
from datetime import datetime, timedelta

# ==========================================
# 1. PARSER DATA MENTAH DENGAN DETEKSI GUST
# ==========================================

def ekstrak_param_metar_speci(sandi_teks):
    if pd.isna(sandi_teks) or sandi_teks == "-":
        return "-", "-", "-", "-", "-", "-"
    sandi = str(sandi_teks).strip()
    sandi_cleaned = re.sub(r'\b\d{4}/\d{4}\b', '', sandi)
    
    arah_wind, kec_wind = "-", "-"
    wind_match = re.search(r'\b(\d{3}|\/\/\/|VRB)(\d{2,3})(G\d{2,3})?KT\b', sandi_cleaned)
    if wind_match:
        arah_wind = wind_match.group(1)
        # Jika ada Gustiness (G), gabungkan ke string kecepatan (Contoh: 15G25)
        if wind_match.group(3):
            kec_wind = f"{int(wind_match.group(2))}G{int(wind_match.group(3)[1:])}"
        else:
            kec_wind = str(int(wind_match.group(2)))
        
    vis = "-"
    if "CAVOK" in sandi_cleaned: vis = "9999"
    else:
        vis_match = re.search(r'\b\d{4}\b', sandi_cleaned)
        if vis_match: vis = vis_match.group(0)
            
    wx = "-"
    if "CAVOK" in sandi_cleaned: wx = "-"
    else:
        wx_match = re.search(r'\b(MI|BC|PR|DR|BL|SH|TS|FZ)?(DZ|RA|SN|SG|PL|GR|GS|BR|FG|FU|VA|DU|SA|HZ|PO|SQ|FC|SS|DS)\b', sandi_cleaned)
        if wx_match: wx = wx_match.group(0)
            
    awan_jml, awan_tgi = "-", "-"
    if "CAVOK" in sandi_cleaned or "NSC" in sandi_cleaned or "NCD" in sandi_cleaned:
        awan_jml, awan_tgi = "NSC", "0"
    else:
        cloud_match = re.search(r'\b(FEW|SCT|BKN|OVC)(\d{3})\b', sandi_cleaned)
        if cloud_match:
            awan_jml = cloud_match.group(1)
            awan_tgi = str(int(cloud_match.group(2)) * 100)
            
    return arah_wind, kec_wind, vis, wx, awan_jml, awan_tgi

def parse_sandi(grup_teks):
    if not grup_teks or grup_teks.strip() == "":
        return "-", "-", "-", "-", "-", "-"
    sandi = str(grup_teks).strip()
    sandi_cleaned = re.sub(r'\b\d{4}/\d{4}\b', '', sandi)
    
    arah, kec = "-", "-"
    w_match = re.search(r'\b(\d{3}|VRB)(\d{2,3})(G\d{2,3})?KT\b', sandi_cleaned)
    if w_match:
        arah = w_match.group(1)
        if w_match.group(3):
            kec = f"{int(w_match.group(2))}G{int(w_match.group(3)[1:])}"
        else:
            kec = str(int(w_match.group(2)))
        
    vis = "-"
    if "CAVOK" in sandi_cleaned: vis = "9999"
    else:
        v_match = re.search(r'\b\d{4}\b', sandi_cleaned)
        if v_match: vis = v_match.group(0)
            
    wx = "-"
    if "CAVOK" in sandi_cleaned: wx = "-"
    elif "NSW" in sandi_cleaned: wx = "-"
    else:
        wx_match = re.search(r'\b(MI|BC|PR|DR|BL|SH|TS|FZ)?(DZ|RA|SN|SG|PL|GR|GS|BR|FG|FU|VA|DU|SA|HZ|PO|SQ|FC|SS|DS)\b', sandi_cleaned)
        if wx_match: wx = wx_match.group(0)
            
    aw_jml, aw_tgi = "-", "-"
    if "CAVOK" in sandi_cleaned: aw_jml, aw_tgi = "NSC", "0"
    else:
        c_match = re.search(r'\b(FEW|SCT|BKN|OVC)(\d{3})\b', sandi_cleaned)
        if c_match:
            aw_jml = c_match.group(1)
            aw_tgi = str(int(c_match.group(2)) * 100)
            
    return arah, kec, vis, wx, aw_jml, aw_tgi

# ==========================================
# 2. EVALUASI TOLERANSI ANGIN (KEC + GUST)
# ==========================================

def hitung_angin_arah(m_arah, t_arah):
    if m_arah == "-" or t_arah == "-": return "-", "NIL"
    if m_arah == "VRB" or t_arah == "VRB": return "0", "B"
    try:
        diff = abs(int(m_arah) - int(t_arah))
        if diff > 180: diff = 360 - diff
        return str(diff), ("B" if diff <= 60 else "S")
    except: return "-", "S"

def hitung_angin_kec(m_kec, t_kec):
    if m_kec == "-" or t_kec == "-": return "-", "NIL"
    try:
        # Pecah komponen Gustiness jika ada huruf 'G'
        m_base = int(m_kec.split('G')[0]) if 'G' in m_kec else int(m_kec)
        t_base = int(t_kec.split('G')[0]) if 'G' in t_kec else int(t_kec)
        
        m_gust = int(m_kec.split('G')[1]) if 'G' in m_kec else 0
        t_gust = int(t_kec.split('G')[1]) if 'G' in t_kec else 0
        
        # Validasi 1: Cek Angin Rata-rata (Toleransi 5 Knot)
        diff_base = abs(m_base - t_base)
        stat_base = "B" if diff_base <= 5 else "S"
        
        # Validasi 2 (Opsi 2): Penegakan Hukum Gustiness Penerbangan
        if m_gust > 0 or t_gust > 0:
            diff_gust = abs(m_gust - t_gust)
            # Salah jika salah satu luput meramal gust padahal terjadi, atau deviasi gust > 5 knot
            if (m_gust > 0 and t_gust == 0) or (m_gust == 0 and t_gust > 0) or (diff_gust > 5):
                return f"B:{diff_base}|G:{abs(m_gust-t_gust)}", "S"
                
        return str(diff_base), stat_base
    except: return "-", "S"

def hitung_vis(m_vis, t_vis):
    if m_vis == "-" or t_vis == "-": return "-", "NIL"
    try:
        mv, tv = int(m_vis), int(t_vis)
        if mv == 9999 and tv == 9999: return "0", "B"
        diff = abs(mv - tv)
        return str(diff), ("B" if diff <= 1000 else "S")
    except: return "-", "S"

def hitung_cuaca(m_wx, t_wx):
    if m_wx == "-" and t_wx == "-": return "MATCH", "B"
    if m_wx != "-" and t_wx == "-": return "MISS", "S"
    if m_wx == "-" and t_wx != "-": return "FALSE_ALARM", "S"
    return ("MATCH" if m_wx == t_wx else "DIFF"), ("B" if m_wx == t_wx else "S")

def hitung_awan_jml(m_jml, t_jml):
    if m_jml == "-" or t_jml == "-": return "-", "NIL"
    peta = {"NSC": 0, "NCD": 0, "FEW": 1, "SCT": 2, "BKN": 3, "OVC": 4}
    try:
        diff = abs(peta.get(m_jml, 0) - peta.get(t_jml, 0))
        return str(diff), ("B" if diff <= 1 else "S")
    except: return "-", "S"

def hitung_awan_tgi(m_tgi, t_tgi):
    if m_tgi == "-" or t_tgi == "-": return "-", "NIL"
    try:
        diff = abs(int(m_tgi) - int(t_tgi))
        return str(diff), ("B" if diff <= 300 else "S")
    except: return "-", "S"

def evaluasi_sandi_tunggal(m_obs_data, t_ar, t_ke, t_vi, t_wx, t_aj, t_at, base_data=None, is_prob=False):
    _, s_ar = hitung_angin_arah(m_obs_data['M_Arah'], t_ar)
    _, s_ke = hitung_angin_kec(m_obs_data['M_Kec'], t_ke)
    _, s_vi = hitung_vis(m_obs_data['M_Vis'], t_vi)
    _, s_wx = hitung_cuaca(m_obs_data['M_Wx'], t_wx)
    _, s_aj = hitung_awan_jml(m_obs_data['M_AwanJml'], t_aj)
    _, s_at = hitung_awan_tgi(m_obs_data['M_AwanTgi'], t_at)
    
    if is_prob and base_data is not None:
        _, b_ar = hitung_angin_arah(m_obs_data['M_Arah'], base_data[0])
        _, b_ke = hitung_angin_kec(m_obs_data['M_Kec'], base_data[1])
        _, b_vi = hitung_vis(m_obs_data['M_Vis'], base_data[2])
        _, b_wx = hitung_cuaca(m_obs_data['M_Wx'], base_data[3])
        _, b_aj = hitung_awan_jml(m_obs_data['M_AwanJml'], base_data[4])
        _, b_at = hitung_awan_tgi(m_obs_data['M_AwanTgi'], base_data[5])
        
        if s_ar == "S" and b_ar == "B": s_ar = "B"
        if s_ke == "S" and b_ke == "B": s_ke = "B"
        if s_vi == "S" and b_vi == "B": s_vi = "B"
        if s_wx == "S" and b_wx == "B": s_wx = "B"
        if s_aj == "S" and b_aj == "B": s_aj = "B"
        if s_at == "S" and b_at == "B": s_at = "B"

    stat_akhir = "S" if 'S' in [s_ar, s_ke, s_vi, s_wx, s_aj, s_at] else "B"
    return stat_akhir, s_ar, s_ke, s_vi, s_wx, s_aj, s_at

# ==========================================
# 3. KONTROLLER SINKRONISASI KRONOLOGIS
# ==========================================

def proses_verifikasi(df_metar, df_taf, df_speci):
    df_metar.columns = df_metar.columns.str.strip()
    df_taf.columns = df_taf.columns.str.strip()
    df_speci.columns = df_speci.columns.str.strip()
    
    col_waktu = next((c for c in df_metar.columns if any(k in c.lower() for k in ['waktu', 'date', 'tanggal', 'time'])), df_metar.columns[0])
    col_teks = next((c for c in df_metar.columns if 'type' not in c.lower() and 'status' not in c.lower() and any(k in c.lower() for k in ['sandi', 'text', 'message', 'report', 'isi'])), df_metar.columns[1])

    df_metar['dt_obj'] = pd.to_datetime(df_metar[col_waktu].astype(str).str.slice(0, 19), errors='coerce')
    df_taf['dt_obj'] = pd.to_datetime(df_taf[col_waktu].astype(str).str.slice(0, 19), errors='coerce')
    df_speci['dt_obj'] = pd.to_datetime(df_speci[col_waktu].astype(str).str.slice(0, 19), errors='coerce')
    
    df_metar = df_metar.dropna(subset=['dt_obj']).sort_values('dt_obj')
    df_taf = df_taf.dropna(subset=['dt_obj']).sort_values('dt_obj')
    df_speci = df_speci.dropna(subset=['dt_obj']).sort_values('dt_obj')
    
    baris_analisis_final = []
    baris_speci_final = []
    
    for _, metar_row in df_metar.iterrows():
        tgl_jam_aktual = metar_row['dt_obj']
        teks_metar = metar_row[col_teks]
        m_ar, m_ke, m_vi, m_wx, m_aj, m_at = ekstrak_param_metar_speci(teks_metar)
        
        taf_aktif = "-"
        taf_terpilih_rows = df_taf[df_taf['dt_obj'] <= tgl_jam_aktual]
        if not taf_terpilih_rows.empty: taf_aktif = taf_terpilih_rows.iloc[-1][col_teks]
        if taf_aktif == "-": continue
            
        speci_terkait = df_speci[(df_speci['dt_obj'] >= tgl_jam_aktual) & (df_speci['dt_obj'] <= tgl_jam_aktual + timedelta(minutes=59))]
        
        parts = re.split(r'\b(BECMG|TEMPO|PROB30 TEMPO|PROB40 TEMPO|PROB30|PROB40)\b', str(taf_aktif))
        base_str = parts[0]
        b_ar, b_ke, b_vi, b_wx, b_aj, b_at = parse_sandi(base_str)
        cur_ar, cur_ke, cur_vi, cur_wx, cur_aj, cur_at = b_ar, b_ke, b_vi, b_wx, b_aj, b_at
        
        t_ar, t_ke, t_vi, t_wx, t_aj, t_at = b_ar, b_ke, b_vi, b_wx, b_aj, b_at
        is_grup_prob = False
        
        target_hour = tgl_jam_aktual.hour
        for i in range(1, len(parts), 2):
            tipe, isi = parts[i], parts[i+1]
            time_match = re.search(r'(\d{2})(\d{2})/(\d{2})(\d{2})', isi)
            if time_match:
                s_hr, e_hr = int(time_match.group(2)), int(time_match.group(4))
                if e_hr == 0: e_hr = 24
                if s_hr <= target_hour < e_hr:
                    g_ar, g_ke, g_vi, g_wx, g_aj, g_at = parse_sandi(isi)
                    if g_ar != "-": t_ar = g_ar
                    if g_ke != "-": t_ke = g_ke
                    if g_vi != "-": t_vi = g_vi
                    if g_wx != "NIL" and not re.search(r'\b(HZ|RA|TSRA|BR|DZ|FG|VCTS|TS|SHRA|MIFG|SQ|FC)\b', isi) and "CAVOK" not in isi: t_wx = g_wx
                    if g_aj != "-": t_aj = g_aj
                    if g_at != "-": t_at = g_at
                    
                    if 'PROB' in tipe: is_grup_prob = True
                    if tipe == 'BECMG': cur_ar, cur_ke, cur_vi, cur_wx, cur_aj, cur_at = t_ar, t_ke, t_vi, t_wx, t_aj, t_at
                        
        m_obs_data = {'M_Arah': m_ar, 'M_Kec': m_ke, 'M_Vis': m_vi, 'M_Wx': m_wx, 'M_AwanJml': m_aj, 'M_AwanTgi': m_at}
        base_bundle = (cur_ar, cur_ke, cur_vi, cur_wx, cur_aj, cur_at)
        
        status_jam_ini, s_ar, s_ke, s_vi, s_wx, s_aj, s_at = evaluasi_sandi_tunggal(m_obs_data, t_ar, t_ke, t_vi, t_wx, t_aj, t_at, base_bundle, is_grup_prob)
        
        if not speci_terkait.empty:
            for _, speci_row in speci_terkait.iterrows():
                sp_ar, sp_ke, sp_vi, sp_wx, sp_aj, sp_at = ekstrak_param_metar_speci(speci_row[col_teks])
                sp_obs_data = {'M_Arah': sp_ar, 'M_Kec': sp_ke, 'M_Vis': sp_vi, 'M_Wx': sp_wx, 'M_AwanJml': sp_aj, 'M_AwanTgi': sp_at}
                status_speci, sp_s_ar, sp_s_ke, sp_s_vi, sp_s_wx, sp_s_aj, sp_s_at = evaluasi_sandi_tunggal(sp_obs_data, t_ar, t_ke, t_vi, t_wx, t_aj, t_at, base_bundle, is_grup_prob)
                
                if status_speci == "S":
                    status_jam_ini = "S"
                    if sp_s_ar == "S": s_ar = "S"
                    if sp_s_ke == "S": s_ke = "S"
                    if sp_s_vi == "S": s_vi = "S"
                    if sp_s_wx == "S": s_wx = "S"
                    if sp_s_aj == "S": s_aj = "S"
                    if sp_s_at == "S": s_at = "S"
                    
                baris_speci_final.append({
                    'Waktu SPECI (UTC)': speci_row['dt_obj'].strftime('%Y-%m-%d %H:%M:%S'),
                    'Sandi SPECI': speci_row[col_teks], 'TAFOR Berlaku': taf_aktif,
                    'M_Arah': sp_ar, 'T_Arah': t_ar, 'S_Arah': sp_s_ar,
                    'M_Kec': sp_ke, 'T_Kec': t_ke, 'S_Kec': sp_s_ke,
                    'M_Vis': sp_vi, 'T_Vis': t_vi, 'S_Vis': sp_s_vi,
                    'M_Wx': sp_wx, 'T_Wx': t_wx, 'S_Wx': sp_s_wx,
                    'M_AwanJml': sp_aj, 'T_AwanJml': t_aj, 'S_AwanJml': sp_s_aj,
                    'M_AwanTgi': sp_at, 'T_AwanTgi': t_at, 'S_AwanTgi': sp_s_at,
                    'Hasil Akhir': "ACCURATE" if status_speci == "B" else "MISS"
                })
                    
        baris_analisis_final.append({
            'Waktu Aktual (UTC)': tgl_jam_aktual.strftime('%Y-%m-%d %H:%M:%S'),
            'Sandi METAR Aktual': teks_metar, 'Sandi TAF Prakiraan': taf_aktif,
            'M_Arah': m_ar, 'T_Arah': t_ar, 'D_Arah': "-", 'S_Arah': s_ar,
            'M_Kec': m_ke, 'T_Kec': t_ke, 'D_Kec': "-", 'S_Kec': s_ke,
            'M_Vis': m_vi, 'T_Vis': t_vi, 'D_Vis': "-", 'S_Vis': s_vi,
            'M_Wx': m_wx, 'T_Wx': t_wx, 'D_Wx': "-", 'S_Wx': s_wx,
            'M_AwanJml': m_aj, 'T_AwanJml': t_aj, 'D_AwanJml': "-", 'S_AwanJml': s_aj,
            'M_AwanTgi': m_at, 'T_AwanTgi': t_at, 'D_AwanTgi': "-", 'S_AwanTgi': s_at,
            'Hasil Akhir': "ACCURATE" if status_jam_ini == "B" else "MISS"
        })
        
    return pd.DataFrame(baris_analisis_final), pd.DataFrame(baris_speci_final), None, None
