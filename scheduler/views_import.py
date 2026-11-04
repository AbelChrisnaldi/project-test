import os
import re
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import ScheduleSession, StudentDefense
from .views_dashboard import get_current_session
from .xlsx_utils import read_xlsx


def import_excel(request):
    session = get_current_session()
    
    if request.method == 'POST':
        file = request.FILES.get('excel_file')
        if not file:
            messages.error(request, "Harap pilih berkas Excel (.xlsx) untuk diunggah.")
            return redirect('scheduler:import_excel')

        import_mode = request.POST.get('import_mode', 'clean')
        sheet_choice = request.POST.get('sheet_name', '')
        
        try:
            sheets = read_xlsx(file)
            if not sheets:
                messages.error(request, "Berkas Excel kosong atau tidak valid.")
                return redirect('scheduler:import_excel')

            target_sheet_name = sheet_choice.strip() if sheet_choice and sheet_choice.strip() in sheets else None
            if not target_sheet_name:
                # Prioritaskan sheet AKD (85 data) atau sheet pertama yang aktif / terlihat
                for candidate in ['Sidang Periode 4 AKD', 'Sidang Periode 4', 'Sheet1']:
                    if candidate in sheets:
                        target_sheet_name = candidate
                        break
            if not target_sheet_name:
                target_sheet_name = list(sheets.keys())[0]

            rows = sheets[target_sheet_name]
            if len(rows) < 2:
                messages.error(request, f"Sheet '{target_sheet_name}' tidak memiliki cukup data baris.")
                return redirect('scheduler:import_excel')

            header_row_idx = 0
            for i, r in enumerate(rows[:5]):
                r_upper = [c.upper() for c in r]
                if 'NIM' in r_upper or any('NIM' in c for c in r_upper):
                    header_row_idx = i
                    break

            headers = [c.strip() for c in rows[header_row_idx]]
            
            def find_col(patterns):
                for idx, h in enumerate(headers):
                    for pat in patterns:
                        if pat.lower() in h.lower():
                            return idx
                return None

            col_no = find_col(['no'])
            col_periode = find_col(['periode'])
            col_kk = find_col(['kelompok', 'keahlian'])
            col_prodi = find_col(['program studi', 'prodi'])
            col_nim = find_col(['nim'])
            col_nama = find_col(['nama'])
            col_judul = find_col(['judul'])
            col_p1 = find_col(['pembimbing 1', 'pembimbing1'])
            col_p2 = find_col(['pembimbing 2', 'pembimbing2'])
            col_u1 = find_col(['penguji 1', 'penguji1'])
            col_u2 = find_col(['penguji 2', 'penguji2'])
            col_status = find_col(['status'])
            col_note = find_col(['note', 'catatan'])
            col_hari = find_col(['hari'])
            col_tgl = find_col(['tanggal'])
            col_jam = find_col(['jam'])
            col_ruang = find_col(['ruang'])

            if col_nim is None:
                messages.error(request, "Kolom 'NIM' tidak ditemukan pada sheet yang dipilih.")
                return redirect('scheduler:import_excel')

            session.students.all().delete()

            day_names_map = {
                'senin': 1, 'selasa': 2, 'rabu': 3, 'kamis': 4, "jum'at": 5, 'jumat': 5,
                'hari 1': 1, 'hari ke-1': 1, 'hari 2': 2, 'hari ke-2': 2, 'hari 3': 3,
                'hari ke-3': 3, 'hari 4': 4, 'hari ke-4': 4, 'hari 5': 5, 'hari ke-5': 5,
                'hari 6': 6, 'hari ke-6': 6, 'hari 7': 7, 'hari ke-7': 7, 'hari 8': 8, 'hari ke-8': 8
            }

            count = 0
            for r_idx in range(header_row_idx + 1, len(rows)):
                r = rows[r_idx]
                if len(r) <= col_nim:
                    continue
                nim_val = r[col_nim].strip()
                if not nim_val or nim_val.lower() == 'nim':
                    continue

                def get_v(col_i):
                    return r[col_i].strip() if col_i is not None and col_i < len(r) else ''

                # Khusus fokus Prodi S1 Sistem Informasi
                prodi_val = get_v(col_prodi)
                if prodi_val and "sistem informasi" not in prodi_val.lower() and "si" != prodi_val.lower():
                    continue

                day_val = None
                slot_val = None
                room_val = None
                is_manual = False

                if import_mode == 'existing':
                    raw_hari = get_v(col_hari).lower()
                    for k, d_num in day_names_map.items():
                        if k in raw_hari:
                            day_val = d_num
                            break

                    raw_jam = get_v(col_jam)
                    slot_times = session.get_slot_times()
                    for idx, s_time in enumerate(slot_times, start=1):
                        if raw_jam and (raw_jam in s_time or s_time in raw_jam or raw_jam[:5] == s_time[:5]):
                            slot_val = idx
                            break

                    raw_ruang = get_v(col_ruang)
                    if raw_ruang and 'ruang' in raw_ruang.lower():
                        nums = re.findall(r'\d+', raw_ruang)
                        if nums:
                            room_val = int(nums[0])
                    if day_val and slot_val:
                        is_manual = True

                StudentDefense.objects.create(
                    session=session,
                    no=get_v(col_no),
                    periode=get_v(col_periode) or '4',
                    kelompok_keahlian=get_v(col_kk),
                    prodi=get_v(col_prodi),
                    nim=nim_val,
                    nama=get_v(col_nama),
                    judul=get_v(col_judul),
                    pembimbing_1=get_v(col_p1),
                    pembimbing_2=get_v(col_p2),
                    penguji_1=get_v(col_u1),
                    penguji_2=get_v(col_u2),
                    status_pendaftaran=get_v(col_status) or 'LENGKAP',
                    note=get_v(col_note),
                    tanggal_text=get_v(col_tgl),
                    day_num=day_val,
                    slot_num=slot_val,
                    room_num=room_val,
                    is_manual=is_manual,
                    is_locked=False
                )
                count += 1

            messages.success(request, f"Berhasil mengimpor {count} data mahasiswa dari sheet '{target_sheet_name}'.")
            return redirect('scheduler:student_list')

        except Exception as e:
            messages.error(request, f"Gagal membaca berkas Excel: {str(e)}")
            return redirect('scheduler:import_excel')

    default_file_exists = os.path.exists("Plotting Periode 4 (1).xlsx")
    return render(request, 'scheduler/import.html', {
        'session': session,
        'default_file_exists': default_file_exists
    })


