import re
import math

# ==============================================================================
# 1. LOGIKA VERIFIKASI ANGIN (WIND) - BERDASARKAN EVALUASI_ANGIN.PY
# ==============================================================================

def ekstrak_angin(sandi):
    """
    Mengekstrak parameter angin dan fenomena terkait (untuk mendeteksi TS/CB).
    Contoh sandi: 31015G25KT, VRB03KT
    """
    hasil = {'Arah_Angin': None, 'Kecepatan_Angin': None, 'Gust': None, 'Ada_TS': False, 'Ada_CB': False}
    if not isinstance(sandi, str):
        return hasil
        
    sandi = sandi.upper()
    
    # Deteksi Angin (Arah, Kecepatan, Gust)
    wind_match = re.search(r'\b(\d{3}|VRB|000)(\d{2,3})(?:G(\d{2,3}))?KT\b', sandi)
    if wind_match:
        hasil['Arah_Angin'] = wind_match.group(1)
        hasil['Kecepatan_Angin'] = wind_match.group(2)
        hasil['Gust'] = wind_match.group(3) # Group 3 menangkap nilai Gust jika ada
        
    # Deteksi Badai Guntur (TS) dan awan Cumulonimbus (CB) untuk syarat arah angin
    if 'TS' in sandi:
        hasil['Ada_TS'] = True
    if 'CB' in sandi:
        hasil['Ada_CB'] = True
        
    return hasil

def hitung_selisih_derajat(dir1, dir2):
    """Menghitung jarak selisih sudut dalam lingkaran 360 derajat"""
    diff = abs(dir1 - dir2)
    return diff if diff <= 180 else 360 - diff

def verifikasi_arah_angin(fcst, obs):
    """
    Menghitung skor Arah Angin (1 = Benar, 0 = Salah) berdasarkan SOP 2025
    """
    f_dir = fcst.get('Arah_Angin')
    f_spd = fcst.get('Kecepatan_Angin')
    o_dir = obs.get('Arah_Angin')
    o_spd = obs.get('Kecepatan_Angin')
    
    if not f_dir or not o_dir:
        return 0

    f_spd_val = int(f_spd) if f_spd and f_spd.isdigit() else 0
    o_spd_val = int(o_spd) if o_spd and o_spd.isdigit() else 0

    # Syarat c: Prakiraan VRB dan Pengamatan VRB
    if f_dir == 'VRB' and o_dir == 'VRB':
        return 1
        
    # Syarat d: Prakiraan VRB, Pengamatan teramati badai guntur (TS) atau awan CB
    if f_dir == 'VRB' and (obs.get('Ada_TS') or obs.get('Ada_CB')):
        return 1

    # Syarat e: Prakiraan kec. < 10 knot (arah bebas), Pengamatan kec. < 10 knot (arah bebas)
    if f_spd_val < 10 and o_spd_val < 10:
        return 1
        
    # Syarat f: Prakiraan VRB, Pengamatan kec. < 10 knot (arah berapapun/VRB)
    if f_dir == 'VRB' and o_spd_val < 10:
        return 1

    # Perhitungan matematis jika keduanya memiliki arah angka (Derajat)
    if f_dir.isdigit() and o_dir.isdigit():
        selisih = hitung_selisih_derajat(int(f_dir), int(o_dir))
        
        # Syarat a: Selisih <= 60 derajat
        if selisih <= 60:
            return 1
            
        # Syarat b: Selisih > 60 derajat, tetapi pengamatan kecepatan angin < 10 knot
        if selisih > 60 and o_spd_val < 10:
            return 1

    return 0

def verifikasi_kecepatan_angin(fcst, obs):
    """
    Menghitung skor Kecepatan Angin berdasarkan SOP 2025 (Toleransi 10 Knot)
    """
    f_spd = fcst.get('Kecepatan_Angin')
    o_spd = obs.get('Kecepatan_Angin')
    
    if not f_spd or not o_spd:
        return 0
        
    f_spd_val = int(f_spd) if f_spd.isdigit() else 0
    o_spd_val = int(o_spd) if o_spd.isdigit() else 0
    
    # Kriteria 2: Selisih absolut <= 10 knot
    if abs(f_spd_val - o_spd_val) <= 10:
        return 1
    return 0

def verifikasi_gusty(fcst, obs):
    """
    Menghitung skor kejadian Gusty berdasarkan SOP 2025
    """
    f_has_gust = fcst.get('Gust') is not None
    o_has_gust = obs.get('Gust') is not None
    
    # Kriteria 3: Benar jika sama-sama diprakirakan terjadi, atau sama-sama tidak terjadi
    if f_has_gust == o_has_gust:
        return 1
    return 0


# ==============================================================================
# 2. LOGIKA VERIFIKASI CUACA & AWAN - BERDASARKAN EVALUASI_CUACA.PY
# ==============================================================================

def klasifikasi_visibilitas(vis_val):
    """
    Mengelompokkan nilai visibilitas (meter) ke dalam 5 kelas sesuai SOP.
    """
    if vis_val is None:
        return -1 # Tidak valid
    if vis_val <= 799:
        return 1
    elif 800 <= vis_val <= 1499:
        return 2
    elif 1500 <= vis_val <= 2999:
        return 3
    elif 3000 <= vis_val <= 5000:
        return 4
    else:
        return 5 # > 5000 m (Termasuk 9999 / CAVOK)

