import pandas as pd
import re

def parse_sandi(sandi):
    arah, kec, vis, cuaca, awan_jml, awan_tgi = "-", "-", "-", "NIL", "-", "-"
    sandi_bersih = str(sandi).upper().replace('\n', ' ')

    wind_match = re.search(r'\b(\d{3}|VRB)(\d{2,3})(?:G\d{2,3})?KT\b', sandi_bersih)
    if wind_match:
        arah = wind_match.group(1)
        kec = wind_match.group(2)

    vis_match = re.search(r'(?<=\s)(\d{4})(?=\s)', sandi_bersih)
    if vis_match: vis = vis_match.group(1)
    elif "CAVOK" in sandi_bersih: vis = "9999"

    wx_pattern = r'\b(-|\+|VC)?(HZ|RA|TSRA|BR|DZ|FG|VCTS|TS|SHRA|MIFG|SQ|FC)\b'
    wx_match = re.search(wx_pattern, sandi_bersih)
    if wx_match: cuaca = wx_match.group(0).strip()
    elif "CAVOK" in sandi_bersih: cuaca = "NIL"

    cloud_match = re.search(r'\b(FEW|SCT|BKN|OVC)(\d{3})(?:CB|TCU)?\b', sandi_bersih)
    if cloud_match:
        awan_jml = cloud_match.group(1)
        awan_tgi = str(int(cloud_match.group(2)) * 100) 
    elif "CAVOK" in sandi_bersih:
        awan_jml = "NIL"
        awan_tgi = "-"

    return arah, kec, vis, cuaca, awan_jml, awan_tgi

def hitung_angin_arah(m_arah, t_arah):
    if m_arah == "-" or t_arah == "-": return "-", "S"
    if m_arah == "VRB" or t_arah == "VRB": return 0, "B"
    try:
        a1, a2 = int(m_arah), int(t_arah)
        deviasi = min(abs(a1 - a2), 360 - abs(a1 - a2))
        return deviasi, "B" if deviasi <= 30 else "S"
    except: return "-", "S"

def hitung_angin_kec(m_kec, t_kec):
    if m_kec == "-" or t_kec == "-": return "-", "S"
    try:
        k1, k2 = int(m_kec), int(t_kec)
        dev = abs(k1 - k2)
        stat = "B" if (k1 <= 25 and dev <= 5) or (k1 > 25 and dev <= 0.2*k1) else "S"
        return dev, stat
    except: return "-", "S"

def hitung_vis(m_vis, t_vis):
    if m_vis == "-" or t_vis == "-": return "-", "S"
    try:
        v1, v2 = int(m_vis), int(t_vis)
        dev = abs(v1 - v2)
        stat = "B" if dev <= (0.3 * v1) or (v1 == 9999 and v2 == 9999) else "S"
        return dev, stat
    except: return "-", "S"

def hitung_cuaca(m_wx, t_wx):
    if m_wx == t_wx or (m_wx != "NIL" and t_wx != "NIL"): return 0, "B" 
    else: return 1, "S" 

def hitung_awan_jml(m_awan, t_awan):
    oktas = {"NIL": 0, "FEW": 2, "SCT": 4, "BKN": 7, "OVC": 8, "-": -99}
    v1, v2 = oktas.get(m_awan, -99), oktas.get(t_awan, -99)
    if v1 == -99 or v2 == -99: return "-", "S"
    dev = abs(v1 - v2)
    return dev, "B" if dev <= 2 else "S"

def hitung_awan_tgi(m_tgi, t_tgi):
    if m_tgi == "-" or t_tgi == "-": return "-", "S"
    try:
        t1, t2 = int(m_tgi), int(t_tgi)
        dev = abs(t1 - t2)
        return dev, "B" if dev <= 100 else "S"
    except: return "-", "S"

def proses_verifikasi(df_metar, df_taf):
    df_metar['waktu'] = pd.to_datetime(df_metar['data_timestamp'].astype(str).str[:19])
    df_taf['waktu'] = pd.to_datetime(df_taf['data_timestamp'].astype(str).str[:19])
    
    df_metar = df_metar.sort_values('waktu')
    df_taf = df_taf.sort_values('waktu')

    df_metar['jam_bulat'] = df_metar['waktu'].dt.floor('h')
    df_metar_hourly = df_metar.drop_duplicates(subset=['jam_bulat'], keep='first').copy()

    df_merged = pd.merge_asof(
        df_metar_hourly, df_taf, left_on='jam_bulat', right_on='waktu', 
        direction='backward', suffixes=('_metar', '_taf')
    )

    rows = []
    for i in range(len(df_merged)):
        s_metar = df_merged.iloc[i]['sandi_metar']
        s_taf = df_merged.iloc[i]['sandi_taf'] if pd.notna(df_merged.iloc[i]['sandi_taf']) else "-"
            
        m_arah, m_kec, m_vis, m_wx, m_aj, m_at = parse_sandi(s_metar)
        t_arah, t_kec, t_vis, t_wx, t_aj, t_at = parse_sandi(s_taf)
        
        d_ar, bs_ar = hitung_angin_arah(m_arah, t_arah)
        d_ke, bs_ke = hitung_angin_kec(m_kec, t_kec)
        d_vi, bs_vi = hitung_vis(m_vis, t_vis)
        d_wx, bs_wx = hitung_cuaca(m_wx, t_wx)
        d_aj, bs_aj = hitung_awan_jml(m_aj, t_aj)
        d_at, bs_at = hitung_awan_tgi(m_at, t_at)
        
        hasil = "MISS" if "S" in [bs_ar, bs_ke, bs_vi, bs_wx, bs_aj, bs_at] else "ACCURATE"

        rows.append({
            "Waktu Aktual (UTC)": df_merged.iloc[i]['jam_bulat'].strftime('%Y-%m-%d %H:00'),
            "Sandi TAF Prakiraan": s_taf, # <--- INI DIA BARIS YANG KELUPAAN!
            "M_Arah": m_arah, "T_Arah": t_arah, "D_Arah": d_ar, "S_Arah": bs_ar,
            "M_Kec": m_kec, "T_Kec": t_kec, "D_Kec": d_ke, "S_Kec": bs_ke,
            "M_Vis": m_vis, "T_Vis": t_vis, "D_Vis": d_vi, "S_Vis": bs_vi,
            "M_Wx": m_wx, "T_Wx": t_wx, "D_Wx": d_wx, "S_Wx": bs_wx,
            "M_AwanJml": m_aj, "T_AwanJml": t_aj, "D_AwanJml": d_aj, "S_AwanJml": bs_aj,
            "M_AwanTgi": m_at, "T_AwanTgi": t_at, "D_AwanTgi": d_at, "S_AwanTgi": bs_at,
            "Hasil Akhir": hasil
        })
        
    df_hasil = pd.DataFrame(rows)
    tot = len(df_hasil)
    ak_tot = round((len(df_hasil[df_hasil["Hasil Akhir"] == "ACCURATE"]) / tot) * 100, 1) if tot > 0 else 0
    ak_vis = round((len(df_hasil[df_hasil["S_Vis"] == "B"]) / tot) * 100, 1) if tot > 0 else 0
    ak_win = round((len(df_hasil[df_hasil["S_Arah"] == "B"]) / tot) * 100, 1) if tot > 0 else 0
    
    return df_hasil, ak_tot, ak_vis, ak_win