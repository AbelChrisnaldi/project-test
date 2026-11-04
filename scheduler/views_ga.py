import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import ScheduleSession, StudentDefense, GARunLog
from .views_dashboard import get_current_session
from .genetic_algorithm import GeneticScheduler


def genetic_view(request):
    session = get_current_session()
    students = list(session.students.all())
    student_count = len(students)
    locked_count = len([s for s in students if s.is_locked])
    unlocked_count = student_count - locked_count

    capacity = session.total_capacity
    capacity_ok = capacity >= student_count

    logs = session.ga_logs.order_by('-id')[:5]

    context = {
        'session': session,
        'student_count': student_count,
        'locked_count': locked_count,
        'unlocked_count': unlocked_count,
        'capacity': capacity,
        'capacity_ok': capacity_ok,
        'logs': logs,
    }
    return render(request, 'scheduler/genetic.html', context)


@csrf_exempt
def api_run_ga(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Metode POST dibutuhkan.'}, status=400)

    session = get_current_session()
    students = list(session.students.all())

    if not students:
        return JsonResponse({'success': False, 'message': 'Belum ada data mahasiswa untuk dijadwalkan.'})

    if session.total_capacity < len(students):
        return JsonResponse({
            'success': False,
            'message': f"Kapasitas slot ({session.total_capacity}) lebih kecil dari jumlah mahasiswa ({len(students)}). Silakan tambah hari atau ruangan pada menu Pengaturan."
        })

    students_payload = []
    for s in students:
        students_payload.append({
            'id': s.id,
            'nim': s.nim,
            'nama': s.nama,
            'lecturers': s.get_lecturers(),
            'is_locked': s.is_locked,
            'is_manual': s.is_manual,
            'day_num': s.day_num,
            'slot_num': s.slot_num,
            'room_num': s.room_num
        })

    try:
        body = json.loads(request.body) if request.body else {}
    except Exception:
        body = {}

    pop_size = int(body.get('population_size', session.population_size))
    max_gen = int(body.get('max_generations', session.max_generations))
    cx_rate = float(body.get('crossover_rate', session.crossover_rate))
    mut_rate = float(body.get('mutation_rate', session.mutation_rate))

    ga = GeneticScheduler(
        students=students_payload,
        total_days=session.total_days,
        slots_per_day=session.slots_per_day,
        total_rooms=session.total_rooms,
        pop_size=pop_size,
        max_generations=max_gen,
        crossover_rate=cx_rate,
        mutation_rate=mut_rate
    )

    result = ga.run()

    if result.get('success'):
        student_map = {s.id: s for s in students}
        to_update = []
        for assign in result.get('assignments', []):
            st = student_map.get(assign['id'])
            if st and not st.is_locked:
                st.day_num = assign['day_num']
                st.slot_num = assign['slot_num']
                st.room_num = assign['room_num']
                st.is_manual = False
                to_update.append(st)

        StudentDefense.objects.bulk_update(to_update, ['day_num', 'slot_num', 'room_num', 'is_manual'])

        GARunLog.objects.create(
            session=session,
            generations_run=result['generations_run'],
            initial_conflicts=result['initial_conflicts'] or 0,
            final_conflicts=result['final_conflicts'],
            room_conflicts=result['room_conflicts'],
            lecturer_conflicts=result['lecturer_conflicts'],
            best_fitness=result['best_fitness'],
            execution_time_seconds=result['execution_time_seconds'],
            message=result['message'],
            history_json=json.dumps(result.get('history', []))
        )

    return JsonResponse(result)
