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
        return "-", "-", "-", "-", "-", "-"
    sandi = str(sandi_teks).strip()
    sandi_cleaned = re.sub(r'\b\d{4}/\d{4}\b', '', sandi)
    
    arah_wind, kec_wind = "-", "-"
    wind_match = re.search(r'\b(\d{3}|\/\/\/|VRB)(\d{2,3})(G\d{2,3})?KT\b', sandi_cleaned)
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
        wx_match = re.search(r'\b(MI|BC|PR|DR|BL|SH|TS|FZ)?(DZ|RA|SN|SG|PL|GR|GS|BR|FG|FU|VA|DU|SA|HZ|PO|SQ|FC|SS|DS)\b', sandi_cleaned)
        if wx_match: wx = wx_match.group(0)
            
    awan_jml, awan_tgi = "-", "-"
    if "CAVOK" in sandi_cleaned or "NSC" in sandi_cleaned or "NCD" in sandi_cleaned:
        awan_jml, awan_tgi = "NSC", "0"
    else:
        cloud_matches = re.findall(r'\b(FEW|SCT|BKN|OVC)(\d{3,4})\b', sandi_cleaned)
        if cloud_matches:
            terendah = min(cloud_matches, key=lambda x: int(x[1]))
            awan_jml = terendah[0]
            awan_tgi = str(int(terendah[1]) * 100)
            
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
        c_matches = re.findall(r'\b(FEW|SCT|BKN|OVC)(\d{3,4})\b', sandi_cleaned)
        if c_matches:
            terendah = min(c_matches, key=lambda x: int(x[1]))
            aw_jml = terendah[0]
            aw_tgi = str(int(terendah[1]) * 100)
            
    return arah, kec, vis, wx, aw_jml, aw_tgi

# =========================================================================
# 2. NAVIGASI GEOGRAFIS LANDASAN RUNWAY (DIVERSIFIKASI CROSSWIND)
# =========================================================================
def hitung_komponen_crosswind(arah_str, kec_str, kode_stasiun="WATU"):
    if arah_str in ["-", "///", "VRB"] or kec_str == "-":
        return 0.0
    try:
        arah_wind = int(arah_str)
        kecepatan = int(kec_str.split('G')[1]) if 'G' in kec_str else int(kec_str)
        
        rw_a, rw_b = 150, 330 
        try:
            conn = sqlite3.connect('verifier_db.sqlite')
            c = conn.cursor()
            c.execute("SELECT heading_a, heading_b FROM master_bandara WHERE icao=?", (str(kode_stasiun).strip().upper(),))
            res = c.fetchone()
            if res:
                rw_a, rw_b = int(res[0]), int(res[1])
            conn.close()
        except: pass
        
        diff_a = abs(arah_wind - rw_a)
        diff_b = abs(arah_wind - rw_b)
        
        min_diff = min(diff_a, 360 - diff_a, diff_b, 360 - diff_b)
        crosswind = kecepatan * math.sin(math.radians(min_diff))
        return round(crosswind, 1)
    except:
        return 0.0

# =========================================================================
# 3. UPGRADE MATEMATIKA TOLERANSI DAN AMBANG BATAS SOP BMKG 2025
# =========================================================================

def hitung_angin_arah(m_dir, t_dir):
    try:
        m = int(m_dir)
        t = int(t_dir)
    except:
        return "S"
    
    diff = abs(m - t)
    if diff > 180:
        diff = 360 - diff
        
    # Poin 3: Selisih < 60° adalah B (Benar), selebihnya S (Salah)
    if diff < 60:
        return "B"
    else:
        return "S"

def hitung_angin_kec(m_kec, t_kec):
    if m_kec == "-" or t_kec == "-": return "-", "NIL"
    try:
        m_base = int(m_kec.split('G')[0]) if 'G' in m_kec else int(m_kec)
        t_base = int(t_kec.split('G')[0]) if 'G' in t_kec else int(t_kec)
        m_gust = int(m_kec.split('G')[1]) if 'G' in m_kec else 0
        t_gust = int(t_kec.split('G')[1]) if 'G' in t_kec else 0
        
        diff_base = abs(m_base - t_base)
        stat_base = "B" if diff_base <= 5 else "S"
        
        if m_gust > 0 or t_gust > 0:
            diff_gust = abs(m_gust - t_gust)
            if (m_gust > 0 and t_gust == 0) or (m_gust == 0 and t_gust > 0) or (diff_gust > 5):
                return f"B:{diff_base}|G:{abs(m_gust-t_gust)}", "S"
        return str(diff_base), stat_base
    except: return "-", "S"

