# 🔥 SIVETA - Excel Export Engine (Full Multi-Sheet: Rangkuman SOP + Detail Harian 1-31)
import io
import re
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
import pandas as pd

# ==========================================
# KAMUS PEMETAAN BULAN BAHASA INDONESIA
# ==========================================
BULAN_INDO = {
    1: 'JANUARI',
    2: 'FEBRUARI',
    3: 'MARET',
    4: 'APRIL',
    5: 'MEI',
    6: 'JUNI',
    7: 'JULI',
    8: 'AGUSTUS',
    9: 'SEPTEMBER',
    10: 'OKTOBER',
    11: 'NOVEMBER',
    12: 'DESEMBER',
    '1': 'JANUARI',
    '2': 'FEBRUARI',
    '3': 'MARET',
    '4': 'APRIL',
    '5': 'MEI',
    '6': 'JUNI',
    '7': 'JULI',
    '8': 'AGUSTUS',
    '9': 'SEPTEMBER',
    '10': 'OKTOBER',
    '11': 'NOVEMBER',
    '12': 'DESEMBER',
    '01': 'JANUARI',
    '02': 'FEBRUARI',
    '03': 'MARET',
    '04': 'APRIL',
    '05': 'MEI',
    '06': 'JUNI',
    '07': 'JULI',
    '08': 'AGUSTUS',
    '09': 'SEPTEMBER',
    '10': 'OKTOBER',
    '11': 'NOVEMBER',
    '12': 'DESEMBER',
    'JANUARY': 'JANUARI',
    'FEBRUARY': 'FEBRUARI',
    'MARCH': 'MARET',
    'APRIL': 'APRIL',
    'MAY': 'MEI',
    'JUNE': 'JUNI',
    'JULY': 'JULI',
    'AUGUST': 'AGUSTUS',
    'SEPTEMBER': 'SEPTEMBER',
    'OCTOBER': 'OKTOBER',
    'NOVEMBER': 'NOVEMBER',
    'DECEMBER': 'DESEMBER',
}


