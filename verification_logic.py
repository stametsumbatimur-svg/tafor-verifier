import pandas as pd
import numpy as np
import re
import math
import sqlite3
from datetime import datetime, timedelta

# =========================================================================
# 1. ROBUST TEXT PARSER — KEBAL TEXT ADMINISTRATIVE (AUTO, COR, AMD)
# =========================================================================

def ekstrak_param_metar_speci(sandi_teks):
    if pd.isna(sandi_teks) or sandi_teks == "-":
        return "-", "-", "-", "-", "-", "-", False
    sandi = str(sandi_teks).strip()
    sandi_cleaned = re.sub(r'\b\d{4}/\d{4}\b', '', sandi)
    
    arah_wind, kec_wind = "-", "-"
    wind_match = re.search(r'\b(\d{3}|\/\/\/|VRB|000)(\d{2,3})(G\d{2,3})?KT\b', sandi_cleaned)
    if wind_match:
        arah_wind = wind_match.group(1)
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
        wx_match = re.search(r'(?<![A-Z])[-+]?(?:MI|BC|PR|DR|BL|SH|TS|FZ)?(?:DZ|RA|SN|SG|PL|GR|GS|BR|FG|FU|VA|DU|SA|HZ|PO|SQ|FC|SS|DS|TS)\b', sandi_cleaned)
        if wx_match: wx = wx_match.group(0)
            
    awan_jml, awan_tgi = "-", "-"
    if "CAVOK" in sandi_cleaned or "NSC" in sandi_cleaned or "NCD" in sandi_cleaned:
        awan_jml, awan_tgi = "NSC", "0"
    else:
        cloud_matches = re.findall(r'\b(FEW|SCT|BKN|OVC)(\d{3,4})(?:CB|TCU)?\b', sandi_cleaned)
        if cloud_matches:
            terendah = min(cloud_matches, key=lambda x: int(x[1]))
            awan_jml = terendah[0]
            awan_tgi = str(int(terendah[1]) * 100)
            
    # SIVETA LOGIC: Deteksi TS atau CB pada observasi
    has_ts_cb = 'TS' in sandi_cleaned or 'CB' in sandi_cleaned
            
    return arah_wind, kec_wind, vis, wx, awan_jml, awan_tgi, has_ts_cb

def parse_sandi(grup_teks):
    if not grup_teks or grup_teks.strip() == "":
        return "-", "-", "-", "-", "-", "-"
    sandi = str(grup_teks).strip()
    sandi_cleaned = re.sub(r'\b\d{4}/\d{4}\b', '', sandi)
    
    arah, kec = "-", "-"
    w_match = re.search(r'\b(\d{3}|VRB|000)(\d{2,3})(G\d{2,3})?KT\b', sandi_cleaned)
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
        wx_match = re.search(r'(?<![A-Z])[-+]?(?:MI|BC|PR|DR|BL|SH|TS|FZ)?(?:DZ|RA|SN|SG|PL|GR|GS|BR|FG|FU|VA|DU|SA|HZ|PO|SQ|FC|SS|DS|TS)\b', sandi_cleaned)
        if wx_match: wx = wx_match.group(0)
            
    aw_jml, aw_tgi = "-", "-"
    if "CAVOK" in sandi_cleaned: aw_jml, aw_tgi = "NSC", "0"
    else:
        c_matches = re.findall(r'\b(FEW|SCT|BKN|OVC)(\d{3,4})\b', sandi_cleaned)
        if c_matches:
            terendah = min(c_matches, key=lambda x: int(x[1]))
            aw_jml = terendah[0]
            aw_tgi = str(int(terendah[1]) * 100)
            
    return arah, kec, vis, wx, aw_jml, aw_tgi

# =========================================================================
# 2. EVALUASI AKURASI PARAMETER (LOGIKA SIVETA)
# =========================================================================

