import pandas as pd
import numpy as np
import re
import math
import sqlite3
from datetime import datetime, timedelta

# =========================================================================
# 0. PRA-KOMPILASI REGEX (SUPER KILAT)
# =========================================================================
RE_DATE_CLEAN = re.compile(r'\b\d{4}/\d{4}\b')
RE_WIND = re.compile(r'\b(\d{3}|\/\/\/|VRB|000)(\d{2,3})(G\d{2,3})?KT\b')
RE_VIS = re.compile(r'\b\d{4}\b')
RE_WX = re.compile(r'(?<![A-Z])[-+]?(?:MI|BC|PR|DR|BL|SH|TS|FZ)?(?:DZ|RA|SN|SG|PL|GR|GS|BR|FG|FU|VA|DU|SA|HZ|PO|SQ|FC|SS|DS|TS)\b')
RE_CLOUD = re.compile(r'\b(FEW|SCT|BKN|OVC)(\d{3,4})(?:CB|TCU)?\b')
RE_PARTS = re.compile(r'\b(BECMG|TEMPO|PROB30 TEMPO|PROB40 TEMPO|PROB30|PROB40|FM\d{6})\b')
RE_TIME_GRP = re.compile(r'(\d{2})(\d{2})/(\d{2})(\d{2})')
RE_WX_EXCLUDE = re.compile(r'\b(HZ|RA|TSRA|BR|DZ|FG|VCTS|TS|SHRA|MIFG|SQ|FC)\b')
RE_VALID_TAF = re.compile(r'\d{6}Z\s+(\d{2})(\d{2})/\d{4}')
RE_AMD_COR = re.compile(r'\b(AMD|COR)\b')

# =========================================================================
# 1. ROBUST TEXT PARSER
# =========================================================================
def ekstrak_param_metar_speci(sandi_teks):
    if pd.isna(sandi_teks) or sandi_teks == "-":
        return "-", "-", "-", "-", "-", "-", False
    sandi_cleaned = RE_DATE_CLEAN.sub('', str(sandi_teks).strip())
    
    arah_wind, kec_wind = "-", "-"
    wind_match = RE_WIND.search(sandi_cleaned)
    if wind_match:
        arah_wind = wind_match.group(1)
        kec_wind = f"{int(wind_match.group(2))}G{int(wind_match.group(3)[1:])}" if wind_match.group(3) else str(int(wind_match.group(2)))
        
    vis = "9999" if "CAVOK" in sandi_cleaned else ("-" if not (v := RE_VIS.search(sandi_cleaned)) else v.group(0))
    wx = "-" if "CAVOK" in sandi_cleaned else ("-" if not (w := RE_WX.search(sandi_cleaned)) else w.group(0))
            
    awan_jml, awan_tgi = "-", "-"
    if any(k in sandi_cleaned for k in ["CAVOK", "NSC", "NCD"]):
        awan_jml, awan_tgi = "NSC", "0"
    else:
        cloud_matches = RE_CLOUD.findall(sandi_cleaned)
        if cloud_matches:
            terendah = min(cloud_matches, key=lambda x: int(x[1]))
            awan_jml, awan_tgi = terendah[0], str(int(terendah[1]) * 100)
            
    has_ts_cb = 'TS' in sandi_cleaned or 'CB' in sandi_cleaned
    return arah_wind, kec_wind, vis, wx, awan_jml, awan_tgi, has_ts_cb

def parse_sandi(grup_teks):
    if not grup_teks or str(grup_teks).strip() == "": return "-", "-", "-", "-", "-", "-"
    sandi_cleaned = RE_DATE_CLEAN.sub('', str(grup_teks).strip())
    
    arah, kec = "-", "-"
    w_match = RE_WIND.search(sandi_cleaned)
    if w_match:
        arah = w_match.group(1)
        kec = f"{int(w_match.group(2))}G{int(w_match.group(3)[1:])}" if w_match.group(3) else str(int(w_match.group(2)))
        
    vis = "9999" if "CAVOK" in sandi_cleaned else ("-" if not (v := RE_VIS.search(sandi_cleaned)) else v.group(0))
    wx = "-" if "CAVOK" in sandi_cleaned or "NSW" in sandi_cleaned else ("-" if not (w := RE_WX.search(sandi_cleaned)) else w.group(0))
            
    aw_jml, aw_tgi = "-", "-"
    if "CAVOK" in sandi_cleaned:
        aw_jml, aw_tgi = "NSC", "0"
    else:
        c_matches = RE_CLOUD.findall(sandi_cleaned)
        if c_matches:
            terendah = min(c_matches, key=lambda x: int(x[1]))
            aw_jml, aw_tgi = terendah[0], str(int(terendah[1]) * 100)
            
    return arah, kec, vis, wx, aw_jml, aw_tgi