def get_vis_class(vis_value):
    # Fungsi pembantu untuk menentukan "Kelas/Kamar" dari sebuah angka visibility
    if vis_value < 800:
        return 1
    elif 800 <= vis_value < 1500:
        return 2
    elif 1500 <= vis_value < 3000:
        return 3
    elif 3000 <= vis_value < 5000:
        return 4
    else:
        return 5 # Kelas 5 untuk Visibility >= 5000 (Aman)

def hitung_vis(m_vis, t_vis):
    try:
        m = int(m_vis)
        t = int(t_vis)
    except:
        return "S"
        
    # Tentukan METAR dan TAF masuk ke kelas mana
    kelas_metar = get_vis_class(m)
    kelas_taf = get_vis_class(t)
    
    # Jika keduanya berada di dalam KELAS YANG SAMA, maka Benar (B)
    if kelas_metar == kelas_taf:
        return "B"
    else:
        return "S"

def is_endapan(wx_str):
    if wx_str == "-" or pd.isna(wx_str): return False
    for p in ["DZ", "RA", "SN", "SG", "PL", "GR", "GS", "TSRA", "SHRA"]:
        if p in str(wx_str).upper(): return True
    return False

def hitung_cuaca(m_wx, t_wx):
    m_is_p = is_endapan(m_wx)
    t_is_p = is_endapan(t_wx)
    return "MATCH" if m_is_p == t_is_p else "DIFF", ("B" if m_is_p == t_is_p else "S")

def hitung_awan_jml(m_jml, t_jml, m_tgi):
    if m_jml == "-" or t_jml == "-": return "-", "NIL"
    try:
        if m_tgi != "-" and int(m_tgi) > 5000:
            return ">5000ft", "B"
        def kateg(jml):
            if str(jml).upper() in ["BKN", "OVC"]: return 2
            return 1
        km = kateg(m_jml)
        kt = kateg(t_jml)
        return f"K:{km}vs{kt}", ("B" if km == kt else "S")
    except: return "-", "S"

def hitung_awan_tgi(m_tgi, t_tgi):
    if m_tgi == "-" or t_tgi == "-": return "-", "NIL"
    try:
        mt, tt = int(m_tgi), int(t_tgi)
        diff = abs(mt - tt)
        if tt < 1000:
            stat = "B" if diff <= 100 else "S"
        else:
            stat = "B" if diff <= 300 else "S"
        return str(diff), stat
    except: return "-", "S"

# =========================================================================
# 4. KONTROLLER UTAMA VERIFIKASI ADIL JAMAN & BULANAN (FORM 029 SOP 2025)
# =========================================================================