def hitung_angin_arah(m_dir, t_dir, m_kec="-", t_kec="-", m_ts_cb=False):
    m_str, t_str = str(m_dir).strip().upper(), str(t_dir).strip().upper()
    
    m_spd = int(str(m_kec).split('G')[0]) if 'G' in str(m_kec) and str(m_kec) != "-" else (int(m_kec) if str(m_kec).isdigit() else 0)
    t_spd = int(str(t_kec).split('G')[0]) if 'G' in str(t_kec) and str(t_kec) != "-" else (int(t_kec) if str(t_kec).isdigit() else 0)

    # 1. Sama persis
    if m_str == t_str: return (m_str, "B")
    
    # 2. VRB di Forecast & VRB di Pengamatan
    if m_str in ["VRB", "///"] and t_str in ["VRB", "///"]: return (m_str, "B")
    
    # 3. SIVETA LOGIC: Forecast VRB, Pengamatan ada TS / CB
    if t_str == "VRB" and m_ts_cb: return (m_str, "B")
    
    # 4. SIVETA LOGIC: Forecast VRB, Pengamatan Kec < 10 knot
    if t_str == "VRB" and m_spd < 10: return (m_str, "B")
    
    # 5. Kecepatan angin pengamatan & forecast keduanya < 10 knot (arah bebas)
    if m_spd < 10 and t_spd < 10: return (m_str, "B")
        
    try:
        m, t = int(m_str), int(t_str)
        diff = abs(m - t)
        diff = diff if diff <= 180 else 360 - diff
        
        # 6. SIVETA LOGIC: Selisih <= 60 ATAU (Selisih > 60 tetapi Kec Aktual < 10)
        if diff <= 60 or (diff > 60 and m_spd < 10):
            return (m_str, "B")
        else:
            return (m_str, "S")
    except:
        return (m_str, "S")

def hitung_angin_kec(m_kec, t_kec):
    if m_kec == "-" or t_kec == "-" or m_kec == "NIL" or t_kec == "NIL": return "-", "NIL"
    try:
        m_base = int(m_kec.split('G')[0]) if 'G' in m_kec else int(m_kec)
        t_base = int(t_kec.split('G')[0]) if 'G' in t_kec else int(t_kec)
        m_gust = int(m_kec.split('G')[1]) if 'G' in m_kec else 0
        t_gust = int(t_kec.split('G')[1]) if 'G' in t_kec else 0
        
        diff_base = abs(m_base - t_base)
        stat_base = "B" if diff_base <= 10 else "S"
        
        has_m_gust, has_t_gust = m_gust > 0, t_gust > 0
        if has_m_gust != has_t_gust:
            return f"B:{diff_base}|G:{abs(m_gust-t_gust)}", "S"
            
        return str(diff_base), stat_base
    except: return "-", "S"

def get_vis_class(vis_value):
    if vis_value < 800: return 1
    elif 800 <= vis_value < 1500: return 2
    elif 1500 <= vis_value < 3000: return 3
    elif 3000 <= vis_value < 5000: return 4
    else: return 5

def hitung_vis(m_vis, t_vis):
    try:
        m, t = int(m_vis), int(t_vis)
        return (m, "B") if get_vis_class(m) == get_vis_class(t) else (m, "S")
    except:
        return (None, "S")

def cek_presipitasi_sedang_lebat(wx_str):
    if pd.isna(wx_str) or wx_str == "-": return False
    wx_str = str(wx_str).upper()
    return True if 'RA' in wx_str and '-RA' not in wx_str else False

def hitung_cuaca(m_wx, t_wx):
    m_heavy = cek_presipitasi_sedang_lebat(m_wx)
    t_heavy = cek_presipitasi_sedang_lebat(t_wx)
    return "MATCH", ("B" if m_heavy == t_heavy else "S")

def klasifikasi_jumlah_awan(amt_string):
    if not amt_string or amt_string == "-": return 1
    return 2 if str(amt_string).upper() in ['BKN', 'OVC'] else 1

def hitung_awan_jml(m_jml, t_jml, m_tgi):
    if m_jml == "-" or t_jml == "-": return "-", "NIL"
    try:
        if m_tgi != "-" and int(m_tgi) > 5000: return ">5000ft", "B"
        km = klasifikasi_jumlah_awan(m_jml)
        kt = klasifikasi_jumlah_awan(t_jml)
        return f"K:{km}vs{kt}", ("B" if km == kt else "S")
    except: return "-", "S"

def hitung_awan_tgi(m_tgi, t_tgi):
    if m_tgi == "-" or t_tgi == "-": return "-", "NIL"
    try:
        mt, tt = int(m_tgi), int(t_tgi)
        diff = abs(mt - tt)
        stat = "B" if (diff <= 100 if mt < 1000 else diff <= (0.3 * mt)) else "S"
        return str(diff), stat
    except: return "-", "S"

# =========================================================================
# 3. KONTROLLER UTAMA VERIFIKASI (MENGGUNAKAN MESIN ORIGINAL LAMA)
# =========================================================================