# =========================================================================
# 2. EVALUASI AKURASI PARAMETER (LOGIKA SIVETA)
# =========================================================================
def hitung_angin_arah(m_dir, t_dir, m_kec="-", t_kec="-", m_ts_cb=False):
    m_str, t_str = str(m_dir).strip().upper(), str(t_dir).strip().upper()
    m_spd = int(str(m_kec).split('G')[0]) if 'G' in str(m_kec) else (int(m_kec) if str(m_kec).isdigit() else 0)
    t_spd = int(str(t_kec).split('G')[0]) if 'G' in str(t_kec) else (int(t_kec) if str(t_kec).isdigit() else 0)

    if m_str == t_str: return (m_str, "B")
    if m_str in ["VRB", "///"] and t_str in ["VRB", "///"]: return (m_str, "B")
    if t_str == "VRB" and (m_ts_cb or m_spd < 10): return (m_str, "B")
    if m_spd < 10 and t_spd < 10: return (m_str, "B")
        
    try:
        m, t = int(m_str), int(t_str)
        diff = abs(m - t)
        diff = diff if diff <= 180 else 360 - diff
        return (m_str, "B") if diff <= 60 or (diff > 60 and m_spd < 10) else (m_str, "S")
    except: return (m_str, "S")

def hitung_angin_kec(m_kec, t_kec):
    if m_kec == "-" or t_kec == "-" or m_kec == "NIL" or t_kec == "NIL": return "-", "NIL"
    try:
        m_base = int(m_kec.split('G')[0]) if 'G' in m_kec else int(m_kec)
        t_base = int(t_kec.split('G')[0]) if 'G' in t_kec else int(t_kec)
        m_gust = int(m_kec.split('G')[1]) if 'G' in m_kec else 0
        t_gust = int(t_kec.split('G')[1]) if 'G' in t_kec else 0
        
        diff_base = abs(m_base - t_base)
        stat_base = "B" if diff_base <= 10 else "S"
        
        if (m_gust > 0) != (t_gust > 0): return f"B:{diff_base}|G:{abs(m_gust-t_gust)}", "S"
        return str(diff_base), stat_base
    except: return "-", "S"

def get_vis_class(vis_value):
    if vis_value < 800: return 1
    elif 800 <= vis_value < 1500: return 2
    elif 1500 <= vis_value < 3000: return 3
    elif 3000 <= vis_value < 5000: return 4
    return 5

def hitung_vis(m_vis, t_vis):
    try:
        m, t = int(m_vis), int(t_vis)
        return (m, "B") if get_vis_class(m) == get_vis_class(t) else (m, "S")
    except: return (None, "S")

def cek_presipitasi_sedang_lebat(wx_str):
    if pd.isna(wx_str) or wx_str == "-": return False
    return 'RA' in str(wx_str).upper() and '-RA' not in str(wx_str).upper()

def hitung_cuaca(m_wx, t_wx):
    return "MATCH", ("B" if cek_presipitasi_sedang_lebat(m_wx) == cek_presipitasi_sedang_lebat(t_wx) else "S")

def hitung_awan_jml(m_jml, t_jml, m_tgi):
    if m_jml == "-" or t_jml == "-": return "-", "NIL"
    try:
        if m_tgi != "-" and int(m_tgi) > 5000: return ">5000ft", "B"
        km = 2 if str(m_jml).upper() in ['BKN', 'OVC'] else 1
        kt = 2 if str(t_jml).upper() in ['BKN', 'OVC'] else 1
        return f"K:{km}vs{kt}", ("B" if km == kt else "S")
    except: return "-", "S"

def hitung_awan_tgi(m_tgi, t_tgi):
    if m_tgi == "-" or t_tgi == "-": return "-", "NIL"
    try:
        mt, tt = int(m_tgi), int(t_tgi)
        diff = abs(mt - tt)
        return str(diff), "B" if (diff <= 100 if mt < 1000 else diff <= (0.3 * mt)) else "S"
    except: return "-", "S"