def export_v_final_excel(
    df_vfinal,
    df_analysis=None,
    bulan='JUNI',
    tahun='2026',
    stasiun='WATU',
    nama_petugas='FORECASTER',
    nip_petugas='[NIP PETUGAS]',
    nama_kepala='[NAMA KEPALA STASIUN]',
    nip_kepala='[NIP KEPALA]',
):
  """Menghasilkan 1 File Excel Utuh (.xlsx) yang berisi:

  1. Sheet 'VERIFIKASI TAFOR' : Sheet Rangkuman SOP BMKG 2025
  2. Sheet '1', '2', ..., '31' : Sheet Komparasi METAR vs TAF per 30 Menit
     (Dasar Akuntabilitas Nilai B/S)
  """
  output = io.BytesIO()

  # Konversi input bulan ke Bahasa Indonesia
  bulan_str = BULAN_INDO.get(str(bulan).strip().upper(), str(bulan).upper())

  # Gunakan openpyxl untuk membangun multi-sheet workbook
  wb = openpyxl.Workbook()

  # Preset Formatting
  font_title = Font(name='Calibri', size=12, bold=True)
  font_sub = Font(name='Calibri', size=10, italic=True)
  font_header = Font(name='Calibri', size=9, bold=True, color='FFFFFF')
  font_subhead = Font(name='Calibri', size=9, bold=True)
  font_body = Font(name='Calibri', size=9)
  font_bold = Font(name='Calibri', size=9, bold=True)
  font_ttd = Font(name='Calibri', size=10, bold=True, underline='single')

  fill_navy = PatternFill(
      start_color='1F4E78', end_color='1F4E78', fill_type='solid'
  )
  fill_gray = PatternFill(
      start_color='D9D9D9', end_color='D9D9D9', fill_type='solid'
  )
  fill_green = PatternFill(
      start_color='C6EFCE', end_color='C6EFCE', fill_type='solid'
  )
  fill_red = PatternFill(
      start_color='FFC7CE', end_color='FFC7CE', fill_type='solid'
  )

  border_thin = Side(border_style='thin', color='BFBFBF')
  border_box = Border(
      left=border_thin, right=border_thin, top=border_thin, bottom=border_thin
  )

  align_center = Alignment(
      horizontal='center', vertical='center', wrap_text=True
  )
  align_left = Alignment(horizontal='left', vertical='center', wrap_text=True)

  # =========================================================================
  # 1. SHEET UTAMA: 'VERIFIKASI TAFOR' (RANGKUMAN SOP BMKG 2025)
  # =========================================================================
  ws_main = wb.active
  ws_main.title = 'VERIFIKASI TAFOR'
  ws_main.views.sheetView[0].showGridLines = True

  # Judul & Header
  ws_main.merge_cells('A1:U1')
  ws_main['A1'] = 'VERIFIKASI AERODROME FORECAST'
  ws_main['A1'].font = font_title
  ws_main['A1'].alignment = align_center

  ws_main.merge_cells('A2:U2')
  ws_main['A2'] = (
      'Standard Operating Procedures (SOP) Nomor: SOP/024/DM/X/2025'
  )
  ws_main['A2'].font = font_title
  ws_main['A2'].alignment = align_center

  ws_main['A4'] = 'PERSYARATAN / TOLERANSI KETELITIAN PRAKIRAAN :'
  ws_main['A4'].font = font_bold

  # Narasi Toleransi SOP
  narasi = [
      (
          'A. Arah Angin',
          (
              'Benar apabila arah sama, atau selisih <= 60 derajat. Jika'
              ' kecepatan angin <10 kt, atau VRB, atau kondisi CB/TS, dianggap'
              ' benar.'
          ),
          'E. Jumlah Awan',
          (
              'Benar apabila berada pada kelompok yang sama: FEW/SCT atau'
              ' BKN/OVC. Jika tinggi awan > 5000 ft, dianggap benar.'
          ),
      ),
      (
          'B. Kecepatan Angin',
          (
              'Selisih kecepatan dasar <= 10 knot. Status gust harus'
              ' konsisten.'
          ),
          'F. Tinggi Dasar Awan',
          (
              'Selisih <= 100 ft untuk <1000 ft. Untuk >= 1000 ft, selisih <='
              ' 30% dari tinggi awan Manual.'
          ),
      ),
      (
          'C. Jarak Pandang',
          'Benar apabila berada pada kelas visibility yang sama.',
          '',
          '',
      ),
      (
          'D. Cuaca / Endapan',
          (
              'Benar apabila sama-sama mendeteksi atau tidak mendeteksi'
              ' presipitasi sedang/lebat. Hujan ringan (-RA) tidak dihitung.'
          ),
          '',
          '',
      ),
  ]

  ws_main.merge_cells('A5:B5')
  ws_main['A5'] = 'UNSUR METEOROLOGI'
  ws_main.merge_cells('C5:H5')
  ws_main['C5'] = 'PERSYARATAN / TOLERANSI KETELITIAN'
  ws_main.merge_cells('I5:K5')
  ws_main['I5'] = 'UNSUR METEOROLOGI'
  ws_main.merge_cells('L5:U5')
  ws_main['L5'] = 'PERSYARATAN / TOLERANSI KETELITIAN'

  for col in ['A5', 'C5', 'I5', 'L5']:
    ws_main[col].font = font_subhead
    ws_main[col].fill = fill_gray
    ws_main[col].alignment = align_center
    ws_main[col].border = border_box

  for idx, (u1, t1, u2, t2) in enumerate(narasi, start=6):
    ws_main.merge_cells(f'A{idx}:B{idx}')
    ws_main[f'A{idx}'] = u1
    ws_main.merge_cells(f'C{idx}:H{idx}')
    ws_main[f'C{idx}'] = t1

    ws_main.merge_cells(f'I{idx}:K{idx}')
    ws_main[f'I{idx}'] = u2
    ws_main.merge_cells(f'L{idx}:U{idx}')
    ws_main[f'L{idx}'] = t2

    for col in [
        f'A{idx}',
        f'C{idx}',
        f'I{idx}',
        f'L{idx}',
    ]:
      ws_main[col].font = font_body
      ws_main[col].border = border_box
      ws_main[col].alignment = align_left

  ws_main['A11'] = f'BULAN : {bulan_str}'
  ws_main['D11'] = f'TAHUN : {tahun}'
  ws_main['G11'] = '(SEMUA WAKTU DALAM GMT)'
  ws_main['L11'] = f'STASIUN METEOROLOGI {stasiun}'
  for col in ['A11', 'D11', 'G11', 'L11']:
    ws_main[col].font = font_bold

  # Header Tabel Rangkuman
  headers_rangkuman = [
      'Tgl',
      'Jangka Waktu',
      'Perubahan',
      'Arah\n(T)',
      'Kec\n(T)',
      'Vis\n(T)',
      'Cuaca\n(T)',
      'Jml\nAwan\n(T)',
      'Tgi\nAwan\n(T)',
      'Arah\n(M)',
      'Skor',
      'Kec\n(M)',
      'Skor',
      'Vis\n(M)',
      'Skor',
      'Cuaca\n(M)',
      'Skor',
      'Jml\nAwan\n(M)',
      'Skor',
      'Tgi\nAwan\n(M)',
      'Skor',
  ]

  for c_idx, h_text in enumerate(headers_rangkuman, start=1):
    cell = ws_main.cell(row=13, column=c_idx)
    cell.value = h_text
    cell.font = font_header
    cell.fill = fill_navy
    cell.alignment = align_center
    cell.border = border_box

  # Isi Data Tabel Rangkuman
  df_excel = df_vfinal.copy()
  kolom_skor = ['S_Arah', 'S_Kec', 'S_Vis', 'S_Wx', 'S_AwanJml', 'S_AwanTgi']
  for col in kolom_skor:
    if col in df_excel.columns:
      df_excel[col] = df_excel[col].apply(
          lambda x: (
              'S'
              if str(x).strip().upper() in ['FALSE', 'SALAH', 'S', '0', '']
              else ('B' if str(x).strip().upper() == 'B' else x)
          )
      )

  if 'Tanggal' in df_excel.columns:
    df_excel.loc[df_excel['Tanggal'].duplicated(), 'Tanggal'] = ''

  start_row = 14
  for r_idx, row_vals in enumerate(df_excel.values, start=start_row):
    for c_idx, val in enumerate(row_vals, start=1):
      if c_idx > 21:
        break
      cell = ws_main.cell(row=r_idx, column=c_idx)
      cell.value = '' if pd.isna(val) else val
      cell.font = font_body
      cell.border = border_box
      cell.alignment = align_center

      v_str = str(cell.value).strip().upper()
      if v_str == 'B':
        cell.fill = fill_green
      elif v_str == 'S':
        cell.fill = fill_red

  # Baris Jumlah & Persentase Kebenaran Rangkuman
  last_data_row = start_row + len(df_excel) - 1
  row_jumlah = last_data_row + 1
  row_persen = last_data_row + 2

  ws_main.merge_cells(f'A{row_jumlah}:C{row_jumlah}')
  ws_main[f'A{row_jumlah}'] = 'JUMLAH'
  ws_main[f'A{row_jumlah}'].font = font_bold
  ws_main[f'A{row_jumlah}'].alignment = align_center
  ws_main[f'A{row_jumlah}'].border = border_box

  ws_main.merge_cells(f'A{row_persen}:C{row_persen}')
  ws_main[f'A{row_persen}'] = 'PROSENTASE KEBENARAN'
  ws_main[f'A{row_persen}'].font = font_bold
  ws_main[f'A{row_persen}'].alignment = align_center
  ws_main[f'A{row_persen}'].border = border_box

  for c_idx in range(4, 22):
    c_letter = get_column_letter(c_idx)
    cell_j = ws_main.cell(row=row_jumlah, column=c_idx)
    cell_p = ws_main.cell(row=row_persen, column=c_idx)
    cell_j.border = border_box
    cell_p.border = border_box

    # Kolom Skor khusus (Kolom 11, 13, 15, 17, 19, 21)
    if c_idx in [11, 13, 15, 17, 19, 21]:
      cell_j.value = f'=COUNTIF({c_letter}{start_row}:{c_letter}{last_data_row}, "B") + COUNTIF({c_letter}{start_row}:{c_letter}{last_data_row}, "S")'
      cell_p.value = f'=IFERROR(COUNTIF({c_letter}{start_row}:{c_letter}{last_data_row}, "B") / {c_letter}{row_jumlah}, 0)'
      cell_j.font = font_bold
      cell_p.font = font_bold
      cell_p.number_format = '0.00%'
      cell_j.alignment = align_center
      cell_p.alignment = align_center

  # Tanda Tangan
  row_ttd = row_persen + 4
  ws_main.merge_cells(f'A{row_ttd}:D{row_ttd}')
  ws_main[f'A{row_ttd}'] = 'Mengetahui,'
  ws_main.merge_cells(f'A{row_ttd+1}:D{row_ttd+1}')
  ws_main[f'A{row_ttd+1}'] = 'Kepala Stasiun'

  ws_main.merge_cells(f'A{row_ttd+5}:D{row_ttd+5}')
  ws_main[f'A{row_ttd+5}'] = nama_kepala
  ws_main[f'A{row_ttd+5}'].font = font_ttd

  ws_main.merge_cells(f'A{row_ttd+6}:D{row_ttd+6}')
  ws_main[f'A{row_ttd+6}'] = f'NIP. {nip_kepala}'

  ws_main.merge_cells(f'P{row_ttd}:U{row_ttd}')
  ws_main[f'P{row_ttd}'] = 'Petugas Pembuat Laporan'

  ws_main.merge_cells(f'P{row_ttd+5}:U{row_ttd+5}')
  ws_main[f'P{row_ttd+5}'] = nama_petugas
  ws_main[f'P{row_ttd+5}'].font = font_ttd

  ws_main.merge_cells(f'P{row_ttd+6}:U{row_ttd+6}')
  ws_main[f'P{row_ttd+6}'] = f'NIP. {nip_petugas}'

  for r in range(row_ttd, row_ttd + 7):
    ws_main[f'A{r}'].alignment = align_center
    ws_main[f'P{r}'].alignment = align_center

  # =========================================================================
  # 2. SHEET PER TANGGAL (1 s.d. 31): LOG KOMPARASI 30-MENITAN (AKUNTABEL)
  # =========================================================================
  df_log = df_analysis if df_analysis is not None else pd.DataFrame()

  if not df_log.empty:
    df_log['Dt_Obj'] = pd.to_datetime(df_log['Waktu Aktual (UTC)'])

    # Buat Sheet untuk Tanggal 1 s.d. 31
    for hari in range(1, 32):
      df_day = df_log[df_log['Dt_Obj'].dt.day == hari].copy()
      if df_day.empty:
        continue

      ws_day = wb.create_sheet(title=str(hari))
      ws_day.views.sheetView[0].showGridLines = True

      # Header Sheet Harian
      ws_day.merge_cells('A1:U1')
      ws_day['A1'] = (
          f'LOG VERIFIKASI TAF vs METAR PER 30 MENIT — TANGGAL {hari} {bulan_str}'
          f' {tahun}'
      )
      ws_day['A1'].font = font_title
      ws_day['A1'].alignment = align_left

      headers_harian = [
          'No',
          'Waktu (UTC)',
          'Change Group',
          'Sandi TAF Prakiraan',
          'Arah (T)',
          'Kec (T)',
          'Vis (T)',
          'Wx (T)',
          'JmlAwan (T)',
          'TgiAwan (T)',
          'Sandi METAR Aktual',
          'Arah (M)',
          'S_Arah',
          'Kec (M)',
          'S_Kec',
          'Vis (M)',
          'S_Vis',
          'Wx (M)',
          'S_Wx',
          'JmlAwan (M)',
          'S_AwanJml',
          'TgiAwan (M)',
          'S_AwanTgi',
      ]

      ws_day.append([])  # Row 2 kosong
      ws_day.append(headers_harian)  # Row 3

      for c_i, h_t in enumerate(headers_harian, start=1):
        c = ws_day.cell(row=3, column=c_i)
        c.font = font_header
        c.fill = PatternFill(
            start_color='203764', end_color='203764', fill_type='solid'
        )
        c.alignment = align_center
        c.border = border_box

      # Append 48 observasi 30-menitan
      df_day = df_day.sort_values('Dt_Obj')
      for row_i, r_data in enumerate(df_day.to_dict('records'), start=1):
        dt_str = pd.to_datetime(r_data['Waktu Aktual (UTC)']).strftime(
            '%H:%M:%S'
        )

        row_harian = [
            row_i,
            dt_str,
            'BASE',
            r_data.get('Sandi TAF Prakiraan', '-'),
            r_data.get('T_Arah', '-'),
            r_data.get('T_Kec', '-'),
            r_data.get('T_Vis', '-'),
            r_data.get('T_Wx', '-'),
            r_data.get('T_AwanJml', '-'),
            r_data.get('T_AwanTgi', '-'),
            r_data.get('Sandi METAR Aktual', '-'),
            r_data.get('M_Arah', '-'),
            r_data.get('S_Arah', 'S'),
            r_data.get('M_Kec', '-'),
            r_data.get('S_Kec', 'S'),
            r_data.get('M_Vis', '-'),
            r_data.get('S_Vis', 'S'),
            r_data.get('M_Wx', '-'),
            r_data.get('S_Wx', 'S'),
            r_data.get('M_AwanJml', '-'),
            r_data.get('S_AwanJml', 'S'),
            r_data.get('M_AwanTgi', '-'),
            r_data.get('S_AwanTgi', 'S'),
        ]
        ws_day.append(row_harian)
        cur_r = ws_day.max_row

        for c_i in range(1, len(row_harian) + 1):
          cell = ws_day.cell(row=cur_r, column=c_i)
          cell.font = font_body
          cell.border = border_box
          cell.alignment = align_left if c_i in [4, 11] else align_center

          v_s = str(cell.value).strip().upper()
          if v_s == 'B':
            cell.fill = fill_green
          elif v_s == 'S':
            cell.fill = fill_red

  # Auto-Fit Lebar Kolom Seluruh Sheet
  for sheet in wb.worksheets:
    for col in sheet.columns:
      max_l = 0
      col_letter = get_column_letter(col[0].column)
      for cell in col:
        if cell.row in [1, 2]:
          continue
        val_str = str(cell.value or '')
        if len(val_str) > max_l:
          max_l = len(val_str)
      sheet.column_dimensions[col_letter].width = min(max(max_l + 2, 8), 45)

  wb.save(output)
  output.seek(0)
  return output.getvalue()
ekspor_ke_excel = export_v_final_excel
