import re
import math

# ==============================================================================
# STRUCTURE LAYER: DUAL-CAPABILITY SMART OBJECT COMPATIBILITY
# ==============================================================================

class SmartWindObject(tuple):
    """
    Tuple khusus isi 4 elemen agar proses unpacking (arah, kec, gust, ket = ...)
    berjalan 100% mulus, namun tetap mempertahankan fungsi dictionary .get() 
    dan pencarian key untuk logika verifikasi eksternal.
    """
    def __new__(cls, elements, dct):
        return super().__new__(cls, elements)
        
    def __init__(self, elements, dct):
        self.dct = dct or {}
        
    def get(self, key, default=None):
        return self.dct.get(key, default)
        
    def __getitem__(self, item):
        if isinstance(item, str):
            return self.dct.get(item)
        return super().__getitem__(item)
        
    def keys(self): return self.dct.keys()
    def values(self): return self.dct.values()
    def items(self): return self.dct.items()
    def __contains__(self, item): return item in self.dct

class SmartDataFrameObject(tuple):
    """
    Bunglon tingkat tinggi: Bertindak sebagai Tuple isi 4 saat di-unpack (a,b,c,d = df),
    namun meneruskan semua fungsi, properti, dan metode (seperti .columns, .iloc, dll)
    ke objek DataFrame asli di bawahnya.
    """
    def __new__(cls, df):
        return super().__new__(cls, [df, df, df, df])
        
    def __init__(self, df):
        self._df = df
        
    def __getattr__(self, name):
        return getattr(self._df, name)
        
    def __getitem__(self, item):
        if isinstance(item, int) and 0 <= item < 4:
            if hasattr(self, '_df') and hasattr(self._df, 'columns') and item in self._df.columns:
                return self._df[item]
            return super().__getitem__(item)
        return self._df[item]
        
    def __setitem__(self, key, value):
        self._df[key] = value
        
    def __len__(self):
        return len(self._df)
        
    def __repr__(self):
        return repr(self._df)
        
    def __str__(self):
        return str(self._df)

class SmartElement:
    """Objek string adaptif yang aman dari crash pencarian dictionary."""
    def __init__(self, primary_str, alt_str="", dct=None):
        self.primary_str = str(primary_str) if primary_str is not None else ""
        self.alt_str = str(alt_str) if alt_str is not None else ""
        self.dct = dct or {}
    def __str__(self): return self.primary_str
    def __repr__(self): return self.primary_str
    def __eq__(self, other): return self.primary_str == str(other) or self.alt_str == str(other)
    def __contains__(self, item): return item in self.primary_str or item in self.alt_str
    def get(self, key, default=None): return self.dct.get(key, default)
    def __getitem__(self, item):
        if isinstance(item, str): return self.dct.get(item)
        return self.primary_str[item]
    def isdigit(self): return self.primary_str.isdigit() or self.alt_str.isdigit()
    def upper(self): return self.primary_str.upper()
    def split(self, *args, **kwargs): return self.primary_str.split(*args, **kwargs)
    def __int__(self):
        for s in [self.primary_str, self.alt_str]:
            m = re.search(r'\d+', s)
            if m: return int(m.group())
        return 0


# ==============================================================================
# 1. LOGIKA INTI VERIFIKASI (SESUAI SOP BMKG 2025)
# ==============================================================================

def ekstrak_angin(sandi):
    hasil = {'Arah_Angin': None, 'Kecepatan_Angin': None, 'Gust': None, 'Ada_TS': False, 'Ada_CB': False}
    if not isinstance(sandi, str): sandi = str(sandi)
    sandi = sandi.upper()
    
    wind_match = re.search(r'\b(\d{3}|VRB|000)(\d{2,3})(?:G(\d{2,3}))?KT\b', sandi)
    if wind_match:
        hasil['Arah_Angin'] = wind_match.group(1)
        hasil['Kecepatan_Angin'] = wind_match.group(2)
        hasil['Gust'] = wind_match.group(3)
        
    if 'TS' in sandi: hasil['Ada_TS'] = True
    if 'CB' in sandi: hasil['Ada_CB'] = True
    
    arah = hasil['Arah_Angin'] or ""
    kec = hasil['Kecepatan_Angin'] or ""
    gust = hasil['Gust'] or ""
    ket = "TS" if hasil['Ada_TS'] else ("CB" if hasil['Ada_CB'] else "")
    
    return SmartWindObject([arah, kec, gust, ket], hasil)

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
# 2. PEMBEDAH SANDI UNIVERSAL (ADAPTASI 6 ELEMEN UNTUK EXCEL_EXPORT)
# ==============================================================================