def evaluasi_sandi_tunggal(m_obs_data, t_ar, t_ke, t_vi, t_wx, t_aj, t_at, base_bundle=None, is_grup_prob=False, is_grup_tempo=False, is_grup_becmg_trans=False):
    # Parameter m_ts_cb dikirim ke hitung_angin_arah
    has_ts_cb = m_obs_data.get('M_TS_CB', False)
    
    _, s_ar = hitung_angin_arah(m_obs_data['M_Arah'], t_ar, m_obs_data['M_Kec'], t_ke, has_ts_cb)
    _, s_ke = hitung_angin_kec(m_obs_data['M_Kec'], t_ke)
    _, s_vi = hitung_vis(m_obs_data['M_Vis'], t_vi)
    _, s_wx = hitung_cuaca(m_obs_data['M_Wx'], t_wx)
    _, s_aj = hitung_awan_jml(m_obs_data['M_AwanJml'], t_aj, m_obs_data['M_AwanTgi'])
    _, s_at = hitung_awan_tgi(m_obs_data['M_AwanTgi'], t_at)
    
    if (is_grup_prob or is_grup_tempo or is_grup_becmg_trans) and base_bundle is not None:
        _, b_ar = hitung_angin_arah(m_obs_data['M_Arah'], base_bundle[0], m_obs_data['M_Kec'], base_bundle[1], has_ts_cb)
        _, b_ke = hitung_angin_kec(m_obs_data['M_Kec'], base_bundle[1])
        _, b_vi = hitung_vis(m_obs_data['M_Vis'], base_bundle[2])
        _, b_wx = hitung_cuaca(m_obs_data['M_Wx'], base_bundle[3])
        _, b_aj = hitung_awan_jml(m_obs_data['M_AwanJml'], base_bundle[4], m_obs_data['M_AwanTgi'])
        _, b_at = hitung_awan_tgi(m_obs_data['M_AwanTgi'], base_bundle[5])
        
        if s_ar == "S" and b_ar == "B": s_ar = "B"
        if s_ke == "S" and b_ke == "B": s_ke = "B"
        if s_vi == "S" and b_vi == "B": s_vi = "B"
        if s_wx == "S" and b_wx == "B": s_wx = "B"
        if s_aj == "S" and b_aj == "B": s_aj = "B"
        if s_at == "S" and b_at == "B": s_at = "B"

    stat_akhir = "S" if 'S' in [s_ar, s_ke, s_vi, s_wx, s_aj, s_at] else "B"
    return stat_akhir, s_ar, s_ke, s_vi, s_wx, s_aj, s_at

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
    
    speci_dict = {}
    for _, row in df_speci.iterrows():
        if pd.notna(row['dt_obj']):
            tgl_d = row['dt_obj'].date()
            if tgl_d not in speci_dict:
                speci_dict[tgl_d] = []
            speci_dict[tgl_d].append(row)
    
    for _, metar_row in df_metar.iterrows():
        tgl_jam_aktual = metar_row['dt_obj']
        teks_metar = metar_row[col_teks]
        m_stasiun = metar_row['cccc'] if 'cccc' in df_metar.columns else "WATU"
        
        # Ekstrak 7 Variabel (SIVETA)
        m_ar, m_ke, m_vi, m_wx, m_aj, m_at, m_ts_cb = ekstrak_param_metar_speci(teks_metar)
        
        taf_aktif = "-"
        
        taf_kandidat = df_taf[df_taf['dt_obj'] <= tgl_jam_aktual]
        if not taf_kandidat.empty:
            valid_tafs = []
            for _, tr in taf_kandidat.iterrows():
                t_teks = str(tr[col_teks])
                t_issue = tr['dt_obj']
                
                v_match = re.search(r'\d{6}Z\s+(\d{2})(\d{2})/\d{4}', t_teks)
                if v_match:
                    v_tgl, v_jam = int(v_match.group(1)), int(v_match.group(2))
                    try:
                        v_dt = tgl_jam_aktual.replace(day=v_tgl, hour=v_jam, minute=0, second=0)
                    except ValueError:
                        v_dt = t_issue
                        
                    # SIVETA LOGIC (POIN 3): TAF Hanya valid pada radius 12 Jam Pertama
                    if v_dt <= tgl_jam_aktual < v_dt + timedelta(hours=12):
                        poin_prioritas = 1 if re.search(r'\b(AMD|COR)\b', t_teks) else 0
                        valid_tafs.append((v_dt, t_issue, poin_prioritas, t_teks))
                else:
                    valid_tafs.append((t_issue, t_issue, 0, t_teks))
                    
            if valid_tafs:
                valid_tafs.sort(key=lambda x: (x[0], x[1], x[2]))
                taf_aktif = valid_tafs[-1][3] 
                
        if taf_aktif == "-": continue
            
        tgl_curr = tgl_jam_aktual.date()
        kandidat_speci = speci_dict.get(tgl_curr, []) + speci_dict.get(tgl_curr + timedelta(days=1), [])
        
        speci_terkait = [
            sp for sp in kandidat_speci 
            if tgl_jam_aktual <= sp['dt_obj'] <= tgl_jam_aktual + timedelta(minutes=59)
        ]
        
        parts = re.split(r'\b(BECMG|TEMPO|PROB30 TEMPO|PROB40 TEMPO|PROB30|PROB40)\b', str(taf_aktif))
        base_str = parts[0]
        b_ar, b_ke, b_vi, b_wx, b_aj, b_at = parse_sandi(base_str)
        cur_ar, cur_ke, cur_vi, cur_wx, cur_aj, cur_at = b_ar, b_ke, b_vi, b_wx, b_aj, b_at
        
        t_ar, t_ke, t_vi, t_wx, t_aj, t_at = b_ar, b_ke, b_vi, b_wx, b_aj, b_at
        is_grup_prob = False
        is_grup_tempo = False
        is_grup_becmg_trans = False
        
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
                    if 'TEMPO' in tipe: is_grup_tempo = True
                    if tipe == 'BECMG':
                        is_grup_becmg_trans = True
                        cur_ar, cur_ke, cur_vi, cur_wx, cur_aj, cur_at = t_ar, t_ke, t_vi, t_wx, t_aj, t_at
                        
        m_obs_data = {'M_Arah': m_ar, 'M_Kec': m_ke, 'M_Vis': m_vi, 'M_Wx': m_wx, 'M_AwanJml': m_aj, 'M_AwanTgi': m_at, 'M_TS_CB': m_ts_cb}
        base_bundle = (cur_ar, cur_ke, cur_vi, cur_wx, cur_aj, cur_at)
        
        status_jam_ini, s_ar, s_ke, s_vi, s_wx, s_aj, s_at = evaluasi_sandi_tunggal(
            m_obs_data, t_ar, t_ke, t_vi, t_wx, t_aj, t_at, base_bundle, is_grup_prob, is_grup_tempo, is_grup_becmg_trans
        )
        
        m_cw = 0.0
        t_cw = 0.0
        
        is_crit = "NORMAL"
        try:
            if int(m_vi) < 5000 or (m_aj in ["BKN", "OVC"] and int(m_at) < 1500):
                is_crit = "CRITICAL MINIMA"
        except: pass

        if speci_terkait:
            for speci_row in speci_terkait:
                sp_ar, sp_ke, sp_vi, sp_wx, sp_aj, sp_at, sp_ts_cb = ekstrak_param_metar_speci(speci_row[col_teks])
                sp_obs_data = {'M_Arah': sp_ar, 'M_Kec': sp_ke, 'M_Vis': sp_vi, 'M_Wx': sp_wx, 'M_AwanJml': sp_aj, 'M_AwanTgi': sp_at, 'M_TS_CB': sp_ts_cb}
                status_speci, sp_s_ar, sp_s_ke, sp_s_vi, sp_s_wx, sp_s_aj, sp_s_at = evaluasi_sandi_tunggal(
                    sp_obs_data, t_ar, t_ke, t_vi, t_wx, t_aj, t_at, base_bundle, is_grup_prob, is_grup_tempo, is_grup_becmg_trans
                )
                
                if status_speci == "S":
                    status_jam_ini = "S"
                    if sp_s_ar == "S": s_ar = "S"
                    if sp_s_ke == "S": s_ke = "S"
                    if sp_s_vi == "S": s_vi = "S"
                    if sp_s_wx == "S": s_wx = "S"
                    if sp_s_aj == "S": s_aj = "S"
                    if sp_s_at == "S": s_at = "S"
                
                try:
                    if int(sp_vi) < 5000 or (sp_aj in ["BKN", "OVC"] and int(sp_at) < 1500): is_crit = "CRITICAL MINIMA"
                except: pass
                    
                baris_speci_final.append({
                    'Waktu SPECI (UTC)': speci_row['dt_obj'].strftime('%Y-%m-%d %H:%M:%S'),
                    'Sandi SPECI':       speci_row[col_teks], 'TAFOR Berlaku': taf_aktif,
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
            'M_Crosswind_Knot': m_cw, 'T_Crosswind_Knot': t_cw, 'Status_Minima': is_crit,
            'Hasil Akhir': "ACCURATE" if status_jam_ini == "B" else "MISS",
            'Kode_Stasiun': m_stasiun
        })
        
    return pd.DataFrame(baris_analisis_final), pd.DataFrame(baris_speci_final), None, None