def load_default_sample(request):
    session = get_current_session()
    sample_path = "Plotting Periode 4 (1).xlsx"

    if not os.path.exists(sample_path):
        messages.error(request, f"Berkas contoh '{sample_path}' tidak ditemukan.")
        return redirect('scheduler:import_excel')

    try:
        sheets = read_xlsx(sample_path)
        # Prioritaskan sheet AKD (khusus prodi Sistem Informasi)
        sheet = sheets.get('Sidang Periode 4 AKD')
        if not sheet:
            sheet = sheets.get('Sidang Periode 4') or list(sheets.values())[0]

        session.students.all().delete()

        count = 0
        for row in sheet[2:]:
            if len(row) > 4 and row[4].strip():
                nim = row[4].strip()
                if not nim.isdigit():
                    continue

                def val(idx):
                    return row[idx].strip() if len(row) > idx else ''

                # Filter khusus S1 Sistem Informasi jika data bercampur
                prodi_text = val(3).lower()
                if prodi_text and 'sistem informasi' not in prodi_text and 'si' != prodi_text:
                    continue

                StudentDefense.objects.create(
                    session=session,
                    no=val(0),
                    periode=val(1) or '4',
                    kelompok_keahlian=val(2),
                    prodi=val(3) or 'S1 Sistem Informasi',
                    nim=nim,
                    nama=val(5),
                    judul=val(6),
                    pembimbing_1=val(7),
                    pembimbing_2=val(8),
                    note=val(9),
                    status_pendaftaran=val(10) or 'LENGKAP',
                    penguji_1=val(15),
                    penguji_2=val(16),
                    day_num=None,
                    slot_num=None,
                    room_num=None,
                    is_manual=False,
                    is_locked=False
                )
                count += 1

        messages.success(request, f"Sukses! {count} mahasiswa dari 'Plotting Periode 4 (1).xlsx' berhasil dimuat.")
        return redirect('scheduler:student_list')
    except Exception as e:
        messages.error(request, f"Gagal memuat berkas contoh: {str(e)}")
        return redirect('scheduler:import_excel')
