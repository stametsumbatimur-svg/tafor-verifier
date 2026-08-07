# 🔥 SIVETA - Verification Core Logic 
import re
from datetime import datetime, timedelta
import pandas as pd
import calendar

# =========================================================================
# 0. PRA-KOMPILASI REGEX & PEMBANTU DATETIME
# =========================================================================
RE_DATE_CLEAN = re.compile(r'\b\d{4}/\d{4}\b')
RE_WIND = re.compile(r'\b(\d{3}|\/\/\/|VRB|000)(\d{2,3})(G\d{2,3})?KT\b')
RE_VIS = re.compile(r'\b\d{4}\b')
RE_WX = re.compile(
    r'(?<![A-Z])[-+]?(?:MI|BC|PR|DR|BL|SH|TS|FZ)?(?:DZ|RA|SN|SG|PL|GR|GS|BR|FG|FU|VA|DU|SA|HZ|PO|SQ|FC|SS|DS|TS)\b'
)
RE_CLOUD = re.compile(r'\b(FEW|SCT|BKN|OVC)(\d{3,4})(?:CB|TCU)?\b')
RE_PARTS = re.compile(
    r'\b(BECMG|TEMPO|PROB30 TEMPO|PROB40 TEMPO|PROB30|PROB40|FM\d{6})\b'
)
RE_TIME_GRP = re.compile(r'(\d{2})(\d{2})/(\d{2})(\d{2})')
RE_WX_EXCLUDE = re.compile(
    r'\b(HZ|RA|TSRA|BR|DZ|FG|VCTS|TS|SHRA|MIFG|SQ|FC)\b'
)
RE_VALID_TAF = re.compile(r'\d{6}Z\s+(\d{2})(\d{2})/\d{4}')
RE_AMD_COR = re.compile(r'\b(AMD|COR)\b')


def fix_valid_datetime(
    t_issue: pd.Timestamp, target_day: int, target_hour: int
) -> pd.Timestamp:
  """Menangani perhitungan tanggal validitas TAF yang menyeberang bulan (Month Rollover)"""
  year = t_issue.year
  month = t_issue.month

  # Jika TAF terbit akhir bulan (tgl 21-31) dan target_day awal bulan (tgl 1-9) -> Masuk Bulan Depan
  if t_issue.day > 20 and target_day < 10:
    if month == 12:
      month = 1
      year += 1
    else:
      month += 1
  # Jika TAF terbit awal bulan (tgl 1-4) dan target_day akhir bulan (tgl 20-31) -> Masuk Bulan Lalu
  elif t_issue.day < 5 and target_day > 20:
    if month == 1:
      month = 12
      year -= 1
    else:
      month -= 1

  day_offset = 0
  if target_hour >= 24:
    target_hour = 0
    day_offset = 1

  # Batasi hari agar tidak melebihi jumlah hari maksimal pada bulan tersebut
  max_days = calendar.monthrange(year, month)[1]
  safe_day = min(max(1, int(target_day)), max_days)

  try:
    dt = pd.Timestamp(
        year=year,
        month=month,
        day=safe_day,
        hour=int(target_hour),
        minute=0,
        second=0,
    )
  except Exception:
    dt = t_issue

  if day_offset:
    dt += pd.Timedelta(days=day_offset)
  return dt

def get_trend_datetime(
    t_valid: pd.Timestamp, day: int, hour: int
) -> pd.Timestamp:
  # Handle TAF 24:00 notation (24:00 represents 00:00 of the next day)
  day_offset = 0
  if hour >= 24:
    hour = 0
    day_offset = 1

  year = t_valid.year
  month = t_valid.month

  # Detect month rollover (e.g., t_valid is late in the month, target day is early next month)
  if day < t_valid.day and (t_valid.day - day) > 15:
    if month == 12:
      month = 1
      year += 1
    else:
      month += 1

  # Batasi hari agar tidak melebihi jumlah hari maksimal pada bulan tersebut
  max_days = calendar.monthrange(year, month)[1]
  safe_day = min(max(1, int(day)), max_days)

  try:
    dt = pd.Timestamp(
        year=year, month=month, day=safe_day, hour=int(hour), minute=0, second=0
    )
  except Exception:
    dt = t_valid

  if day_offset:
    dt += pd.Timedelta(days=day_offset)

  return dt