# =========================================================================
# 3. KONTROLLER UTAMA VERIFIKASI (SUPERCHARGED)
# =========================================================================
def evaluasi_sandi_tunggal(m_obs_data, t_ar, t_ke, t_vi, t_wx, t_aj, t_at, base_bundle=None, is_grup_prob=False, is_grup_tempo=False, is_grup_becmg_trans=False):
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

    return ("S" if 'S' in [s_ar, s_ke, s_vi, s_wx, s_aj, s_at] else "B"), s_ar, s_ke, s_vi, s_wx, s_aj, s_at

def proses_verifikasi(df_metar, df_taf, df_speci):
    col_waktu_metar = next((c for c in df_metar.columns if any(k in c.lower() for k in ['waktu', 'date', 'tanggal', 'time'])), df_metar.columns[0])
    col_teks_metar = next((c for c in df_metar.columns if 'type' not in c.lower() and 'status' not in c.lower() and any(k in c.lower() for k in ['sandi', 'text', 'message', 'report', 'isi'])), df_metar.columns[1])
    col_waktu_taf = next((c for c in df_taf.columns if any(k in c.lower() for k in ['waktu', 'date', 'tanggal', 'time'])), df_taf.columns[0])
    col_teks_taf = next((c for c in df_taf.columns if 'type' not in c.lower() and 'status' not in c.lower() and any(k in c.lower() for k in ['sandi', 'text', 'message', 'report', 'isi'])), df_taf.columns[1])
    
    has_cccc = 'cccc' in df_metar.columns

    # Pra-pemrosesan Data (Menghindari Series indexing dalam loop)
    metar_list = df_metar.assign(dt_obj=pd.to_datetime(df_metar[col_waktu_metar].astype(str).str.slice(0, 19), errors='coerce')).dropna(subset=['dt_obj']).sort_values('dt_obj').to_dict('records')
    taf_raw = df_taf.assign(dt_obj=pd.to_datetime(df_taf[col_waktu_taf].astype(str).str.slice(0, 19), errors='coerce')).dropna(subset=['dt_obj']).sort_values('dt_obj').to_dict('records')
    speci_raw = df_speci.assign(dt_obj=pd.to_datetime(df_speci[df_speci.columns[0]].astype(str).str.slice(0, 19), errors='coerce')).dropna(subset=['dt_obj']).sort_values('dt_obj').to_dict('records')

    # Pra-Kompilasi Daftar TAF Aktif (Sangat Cepat)
    taf_list = []
    for tr in taf_raw:
        t_teks = str(tr[col_teks_taf])
        t_issue = tr['dt_obj']
        v_match = RE_VALID_TAF.search(t_teks)
        v_dt = t_issue
        if v_match:
            try: v_dt = t_issue.replace(day=int(v_match.group(1)), hour=int(v_match.group(2)), minute=0, second=0)
            except ValueError: pass
        poin = 1 if RE_AMD_COR.search(t_teks) else 0
        taf_list.append({'issue': t_issue, 'valid': v_dt, 'poin': poin, 'teks': t_teks})

    baris_analisis_final, baris_speci_final = [], []

    for m in metar_list:
        tgl_jam_aktual = m['dt_obj']
        teks_metar = m[col_teks_metar]
        m_stasiun = m['cccc'] if has_cccc else "WATU"
        
        m_ar, m_ke, m_vi, m_wx, m_aj, m_at, m_ts_cb = ekstrak_param_metar_speci(teks_metar)
        
        # Filter TAF tanpa memanggil Pandas DataFrame
        kandidat = [t for t in taf_list if t['issue'] <= tgl_jam_aktual and t['valid'] <= tgl_jam_aktual < t['valid'] + timedelta(hours=12)]
        if not kandidat: continue
        
        kandidat.sort(key=lambda x: (x['valid'], x['issue'], x['poin']))
        taf_aktif = kandidat[-1]['teks']
        
        speci_terkait = [sp for sp in speci_raw if tgl_jam_aktual <= sp['dt_obj'] <= tgl_jam_aktual + timedelta(minutes=59)]
        
        parts = RE_PARTS.split(str(taf_aktif))
        b_ar, b_ke, b_vi, b_wx, b_aj, b_at = parse_sandi(parts[0])
        cur_ar, cur_ke, cur_vi, cur_wx, cur_aj, cur_at = b_ar, b_ke, b_vi, b_wx, b_aj, b_at
        t_ar, t_ke, t_vi, t_wx, t_aj, t_at = b_ar, b_ke, b_vi, b_wx, b_aj, b_at
        
        is_grup_prob = is_grup_tempo = is_grup_becmg_trans = False
        target_hour = tgl_jam_aktual.hour
        
        for i in range(1, len(parts), 2):
            tipe, isi = parts[i], parts[i+1]
            
            # 1. Ekstraksi Waktu (Pisahkan logika FM dan BECMG/TEMPO)
            if tipe.startswith('FM'):
                s_hr = int(tipe[4:6]) # Ekstrak jam dari FMddhhmm
                e_hr = 24
            else:
                time_match = RE_TIME_GRP.search(isi)
                if time_match:
                    s_hr, e_hr = int(time_match.group(2)), int(time_match.group(4))
                    if e_hr == 0: e_hr = 24
                else:
                    continue # Skip jika tidak ada format waktu standar
            
            # 2. Logika Evaluasi dan Override
            if s_hr <= target_hour < e_hr:
                g_ar, g_ke, g_vi, g_wx, g_aj, g_at = parse_sandi(isi)
                
                if tipe.startswith('FM'):
                    # FM Override total (Ganti lembaran baru)
                    t_ar = g_ar if g_ar != "-" else "VRB"
                    t_ke = g_ke if g_ke != "-" else "00"
                    t_vi = g_vi if g_vi != "-" else "9999"
                    t_wx = g_wx if g_wx != "-" else "NIL"
                    t_aj = g_aj if g_aj != "-" else "NSC"
                    t_at = g_at if g_at != "-" else "0"
                    # FM otomatis menjadi base baru
                    cur_ar, cur_ke, cur_vi, cur_wx, cur_aj, cur_at = t_ar, t_ke, t_vi, t_wx, t_aj, t_at
                else:
                    # BECMG / TEMPO Override parsial
                    if g_ar != "-": t_ar = g_ar
                    if g_ke != "-": t_ke = g_ke
                    if g_vi != "-": t_vi = g_vi
                    if g_wx != "-" and not RE_WX_EXCLUDE.search(isi) and "CAVOK" not in isi: t_wx = g_wx
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
        
        is_crit = "NORMAL"
        try:
            if int(m_vi) < 5000 or (m_aj in ["BKN", "OVC"] and int(m_at) < 1500): is_crit = "CRITICAL MINIMA"
        except: pass

        if speci_terkait:
            for sp in speci_terkait:
                sp_ar, sp_ke, sp_vi, sp_wx, sp_aj, sp_at, sp_ts_cb = ekstrak_param_metar_speci(sp[list(sp.keys())[1]])
                sp_obs_data = {'M_Arah': sp_ar, 'M_Kec': sp_ke, 'M_Vis': sp_vi, 'M_Wx': sp_wx, 'M_AwanJml': sp_aj, 'M_AwanTgi': sp_at, 'M_TS_CB': sp_ts_cb}
                status_speci, sp_s_ar, sp_s_ke, sp_s_vi, sp_s_wx, sp_s_aj, sp_s_at = evaluasi_sandi_tunggal(
                    sp_obs_data, t_ar, t_ke, t_vi, t_wx, t_aj, t_at, base_bundle, is_grup_prob, is_grup_tempo, is_grup_becmg_trans
                )
                
                if status_speci == "S":
                    status_jam_ini = "S"
                    s_ar = "S" if sp_s_ar == "S" else s_ar
                    s_ke = "S" if sp_s_ke == "S" else s_ke
                    s_vi = "S" if sp_s_vi == "S" else s_vi
                    s_wx = "S" if sp_s_wx == "S" else s_wx
                    s_aj = "S" if sp_s_aj == "S" else s_aj
                    s_at = "S" if sp_s_at == "S" else s_at
                    
                baris_speci_final.append({
                    'Waktu SPECI (UTC)': sp['dt_obj'].strftime('%Y-%m-%d %H:%M:%S'),
                    'Sandi SPECI':       sp[list(sp.keys())[1]], 'TAFOR Berlaku': taf_aktif,
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
            'M_Crosswind_Knot': 0.0, 'T_Crosswind_Knot': 0.0, 'Status_Minima': is_crit,
            'Hasil Akhir': "ACCURATE" if status_jam_ini == "B" else "MISS",
            'Kode_Stasiun': m_stasiun
        })
        
    return pd.DataFrame(baris_analisis_final), pd.DataFrame(baris_speci_final), None, None

