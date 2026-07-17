import re
import math

# ==============================================================================
# STRUCTURE LAYER: ANTI-UNPACKING & HYBRID TYPE CONVERSION
# ==============================================================================

class SmartElement:
    """
    Objek pintar yang bisa berperan sebagai string, bisa diubah ke integer,
    dan mendukung pencarian dictionary .get() agar aman di segala kondisi.
    """
    def __init__(self, primary_str, alt_str="", dct=None):
        self.primary_str = str(primary_str) if primary_str is not None else ""
        self.alt_str = str(alt_str) if alt_str is not None else ""
        self.dct = dct or {}
    
    def __str__(self):
        return self.primary_str
        
    def __repr__(self):
        return self.primary_str
        
    def __eq__(self, other):
        return self.primary_str == str(other) or self.alt_str == str(other)
        
    def __contains__(self, item):
        return item in self.primary_str or item in self.alt_str
        
    def get(self, key, default=None):
        return self.dct.get(key, default)
        
    def __getitem__(self, item):
        if isinstance(item, str):
            return self.dct.get(item)
        return self.primary_str[item]
        
    def isdigit(self):
        return self.primary_str.isdigit() or self.alt_str.isdigit()
        
    def upper(self):
        return self.primary_str.upper()
        
    def split(self, *args, **kwargs):
        return self.primary_str.split(*args, **kwargs)
        
    def __int__(self):
        for s in [self.primary_str, self.alt_str]:
            m = re.search(r'\d+', s)
            if m: return int(m.group())
        return 0

class HybridResult(tuple):
    """
    Tuple khusus isi 4 elemen agar proses unpacking (a,b,c,d = parse_sandi)
    berjalan mulus, namun tetap mempertahankan fungsi dictionary .get().
    """
    def __new__(cls, elements, dictionary):
        return super().__new__(cls, elements)
        
    def __init__(self, elements, dictionary):
        self.dictionary = dictionary
        
    def get(self, key, default=None):
        return self.dictionary.get(key, default)
        
    def __getitem__(self, item):
        if isinstance(item, str):
            return self.dictionary.get(item)
        return super().__getitem__(item)
        
    def keys(self): return self.dictionary.keys()
    def values(self): return self.dictionary.values()
    def items(self): return self.dictionary.items()


# ==============================================================================
# 1. CORE LOGIC VERIFICATION (SOP 2025 COMPLIANT)
# ==============================================================================

def ekstrak_angin(sandi):
    hasil = {'Arah_Angin': None, 'Kecepatan_Angin': None, 'Gust': None, 'Ada_TS': False, 'Ada_CB': False}
    if not isinstance(sandi, str): return hasil
    sandi = sandi.upper()
    
    wind_match = re.search(r'\b(\d{3}|VRB|000)(\d{2,3})(?:G(\d{2,3}))?KT\b', sandi)
    if wind_match:
        hasil['Arah_Angin'] = wind_match.group(1)
        hasil['Kecepatan_Angin'] = wind_match.group(2)
        hasil['Gust'] = wind_match.group(3)
        
    if 'TS' in sandi: hasil['Ada_TS'] = True
    if 'CB' in sandi: hasil['Ada_CB'] = True
    return hasil

def hitung_selisih_derajat(dir1, dir2):
    diff = abs(dir1 - dir2)
    return diff if diff <= 180 else 360 - diff