# =========================================================================
# 1. PARSER SANDI METAR / SPECI / TAF
# =========================================================================
def ekstrak_param_metar_speci(sandi_teks):
    if pd.isna(sandi_teks) or sandi_teks == '-':
        return '-', '-', '-', '-', '-', '-', False
    sandi_cleaned = RE_DATE_CLEAN.sub('', str(sandi_teks).strip())

    arah_wind, kec_wind = '-', '-'
    wind_match = RE_WIND.search(sandi_cleaned)
    if wind_match:
        arah_wind = wind_match.group(1)
        kec_wind = (
            f'{int(wind_match.group(2))}G{int(wind_match.group(3)[1:])}'
            if wind_match.group(3)
            else str(int(wind_match.group(2)))
        )

    vis = (
        '9999'
        if 'CAVOK' in sandi_cleaned
        else ('-' if not (v := RE_VIS.search(sandi_cleaned)) else v.group(0))
    )
    wx = (
        '-'
        if 'CAVOK' in sandi_cleaned
        else ('-' if not (w := RE_WX.search(sandi_cleaned)) else w.group(0))
    )

    awan_jml, awan_tgi = '-', '-'
    if any(k in sandi_cleaned for k in ['CAVOK', 'NSC', 'NCD']):
        awan_jml, awan_tgi = 'NSC', '5000'
    else:
        cloud_matches = RE_CLOUD.findall(sandi_cleaned)
        if cloud_matches:
            terendah = min(cloud_matches, key=lambda x: int(x[1]))
            awan_jml, awan_tgi = terendah[0], str(int(terendah[1]) * 100)

    has_ts_cb = 'TS' in sandi_cleaned or 'CB' in sandi_cleaned
    return arah_wind, kec_wind, vis, wx, awan_jml, awan_tgi, has_ts_cb


def parse_sandi(grup_teks):
    if not grup_teks or str(grup_teks).strip() == '':
        return '-', '-', '-', '-', '-', '-'
    sandi_cleaned = RE_DATE_CLEAN.sub('', str(grup_teks).strip())

    arah, kec = '-', '-'
    w_match = RE_WIND.search(sandi_cleaned)
    if w_match:
        arah = w_match.group(1)
        kec = (
            f'{int(w_match.group(2))}G{int(w_match.group(3)[1:])}'
            if w_match.group(3)
            else str(int(w_match.group(2)))
        )

    vis = (
        '9999'
        if 'CAVOK' in sandi_cleaned
        else ('-' if not (v := RE_VIS.search(sandi_cleaned)) else v.group(0))
    )
    wx = (
        '-'
        if 'CAVOK' in sandi_cleaned or 'NSW' in sandi_cleaned
        else ('-' if not (w := RE_WX.search(sandi_cleaned)) else w.group(0))
    )

    aw_jml, aw_tgi = '-', '-'
    if 'CAVOK' in sandi_cleaned:
        aw_jml, aw_tgi = 'NSC', '5000'
    else:
        c_matches = RE_CLOUD.findall(sandi_cleaned)
        if c_matches:
            terendah = min(c_matches, key=lambda x: int(x[1]))
            aw_jml, aw_tgi = terendah[0], str(int(terendah[1]) * 100)

    return arah, kec, vis, wx, aw_jml, aw_tgi


# =========================================================================
# 2. KRITERIA EVALUASI AKURASI (SOP BMKG 2025)
# =========================================================================
def hitung_angin_arah(m_dir, t_dir, m_kec='-', t_kec='-', m_ts_cb=False):
    m_str, t_str = str(m_dir).strip().upper(), str(t_dir).strip().upper()
    m_spd = (
        int(str(m_kec).split('G')[0])
        if 'G' in str(m_kec)
        else (int(m_kec) if str(m_kec).isdigit() else 0)
    )
    t_spd = (
        int(str(t_kec).split('G')[0])
        if 'G' in str(t_kec)
        else (int(t_kec) if str(t_kec).isdigit() else 0)
    )

    if m_str == t_str:
        return (m_str, 'B')
    if m_str in ['VRB', '///'] and t_str in ['VRB', '///']:
        return (m_str, 'B')
    if (m_str == 'VRB' or t_str == 'VRB') and (
        m_ts_cb or m_spd < 10 or t_spd < 10
    ):
        return (m_str, 'B')
    if m_spd < 10 and t_spd < 10:
        return (m_str, 'B')

    try:
        m, t = int(m_str), int(t_str)
        diff = abs(m - t)
        diff = diff if diff <= 180 else 360 - diff
        return (
            (m_str, 'B')
            if diff <= 60 or (diff > 60 and m_spd < 10) or m_ts_cb
            else (m_str, 'S')
        )
    except:
        return (m_str, 'S')


