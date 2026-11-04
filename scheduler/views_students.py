from django.core.paginator import Paginator
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import ScheduleSession, StudentDefense
from .views_dashboard import get_current_session


def student_list(request):
    session = get_current_session()
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', 'all')
    prodi_filter = request.GET.get('prodi', 'all')
    limit = request.GET.get('limit', '50').strip()

    students = session.students.all().order_by('id')

    if query:
        students = students.filter(
            nim__icontains=query
        ) | students.filter(
            nama__icontains=query
        ) | students.filter(
            pembimbing_1__icontains=query
        ) | students.filter(
            pembimbing_2__icontains=query
        ) | students.filter(
            penguji_1__icontains=query
        ) | students.filter(
            penguji_2__icontains=query
        )

    if status_filter == 'scheduled':
        students = students.filter(day_num__isnull=False, slot_num__isnull=False, room_num__isnull=False)
    elif status_filter == 'unscheduled':
        students = students.filter(day_num__isnull=True)
    elif status_filter == 'locked':
        students = students.filter(is_locked=True)

    if prodi_filter != 'all' and prodi_filter:
        students = students.filter(prodi=prodi_filter)

    all_prodis = session.students.values_list('prodi', flat=True).distinct()
    all_prodis = sorted([p for p in all_prodis if p])

    total_count = session.students.count()
    scheduled_count = session.students.filter(day_num__isnull=False, slot_num__isnull=False, room_num__isnull=False).count()
    unscheduled_count = total_count - scheduled_count
    filtered_count = students.count()

    # Limit data / Pagination (50, 75, 100, atau semua)
    if limit in ['50', '75', '100']:
        per_page = int(limit)
        paginator = Paginator(students, per_page)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        students_display = page_obj
        is_paginated = True
    else:
        limit = 'all'
        paginator = None
        page_obj = None
        students_display = students
        is_paginated = False

    context = {
        'session': session,
        'students': students_display,
        'page_obj': page_obj,
        'is_paginated': is_paginated,
        'limit': limit,
        'total_count': total_count,
        'scheduled_count': scheduled_count,
        'unscheduled_count': unscheduled_count,
        'filtered_count': filtered_count,
        'query': query,
        'status_filter': status_filter,
        'prodi_filter': prodi_filter,
        'all_prodis': all_prodis,
        'day_labels': session.get_day_labels(),
        'slot_times': session.get_slot_times(),
        'room_labels': session.get_room_labels(),
    }
    return render(request, 'scheduler/student_list.html', context)


def student_edit(request, student_id):
    session = get_current_session()
    student = get_object_or_404(StudentDefense, id=student_id, session=session)

    if request.method == 'POST':
        student.nim = request.POST.get('nim', student.nim).strip()
        student.nama = request.POST.get('nama', student.nama).strip()
        student.prodi = request.POST.get('prodi', student.prodi).strip()
        student.kelompok_keahlian = request.POST.get('kelompok_keahlian', student.kelompok_keahlian).strip()
        student.judul = request.POST.get('judul', student.judul).strip()
        student.pembimbing_1 = request.POST.get('pembimbing_1', student.pembimbing_1).strip().upper()
        student.pembimbing_2 = request.POST.get('pembimbing_2', student.pembimbing_2).strip().upper()
        student.penguji_1 = request.POST.get('penguji_1', student.penguji_1).strip().upper()
        student.penguji_2 = request.POST.get('penguji_2', student.penguji_2).strip().upper()

        day_raw = request.POST.get('day_num', '').strip()
        slot_raw = request.POST.get('slot_num', '').strip()
        room_raw = request.POST.get('room_num', '').strip()

        if day_raw and slot_raw and room_raw:
            student.day_num = int(day_raw)
            student.slot_num = int(slot_raw)
            student.room_num = int(room_raw)
            student.is_manual = True
        else:
            student.day_num = None
            student.slot_num = None
            student.room_num = None
            student.is_manual = False

        student.is_locked = bool(request.POST.get('is_locked'))
        student.save()

        messages.success(request, f"Data mahasiswa {student.nim} ({student.nama}) berhasil diperbarui.")
        return redirect('scheduler:student_list')

    # Bangun peta keterisian slot dan aktivitas dosen untuk seluruh mahasiswa lain
    other_students = session.students.exclude(id=student.id).filter(
        day_num__isnull=False, slot_num__isnull=False, room_num__isnull=False
    )

    room_map = {}
    lecturer_map = {}

    for s in other_students:
        rk = f"{s.day_num}_{s.slot_num}_{s.room_num}"
        room_map[rk] = {
            'id': s.id,
            'nim': s.nim,
            'nama': s.nama,
            'prodi': s.prodi
        }

        pk = f"{s.day_num}_{s.slot_num}"
        if pk not in lecturer_map:
            lecturer_map[pk] = []

        for lec in s.get_lecturers():
            lecturer_map[pk].append({
                'lecturer': lec,
                'room_num': s.room_num,
                'student_nim': s.nim,
                'student_nama': s.nama
            })

    context = {
        'session': session,
        'student': student,
        'student_lecturers': student.get_lecturers(),
        'day_labels': session.get_day_labels(),
        'slot_times': session.get_slot_times(),
        'room_labels': session.get_room_labels(),
        'room_map_json': json.dumps(room_map),
        'lecturer_map_json': json.dumps(lecturer_map),
    }
    return render(request, 'scheduler/student_edit.html', context)


def student_delete(request, student_id):
    session = get_current_session()
    student = get_object_or_404(StudentDefense, id=student_id, session=session)
    nim = student.nim
    nama = student.nama
    student.delete()
    messages.success(request, f"Data mahasiswa {nim} ({nama}) berhasil dihapus permanen.")
    return redirect('scheduler:student_list')


def student_clear_slot(request, student_id):
    session = get_current_session()
    student = get_object_or_404(StudentDefense, id=student_id, session=session)
    student.day_num = None
    student.slot_num = None
    student.room_num = None
    student.is_manual = False
    student.is_locked = False
    student.save()
    messages.info(request, f"Slot untuk mahasiswa {student.nim} dikosongkan.")
    return redirect(request.META.get('HTTP_REFERER', 'scheduler:student_list'))


def student_toggle_lock(request, student_id):
    session = get_current_session()
    student = get_object_or_404(StudentDefense, id=student_id, session=session)
    student.is_locked = not student.is_locked
    student.save()
    status_str = "dikunci" if student.is_locked else "dibuka kuncinya"
    messages.info(request, f"Jadwal {student.nim} berhasil {status_str}.")
    return redirect(request.META.get('HTTP_REFERER', 'scheduler:student_list'))