def evaluasi_sandi_tunggal(m_obs_data, t_ar, t_ke, t_vi, t_wx, t_aj, t_at, base_bundle=None, is_grup_prob=False, is_grup_tempo=False, is_grup_becmg_trans=False):
    _, s_ar = hitung_angin_arah(m_obs_data['M_Arah'], t_ar)
    _, s_ke = hitung_angin_kec(m_obs_data['M_Kec'], t_ke)
    _, s_vi = hitung_vis(m_obs_data['M_Vis'], t_vi)
    _, s_wx = hitung_cuaca(m_obs_data['M_Wx'], t_wx)
    _, s_aj = hitung_awan_jml(m_obs_data['M_AwanJml'], t_aj, m_obs_data['M_AwanTgi'])
    _, s_at = hitung_awan_tgi(m_obs_data['M_AwanTgi'], t_at)
    
    if (is_grup_prob or is_grup_tempo or is_grup_becmg_trans) and base_bundle is not None:
        _, b_ar = hitung_angin_arah(m_obs_data['M_Arah'], base_bundle[0])
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
    
    for _, metar_row in df_metar.iterrows():
        tgl_jam_aktual = metar_row['dt_obj']
        teks_metar = metar_row[col_teks]
        m_stasiun = metar_row['cccc'] if 'cccc' in df_metar.columns else "WATU"
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
                        
        m_obs_data = {'M_Arah': m_ar, 'M_Kec': m_ke, 'M_Vis': m_vi, 'M_Wx': m_wx, 'M_AwanJml': m_aj, 'M_AwanTgi': m_at}
        base_bundle = (cur_ar, cur_ke, cur_vi, cur_wx, cur_aj, cur_at)
        
        status_jam_ini, s_ar, s_ke, s_vi, s_wx, s_aj, s_at = evaluasi_sandi_tunggal(
            m_obs_data, t_ar, t_ke, t_vi, t_wx, t_aj, t_at, base_bundle, is_grup_prob, is_grup_tempo, is_grup_becmg_trans
        )
        
        m_cw = hitung_komponen_crosswind(m_ar, m_ke, m_stasiun)
        t_cw = hitung_komponen_crosswind(t_ar, t_ke, m_stasiun)
        
        is_crit = "NORMAL"
        try:
            if int(m_vi) < 5000 or (m_aj in ["BKN", "OVC"] and int(m_at) < 1500):
                is_crit = "CRITICAL MINIMA"
        except: pass

        if not speci_terkait.empty:
            for _, speci_row in speci_terkait.iterrows():
                sp_ar, sp_ke, sp_vi, sp_wx, sp_aj, sp_at = ekstrak_param_metar_speci(speci_row[col_teks])
                sp_obs_data = {'M_Arah': sp_ar, 'M_Kec': sp_ke, 'M_Vis': sp_vi, 'M_Wx': sp_wx, 'M_AwanJml': sp_aj, 'M_AwanTgi': sp_at}
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
                
                sp_cw = hitung_komponen_crosswind(sp_ar, sp_ke, m_stasiun)
                if sp_cw > m_cw: m_cw = sp_cw
                try:
                    if int(sp_vi) < 5000 or (sp_aj in ["BKN", "OVC"] and int(sp_at) < 1500): is_crit = "CRITICAL MINIMA"
                except: pass
                    
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
            'M_Crosswind_Knot': m_cw, 'T_Crosswind_Knot': t_cw, 'Status_Minima': is_crit,
            'Hasil Akhir': "ACCURATE" if status_jam_ini == "B" else "MISS",
            'Kode_Stasiun': m_stasiun
        })
        
    return pd.DataFrame(baris_analisis_final), pd.DataFrame(baris_speci_final), None, None

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
            
            # 🔥 PERBAIKAN: Unpack Sempurna (Expected 4, Got 4)
            for k, func, m_col, tar in [
                ('A', hitung_angin_arah, 'M_Arah', b_ar), 
                ('B', hitung_angin_kec, 'M_Kec', b_ke),
                ('C', hitung_vis, 'M_Vis', b_vi), 
                ('D', hitung_cuaca, 'M_Wx', b_wx),
                ('F', hitung_awan_tgi, 'M_AwanTgi', b_at)
            ]:
                _, stat = func(baris_m_base[m_col], tar)
                if stat in ['B', 'S']: rekapan[k][stat] += 1
            
            _, stat_e = hitung_awan_jml(baris_m_base['M_AwanJml'], b_aj, baris_m_base['M_AwanTgi'])
            if stat_e in ['B', 'S']: rekapan['E'][stat_e] += 1
                    
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
                
                # 🔥 PERBAIKAN: Unpack Sempurna (Expected 4, Got 4)
                for k, func, m_col, tar in [
                    ('A', hitung_angin_arah, 'M_Arah', t_ar), 
                    ('B', hitung_angin_kec, 'M_Kec', t_ke),
                    ('C', hitung_vis, 'M_Vis', t_vi), 
                    ('D', hitung_cuaca, 'M_Wx', t_wx),
                    ('F', hitung_awan_tgi, 'M_AwanTgi', t_at)
                ]:
                    _, stat = func(baris_m_trend[m_col], tar)
                    if stat in ['B', 'S']: rekapan[k][stat] += 1
                
                _, stat_e_tr = hitung_awan_jml(baris_m_trend['M_AwanJml'], t_aj, baris_m_trend['M_AwanTgi'])
                if stat_e_tr in ['B', 'S']: rekapan['E'][stat_e_tr] += 1
                
                if tipe == 'BECMG': cur_ar, cur_ke, cur_vi, cur_wx, cur_aj, cur_at = t_ar, t_ke, t_vi, t_wx, t_aj, t_at
    return rekapan
