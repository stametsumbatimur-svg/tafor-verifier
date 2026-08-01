# 🔥 SIVETA - Excel Exporter Engine (Multi-Sheet: Rekap SOP + Detail 30-Menit Akuntabel)
import io
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


def ekspor_ke_excel(df_analysis, df_laporan, df_speci=None):
  """Menghasilkan file Excel BytesIO 'VERIFIKASI TAFOR.xlsx' dengan 2 Sheet Utama:

  1. Laporan_Rekap_SOP : Tabel Rekapitulasi Format SOP BMKG 2025
  2. Detail_Verifikasi_30Min : Log Evaluasi METAR 30-Menitan secara
  Akuntabel/Transparan
  """
  output = io.BytesIO()
  wb = openpyxl.Workbook()

  # Styling Presets
  font_header = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
  font_body = Font(name='Calibri', size=10)
  font_title = Font(name='Calibri', size=14, bold=True)

  fill_header = PatternFill(
      start_color='1F4E78', end_color='1F4E78', fill_type='solid'
  )
  fill_green = PatternFill(
      start_color='C6EFCE', end_color='C6EFCE', fill_type='solid'
  )
  fill_red = PatternFill(
      start_color='FFC7CE', end_color='FFC7CE', fill_type='solid'
  )
  fill_subhead = PatternFill(
      start_color='D9E1F2', end_color='D9E1F2', fill_type='solid'
  )

  border_thin = Side(border_style='thin', color='D9D9D9')
  border_box = Border(
      left=border_thin, right=border_thin, top=border_thin, bottom=border_thin
  )

  align_center = Alignment(horizontal='center', vertical='center')
  align_left = Alignment(horizontal='left', vertical='center')

  # =========================================================================
  # SHEET 1: LAPORAN REKAP SOP BMKG 2025
  # =========================================================================
  ws_rekap = wb.active
  ws_rekap.title = 'Laporan_Rekap_SOP'
  ws_rekap.views.sheetView[0].showGridLines = True

  # Judul Sheet 1
  ws_rekap.merge_cells('A1:U1')
  ws_rekap['A1'] = (
      'LAPORAN REKAPITULASI VERIFIKASI TAF (SOP/024/DM/X/2025 - BMKG)'
  )
  ws_rekap['A1'].font = font_title
  ws_rekap['A1'].alignment = align_left

  # Header Tabel Rekap
  headers_rekap = [
      'Tanggal',
      'Jangka Waktu',
      'Perubahan',
      'T_Arah',
      'T_Kec',
      'T_Vis',
      'T_Wx',
      'T_AwanJml',
      'T_AwanTgi',
      'M_Arah',
      'S_Arah',
      'M_Kec',
      'S_Kec',
      'M_Vis',
      'S_Vis',
      'M_Wx',
      'S_Wx',
      'M_AwanJml',
      'S_AwanJml',
      'M_AwanTgi',
      'S_AwanTgi',
  ]

  ws_rekap.append([])  # Baris 2 kosong
  ws_rekap.append(headers_rekap)  # Baris 3 Header

  for col_idx in range(1, len(headers_rekap) + 1):
    cell = ws_rekap.cell(row=3, column=col_idx)
    cell.font = font_header
    cell.fill = fill_header
    cell.alignment = align_center

  # Isi Data Rekap
  for r_idx, row in df_laporan.iterrows():
    row_data = [
        row.get('Tanggal', '-'),
        row.get('Jangka_Waktu', '-'),
        row.get('Perubahan', '-'),
        row.get('T_Arah', '-'),
        row.get('T_Kec', '-'),
        row.get('T_Vis', '-'),
        row.get('T_Wx', '-'),
        row.get('T_AwanJml', '-'),
        row.get('T_AwanTgi', '-'),
        row.get('M_Arah', '-'),
        row.get('S_Arah', '-'),
        row.get('M_Kec', '-'),
        row.get('S_Kec', '-'),
        row.get('M_Vis', '-'),
        row.get('S_Vis', '-'),
        row.get('M_Wx', '-'),
        row.get('S_Wx', '-'),
        row.get('M_AwanJml', '-'),
        row.get('S_AwanJml', '-'),
        row.get('M_AwanTgi', '-'),
        row.get('S_AwanTgi', '-'),
    ]
    ws_rekap.append(row_data)
    curr_row = ws_rekap.max_row

    for c_idx in range(1, len(row_data) + 1):
      cell = ws_rekap.cell(row=curr_row, column=c_idx)
      cell.font = font_body
      cell.border = border_box
      cell.alignment = align_center

      # Pewarnaan Sel B / S
      val = str(cell.value).strip().upper()
      if val == 'B':
        cell.fill = fill_green
      elif val == 'S':
        cell.fill = fill_red

  # =========================================================================
  # SHEET 2: DETAIL VERIFIKASI 30-MENITAN (AKUNTABEL & TRANSPARAN)
  # =========================================================================
  ws_detail = wb.create_sheet(title='Detail_Verifikasi_30Min')
  ws_detail.views.sheetView[0].showGridLines = True

  ws_detail.merge_cells('A1:W1')
  ws_detail['A1'] = (
      'LOG EVALUASI AKURASI TAF vs METAR PER 30 MENIT (TRANSPARANSI AKUNTABEL)'
  )
  ws_detail['A1'].font = font_title
  ws_detail['A1'].alignment = align_left

  headers_detail = [
      'Waktu UTC',
      'Sandi METAR Aktual',
      'Sandi TAF Berlaku',
      'M_Arah',
      'T_Arah',
      'S_Arah',
      'M_Kec',
      'T_Kec',
      'S_Kec',
      'M_Vis',
      'T_Vis',
      'S_Vis',
      'M_Wx',
      'T_Wx',
      'S_Wx',
      'M_AwanJml',
      'T_AwanJml',
      'S_AwanJml',
      'M_AwanTgi',
      'T_AwanTgi',
      'S_AwanTgi',
      'Status Minima',
      'Hasil Akhir',
  ]

  ws_detail.append([])  # Baris 2
  ws_detail.append(headers_detail)  # Baris 3

  for col_idx in range(1, len(headers_detail) + 1):
    cell = ws_detail.cell(row=3, column=col_idx)
    cell.font = font_header
    cell.fill = PatternFill(
        start_color='203764', end_color='203764', fill_type='solid'
    )
    cell.alignment = align_center

  for _, row in df_analysis.iterrows():
    row_detail = [
        str(row.get('Waktu Aktual (UTC)', '-')),
        str(row.get('Sandi METAR Aktual', '-')),
        str(row.get('Sandi TAF Prakiraan', '-')),
        row.get('M_Arah', '-'),
        row.get('T_Arah', '-'),
        row.get('S_Arah', '-'),
        row.get('M_Kec', '-'),
        row.get('T_Kec', '-'),
        row.get('S_Kec', '-'),
        row.get('M_Vis', '-'),
        row.get('T_Vis', '-'),
        row.get('S_Vis', '-'),
        row.get('M_Wx', '-'),
        row.get('T_Wx', '-'),
        row.get('S_Wx', '-'),
        row.get('M_AwanJml', '-'),
        row.get('T_AwanJml', '-'),
        row.get('S_AwanJml', '-'),
        row.get('M_AwanTgi', '-'),
        row.get('T_AwanTgi', '-'),
        row.get('S_AwanTgi', '-'),
        row.get('Status_Minima', 'NORMAL'),
        row.get('Hasil Akhir', 'MISS'),
    ]
    ws_detail.append(row_detail)
    curr_row = ws_detail.max_row

    for c_idx in range(1, len(row_detail) + 1):
      cell = ws_detail.cell(row=curr_row, column=c_idx)
      cell.font = font_body
      cell.border = border_box
      cell.alignment = (
          align_left if c_idx in [2, 3] else align_center
      )  # Sandi rata kiri

      # Highlight Warna Status B / S & ACCURATE / MISS
      val = str(cell.value).strip().upper()
      if val in ['B', 'ACCURATE']:
        cell.fill = fill_green
      elif val in ['S', 'MISS']:
        cell.fill = fill_red

  # =========================================================================
  # SHEET 3: SPECI EVALUATION (JIKA ADA DATA SPECI)
  # =========================================================================
  if df_speci is not None and not df_speci.empty:
    ws_speci = wb.create_sheet(title='Detail_SPECI')
    ws_speci.views.sheetView[0].showGridLines = True
    ws_speci.append(['LOG EVALUASI KHUSUS SANDI SPECI'])
    ws_speci.append([])

    headers_speci = list(df_speci.columns)
    ws_speci.append(headers_speci)

    for col_idx in range(1, len(headers_speci) + 1):
      cell = ws_speci.cell(row=3, column=col_idx)
      cell.font = font_header
      cell.fill = PatternFill(
          start_color='7030A0', end_color='7030A0', fill_type='solid'
      )
      cell.alignment = align_center

    for _, row in df_speci.iterrows():
      ws_speci.append(list(row.values))
      curr_row = ws_speci.max_row
      for c_idx in range(1, len(row.values) + 1):
        cell = ws_speci.cell(row=curr_row, column=c_idx)
        cell.font = font_body
        cell.border = border_box
        cell.alignment = align_center
        val = str(cell.value).strip().upper()
        if val in ['B', 'ACCURATE']:
          cell.fill = fill_green
        elif val in ['S', 'MISS']:
          cell.fill = fill_red

  # Auto-Fit Lebar Kolom untuk Semua Sheet
  for sheet in wb.worksheets:
    for col in sheet.columns:
      max_len = 0
      col_letter = get_column_letter(col[0].column)
      for cell in col:
        if cell.row == 1:
          continue  # Abaikan judul gabungan
        val_str = str(cell.value or '')
        if len(val_str) > max_len:
          max_len = len(val_str)
      sheet.column_dimensions[col_letter].width = min(max(max_len + 3, 10), 50)

  wb.save(output)
  output.seek(0)
  return output.getvalue()
