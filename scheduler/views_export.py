from django.shortcuts import render
from django.http import HttpResponse
from .views_dashboard import get_current_session
from .xlsx_utils import write_xlsx


def export_view(request):
    session = get_current_session()
    students = session.students.all().order_by('day_num', 'slot_num', 'room_num', 'id')
    scheduled_count = students.filter(day_num__isnull=False).count()

    context = {
        'session': session,
        'total_count': students.count(),
        'scheduled_count': scheduled_count,
        'unscheduled_count': students.count() - scheduled_count,
        'day_labels': session.get_day_labels(),
        'room_labels': session.get_room_labels(),
        'slot_times': session.get_slot_times(),
    }
    return render(request, 'scheduler/export.html', context)


def export_download(request):
    session = get_current_session()
    export_type = request.GET.get('type', 'standard')
    naming_style = request.GET.get('naming', 'named')

    day_labels = session.get_day_labels()
    room_labels = session.get_room_labels()
    slot_times = session.get_slot_times()

    students = session.students.all().order_by('day_num', 'slot_num', 'room_num', 'nim')

    if export_type == 'matrix':
        # Sheet Matriks Jadwal
        headers = ['Hari', 'Jam / Sesi'] + [
            f"{room_labels[i-1]}\n(Ruang {i})" if naming_style == 'named' and i <= len(room_labels) else f"Ruang {i}"
            for i in range(1, session.total_rooms + 1)
        ]

        matrix_rows = []
        for d in range(1, session.total_days + 1):
            day_str = f"{day_labels[d-1]} (Hari {d})" if naming_style == 'named' and d <= len(day_labels) else f"Hari Ke-{d}"
            for s in range(1, session.slots_per_day + 1):
                time_str = slot_times[s-1] if s <= len(slot_times) else f"Sesi {s}"
                row_val = [day_str, time_str]
                for r in range(1, session.total_rooms + 1):
                    match = [st for st in students if st.day_num == d and st.slot_num == s and st.room_num == r]
                    if match:
                        st = match[0]
                        lecs = f"P:[{st.pembimbing_1 or '-'}/{st.pembimbing_2 or '-'}] U:[{st.penguji_1 or '-'}/{st.penguji_2 or '-'}]"
                        row_val.append(f"{st.nim} - {st.nama}\n{lecs}")
                    else:
                        row_val.append("-")
                matrix_rows.append(row_val)

        # Lebar kolom matriks: Hari 16, Sesi 18, Ruangan 28 masing-masing
        col_widths = [16, 18] + [28] * session.total_rooms
        center_cols = [0, 1]  # Hari & Sesi rata tengah

        sheets_dict = {
            'Matriks Jadwal Sidang': {
                'title': f"MATRIKS JADWAL SIDANG TUGAS AKHIR - {session.name.upper()}",
                'headers': headers,
                'rows': matrix_rows,
                'col_widths': col_widths,
                'center_cols': center_cols
            }
        }
    else:
        # Format Standar Rekapitulasi Sidang Akademik
        headers = [
            'No',
            'Periode Sidang TA',
            'Kelompok Keahlian',
            'Program Studi',
            'NIM',
            'Nama Mahasiswa',
            'Judul Tugas Akhir (sesuai SK)',
            'Pembimbing 1',
            'Pembimbing 2',
            'Penguji 1',
            'Penguji 2',
            'Status',
            'Hari',
            'Jam / Sesi',
            'Ruangan'
        ]

        # Lebar kolom spesifik agar tampilan proporsional dan mudah dibaca
        # 0:No(6), 1:Periode(10), 2:KK(24), 3:Prodi(26), 4:NIM(14), 5:Nama(28), 6:Judul(46),
        # 7:P1(12), 8:P2(12), 9:U1(12), 10:U2(12), 11:Status(12), 12:Hari(16), 13:Jam(18), 14:Ruang(18)
        col_widths = [6, 10, 24, 26, 14, 28, 46, 12, 12, 12, 12, 12, 16, 18, 18]

        # Kolom yang diratakan tengah (center): No, Periode, NIM, Kode Dosen, Status, Hari, Jam, Ruang
        center_cols = [0, 1, 4, 7, 8, 9, 10, 11, 12, 13, 14]

        data_rows = []
        for idx, s in enumerate(students, start=1):
            if s.day_num:
                if naming_style == 'named' and s.day_num <= len(day_labels):
                    hari_str = f"{day_labels[s.day_num - 1]} (Hari {s.day_num})"
                else:
                    hari_str = f"Hari Ke-{s.day_num}"
            else:
                hari_str = "Belum Terjadwal"

            if s.slot_num and s.slot_num <= len(slot_times):
                jam_str = slot_times[s.slot_num - 1]
            elif s.slot_num:
                jam_str = f"Sesi {s.slot_num}"
            else:
                jam_str = "-"

            if s.room_num:
                if naming_style == 'named' and s.room_num <= len(room_labels):
                    ruang_str = f"{room_labels[s.room_num - 1]} (R.{s.room_num})"
                else:
                    ruang_str = f"Ruang {s.room_num}"
            else:
                ruang_str = "-"

            data_rows.append([
                str(idx),
                s.periode or '4',
                s.kelompok_keahlian or '-',
                s.prodi or '-',
                s.nim,
                s.nama,
                s.judul or '-',
                s.pembimbing_1 or '-',
                s.pembimbing_2 or '-',
                s.penguji_1 or '-',
                s.penguji_2 or '-',
                s.status_pendaftaran or 'LENGKAP',
                hari_str,
                jam_str,
                ruang_str
            ])

        sheets_dict = {
            'Plotting Jadwal Sidang': {
                'title': f"REKAPITULASI PLOTTING JADWAL SIDANG TUGAS AKHIR - {session.name.upper()}",
                'headers': headers,
                'rows': data_rows,
                'col_widths': col_widths,
                'center_cols': center_cols
            }
        }

    xlsx_bytes = write_xlsx(sheets_dict)
    filename = f"Jadwal_Sidang_TA_{export_type}_{naming_style}.xlsx"

    response = HttpResponse(
        xlsx_bytes,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