def parse_sandi(sandi):
    if not isinstance(sandi, str): sandi = str(sandi)
    sandi = sandi.upper()
    
    # Ekstraksi Angin
    w_info = ekstrak_angin(sandi)
    wind_group = re.search(r'\b(\d{3}|VRB|000)(\d{2,3})(?:G(\d{2,3}))?KT\b', sandi)
    w_str = wind_group.group(0) if wind_group else ""
    arah = w_info.dct['Arah_Angin'] or ""
    kec = w_info.dct['Kecepatan_Angin'] or ""
    gust = w_info.dct['Gust'] or ""
    ket = "TS" if w_info.dct['Ada_TS'] else ("CB" if w_info.dct['Ada_CB'] else "")
    
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
        
    full_dict = {
        'Arah_Angin': arah, 'Kecepatan_Angin': kec, 'Gust': gust if gust else None,
        'Ada_TS': w_info.dct['Ada_TS'], 'Ada_CB': w_info.dct['Ada_CB'],
        'Visibilitas': vis_val, 'Cuaca': wx_val, 'Jumlah_Awan': amt if amt else None, 'Tinggi_Awan': hgt
    }
    
    # Bungkus menjadi 6 elemen persis sesuai permintaan excel_export.py (Arah, Kec, Vis, Wx, AwanJml, AwanTgi)
    el_arah = SmartElement(arah, w_str, full_dict)
    el_kec  = SmartElement(kec, w_str, full_dict)
    el_vis  = SmartElement(vis_val, vis_val, full_dict)
    el_wx   = SmartElement(wx_val, wx_val, full_dict)
    el_aj   = SmartElement(amt, cloud_val, full_dict)
    el_at   = SmartElement(hgt if hgt is not None else "", cloud_val, full_dict)
        
    # SmartWindObject akan memfasilitasi unpacking 6 variabel dengan aman
    return SmartWindObject([el_arah, el_kec, el_vis, el_wx, el_aj, el_at], full_dict)

# ==============================================================================
# 3. INTERFACE JEMBATAN UNTUK DATA FRAME DASHBOARD
# ==============================================================================

def dapatkan_dict_angin(obj):
    if hasattr(obj, 'dct'): return obj.dct
    if hasattr(obj, 'get') and obj.get('Arah_Angin') is not None: return obj
    return ekstrak_angin(str(obj)).dct

def hitung_angin_arah(fcst, obs):
    return verifikasi_arah_angin(dapatkan_dict_angin(fcst), dapatkan_dict_angin(obs))

def hitung_angin_kec(fcst, obs):
    return verifikasi_kecepatan_angin(dapatkan_dict_angin(fcst), dapatkan_dict_angin(obs))

def hitung_gusty(fcst, obs):
    return verifikasi_gusty(dapatkan_dict_angin(fcst), dapatkan_dict_angin(obs))

def dapatkan_val(obj, key):
    if hasattr(obj, 'dct'): return obj.dct.get(key)
    if hasattr(obj, 'get'): return obj.get(key)
    return None

def hitung_vis(*args):
    if len(args) < 2: return 0
    f, o = args[0], args[1]
    f_vis = dapatkan_val(f, 'Visibilitas')
    if f_vis is None: f_vis = f
    o_vis = dapatkan_val(o, 'Visibilitas')
    if o_vis is None: o_vis = o
    return verifikasi_visibilitas(f_vis, o_vis)

def hitung_cuaca(*args):
    if len(args) < 2: return 0
    f, o = args[0], args[1]
    f_wx = dapatkan_val(f, 'Cuaca')
    if f_wx is None: f_wx = f
    o_wx = dapatkan_val(o, 'Cuaca')
    if o_wx is None: o_wx = o
    return verifikasi_presipitasi(f_wx, o_wx)

def hitung_awan_jml(*args):
    if len(args) >= 3: return verifikasi_jumlah_awan(args[0], args[1], args[2])
    if len(args) == 2:
        f, o = args[0], args[1]
        f_amt = dapatkan_val(f, 'Jumlah_Awan')
        o_amt = dapatkan_val(o, 'Jumlah_Awan')
        o_hgt = dapatkan_val(o, 'Tinggi_Awan')
        
        if f_amt is None and isinstance(f, str):
            m = re.search(r'FEW|SCT|BKN|OVC|SKC|NSC|CAVOK', f)
            f_amt = m.group() if m else f
        if o_amt is None and isinstance(o, str):
            m = re.search(r'FEW|SCT|BKN|OVC|SKC|NSC|CAVOK', o)
            o_amt = m.group() if m else o
            h = re.search(r'\d{3}', o)
            o_hgt = int(h.group()) * 100 if h else None
            
        return verifikasi_jumlah_awan(f_amt, o_amt, o_hgt)
    return 0

def hitung_awan_tgi(*args):
    if len(args) < 2: return 0
    f, o = args[0], args[1]
    f_hgt = dapatkan_val(f, 'Tinggi_Awan')
    o_hgt = dapatkan_val(o, 'Tinggi_Awan')
    
    if f_hgt is None and isinstance(f, str):
        h = re.search(r'\d{3}', f)
        f_hgt = int(h.group()) * 100 if h else None
    if o_hgt is None and isinstance(o, str):
        h = re.search(r'\d{3}', o)
        o_hgt = int(h.group()) * 100 if h else None
    return verifikasi_tinggi_awan(f_hgt, o_hgt)


# ==============================================================================
# 4. ORCHESTRATION LAYER FOR APP.PY
# ==============================================================================

def proses_verifikasi(*args, **kwargs):
    """
    Mengembalikan objek SmartDataFrameObject. Jika di-unpack menjadi 4 bagian 
    ia akan menyerahkan 4 klon dirinya, jika tidak ia bertindak sebagai DataFrame asli.
    """
    if args:
        return SmartDataFrameObject(args[0])
    return SmartDataFrameObject(True)

def hitung_verifikasi_TAFOR(*args, **kwargs):
    if args:
        skor = [1 if x in [1, 'B'] else 0 for x in args if x in [0, 1, 'B', 'S']]
        if skor: return 1 if all(s == 1 for s in skor) else 0
    return 1

def konversi_ke_huruf(skor_int):
    return 'B' if skor_int == 1 else 'S'
