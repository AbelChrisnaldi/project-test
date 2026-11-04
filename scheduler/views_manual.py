import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import ScheduleSession, StudentDefense
from .views_dashboard import get_current_session
from .genetic_algorithm import check_conflicts


def manual_grid(request):
    session = get_current_session()
    
    selected_day = int(request.GET.get('day', 1))
    if selected_day < 1 or selected_day > session.total_days:
        selected_day = 1

    students = list(session.students.all())
    
    students_data = []
    for s in students:
        students_data.append({
            'id': s.id,
            'nim': s.nim,
            'nama': s.nama,
            'day_num': s.day_num,
            'slot_num': s.slot_num,
            'room_num': s.room_num,
            'lecturers': s.get_lecturers(),
            'is_locked': s.is_locked
        })

    conflict_data = check_conflicts(
        students_data,
        session.total_days,
        session.slots_per_day,
        session.total_rooms
    )

    clashing_student_ids = set()
    for rc in conflict_data['room_conflicts']:
        for st in rc['students']:
            clashing_student_ids.add(st['id'])
    for lc in conflict_data['lecturer_conflicts']:
        for st in lc['students']:
            clashing_student_ids.add(st['id'])

    slots = list(range(1, session.slots_per_day + 1))
    rooms = list(range(1, session.total_rooms + 1))
    slot_times = session.get_slot_times()
    room_labels = session.get_room_labels()
    day_labels = session.get_day_labels()

    grid = []
    for s_idx in slots:
        row_cells = []
        for r_idx in rooms:
            matching = [s for s in students if s.day_num == selected_day and s.slot_num == s_idx and s.room_num == r_idx]
            cell_data = {
                'slot_num': s_idx,
                'room_num': r_idx,
                'time_str': slot_times[s_idx - 1] if s_idx <= len(slot_times) else f"Sesi {s_idx}",
                'room_name': room_labels[r_idx - 1] if r_idx <= len(room_labels) else f"Ruang {r_idx}",
                'student': matching[0] if matching else None,
                'multiple_students': matching[1:] if len(matching) > 1 else [],
                'is_clash': any(m.id in clashing_student_ids for m in matching)
            }
            row_cells.append(cell_data)
        grid.append({
            'slot_num': s_idx,
            'time_str': slot_times[s_idx - 1] if s_idx <= len(slot_times) else f"Sesi {s_idx}",
            'cells': row_cells
        })

    unscheduled_students = [s for s in students if not s.is_scheduled]

    # Map of days with labels
    day_cards = []
    for d in range(1, session.total_days + 1):
        lbl = day_labels[d - 1] if d <= len(day_labels) else f"Hari Ke-{d}"
        count = len([s for s in students if s.day_num == d])
        day_cards.append({'day_num': d, 'label': lbl, 'count': count})

    context = {
        'session': session,
        'selected_day': selected_day,
        'day_cards': day_cards,
        'room_labels': room_labels,
        'slot_times': slot_times,
        'grid': grid,
        'unscheduled_students': unscheduled_students,
        'conflict_data': conflict_data,
        'clashing_student_ids': clashing_student_ids,
        'total_students': len(students),
        'scheduled_count': len(students) - len(unscheduled_students),
        'unscheduled_count': len(unscheduled_students),
    }
    return render(request, 'scheduler/manual_grid.html', context)


@csrf_exempt
def api_assign_slot(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Metode POST dibutuhkan.'}, status=400)

    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        day_num = data.get('day_num')
        slot_num = data.get('slot_num')
        room_num = data.get('room_num')
        is_locked = data.get('is_locked', False)

        session = get_current_session()
        student = get_object_or_404(StudentDefense, id=student_id, session=session)

        student.day_num = int(day_num) if day_num else None
        student.slot_num = int(slot_num) if slot_num else None
        student.room_num = int(room_num) if room_num else None
        student.is_manual = True if student.day_num else False
        student.is_locked = bool(is_locked)
        student.save()

        students_all = list(session.students.all())
        students_data = [{
            'id': s.id,
            'nim': s.nim,
            'nama': s.nama,
            'day_num': s.day_num,
            'slot_num': s.slot_num,
            'room_num': s.room_num,
            'lecturers': s.get_lecturers(),
            'is_locked': s.is_locked
        } for s in students_all]

        conflict_info = check_conflicts(
            students_data,
            session.total_days,
            session.slots_per_day,
            session.total_rooms
        )

        return JsonResponse({
            'success': True,
            'message': f"Jadwal {student.nim} ({student.nama}) berhasil diperbarui.",
            'total_conflicts': conflict_info['total_conflicts'],
            'student': {
                'id': student.id,
                'nim': student.nim,
                'nama': student.nama,
                'day_num': student.day_num,
                'slot_num': student.slot_num,
                'room_num': student.room_num,
                'is_locked': student.is_locked
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@csrf_exempt
def api_clear_slot(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Metode POST dibutuhkan.'}, status=400)

    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        session = get_current_session()
        student = get_object_or_404(StudentDefense, id=student_id, session=session)

        student.day_num = None
        student.slot_num = None
        student.room_num = None
        student.is_manual = False
        student.is_locked = False
        student.save()

        return JsonResponse({
            'success': True,
            'message': f"Slot {student.nim} berhasil dikosongkan."
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@csrf_exempt
def api_batch_action(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Metode POST dibutuhkan.'}, status=400)

    try:
        data = json.loads(request.body)
        action = data.get('action')
        session = get_current_session()

        if action == 'clear_all':
            session.students.update(day_num=None, slot_num=None, room_num=None, is_manual=False, is_locked=False)
            msg = "Semua jadwal telah dikosongkan."
        elif action == 'clear_unlocked':
            session.students.filter(is_locked=False).update(day_num=None, slot_num=None, room_num=None, is_manual=False)
            msg = "Jadwal yang tidak terkunci telah dikosongkan."
        elif action == 'lock_all':
            session.students.filter(day_num__isnull=False).update(is_locked=True)
            msg = "Semua jadwal yang sudah terisi berhasil dikunci."
        elif action == 'unlock_all':
            session.students.update(is_locked=False)
            msg = "Semua kunci jadwal telah dilepas."
        else:
            return JsonResponse({'success': False, 'message': 'Aksi tidak dikenal.'}, status=400)

        return JsonResponse({'success': True, 'message': msg})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)
