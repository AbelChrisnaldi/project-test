import json
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import ScheduleSession, StudentDefense, GARunLog
from .genetic_algorithm import check_conflicts


def get_current_session():
    session = ScheduleSession.objects.filter(is_active=True).first()
    if not session:
        session = ScheduleSession.objects.create(
            name="Jadwal Sidang Tugas Akhir - S1 Sistem Informasi",
            total_days=8,
            start_time="08:00",
            end_time="16:30",
            total_rooms=3,
            room_labels_json='["KTT2.04", "KTT2.05", "KTT2.06"]'
        )
    return session


def dashboard(request):
    session = get_current_session()
    students = list(session.students.all())
    
    total_students = len(students)
    scheduled_students = [s for s in students if s.is_scheduled]
    unscheduled_students = [s for s in students if not s.is_scheduled]
    locked_students = [s for s in students if s.is_locked]
    
    students_data = []
    unique_lecturers = set()
    for s in students:
        lecs = s.get_lecturers()
        for l in lecs:
            unique_lecturers.add(l)
        students_data.append({
            'id': s.id,
            'nim': s.nim,
            'nama': s.nama,
            'day_num': s.day_num,
            'slot_num': s.slot_num,
            'room_num': s.room_num,
            'lecturers': lecs,
            'is_locked': s.is_locked
        })
        
    conflict_data = check_conflicts(
        students_data,
        session.total_days,
        session.slots_per_day,
        session.total_rooms
    )
    
    latest_log = session.ga_logs.order_by('-id').first()

    prodi_counter = {}
    for s in students:
        p = s.prodi or 'Lainnya'
        prodi_counter[p] = prodi_counter.get(p, 0) + 1

    context = {
        'session': session,
        'total_students': total_students,
        'scheduled_count': len(scheduled_students),
        'unscheduled_count': len(unscheduled_students),
        'locked_count': len(locked_students),
        'unique_lecturers_count': len(unique_lecturers),
        'total_capacity': session.total_capacity,
        'conflict_data': conflict_data,
        'latest_log': latest_log,
        'prodi_counter': sorted(prodi_counter.items(), key=lambda x: x[1], reverse=True)[:6],
    }
    return render(request, 'scheduler/dashboard.html', context)


def settings_view(request):
    session = get_current_session()

    if request.method == 'POST':
        session.name = request.POST.get('name', session.name).strip()
        session.total_days = max(1, int(request.POST.get('total_days', session.total_days)))
        session.start_time = request.POST.get('start_time', session.start_time).strip()
        session.end_time = request.POST.get('end_time', session.end_time).strip()
        session.total_rooms = max(1, int(request.POST.get('total_rooms', session.total_rooms)))

        slot_lines = request.POST.get('slot_times_text', '').strip().splitlines()
        slot_times = [s.strip() for s in slot_lines if s.strip()]
        if slot_times:
            session.set_slot_times(slot_times)

        day_lines = request.POST.get('day_labels_text', '').strip().splitlines()
        day_labels = [s.strip() for s in day_lines if s.strip()]
        if day_labels:
            session.day_labels_json = json.dumps(day_labels)

        room_lines = request.POST.get('room_labels_text', '').strip().splitlines()
        room_labels = [s.strip() for s in room_lines if s.strip()]
        if room_labels:
            session.room_labels_json = json.dumps(room_labels)

        session.population_size = max(10, int(request.POST.get('population_size', 50)))
        session.max_generations = max(10, int(request.POST.get('max_generations', 100)))
        session.crossover_rate = float(request.POST.get('crossover_rate', 0.8))
        session.mutation_rate = float(request.POST.get('mutation_rate', 0.3))

        session.save()
        messages.success(request, "Pengaturan batasan slot dan algoritma berhasil disimpan.")
        return redirect('scheduler:settings')

    slot_times = session.get_slot_times()
    day_labels = session.get_day_labels()
    room_labels = session.get_room_labels()
    student_count = session.students.count()

    context = {
        'session': session,
        'slot_times': slot_times,
        'slot_times_text': '\n'.join(slot_times),
        'day_labels_text': '\n'.join(day_labels),
        'room_labels_text': '\n'.join(room_labels),
        'student_count': student_count,
        'total_capacity': session.total_capacity,
        'capacity_sufficient': session.total_capacity >= student_count,
        'capacity_diff': session.total_capacity - student_count,
    }
    return render(request, 'scheduler/settings.html', context)