def hitung_angin_kec(m_kec, t_kec):
    if m_kec == '-' or t_kec == '-' or m_kec == 'NIL' or t_kec == 'NIL':
        return '-', 'NIL'
    try:
        m_base = int(str(m_kec).split('G')[0]) if 'G' in str(m_kec) else int(m_kec)
        t_base = int(str(t_kec).split('G')[0]) if 'G' in str(t_kec) else int(t_kec)
        m_gust = int(str(m_kec).split('G')[1]) if 'G' in str(m_kec) else 0
        t_gust = int(str(t_kec).split('G')[1]) if 'G' in str(t_kec) else 0

        diff_base = abs(m_base - t_base)
        stat_base = 'B' if diff_base <= 10 else 'S'

        if (m_gust > 0) != (t_gust > 0):
            return f'B:{diff_base}|G:{abs(m_gust-t_gust)}', 'S'
        return str(diff_base), stat_base
    except:
        return '-', 'S'


def get_vis_class(vis_value):
    if vis_value < 800:
        return 1
    elif 800 <= vis_value < 1500:
        return 2
    elif 1500 <= vis_value < 3000:
        return 3
    elif 3000 <= vis_value <= 5000:
        return 4
    return 5


def hitung_vis(m_vis, t_vis):
    try:
        m, t = int(m_vis), int(t_vis)
        return (m, 'B') if get_vis_class(m) == get_vis_class(t) else (m, 'S')
    except:
        return (None, 'S')


def cek_presipitasi_sedang_lebat(wx_str):
    if pd.isna(wx_str) or wx_str in ['-', 'NSW', 'NIL', 'CAVOK']:
        return False
    s = str(wx_str).upper().strip()
    precip_codes = ['RA', 'DZ', 'SN', 'SG', 'PL', 'GR', 'GS', 'SH', 'TS']
    if not any(code in s for code in precip_codes):
        return False

    tokens = s.split()
    for t in tokens:
        if any(code in t for code in precip_codes):
            if not t.startswith('-'):
                return True
    return False


def hitung_cuaca(m_wx, t_wx):
    return 'MATCH', (
        'B'
        if cek_presipitasi_sedang_lebat(m_wx)
        == cek_presipitasi_sedang_lebat(t_wx)
        else 'S'
    )


def hitung_awan_jml(m_jml, t_jml, m_tgi):
    if m_jml == '-' or t_jml == '-':
        return '-', 'NIL'
    try:
        if m_tgi != '-' and int(m_tgi) >= 5000:
            return '>5000ft', 'B'
        km = 2 if str(m_jml).upper() in ['BKN', 'OVC'] else 1
        kt = 2 if str(t_jml).upper() in ['BKN', 'OVC'] else 1
        return f'K:{km}vs{kt}', ('B' if km == kt else 'S')
    except:
        return '-', 'S'


def hitung_awan_tgi(m_tgi, t_tgi):
    if m_tgi == '-' or t_tgi == '-':
        return '-', 'NIL'
    try:
        mt, tt = int(m_tgi), int(t_tgi)
        if mt >= 5000 or tt >= 5000:
            return '>5000ft', 'B'

        diff = abs(mt - tt)
        return (
            str(diff),
            'B' if (diff <= 100 if tt < 1000 else diff <= (0.3 * tt)) else 'S',
        )
    except:
        return '-', 'S'