def verifikasi_visibilitas(fcst_vis, obs_vis):
    """
    Skor Visibilitas: Benar (1) jika prakiraan dan pengamatan berada di kelas yang sama.
    """
    if fcst_vis is None or obs_vis is None:
        return 0
        
    kelas_f = klasifikasi_visibilitas(fcst_vis)
    kelas_o = klasifikasi_visibilitas(obs_vis)
    
    if kelas_f == kelas_o and kelas_f != -1:
        return 1
    return 0

def cek_presipitasi_sedang_lebat(wx_string):
    """
    Mendeteksi apakah terdapat presipitasi sedang (RA) atau lebat (+RA).
    Abaikan presipitasi ringan (-RA).
    """
    if not wx_string:
        return False
        
    wx_string = str(wx_string).upper()
    # Jika mengandung 'RA' tetapi TIDAK mengandung '-RA' (hujan ringan)
    if 'RA' in wx_string and '-RA' not in wx_string:
        return True
    return False

def verifikasi_presipitasi(fcst_wx, obs_wx):
    """
    Verifikasi fenomena cuaca hanya fokus pada presipitasi sedang/lebat.
    """
    f_is_heavy_mod = cek_presipitasi_sedang_lebat(fcst_wx)
    o_is_heavy_mod = cek_presipitasi_sedang_lebat(obs_wx)
    
    # Syarat 1: Diprakirakan sedang/lebat, dan teramati sedang/lebat
    if f_is_heavy_mod and o_is_heavy_mod:
        return 1
        
    # Syarat 2: Diprakirakan TIDAK terjadi sedang/lebat, dan teramati TIDAK terjadi/hanya ringan
    if not f_is_heavy_mod and not o_is_heavy_mod:
        return 1
        
    return 0

def klasifikasi_jumlah_awan(amt_string):
    """
    Mengelompokkan jumlah awan ke dalam 2 kelas biner.
    Kelas 1: SKC, NSC, CAVOK, FEW, SCT
    Kelas 2: BKN, OVC
    """
    if not amt_string:
        return 1 # Asumsi clear
        
    amt_string = str(amt_string).upper()
    if amt_string in ['BKN', 'OVC']:
        return 2
    return 1

def verifikasi_jumlah_awan(fcst_amt, obs_amt, obs_height_ft):
    """
    Verifikasi jumlah awan bergantung pada tinggi dasar awan observasi.
    """
    # SOP: Jika awan observasi di atas 1500 m / 5000 ft, prakiraan apapun nilainya SELALU BENAR
    if obs_height_ft is not None and obs_height_ft > 5000:
        return 1
        
    # Jika tinggi <= 1500 m, cocokkan kelas binernya
    kelas_f = klasifikasi_jumlah_awan(fcst_amt)
    kelas_o = klasifikasi_jumlah_awan(obs_amt)
    
    if kelas_f == kelas_o:
        return 1
    return 0

def verifikasi_tinggi_awan(fcst_height_ft, obs_height_ft):
    """
    Verifikasi tinggi dasar awan menggunakan batas toleransi selisih dan persentase.
    """
    # Jika tidak ada awan di kedua belah pihak (CAVOK/NSC) = Benar
    if fcst_height_ft is None and obs_height_ft is None:
        return 1
        
    # Jika salah satu ada awan dan satunya tidak, otomatis salah
    if fcst_height_ft is None or obs_height_ft is None:
        return 0
        
    selisih = abs(fcst_height_ft - obs_height_ft)
    
    # Kriteria a: Nilai prakiraan < 1000 ft, selisih <= 100 ft
    if fcst_height_ft < 1000:
        if selisih <= 100:
            return 1
            
    # Kriteria b: Nilai prakiraan >= 1000 ft, selisih <= 30% dari nilai prakiraan
    else:
        toleransi = 0.3 * fcst_height_ft
        if selisih <= toleransi:
            return 1
            
    return 0


# ==============================================================================
# 3. UTILITY INTERFACE - KONVERSI SKOR
# ==============================================================================

def konversi_ke_huruf(skor_int):
    """Mengubah nilai integer 1/0 menjadi string B/S"""
    return 'B' if skor_int == 1 else 'S'


# ==============================================================================
# 4. JEMBATAN PENGHUBUNG KODE LAMA (LEGACY COMPATIBILITY LAYER FOR EXCEL EXPORT)
# ==============================================================================

def hitung_angin_arah(fcst, obs):
    """Jembatan pintar untuk excel_export yang mengirim string langsung atau dict"""
    if isinstance(fcst, str): fcst = ekstrak_angin(fcst)
    if isinstance(obs, str): obs = ekstrak_angin(obs)
    return verifikasi_arah_angin(fcst, obs)

def hitung_angin_kec(fcst, obs):
    """Jembatan pintar untuk excel_export yang mengirim string langsung atau dict"""
    if isinstance(fcst, str): fcst = ekstrak_angin(fcst)
    if isinstance(obs, str): obs = ekstrak_angin(obs)
    return verifikasi_kecepatan_angin(fcst, obs)

def hitung_gusty(fcst, obs):
    if isinstance(fcst, str): fcst = ekstrak_angin(fcst)
    if isinstance(obs, str): obs = ekstrak_angin(obs)
    return verifikasi_gusty(fcst, obs)

# Menyediakan alias nama lama agar tidak merusak proses impor di excel_export.py
hitung_visibilitas = verifikasi_visibilitas
hitung_cuaca = verifikasi_presipitasi
hitung_presipitasi = verifikasi_presipitasi
hitung_jumlah_awan = verifikasi_jumlah_awan
hitung_awan_jumlah = verifikasi_jumlah_awan
hitung_tinggi_awan = verifikasi_tinggi_awan
hitung_awan_tinggi = verifikasi_tinggi_awan