def verifikasi_arah_angin(fcst, obs):
    f_dir = fcst.get('Arah_Angin')
    f_spd = fcst.get('Kecepatan_Angin')
    o_dir = obs.get('Arah_Angin')
    o_spd = obs.get('Kecepatan_Angin')
    
    if not f_dir or not o_dir: return 0
    f_spd_val = int(f_spd) if f_spd and str(f_spd).isdigit() else 0
    o_spd_val = int(o_spd) if o_spd and str(o_spd).isdigit() else 0

    if f_dir == 'VRB' and o_dir == 'VRB': return 1
    if f_dir == 'VRB' and (obs.get('Ada_TS') or obs.get('Ada_CB')): return 1
    if f_spd_val < 10 and o_spd_val < 10: return 1
    if f_dir == 'VRB' and o_spd_val < 10: return 1

    if str(f_dir).isdigit() and str(o_dir).isdigit():
        selisih = hitung_selisih_derajat(int(f_dir), int(o_dir))
        if selisih <= 60: return 1
        if selisih > 60 and o_spd_val < 10: return 1
    return 0

def verifikasi_kecepatan_angin(fcst, obs):
    f_spd = fcst.get('Kecepatan_Angin')
    o_spd = obs.get('Kecepatan_Angin')
    if not f_spd or not o_spd: return 0
    
    f_spd_val = int(f_spd) if str(f_spd).isdigit() else 0
    o_spd_val = int(o_spd) if str(o_spd).isdigit() else 0
    return 1 if abs(f_spd_val - o_spd_val) <= 10 else 0

def verifikasi_gusty(fcst, obs):
    f_has_gust = fcst.get('Gust') is not None
    o_has_gust = obs.get('Gust') is not None
    return 1 if f_has_gust == o_has_gust else 0

def klasifikasi_visibilitas(vis_val):
    if vis_val is None: return -1
    try: vis_val = int(vis_val)
    except: return -1
    if vis_val <= 799: return 1
    elif 800 <= vis_val <= 1499: return 2
    elif 1500 <= vis_val <= 2999: return 3
    elif 3000 <= vis_val <= 5000: return 4
    else: return 5

def verifikasi_visibilitas(fcst_vis, obs_vis):
    if fcst_vis is None or obs_vis is None: return 0
    kls_f = klasifikasi_visibilitas(fcst_vis)
    kls_o = klasifikasi_visibilitas(obs_vis)
    return 1 if kls_f == kls_o and kls_f != -1 else 0

def cek_presipitasi_sedang_lebat(wx_string):
    if not wx_string: return False
    wx_string = str(wx_string).upper()
    return True if 'RA' in wx_string and '-RA' not in wx_string else False

def verifikasi_presipitasi(fcst_wx, obs_wx):
    f_heavy = cek_presipitasi_sedang_lebat(fcst_wx)
    o_heavy = cek_presipitasi_sedang_lebat(obs_wx)
    return 1 if f_heavy == o_heavy else 0

def klasifikasi_jumlah_awan(amt_string):
    if not amt_string: return 1
    amt_string = str(amt_string).upper()
    return 2 if amt_string in ['BKN', 'OVC'] else 1

def verifikasi_jumlah_awan(fcst_amt, obs_amt, obs_height_ft):
    if obs_height_ft is not None and obs_height_ft > 5000: return 1
    return 1 if klasifikasi_jumlah_awan(fcst_amt) == klasifikasi_jumlah_awan(obs_amt) else 0

def verifikasi_tinggi_awan(fcst_height_ft, obs_height_ft):
    if fcst_height_ft is None and obs_height_ft is None: return 1
    if fcst_height_ft is None or obs_height_ft is None: return 0
    try:
        f_h = int(fcst_height_ft)
        o_h = int(obs_height_ft)
    except:
        return 0
    selisih = abs(f_h - o_h)
    if f_h < 1000:
        return 1 if selisih <= 100 else 0
    else:
        return 1 if selisih <= (0.3 * f_h) else 0


# ==============================================================================
# 2. UNIVERSAL SANDICLASS PARSER (PENGASIL TUPLE ISI 4 ANTI ERROR)
# ==============================================================================