# =========================================================================
# 3. KONTROLLER EVALUASI
# =========================================================================
def evaluasi_sandi_tunggal(
    m_obs_data,
    t_ar,
    t_ke,
    t_vi,
    t_wx,
    t_aj,
    t_at,
    base_bundle=None,
    is_grup_prob=False,
    is_grup_tempo=False,
    is_grup_becmg_trans=False,
):
    has_ts_cb = m_obs_data.get('M_TS_CB', False)
    _, s_ar = hitung_angin_arah(
        m_obs_data['M_Arah'], t_ar, m_obs_data['M_Kec'], t_ke, has_ts_cb
    )
    _, s_ke = hitung_angin_kec(m_obs_data['M_Kec'], t_ke)
    _, s_vi = hitung_vis(m_obs_data['M_Vis'], t_vi)
    _, s_wx = hitung_cuaca(m_obs_data['M_Wx'], t_wx)
    _, s_aj = hitung_awan_jml(
        m_obs_data['M_AwanJml'], t_aj, m_obs_data['M_AwanTgi']
    )
    _, s_at = hitung_awan_tgi(m_obs_data['M_AwanTgi'], t_at)

    if (
        is_grup_prob or is_grup_tempo or is_grup_becmg_trans
    ) and base_bundle is not None:
        _, b_ar = hitung_angin_arah(
            m_obs_data['M_Arah'],
            base_bundle[0],
            m_obs_data['M_Kec'],
            base_bundle[1],
            has_ts_cb,
        )
        _, b_ke = hitung_angin_kec(m_obs_data['M_Kec'], base_bundle[1])
        _, b_vi = hitung_vis(m_obs_data['M_Vis'], base_bundle[2])
        _, b_wx = hitung_cuaca(m_obs_data['M_Wx'], base_bundle[3])
        _, b_aj = hitung_awan_jml(
            m_obs_data['M_AwanJml'], base_bundle[4], m_obs_data['M_AwanTgi']
        )
        _, b_at = hitung_awan_tgi(m_obs_data['M_AwanTgi'], base_bundle[5])

        if s_ar == 'S' and b_ar == 'B': s_ar = 'B'
        if s_ke == 'S' and b_ke == 'B': s_ke = 'B'
        if s_vi == 'S' and b_vi == 'B': s_vi = 'B'
        if s_wx == 'S' and b_wx == 'B': s_wx = 'B'
        if s_aj == 'S' and b_aj == 'B': s_aj = 'B'
        if s_at == 'S' and b_at == 'B': s_at = 'B'

    return (
        ('S' if 'S' in [s_ar, s_ke, s_vi, s_wx, s_aj, s_at] else 'B'),
        s_ar,
        s_ke,
        s_vi,
        s_wx,
        s_aj,
        s_at,
    )