def hitung_verifikasi_TAFOR(df_input):
    df_work = df_input.copy()
    df_work['Bulan_Tahun'] = pd.to_datetime(df_work['Waktu Aktual (UTC)']).dt.strftime('%Y-%m')
    df_work['Tanggal'] = pd.to_datetime(df_work['Waktu Aktual (UTC)']).dt.day
    df_work['Jam'] = pd.to_datetime(df_work['Waktu Aktual (UTC)']).dt.hour
    rekapan = {k: {'B': 0, 'S': 0} for k in ['A', 'B', 'C', 'D', 'E', 'F']}
    
    for bln_thn in df_work['Bulan_Tahun'].unique():
        df_bulan = df_work[df_work['Bulan_Tahun'] == bln_thn]
        
        for tgl in range(1, 32):
            data_tgl = df_bulan[df_bulan['Tanggal'] == tgl]
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
                
                b_ar, b_ke, b_vi, b_wx, b_aj, b_at = parse_sandi(parts[0])
                cur_ar, cur_ke, cur_vi, cur_wx, cur_aj, cur_at = b_ar, b_ke, b_vi, b_wx, b_aj, b_at
                
                m_obs_base = {'M_Arah': baris_m_base['M_Arah'], 'M_Kec': baris_m_base['M_Kec'], 'M_Vis': baris_m_base['M_Vis'], 'M_Wx': baris_m_base['M_Wx'], 'M_AwanJml': baris_m_base['M_AwanJml'], 'M_AwanTgi': baris_m_base['M_AwanTgi'], 'M_TS_CB': False}
                _, s_ar, s_ke, s_vi, s_wx, s_aj, s_at = evaluasi_sandi_tunggal(m_obs_base, b_ar, b_ke, b_vi, b_wx, b_aj, b_at)
                
                for k, stat in zip(['A','B','C','D','E','F'], [s_ar, s_ke, s_vi, s_wx, s_aj, s_at]):
                    if stat in ['B', 'S']: rekapan[k][stat] += 1
                        
                for i in range(1, len(parts), 2):
                    tipe, isi = parts[i], parts[i+1]
                    time_match = re.search(r'(\d{2})(\d{2})/(\d{2})(\d{2})', isi)
                    jam_target = int(time_match.group(2)) if time_match else 0
                    
                    data_jam = data_tgl_sorted[(data_tgl_sorted['Jam'] == jam_target) & (data_tgl_sorted['Sandi TAF Prakiraan'] == taf_sandi)]
                    baris_m_trend = data_jam.iloc[0] if not data_jam.empty else baris_m_base
                    
                    t_ar, t_ke, t_vi, t_wx, t_aj, t_at = parse_sandi(isi)
                    if t_ar == "-": t_ar = cur_ar
                    if t_ke == "-": t_ke = cur_ke
                    if t_vi == "-": t_vi = cur_vi
                    if t_wx == "NIL" and not re.search(r'\b(HZ|RA|TSRA|BR|DZ|FG|VCTS|TS|SHRA|MIFG|SQ|FC)\b', isi) and "CAVOK" not in isi: t_wx = cur_wx
                    if t_aj == "-": t_aj = cur_aj
                    if t_at == "-": t_at = cur_at
                    
                    m_obs_trend = {'M_Arah': baris_m_trend['M_Arah'], 'M_Kec': baris_m_trend['M_Kec'], 'M_Vis': baris_m_trend['M_Vis'], 'M_Wx': baris_m_trend['M_Wx'], 'M_AwanJml': baris_m_trend['M_AwanJml'], 'M_AwanTgi': baris_m_trend['M_AwanTgi'], 'M_TS_CB': False}
                    
                    _, s_ar_t, s_ke_t, s_vi_t, s_wx_t, s_aj_t, s_at_t = evaluasi_sandi_tunggal(
                        m_obs_trend, t_ar, t_ke, t_vi, t_wx, t_aj, t_at, 
                        base_bundle=(cur_ar, cur_ke, cur_vi, cur_wx, cur_aj, cur_at), 
                        is_grup_prob=('PROB' in tipe), is_grup_tempo=('TEMPO' in tipe), is_grup_becmg_trans=('BECMG' in tipe)
                    )
                    
                    for k, stat in zip(['A','B','C','D','E','F'], [s_ar_t, s_ke_t, s_vi_t, s_wx_t, s_aj_t, s_at_t]):
                        if stat in ['B', 'S']: rekapan[k][stat] += 1
                        
                    if tipe == 'BECMG':
                        cur_ar, cur_ke, cur_vi, cur_wx, cur_aj, cur_at = t_ar, t_ke, t_vi, t_wx, t_aj, t_at
                        
    return rekapan