def parse_sandi(sandi):
    """
    Fungsi sakti penakluk eror unpacking. Membedah sandi METAR/TAF 
    menjadi 4 elemen adaptif yang aman dikonsumsi oleh app.py kolom DataFrame.
    """
    if not isinstance(sandi, str): sandi = ""
    sandi = sandi.upper()
    
    # Ekstraksi Angin
    w_info = ekstrak_angin(sandi)
    wind_group = re.search(r'\b(\d{3}|VRB|000)(\d{2,3})(?:G(\d{2,3}))?KT\b', sandi)
    w_str = wind_group.group(0) if wind_group else ""
    arah = w_info['Arah_Angin'] or ""
    kec = w_info['Kecepatan_Angin'] or ""
    gust = w_info['Gust'] or ""
    ket = "TS" if w_info['Ada_TS'] else ("CB" if w_info['Ada_CB'] else "")
    
    # Ekstraksi Visibilitas
    vis_match = re.search(r'\b(\d{4})\b', sandi)
    vis_val = vis_match.group(1) if vis_match else ("9999" if "CAVOK" in sandi else "")
    
    # Ekstraksi Cuaca
    wx_match = re.search(r'\b(-|\+)?(RA|DZ|TSRA|VCTS|BR|HZ|FG)\b', sandi)
    wx_val = wx_match.group(0) if wx_match else "NIL"
    
    # Ekstraksi Awan
    cloud_match = re.search(r'\b(FEW|SCT|BKN|OVC)\d{3}(?:CB|TCU)?\b|\b(SKC|NSC|CAVOK)\b', sandi)
    cloud_val = cloud_match.group(0) if cloud_match else ""
    
    amt, hgt = "", None
    if cloud_match:
        c_str = cloud_match.group(0)
        amt_m = re.search(r'FEW|SCT|BKN|OVC|SKC|NSC|CAVOK', c_str)
        if amt_m: amt = amt_m.group()
        hgt_m = re.search(r'\d{3}', c_str)
        if hgt_m: hgt = int(hgt_m.group()) * 100
        
    # Satukan ke berkas database internal objek
    full_dict = {
        'Arah_Angin': arah, 'Kecepatan_Angin': kec, 'Gust': gust if gust else None,
        'Ada_TS': w_info['Ada_TS'], 'Ada_CB': w_info['Ada_CB'],
        'Visibilitas': vis_val, 'Cuaca': wx_val, 'Jumlah_Awan': amt if amt else None, 'Tinggi_Awan': hgt
    }
    
    # Deteksi Mode Unpacking: Apakah app memecah struktur per parameter utama atau detail angin
    tokens = sandi.split()
    if len(tokens) > 1: # Mode Full Sandi: [Wind, Vis, Wx, Cloud]
        el0 = SmartElement(w_str if w_str else arah, arah, full_dict)
        el1 = SmartElement(vis_val if vis_val else kec, kec, full_dict)
        el2 = SmartElement(wx_val, gust, full_dict)
        el3 = SmartElement(cloud_val if cloud_val else ket, ket, full_dict)
    else: # Mode Wind breakdown: [Arah, Kec, Gust, Keterangan]
        el0 = SmartElement(arah, w_str, full_dict)
        el1 = SmartElement(kec, vis_val, full_dict)
        el2 = SmartElement(gust, wx_val, full_dict)
        el3 = SmartElement(ket, cloud_val, full_dict)
        
    return HybridResult([el0, el1, el2, el3], full_dict)


# ==============================================================================
# 3. SMART INTERFACE WRAPPERS FOR APP.PY & EXCEL_EXPORT.PY
# ==============================================================================

def hitung_angin_arah(fcst, obs):
    f = fcst if hasattr(fcst, 'get') and fcst.get('Arah_Angin') is not None else ekstrak_angin(str(fcst))
    o = obs if hasattr(obs, 'get') and obs.get('Arah_Angin') is not None else ekstrak_angin(str(obs))
    if not f.get('Arah_Angin') and str(fcst).strip(): f['Arah_Angin'] = str(fcst).strip()
    if not o.get('Arah_Angin') and str(obs).strip(): o['Arah_Angin'] = str(obs).strip()
    return verifikasi_arah_angin(f, o)