def hitung_verifikasi_TAFOR(df_input):
    df_work = df_input.to_dict('records')
    rekapan = {k: {'B': 0, 'S': 0} for k in ['A', 'B', 'C', 'D', 'E', 'F']}
    
    # Kelompokkan berdasar hari & sandi TAF dengan memori Cepat
    taf_harian = {}
    for row in df_work:
        if row['Sandi TAF Prakiraan'] == "-": continue
        dt_val = datetime.strptime(row['Waktu Aktual (UTC)'], '%Y-%m-%d %H:%M:%S')
        key_hari = dt_val.strftime('%Y-%m-%d')
        sandi = row['Sandi TAF Prakiraan']
        
        if key_hari not in taf_harian: taf_harian[key_hari] = {}
        if sandi not in taf_harian[key_hari]: taf_harian[key_hari][sandi] = []
        taf_harian[key_hari][sandi].append((dt_val.hour, row))
        
    for hari, dict_tafs in taf_harian.items():
        for taf_sandi, list_rows in dict_tafs.items():
            list_rows.sort(key=lambda x: x[0]) 
            baris_m_base = list_rows[0][1]
            
            parts = RE_PARTS.split(str(taf_sandi))
            b_ar, b_ke, b_vi, b_wx, b_aj, b_at = parse_sandi(parts[0])
            cur_ar, cur_ke, cur_vi, cur_wx, cur_aj, cur_at = b_ar, b_ke, b_vi, b_wx, b_aj, b_at
            
            m_obs_base = {'M_Arah': baris_m_base['M_Arah'], 'M_Kec': baris_m_base['M_Kec'], 'M_Vis': baris_m_base['M_Vis'], 'M_Wx': baris_m_base['M_Wx'], 'M_AwanJml': baris_m_base['M_AwanJml'], 'M_AwanTgi': baris_m_base['M_AwanTgi'], 'M_TS_CB': False}
            _, s_ar, s_ke, s_vi, s_wx, s_aj, s_at = evaluasi_sandi_tunggal(m_obs_base, b_ar, b_ke, b_vi, b_wx, b_aj, b_at)
            
            for k, stat in zip(['A','B','C','D','E','F'], [s_ar, s_ke, s_vi, s_wx, s_aj, s_at]):
                if stat in ['B', 'S']: rekapan[k][stat] += 1
                    
            for i in range(1, len(parts), 2):
                tipe, isi = parts[i], parts[i+1]
                
                # Ekstraksi waktu target
                if tipe.startswith('FM'):
                    jam_target = int(tipe[4:6])
                else:
                    time_match = RE_TIME_GRP.search(isi)
                    jam_target = int(time_match.group(2)) if time_match else 0
                
                # Cari baris yang jamnya pas, atau fallback ke base
                baris_m_trend = next((r for h, r in list_rows if h == jam_target), baris_m_base)
                
                g_ar, g_ke, g_vi, g_wx, g_aj, g_at = parse_sandi(isi)
                
                # Override Logika Rekapan
                if tipe.startswith('FM'):
                    t_ar = g_ar if g_ar != "-" else "VRB"
                    t_ke = g_ke if g_ke != "-" else "00"
                    t_vi = g_vi if g_vi != "-" else "9999"
                    t_wx = g_wx if g_wx != "-" else "NIL"
                    t_aj = g_aj if g_aj != "-" else "NSC"
                    t_at = g_at if g_at != "-" else "0"
                else:
                    t_ar = g_ar if g_ar != "-" else cur_ar
                    t_ke = g_ke if g_ke != "-" else cur_ke
                    t_vi = g_vi if g_vi != "-" else cur_vi
                    t_wx = g_wx if (g_wx != "-" and not RE_WX_EXCLUDE.search(isi) and "CAVOK" not in isi) else cur_wx
                    t_aj = g_aj if g_aj != "-" else cur_aj
                    t_at = g_at if g_at != "-" else cur_at
                
                m_obs_trend = {'M_Arah': baris_m_trend['M_Arah'], 'M_Kec': baris_m_trend['M_Kec'], 'M_Vis': baris_m_trend['M_Vis'], 'M_Wx': baris_m_trend['M_Wx'], 'M_AwanJml': baris_m_trend['M_AwanJml'], 'M_AwanTgi': baris_m_trend['M_AwanTgi'], 'M_TS_CB': False}
                
                _, s_ar_t, s_ke_t, s_vi_t, s_wx_t, s_aj_t, s_at_t = evaluasi_sandi_tunggal(
                    m_obs_trend, t_ar, t_ke, t_vi, t_wx, t_aj, t_at, 
                    base_bundle=(cur_ar, cur_ke, cur_vi, cur_wx, cur_aj, cur_at), 
                    is_grup_prob=('PROB' in tipe), is_grup_tempo=('TEMPO' in tipe), is_grup_becmg_trans=('BECMG' in tipe)
                )
                
                for k, stat in zip(['A','B','C','D','E','F'], [s_ar_t, s_ke_t, s_vi_t, s_wx_t, s_aj_t, s_at_t]):
                    if stat in ['B', 'S']: rekapan[k][stat] += 1
                    
                if tipe.startswith('FM') or tipe == 'BECMG':
                    cur_ar, cur_ke, cur_vi, cur_wx, cur_aj, cur_at = t_ar, t_ke, t_vi, t_wx, t_aj, t_at
                    
    return rekapan