def proses_verifikasi(df_metar, df_taf, df_speci):
    col_waktu_metar = next(
        (
            c
            for c in df_metar.columns
            if any(k in c.lower() for k in ['waktu', 'date', 'tanggal', 'time'])
        ),
        df_metar.columns[0],
    )
    col_teks_metar = next(
        (
            c
            for c in df_metar.columns
            if 'type' not in c.lower()
            and 'status' not in c.lower()
            and any(
                k in c.lower() for k in ['sandi', 'text', 'message', 'report', 'isi']
            )
        ),
        df_metar.columns[1],
    )
    col_waktu_taf = next(
        (
            c
            for c in df_taf.columns
            if any(k in c.lower() for k in ['waktu', 'date', 'tanggal', 'time'])
        ),
        df_taf.columns[0],
    )
    col_teks_taf = next(
        (
            c
            for c in df_taf.columns
            if 'type' not in c.lower()
            and 'status' not in c.lower()
            and any(
                k in c.lower() for k in ['sandi', 'text', 'message', 'report', 'isi']
            )
        ),
        df_taf.columns[1],
    )

    has_cccc = 'cccc' in df_metar.columns

    metar_list = (
        df_metar.assign(
            dt_obj=pd.to_datetime(
                df_metar[col_waktu_metar].astype(str).str.slice(0, 19),
                format='%Y-%m-%d %H:%M:%S',
                errors='coerce',
            )
        )
        .dropna(subset=['dt_obj'])
        .sort_values('dt_obj')
        .to_dict('records')
    )
    taf_raw = (
        df_taf.assign(
            dt_obj=pd.to_datetime(
                df_taf[col_waktu_taf].astype(str).str.slice(0, 19),
                format='%Y-%m-%d %H:%M:%S',
                errors='coerce',
            )
        )
        .dropna(subset=['dt_obj'])
        .sort_values('dt_obj')
        .to_dict('records')
    )

    if df_speci is not None and not df_speci.empty:
        speci_raw = (
            df_speci.assign(
                dt_obj=pd.to_datetime(
                    df_speci[df_speci.columns[0]].astype(str).str.slice(0, 19),
                    format='%Y-%m-%d %H:%M:%S',
                    errors='coerce',
                )
            )
            .dropna(subset=['dt_obj'])
            .sort_values('dt_obj')
            .to_dict('records')
        )
    else:
        speci_raw = []

    taf_list = []
    for tr in taf_raw:
        t_teks = str(tr[col_teks_taf])
        t_issue = tr['dt_obj']
        v_match = RE_VALID_TAF.search(t_teks)
        v_dt = t_issue
        if v_match:
            try:
                target_day = int(v_match.group(1))
                target_hour = int(v_match.group(2))
                v_dt = fix_valid_datetime(t_issue, target_day, target_hour)
            except ValueError:
                pass
        poin = 1 if RE_AMD_COR.search(t_teks) else 0
        taf_list.append(
            {'issue': t_issue, 'valid': v_dt, 'poin': poin, 'teks': t_teks}
        )

    baris_analisis_final, baris_speci_final = [], []

    for m in metar_list:
        tgl_jam_aktual = m['dt_obj']
        teks_metar = m[col_teks_metar]
        m_stasiun = m['cccc'] if has_cccc else 'WATU'

        m_ar, m_ke, m_vi, m_wx, m_aj, m_at, m_ts_cb = ekstrak_param_metar_speci(
            teks_metar
        )

        kandidat = [
            t
            for t in taf_list
            if t['issue'] <= tgl_jam_aktual
            and t['valid'] <= tgl_jam_aktual < t['valid'] + timedelta(hours=12)
        ]
        if not kandidat:
            continue

        kandidat.sort(key=lambda x: (x['valid'], x['issue'], x['poin']))
        taf_obj_aktif = kandidat[-1]
        taf_aktif = taf_obj_aktif['teks']
        t_valid_aktif = taf_obj_aktif['valid']

        parts = RE_PARTS.split(str(taf_aktif))
        b_ar, b_ke, b_vi, b_wx, b_aj, b_at = parse_sandi(parts[0])
        cur_ar, cur_ke, cur_vi, cur_wx, cur_aj, cur_at = (
            b_ar, b_ke, b_vi, b_wx, b_aj, b_at,
        )
        t_ar, t_ke, t_vi, t_wx, t_aj, t_at = b_ar, b_ke, b_vi, b_wx, b_aj, b_at

        is_grup_prob = is_grup_tempo = is_grup_becmg_trans = False
        cur_grup_aktif = 'BASE'

        for i in range(1, len(parts), 2):
            tipe, isi = parts[i], parts[i + 1]

            if tipe.startswith('FM'):
                s_hr = int(tipe[4:6])
                dt_start = get_trend_datetime(t_valid_aktif, t_valid_aktif.day, s_hr)
                dt_end = t_valid_aktif + timedelta(hours=12)
            else:
                time_match = RE_TIME_GRP.search(isi)
                if time_match:
                    s_day, s_hr = int(time_match.group(1)), int(time_match.group(2))
                    e_day, e_hr = int(time_match.group(3)), int(time_match.group(4))
                    dt_start = get_trend_datetime(t_valid_aktif, s_day, s_hr)
                    dt_end = get_trend_datetime(t_valid_aktif, e_day, e_hr)
                else:
                    continue

            g_ar, g_ke, g_vi, g_wx, g_aj, g_at = parse_sandi(isi)

            if tipe.startswith('FM') or tipe == 'BECMG':
                if tgl_jam_aktual >= dt_start:
                    if g_ar != '-': cur_ar = g_ar
                    if g_ke != '-': cur_ke = g_ke
                    if g_vi != '-': cur_vi = g_vi
                    if (
                        g_wx != '-'
                        and not RE_WX_EXCLUDE.search(isi)
                        and 'CAVOK' not in isi
                    ):
                        cur_wx = g_wx
                    if g_aj != '-': cur_aj = g_aj
                    if g_at != '-': cur_at = g_at

                    t_ar, t_ke, t_vi, t_wx, t_aj, t_at = (
                        cur_ar, cur_ke, cur_vi, cur_wx, cur_aj, cur_at,
                    )
                    if tipe == 'BECMG':
                        is_grup_becmg_trans = tgl_jam_aktual < dt_end

                    if time_match:
                        cur_grup_aktif = (
                            f'{tipe}'
                            f' {time_match.group(1)}{time_match.group(2)}/{time_match.group(3)}{time_match.group(4)}'
                        )
                    else:
                        cur_grup_aktif = tipe

            elif 'TEMPO' in tipe or 'PROB' in tipe:
                if dt_start <= tgl_jam_aktual < dt_end:
                    if g_ar != '-': t_ar = g_ar
                    if g_ke != '-': t_ke = g_ke
                    if g_vi != '-': t_vi = g_vi
                    if (
                        g_wx != '-'
                        and not RE_WX_EXCLUDE.search(isi)
                        and 'CAVOK' not in isi
                    ):
                        t_wx = g_wx
                    if g_aj != '-': t_aj = g_aj
                    if g_at != '-': t_at = g_at

                    if 'PROB' in tipe: is_grup_prob = True
                    if 'TEMPO' in tipe: is_grup_tempo = True

                    if time_match:
                        cur_grup_aktif = (
                            f'{tipe}'
                            f' {time_match.group(1)}{time_match.group(2)}/{time_match.group(3)}{time_match.group(4)}'
                        )
                    else:
                        cur_grup_aktif = tipe

        m_obs_data = {
            'M_Arah': m_ar,
            'M_Kec': m_ke,
            'M_Vis': m_vi,
            'M_Wx': m_wx,
            'M_AwanJml': m_aj,
            'M_AwanTgi': m_at,
            'M_TS_CB': m_ts_cb,
        }
        base_bundle = (cur_ar, cur_ke, cur_vi, cur_wx, cur_aj, cur_at)

        status_jam_ini, s_ar, s_ke, s_vi, s_wx, s_aj, s_at = evaluasi_sandi_tunggal(
            m_obs_data,
            t_ar,
            t_ke,
            t_vi,
            t_wx,
            t_aj,
            t_at,
            base_bundle,
            is_grup_prob,
            is_grup_tempo,
            is_grup_becmg_trans,
        )

        is_crit = 'NORMAL'
        try:
            if int(m_vi) < 5000 or (m_aj in ['BKN', 'OVC'] and int(m_at) < 1500):
                is_crit = 'CRITICAL MINIMA'
        except:
            pass

        baris_analisis_final.append({
            'Waktu Aktual (UTC)': tgl_jam_aktual.strftime('%Y-%m-%d %H:%M:%S'),
            'Sandi METAR Aktual': teks_metar,
            'Sandi TAF Prakiraan': taf_aktif,
            'Grup_Aktif': cur_grup_aktif,
            'Change_Group': cur_grup_aktif,
            'M_Arah': m_ar,
            'T_Arah': t_ar,
            'S_Arah': s_ar,
            'M_Kec': m_ke,
            'T_Kec': t_ke,
            'S_Kec': s_ke,
            'M_Vis': m_vi,
            'T_Vis': t_vi,
            'S_Vis': s_vi,
            'M_Wx': m_wx,
            'T_Wx': t_wx,
            'S_Wx': s_wx,
            'M_AwanJml': m_aj,
            'T_AwanJml': t_aj,
            'S_AwanJml': s_aj,
            'M_AwanTgi': m_at,
            'T_AwanTgi': t_at,
            'S_AwanTgi': s_at,
            'M_TS_CB': m_ts_cb,
            'Status_Minima': is_crit,
            'Hasil Akhir': 'ACCURATE' if status_jam_ini == 'B' else 'MISS',
            'Kode_Stasiun': m_stasiun,
        })

    return (
        pd.DataFrame(baris_analisis_final),
        pd.DataFrame(baris_speci_final),
        None,
        None,
    )


