# 🔥 SIVETA - Excel Export Engine
import io
import re
from xlsxwriter.utility import xl_col_to_name
import pandas as pd
import xlsxwriter

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
  df_excel = df_vfinal.copy()
  bulan_str = BULAN_INDO.get(str(bulan).strip().upper(), str(bulan).upper())

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

  output = io.BytesIO()
  workbook = xlsxwriter.Workbook(output, {'in_memory': True})

  # =========================================================================
  # 1. SHEET UTAMA: 'VERIFIKASI TAFOR' (RANGKUMAN RESMI FORMAT SOP 2025)
  # =========================================================================
  worksheet = workbook.add_worksheet('VERIFIKASI TAFOR')
  worksheet.hide_gridlines(2)

  # Formats
  format_title = workbook.add_format(
      {'bold': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 11}
  )
  format_subtitle = workbook.add_format(
      {'align': 'center', 'valign': 'vcenter', 'font_size': 9}
  )
  format_bold_left = workbook.add_format(
      {'bold': True, 'align': 'left', 'valign': 'vcenter', 'font_size': 9.5}
  )

  format_req_header = workbook.add_format({
      'border': 1,
      'bold': True,
      'align': 'center',
      'valign': 'vcenter',
      'bg_color': '#D9D9D9',
      'text_wrap': True,
      'font_size': 8.5,
  })
  format_req_text = workbook.add_format({
      'border': 1,
      'align': 'left',
      'valign': 'vcenter',
      'text_wrap': True,
      'font_size': 8,
  })
  format_req_bold = workbook.add_format({
      'border': 1,
      'bold': True,
      'align': 'left',
      'valign': 'vcenter',
      'font_size': 8.5,
  })

  format_border_bold = workbook.add_format({
      'border': 1,
      'bold': True,
      'align': 'center',
      'valign': 'vcenter',
      'text_wrap': True,
      'font_size': 8.5,
  })
  format_persen = workbook.add_format({
      'border': 1,
      'bold': True,
      'align': 'center',
      'num_format': '0.00%',
      'font_size': 8.5,
  })

  format_tabel_header = workbook.add_format({
      'border': 1,
      'bold': True,
      'align': 'center',
      'valign': 'vcenter',
      'bg_color': '#D9D9D9',
      'text_wrap': True,
      'font_size': 8.5,
  })
  format_tabel_data = workbook.add_format({
      'border': 1,
      'align': 'center',
      'valign': 'vcenter',
      'font_size': 8.5,
      'text_wrap': True,
  })

  format_hijau = workbook.add_format({
      'bg_color': '#C6EFCE',
      'font_color': '#006100',
      'align': 'center',
      'valign': 'vcenter',
      'border': 1,
      'font_size': 8.5,
  })
  format_merah = workbook.add_format({
      'bg_color': '#FFC7CE',
      'font_color': '#9C0006',
      'align': 'center',
      'valign': 'vcenter',
      'border': 1,
      'font_size': 8.5,
  })

  format_ttd_nama = workbook.add_format({
      'bold': True,
      'align': 'center',
      'valign': 'vcenter',
      'font_size': 9.5,
      'underline': True,
  })

  batas_col = (
      df_excel.columns.get_loc('S_AwanTgi')
      if 'S_AwanTgi' in df_excel.columns
      else len(df_excel.columns) - 1
  )
  batas_col = max(batas_col, 15)
  max_col_data = len(df_excel.columns) - 1

  nama_kolom_cantik = [
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

  worksheet.set_row(12, 38)
  for col_num, col_name in enumerate(nama_kolom_cantik):
    worksheet.write(12, col_num, col_name, format_tabel_header)

  for row_num, row_data in enumerate(df_excel.values):
    for col_num, value in enumerate(row_data):
      val = '' if pd.isna(value) else value
      worksheet.write(13 + row_num, col_num, val, format_tabel_data)

  worksheet.merge_range(
      0, 0, 0, batas_col, 'VERIFIKASI AERODROME FORECAST', format_title
  )
  worksheet.merge_range(
      1,
      0,
      1,
      batas_col,
      'Standard Operating Procedures (SOP) Nomor: SOP/024/DM/X/2025',
      format_title,
  )
  worksheet.write(
      3, 0, 'PERSYARATAN / TOLERANSI KETELITIAN PRAKIRAAN :', format_bold_left
  )

  worksheet.merge_range(4, 0, 4, 1, 'UNSUR METEOROLOGI', format_req_header)
  worksheet.merge_range(
      4, 2, 4, 7, 'PERSYARATAN / TOLERANSI KETELITIAN', format_req_header
  )
  worksheet.merge_range(4, 8, 4, 10, 'UNSUR METEOROLOGI', format_req_header)
  worksheet.merge_range(
      4, 11, 4, batas_col, 'PERSYARATAN / TOLERANSI KETELITIAN', format_req_header
  )

  worksheet.merge_range(5, 0, 5, 1, 'A. Arah Angin', format_req_bold)
  worksheet.merge_range(
      5,
      2,
      5,
      7,
      'Benar apabila arah sama, atau selisih <= 60 derajat. Jika kecepatan'
      ' angin <10 kt, atau VRB, atau kondisi CB/TS, dianggap benar.',
      format_req_text,
  )
  worksheet.merge_range(5, 8, 5, 10, 'E. Jumlah Awan', format_req_bold)
  worksheet.merge_range(
      5,
      11,
      5,
      batas_col,
      'Benar apabila berada pada kelompok yang sama: FEW/SCT atau BKN/OVC. Jika'
      ' tinggi awan > 5000 ft, dianggap benar.',
      format_req_text,
  )

  worksheet.merge_range(6, 0, 6, 1, 'B. Kecepatan Angin', format_req_bold)
  worksheet.merge_range(
      6,
      2,
      6,
      7,
      'Selisih kecepatan dasar <= 10 knot. Status gust harus konsisten.',
      format_req_text,
  )
  worksheet.merge_range(6, 8, 6, 10, 'F. Tinggi Dasar Awan', format_req_bold)
  worksheet.merge_range(
      6,
      11,
      6,
      batas_col,
      'Selisih <= 100 ft untuk <1000 ft. Untuk >= 1000 ft, selisih <= 30% dari'
      ' tinggi awan Manual.',
      format_req_text,
  )

  worksheet.merge_range(7, 0, 7, 1, 'C. Jarak Pandang', format_req_bold)
  worksheet.merge_range(
      7,
      2,
      7,
      7,
      'Benar apabila berada pada kelas visibility yang sama.',
      format_req_text,
  )
  worksheet.merge_range(7, 8, 7, 10, '', format_req_bold)
  worksheet.merge_range(7, 11, 7, batas_col, '', format_req_text)

  worksheet.merge_range(8, 0, 8, 1, 'D. Cuaca / Endapan', format_req_bold)
  worksheet.merge_range(
      8,
      2,
      8,
      7,
      'Benar apabila sama-sama mendeteksi atau tidak mendeteksi presipitasi'
      ' sedang/lebat. Hujan ringan (-RA) tidak dihitung.',
      format_req_text,
  )
  worksheet.merge_range(8, 8, 8, 10, '', format_req_bold)
  worksheet.merge_range(8, 11, 8, batas_col, '', format_req_text)

  worksheet.set_row(5, 68)
  worksheet.set_row(6, 52)
  worksheet.set_row(7, 35)
  worksheet.set_row(8, 68)

  worksheet.write(10, 0, f'BULAN : {bulan_str}', format_bold_left)
  worksheet.write(10, 3, f'TAHUN : {tahun}', format_bold_left)
  worksheet.write(10, 6, '(SEMUA WAKTU DALAM GMT)', format_bold_left)
  worksheet.write(10, 11, f'STASIUN METEOROLOGI {stasiun}', format_bold_left)

  jumlah_baris_data = len(df_excel)
  excel_start_data_row = 14
  excel_last_data_row = excel_start_data_row + jumlah_baris_data - 1

  data_range = f'A{excel_start_data_row}:U{excel_last_data_row}'
  worksheet.conditional_format(
      data_range,
      {
          'type': 'cell',
          'criteria': '==',
          'value': '"B"',
          'format': format_hijau,
      },
  )
  worksheet.conditional_format(
      data_range,
      {'type': 'cell', 'criteria': '==', 'value': '"S"', 'format': format_merah},
  )

  worksheet.autofilter(12, 0, 12 + jumlah_baris_data, max_col_data)
  worksheet.freeze_panes(13, 0)

  baris_jumlah_idx = 12 + jumlah_baris_data + 1
  excel_baris_jumlah = baris_jumlah_idx + 1
  baris_persen_idx = baris_jumlah_idx + 1
  excel_baris_persen = baris_persen_idx + 1

  worksheet.merge_range(
      baris_jumlah_idx, 0, baris_jumlah_idx, 2, 'JUMLAH', format_border_bold
  )
  worksheet.merge_range(
      baris_persen_idx,
      0,
      baris_persen_idx,
      2,
      'PROSENTASE KEBENARAN',
      format_border_bold,
  )

  for col_idx in range(3, max_col_data + 1):
    worksheet.write(
        baris_jumlah_idx, col_idx, jumlah_baris_data, format_border_bold
    )
    worksheet.write(baris_persen_idx, col_idx, '', format_border_bold)

  for col_name in kolom_skor:
    if col_name in df_excel.columns:
      col_idx = df_excel.columns.get_loc(col_name)
      col_huruf = xl_col_to_name(col_idx)

      rumus_jumlah = f'=COUNTIF({col_huruf}{excel_start_data_row}:{col_huruf}{excel_last_data_row}, "B") + COUNTIF({col_huruf}{excel_start_data_row}:{col_huruf}{excel_last_data_row}, "S")'
      worksheet.write_formula(
          baris_jumlah_idx, col_idx, rumus_jumlah, format_border_bold
      )

      rumus_persen = f'=IFERROR(COUNTIF({col_huruf}{excel_start_data_row}:{col_huruf}{excel_last_data_row}, "B") / {col_huruf}{excel_baris_jumlah}, 0)'
      worksheet.write_formula(
          baris_persen_idx, col_idx, rumus_persen, format_persen
      )

  baris_ttd = baris_persen_idx + 4
  worksheet.merge_range(
      baris_ttd, 0, baris_ttd, 3, 'Mengetahui,', format_subtitle
  )
  worksheet.merge_range(
      baris_ttd + 1, 0, baris_ttd + 1, 3, 'Kepala Stasiun', format_subtitle
  )
  worksheet.merge_range(
      baris_ttd + 5, 0, baris_ttd + 5, 3, nama_kepala, format_ttd_nama
  )
  worksheet.merge_range(
      baris_ttd + 6, 0, baris_ttd + 6, 3, f'NIP. {nip_kepala}', format_subtitle
  )

  col_ttd_start = max(batas_col - 4, 4)
  col_ttd_end = batas_col
  worksheet.merge_range(
      baris_ttd,
      col_ttd_start,
      baris_ttd,
      col_ttd_end,
      'Petugas Pembuat Laporan',
      format_subtitle,
  )
  worksheet.merge_range(
      baris_ttd + 5,
      col_ttd_start,
      baris_ttd + 5,
      col_ttd_end,
      nama_petugas,
      format_ttd_nama,
  )
  worksheet.merge_range(
      baris_ttd + 6,
      col_ttd_start,
      baris_ttd + 6,
      col_ttd_end,
      f'NIP. {nip_petugas}',
      format_subtitle,
  )

  worksheet.set_column('A:A', 4.5)
  worksheet.set_column('B:C', 9.5)
  worksheet.set_column('D:E', 6.0)
  worksheet.set_column('F:I', 7.0)
  worksheet.set_column('J:J', 6.0)
  worksheet.set_column('K:K', 6.8)
  worksheet.set_column('L:L', 6.0)
  worksheet.set_column('M:M', 6.8)
  worksheet.set_column('N:N', 7.0)
  worksheet.set_column('O:O', 6.8)
  worksheet.set_column('P:P', 7.0)
  worksheet.set_column('Q:Q', 6.8)
  worksheet.set_column('R:R', 7.0)
  worksheet.set_column('S:S', 6.8)
  worksheet.set_column('T:T', 7.0)
  worksheet.set_column('U:U', 6.8)

  worksheet.set_portrait()
  worksheet.set_paper(9)
  worksheet.fit_to_pages(1, 0)
  worksheet.set_margins(left=0.15, right=0.15, top=0.4, bottom=0.4)
  worksheet.repeat_rows(12, 12)

  akhir_baris_print = baris_ttd + 7
  worksheet.print_area(0, 0, akhir_baris_print, max_col_data)

  # =========================================================================
  # 2. SHEET HARIAN (1 s.d. 31): LOG KOMPARASI DINAMIS PER 30-MENIT
  # =========================================================================
  if df_analysis is not None and not df_analysis.empty:
    df_log = df_analysis.copy()
    df_log['Dt_Obj'] = pd.to_datetime(df_log['Waktu Aktual (UTC)'])

    fmt_harian_hdr = workbook.add_format({
        'border': 1, 'bold': True, 'align': 'center', 'valign': 'vcenter',
        'bg_color': '#1F4E78', 'font_color': '#FFFFFF', 'text_wrap': True, 'font_size': 8.5
    })
    # Format Default (METAR)
    fmt_harian_data = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 8.5})
    fmt_harian_left = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter', 'font_size': 8.5})
    
    # Format Khusus SPECI (Kuning Muda)
    fmt_speci_data = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 8.5, 'bg_color': '#FFF2CC'})
    fmt_speci_left = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter', 'font_size': 8.5, 'bg_color': '#FFF2CC'})

    fmt_harian_title = workbook.add_format({'bold': True, 'align': 'left', 'valign': 'vcenter', 'font_size': 11})

    headers_harian = [
        'No', 'Waktu (UTC)', 'Change Group', 'Sandi TAF Prakiraan',
        'Arah (T)', 'Kec (T)', 'Vis (T)', 'Wx (T)', 'JmlAwan (T)', 'TgiAwan (T)',
        'Sandi METAR Aktual', 'Arah (M)', 'S_Arah', 'Kec (M)', 'S_Kec',
        'Vis (M)', 'S_Vis', 'Wx (M)', 'S_Wx', 'JmlAwan (M)', 'S_AwanJml',
        'TgiAwan (M)', 'S_AwanTgi',
    ]

    for hari in range(1, 32):
      df_day = df_log[df_log['Dt_Obj'].dt.day == hari].copy()
      if df_day.empty:
        continue

      ws_day = workbook.add_worksheet(str(hari))
      ws_day.hide_gridlines(2)

      ws_day.merge_range(
          'A1:W1',
          f'LOG VERIFIKASI TAF vs METAR PER 30 MENIT — TANGGAL {hari} {bulan_str} {tahun}',
          fmt_harian_title,
      )

      for col_i, h_text in enumerate(headers_harian):
        ws_day.write(2, col_i, h_text, fmt_harian_hdr)

      df_day = df_day.sort_values('Dt_Obj')
      for row_i, r_data in enumerate(df_day.to_dict('records'), start=1):
        dt_str = pd.to_datetime(r_data['Waktu Aktual (UTC)']).strftime('%H:%M:%S')
        is_speci = r_data.get('Jenis_Observasi', 'METAR') == 'SPECI' # 👈 Cek apakah baris ini SPECI

        grup_val = r_data.get('Grup_Aktif') or r_data.get('Change_Group') or r_data.get('Perubahan')
        if pd.isna(grup_val) or str(grup_val).strip() in ['', 'nan', 'None', '-']:
          grup_aktif = 'BASE'
        else:
          grup_aktif = str(grup_val).strip()

        row_harian = [
            row_i, dt_str, grup_aktif, r_data.get('Sandi TAF Prakiraan', '-'),
            r_data.get('T_Arah', '-'), r_data.get('T_Kec', '-'), r_data.get('T_Vis', '-'),
            r_data.get('T_Wx', '-'), r_data.get('T_AwanJml', '-'), r_data.get('T_AwanTgi', '-'),
            r_data.get('Sandi METAR Aktual', '-'), r_data.get('M_Arah', '-'), r_data.get('S_Arah', 'S'),
            r_data.get('M_Kec', '-'), r_data.get('S_Kec', 'S'), r_data.get('M_Vis', '-'),
            r_data.get('S_Vis', 'S'), r_data.get('M_Wx', '-'), r_data.get('S_Wx', 'S'),
            r_data.get('M_AwanJml', '-'), r_data.get('S_AwanJml', 'S'), r_data.get('M_AwanTgi', '-'),
            r_data.get('S_AwanTgi', 'S'),
        ]

        excel_row = 2 + row_i
        
        # 👈 Tentukan format baris berdasarkan jenis observasi (METAR/SPECI)
        fmt_base_data = fmt_speci_data if is_speci else fmt_harian_data
        fmt_base_left = fmt_speci_left if is_speci else fmt_harian_left

        for col_i, val in enumerate(row_harian):
          fmt = fmt_base_left if col_i in [3, 10] else fmt_base_data
          v_str = str(val).strip().upper()

          # Tetap pertahankan warna Hijau/Merah untuk Kolom Penilaian B/S
          if v_str == 'B':
            ws_day.write(excel_row, col_i, val, format_hijau)
          elif v_str == 'S' and col_i in [12, 14, 16, 18, 20, 22]:
            ws_day.write(excel_row, col_i, val, format_merah)
          else:
            ws_day.write(excel_row, col_i, val, fmt)

      ws_day.set_column('A:A', 5)
      ws_day.set_column('B:B', 10)
      ws_day.set_column('C:C', 14)
      ws_day.set_column('D:D', 32)
      ws_day.set_column('E:J', 8)
      ws_day.set_column('K:K', 32)
      ws_day.set_column('L:W', 8)

  workbook.close()
  return output.getvalue()


ekspor_ke_excel = export_v_final_excel