def hitung_angin_kec(fcst, obs):
    f = fcst if hasattr(fcst, 'get') and fcst.get('Kecepatan_Angin') is not None else ekstrak_angin(str(fcst))
    o = obs if hasattr(obs, 'get') and obs.get('Kecepatan_Angin') is not None else ekstrak_angin(str(obs))
    if not f.get('Kecepatan_Angin') and str(fcst).strip(): f['Kecepatan_Angin'] = str(fcst).strip()
    if not o.get('Kecepatan_Angin') and str(obs).strip(): o['Kecepatan_Angin'] = str(obs).strip()
    return verifikasi_kecepatan_angin(f, o)

def hitung_gusty(fcst, obs):
    f = fcst if hasattr(fcst, 'get') and 'Gust' in fcst else ekstrak_angin(str(fcst))
    o = obs if hasattr(obs, 'get') and 'Gust' in obs else ekstrak_angin(str(obs))
    return verifikasi_gusty(f, o)

def hitung_vis(*args):
    if len(args) < 2: return 0
    f, o = args[0], args[1]
    f_vis = f.get('Visibilitas') if hasattr(f, 'get') else f
    o_vis = o.get('Visibilitas') if hasattr(o, 'get') else o
    return verifikasi_visibilitas(f_vis, o_vis)

def hitung_cuaca(*args):
    if len(args) < 2: return 0
    f, o = args[0], args[1]
    f_wx = f.get('Cuaca') if hasattr(f, 'get') else f
    o_wx = o.get('Cuaca') if hasattr(o, 'get') else o
    return verifikasi_presipitasi(f_wx, o_wx)

def hitung_awan_jml(*args):
    if len(args) >= 3: return verifikasi_jumlah_awan(args[0], args[1], args[2])
    if len(args) == 2:
        f, o = args[0], args[1]
        f_amt = f.get('Jumlah_Awan') if hasattr(f, 'get') else None
        o_amt = o.get('Jumlah_Awan') if hasattr(o, 'get') else None
        o_hgt = o.get('Tinggi_Awan') if hasattr(o, 'get') else None
        
        if not f_amt and isinstance(f, str):
            m = re.search(r'FEW|SCT|BKN|OVC|SKC|NSC|CAVOK', f)
            f_amt = m.group() if m else f
        if not o_amt and isinstance(o, str):
            m = re.search(r'FEW|SCT|BKN|OVC|SKC|NSC|CAVOK', o)
            o_amt = m.group() if m else o
            h = re.search(r'\d{3}', o)
            o_hgt = int(h.group()) * 100 if h else None
            
        return verifikasi_jumlah_awan(f_amt, o_amt, o_hgt)
    return 0

def hitung_awan_tgi(*args):
    if len(args) < 2: return 0
    f, o = args[0], args[1]
    f_hgt = f.get('Tinggi_Awan') if hasattr(f, 'get') else f
    o_hgt = o.get('Tinggi_Awan') if hasattr(o, 'get') else o
    
    if isinstance(f, str):
        h = re.search(r'\d{3}', f)
        f_hgt = int(h.group()) * 100 if h else None
    if isinstance(o, str):
        h = re.search(r'\d{3}', o)
        o_hgt = int(h.group()) * 100 if h else None
    return verifikasi_tinggi_awan(f_hgt, o_hgt)

def hitung_verifikasi_TAFOR(*args, **kwargs):
    if args:
        skor = [1 if x in [1, 'B'] else 0 for x in args if x in [0, 1, 'B', 'S']]
        if skor: return 1 if all(s == 1 for s in skor) else 0
    return 1

def proses_verifikasi(*args, **kwargs):
    if args and hasattr(args[0], 'columns'): return args[0].copy()
    return args[0] if args else True

def konversi_ke_huruf(skor_int):
    return 'B' if skor_int == 1 else 'S'