# =========================================================================
# 4. PEMBUATAN LAPORAN EXCEL (DENGAN SELEKSI OTOMATIS METAR TERBAIK)
# =========================================================================
def buat_tabel_laporan_excel(df_input):
  df_work = df_input.to_dict('records')
  # 🎯 KUMPULKAN SELURUH METAR BULANAN UNTUK PENCARIAN JENDELA WAKTU LENGKAP
  all_metars = [
      (
          pd.to_datetime(
              r['Waktu Aktual (UTC)'],
              format='%Y-%m-%d %H:%M:%S',
              errors='coerce',
          ),
          r,
      )
      for r in df_work
  ]
  all_metars.sort(key=lambda x: x[0])
  baris_laporan = []

  taf_groups = {}
  for row in df_work:
    if row['Sandi TAF Prakiraan'] == '-':
      continue
    sandi = row['Sandi TAF Prakiraan']

    validity_match = re.search(r'\b(\d{2})\d{2}/\d{2}\d{2}\b', str(sandi))
    dt_val = pd.to_datetime(
        row['Waktu Aktual (UTC)'],
        format='%Y-%m-%d %H:%M:%S',
        errors='coerce',
    )

    tgl_taf = (
        validity_match.group(1) if validity_match else dt_val.strftime('%d')
    )

    key_taf = (tgl_taf, sandi)
    if key_taf not in taf_groups:
      taf_groups[key_taf] = []
    taf_groups[key_taf].append((dt_val, row))

  for (tgl_str, taf_sandi), list_rows in taf_groups.items():
    list_rows.sort(key=lambda x: x[0])

    v_match = RE_VALID_TAF.search(taf_sandi)
    if v_match:
      try:
        target_day = int(v_match.group(1))
        target_hour = int(v_match.group(2))
        t_valid_taf = fix_valid_datetime(
            list_rows[0][0], target_day, target_hour
        )
      except Exception:
        t_valid_taf = list_rows[0][0]
    else:
      t_valid_taf = list_rows[0][0]

    baris_m_base = list_rows[0][1]

    parts = RE_PARTS.split(str(taf_sandi))
    b_ar, b_ke, b_vi, b_wx, b_aj, b_at = parse_sandi(parts[0])
    cur_ar, cur_ke, cur_vi, cur_wx, cur_aj, cur_at = (
        b_ar,
        b_ke,
        b_vi,
        b_wx,
        b_aj,
        b_at,
    )

    validity_match = re.search(r'\b\d{2}(\d{2})/\d{2}(\d{2})\b', str(taf_sandi))
    if validity_match:
      jam_mulai = validity_match.group(1)
      jam_selesai = validity_match.group(2)
      jangka_base = f'{jam_mulai}-{jam_selesai}'
      jam_akhir_taf = jam_selesai
    else:
      jam_mulai = '00'
      jam_selesai = '24'
      jangka_base = '00-24'
      jam_akhir_taf = '24'

    label_perubahan = (
        'Base (AMD)'
        if 'AMD' in str(taf_sandi).upper()
        else ('Base (COR)' if 'COR' in str(taf_sandi).upper() else 'Base')
    )

    m_obs_base = {
        'M_Arah': baris_m_base['M_Arah'],
        'M_Kec': baris_m_base['M_Kec'],
        'M_Vis': baris_m_base['M_Vis'],
        'M_Wx': baris_m_base['M_Wx'],
        'M_AwanJml': baris_m_base['M_AwanJml'],
        'M_AwanTgi': baris_m_base['M_AwanTgi'],
        'M_TS_CB': baris_m_base.get('M_TS_CB', False),
    }
    _, s_ar, s_ke, s_vi, s_wx, s_aj, s_at = evaluasi_sandi_tunggal(
        m_obs_base, b_ar, b_ke, b_vi, b_wx, b_aj, b_at
    )

    baris_laporan.append({
        'Tanggal': tgl_str,
        'Jangka_Waktu': jangka_base,
        'Perubahan': label_perubahan,
        'T_Arah': b_ar,
        'T_Kec': b_ke,
        'T_Vis': b_vi,
        'T_Wx': b_wx,
        'T_AwanJml': b_aj,
        'T_AwanTgi': b_at,
        'M_Arah': baris_m_base['M_Arah'],
        'S_Arah': s_ar,
        'M_Kec': baris_m_base['M_Kec'],
        'S_Kec': s_ke,
        'M_Vis': baris_m_base['M_Vis'],
        'S_Vis': s_vi,
        'M_Wx': baris_m_base['M_Wx'],
        'S_Wx': s_wx,
        'M_AwanJml': baris_m_base['M_AwanJml'],
        'S_AwanJml': s_aj,
        'M_AwanTgi': baris_m_base['M_AwanTgi'],
        'S_AwanTgi': s_at,
    })

    for i in range(1, len(parts), 2):
      tipe, isi = parts[i], parts[i + 1]

      label_trend = (
          'FM'
          if tipe.startswith('FM')
          else (
              'TEMPO'
              if 'TEMPO' in tipe
              else (
                  'BECMG'
                  if 'BECMG' in tipe
                  else ('PROB' if 'PROB' in tipe else tipe)
              )
          )
      )

      time_match = RE_TIME_GRP.search(isi)

      if tipe.startswith('FM'):
        s_hr = int(tipe[4:6])
        dt_start = get_trend_datetime(t_valid_taf, t_valid_taf.day, s_hr)
        dt_end = t_valid_taf + timedelta(hours=12)
        jangka_trend = f'FM.{tipe[4:6]}-{jam_akhir_taf}'
      else:
        if time_match:
          s_day, s_hr = int(time_match.group(1)), int(time_match.group(2))
          e_day, e_hr = int(time_match.group(3)), int(time_match.group(4))
          dt_start = get_trend_datetime(t_valid_taf, s_day, s_hr)
          dt_end = get_trend_datetime(t_valid_taf, e_day, e_hr)
          prefix = 'T' if 'TEMPO' in tipe else ('B' if 'BECMG' in tipe else 'P')
          jangka_trend = (
              f'{prefix}.{time_match.group(2)}-{time_match.group(4)}'
          )
        else:
          dt_start = t_valid_taf
          dt_end = t_valid_taf + timedelta(hours=12)
          jangka_trend = tipe

      base_bundle_prev = (cur_ar, cur_ke, cur_vi, cur_wx, cur_aj, cur_at)
      g_ar, g_ke, g_vi, g_wx, g_aj, g_at = parse_sandi(isi)

      if tipe.startswith('FM') or tipe == 'BECMG':
        if g_ar != '-':
          cur_ar = g_ar
        if g_ke != '-':
          cur_ke = g_ke
        if g_vi != '-':
          cur_vi = g_vi
        if g_wx != '-' and not RE_WX_EXCLUDE.search(isi) and 'CAVOK' not in isi:
          cur_wx = g_wx
        if g_aj != '-':
          cur_aj = g_aj
        if g_at != '-':
          cur_at = g_at
        t_ar, t_ke, t_vi, t_wx, t_aj, t_at = (
            cur_ar,
            cur_ke,
            cur_vi,
            cur_wx,
            cur_aj,
            cur_at,
        )
      else:
        t_ar = g_ar if g_ar != '-' else cur_ar
        t_ke = g_ke if g_ke != '-' else cur_ke
        t_vi = g_vi if g_vi != '-' else cur_vi
        t_wx = (
            g_wx
            if (
                g_wx != '-'
                and not RE_WX_EXCLUDE.search(isi)
                and 'CAVOK' not in isi
            )
            else cur_wx
        )
        t_aj = g_aj if g_aj != '-' else cur_aj
        t_at = g_at if g_at != '-' else cur_at

      # 🎯 1. KUMPULKAN SELURUH METAR DI JENDELA WAKTU [dt_start, dt_end] DARI SELURUH DATASET BULANAN
      in_window_rows = [
          r for dt_o, r in all_metars if dt_start <= dt_o <= dt_end
      ]
      if not in_window_rows:
        in_window_rows = [baris_m_base]

      # 🎯 2. SELEKSI OTOMATIS BERDASARKAN RANKING 2 TINGKAT (SMART BEST-MATCH)
      best_metar = in_window_rows[0]
      best_tuple = (-1, -1)
      best_scores = None

      for r in in_window_rows:
        m_obs = {
            'M_Arah': r['M_Arah'],
            'M_Kec': r['M_Kec'],
            'M_Vis': r['M_Vis'],
            'M_Wx': r['M_Wx'],
            'M_AwanJml': r['M_AwanJml'],
            'M_AwanTgi': r['M_AwanTgi'],
            'M_TS_CB': r.get('M_TS_CB', False),
        }

        _, ar_d, ke_d, vi_d, wx_d, aj_d, at_d = evaluasi_sandi_tunggal(
            m_obs,
            t_ar,
            t_ke,
            t_vi,
            t_wx,
            t_aj,
            t_at,
            base_bundle=None,
            is_grup_prob=False,
            is_grup_tempo=False,
            is_grup_becmg_trans=False,
        )
        direct_b = [ar_d, ke_d, vi_d, wx_d, aj_d, at_d].count('B')

        _, ar_t, ke_t, vi_t, wx_t, aj_t, at_t = evaluasi_sandi_tunggal(
            m_obs,
            t_ar,
            t_ke,
            t_vi,
            t_wx,
            t_aj,
            t_at,
            base_bundle=base_bundle_prev,
            is_grup_prob=('PROB' in tipe),
            is_grup_tempo=('TEMPO' in tipe),
            is_grup_becmg_trans=('BECMG' in tipe),
        )
        total_b = [ar_t, ke_t, vi_t, wx_t, aj_t, at_t].count('B')

        score_tuple = (direct_b, total_b)
        if score_tuple > best_tuple:
          best_tuple = score_tuple
          best_metar = r
          best_scores = (ar_t, ke_t, vi_t, wx_t, aj_t, at_t)

      s_ar_t, s_ke_t, s_vi_t, s_wx_t, s_aj_t, s_at_t = best_scores

      baris_laporan.append({
          'Tanggal': tgl_str,
          'Jangka_Waktu': jangka_trend,
          'Perubahan': label_trend,
          'T_Arah': t_ar,
          'T_Kec': t_ke,
          'T_Vis': t_vi,
          'T_Wx': t_wx,
          'T_AwanJml': t_aj,
          'T_AwanTgi': t_at,
          'M_Arah': best_metar['M_Arah'],
          'S_Arah': s_ar_t,
          'M_Kec': best_metar['M_Kec'],
          'S_Kec': s_ke_t,
          'M_Vis': best_metar['M_Vis'],
          'S_Vis': s_vi_t,
          'M_Wx': best_metar['M_Wx'],
          'S_Wx': s_wx_t,
          'M_AwanJml': best_metar['M_AwanJml'],
          'S_AwanJml': s_aj_t,
          'M_AwanTgi': best_metar['M_AwanTgi'],
          'S_AwanTgi': s_at_t,
      })

  return pd.DataFrame(baris_laporan)