def buat_tabel_laporan_excel(df_input):
    """
    Fungsi khusus untuk memecah data verifikasi SIVETA menjadi format per-baris 
    (Base, TEMPO, BECMG, FM) agar siap di-export ke format V FINAL.xlsx BMKG.
    """
    df_work = df_input.to_dict('records')
    baris_laporan = []
    
    # Kelompokkan data berdasarkan tanggal dan sandi TAF
    taf_harian = {}
    for row in df_work:
        if row['Sandi TAF Prakiraan'] == "-": continue
        # Pastikan kolom waktu diparsing dengan benar
        dt_val = pd.to_datetime(row['Waktu Aktual (UTC)'])
        key_hari = dt_val.strftime('%Y-%m-%d')
        sandi = row['Sandi TAF Prakiraan']
        
        if key_hari not in taf_harian: taf_harian[key_hari] = {}
        if sandi not in taf_harian[key_hari]: taf_harian[key_hari][sandi] = []
        taf_harian[key_hari][sandi].append((dt_val.hour, row))
        
    for hari, dict_tafs in taf_harian.items():
        tgl_str = datetime.strptime(hari, '%Y-%m-%d').strftime('%d')
        
        for taf_sandi, list_rows in dict_tafs.items():
            # Urutkan berdasarkan jam agar sinkron
            list_rows.sort(key=lambda x: x[0]) 
            baris_m_base = list_rows[0][1]
            
            # Parsing Base TAF
            parts = RE_PARTS.split(str(taf_sandi))
            b_ar, b_ke, b_vi, b_wx, b_aj, b_at = parse_sandi(parts[0])
            cur_ar, cur_ke, cur_vi, cur_wx, cur_aj, cur_at = b_ar, b_ke, b_vi, b_wx, b_aj, b_at
            
            jangka_base = "00-24" # Standar jangka waktu base harian
            
            # Evaluasi Base
            m_obs_base = {'M_Arah': baris_m_base['M_Arah'], 'M_Kec': baris_m_base['M_Kec'], 
                          'M_Vis': baris_m_base['M_Vis'], 'M_Wx': baris_m_base['M_Wx'], 
                          'M_AwanJml': baris_m_base['M_AwanJml'], 'M_AwanTgi': baris_m_base['M_AwanTgi'], 'M_TS_CB': False}
            _, s_ar, s_ke, s_vi, s_wx, s_aj, s_at = evaluasi_sandi_tunggal(m_obs_base, b_ar, b_ke, b_vi, b_wx, b_aj, b_at)
            
            # Simpan baris Base
            baris_laporan.append({
                'Tanggal': tgl_str, 'Jangka_Waktu': jangka_base,
                'T_Arah': b_ar, 'T_Kec': b_ke, 'T_Vis': b_vi, 'T_Wx': b_wx, 'T_AwanJml': b_aj, 'T_AwanTgi': b_at,
                'M_Arah': baris_m_base['M_Arah'], 'S_Arah': s_ar,
                'M_Kec': baris_m_base['M_Kec'], 'S_Kec': s_ke,
                'M_Vis': baris_m_base['M_Vis'], 'S_Vis': s_vi,
                'M_Wx': baris_m_base['M_Wx'], 'S_Wx': s_wx,
                'M_AwanJml': baris_m_base['M_AwanJml'], 'S_AwanJml': s_aj,
                'M_AwanTgi': baris_m_base['M_AwanTgi'], 'S_AwanTgi': s_at
            })
            
            # Evaluasi Trend (FM / TEMPO / BECMG / PROB)
            for i in range(1, len(parts), 2):
                tipe, isi = parts[i], parts[i+1]
                
                # Ekstraksi Waktu dan Penamaan Jangka Waktu
                if tipe.startswith('FM'):
                    jam_target = int(tipe[4:6])
                    jangka_trend = tipe # Akan tertulis misal: FM150200
                else:
                    time_match = RE_TIME_GRP.search(isi)
                    jam_target = int(time_match.group(2)) if time_match else 0
                    prefix = 'T' if 'TEMPO' in tipe else ('B' if 'BECMG' in tipe else 'P')
                    jangka_trend = f"{prefix}.{time_match.group(2)}-{time_match.group(4)}" if time_match else tipe
                
                # Cari data METAR aktual yang paling mendekati jam target
                baris_m_trend = next((r for h, r in list_rows if h == jam_target), baris_m_base)
                
                g_ar, g_ke, g_vi, g_wx, g_aj, g_at = parse_sandi(isi)
                
                # Terapkan Logika Override FM vs BECMG/TEMPO
                if tipe.startswith('FM'):
                    t_ar = g_ar if g_ar != "-" else "VRB"
                    t_ke = g_ke if g_ke != "-" else "00"
                    t_vi = g_vi if g_vi != "-" else "9999"
                    t_wx = g_wx if g_wx != "-" else "NIL"
                    t_aj = g_aj if g_aj != "-" else "NSC"
                    t_at = g_at if g_at != "-" else "0"
                else:
                    t_ar = g_ar if g_ar != "-" else cur_ar
                    t_ke = g_ke if g_ke != "-" else cur_ke
                    t_vi = g_vi if g_vi != "-" else cur_vi
                    t_wx = g_wx if (g_wx != "-" and not RE_WX_EXCLUDE.search(isi) and "CAVOK" not in isi) else cur_wx
                    t_aj = g_aj if g_aj != "-" else cur_aj
                    t_at = g_at if g_at != "-" else cur_at
                
                m_obs_trend = {'M_Arah': baris_m_trend['M_Arah'], 'M_Kec': baris_m_trend['M_Kec'], 
                               'M_Vis': baris_m_trend['M_Vis'], 'M_Wx': baris_m_trend['M_Wx'], 
                               'M_AwanJml': baris_m_trend['M_AwanJml'], 'M_AwanTgi': baris_m_trend['M_AwanTgi'], 'M_TS_CB': False}
                
                _, s_ar_t, s_ke_t, s_vi_t, s_wx_t, s_aj_t, s_at_t = evaluasi_sandi_tunggal(
                    m_obs_trend, t_ar, t_ke, t_vi, t_wx, t_aj, t_at, 
                    base_bundle=(cur_ar, cur_ke, cur_vi, cur_wx, cur_aj, cur_at), 
                    is_grup_prob=('PROB' in tipe), is_grup_tempo=('TEMPO' in tipe), is_grup_becmg_trans=('BECMG' in tipe)
                )
                
                # Simpan baris Trend
                baris_laporan.append({
                    'Tanggal': tgl_str, 'Jangka_Waktu': jangka_trend,
                    'T_Arah': t_ar, 'T_Kec': t_ke, 'T_Vis': t_vi, 'T_Wx': t_wx, 'T_AwanJml': t_aj, 'T_AwanTgi': t_at,
                    'M_Arah': baris_m_trend['M_Arah'], 'S_Arah': s_ar_t,
                    'M_Kec': baris_m_trend['M_Kec'], 'S_Kec': s_ke_t,
                    'M_Vis': baris_m_trend['M_Vis'], 'S_Vis': s_vi_t,
                    'M_Wx': baris_m_trend['M_Wx'], 'S_Wx': s_wx_t,
                    'M_AwanJml': baris_m_trend['M_AwanJml'], 'S_AwanJml': s_aj_t,
                    'M_AwanTgi': baris_m_trend['M_AwanTgi'], 'S_AwanTgi': s_at_t
                })
                
                # Wariskan kondisi base baru jika FM atau BECMG
                if tipe.startswith('FM') or 'BECMG' in tipe:
                    cur_ar, cur_ke, cur_vi, cur_wx, cur_aj, cur_at = t_ar, t_ke, t_vi, t_wx, t_aj, t_at

    return pd.DataFrame(baris_laporan)
