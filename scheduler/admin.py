from django.contrib import admin
from .models import ScheduleSession, StudentDefense, GARunLog


@admin.register(ScheduleSession)
class ScheduleSessionAdmin(admin.ModelAdmin):
    list_display = ('name', 'total_days', 'total_rooms', 'is_active', 'created_at')
    list_filter = ('is_active',)


@admin.register(StudentDefense)
class StudentDefenseAdmin(admin.ModelAdmin):
    list_display = ('nim', 'nama', 'prodi', 'pembimbing_1', 'pembimbing_2', 'penguji_1', 'penguji_2', 'day_num', 'slot_num', 'room_num', 'is_locked', 'is_manual')
    list_filter = ('session', 'is_locked', 'is_manual', 'prodi')
    search_fields = ('nim', 'nama', 'pembimbing_1', 'pembimbing_2', 'penguji_1', 'penguji_2')


@admin.register(GARunLog)
class GARunLogAdmin(admin.ModelAdmin):
    list_display = ('session', 'timestamp', 'generations_run', 'initial_conflicts', 'final_conflicts', 'best_fitness', 'execution_time_seconds')
    list_filter = ('session',)
