from django.db import models
import json

class ScheduleSession(models.Model):
    name = models.CharField(max_length=200, default="Jadwal Sidang Tugas Akhir - S1 Sistem Informasi")
    total_days = models.PositiveIntegerField(default=8)
    start_time = models.CharField(max_length=10, default="08:00")
    end_time = models.CharField(max_length=10, default="16:30")
    session_duration_minutes = models.PositiveIntegerField(default=90)
    total_rooms = models.PositiveIntegerField(default=3)
    
    # JSON arrays for configuration
    slot_times_json = models.TextField(default='["08.00 - 09.30", "09.30 - 11.00", "11.00 - 12.30", "13.00 - 14.30", "15.00 - 16.30"]')
    day_labels_json = models.TextField(default='["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Senin", "Selasa", "Rabu"]')
    room_labels_json = models.TextField(default='["KTT2.04", "KTT2.05", "KTT2.06"]')
    
    # GA Parameters
    population_size = models.PositiveIntegerField(default=60)
    max_generations = models.PositiveIntegerField(default=150)
    crossover_rate = models.FloatField(default=0.8)
    mutation_rate = models.FloatField(default=0.2)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_slot_times(self):
        try:
            return json.loads(self.slot_times_json)
        except Exception:
            return ["08.00 - 09.30", "09.30 - 11.00", "11.00 - 12.30", "13.00 - 14.30", "15.00 - 16.30"]

    def set_slot_times(self, times_list):
        self.slot_times_json = json.dumps(times_list)

    def get_day_labels(self):
        try:
            labels = json.loads(self.day_labels_json)
            if len(labels) < self.total_days:
                labels.extend([f"Hari Ke-{i}" for i in range(len(labels) + 1, self.total_days + 1)])
            return labels[:self.total_days]
        except Exception:
            return [f"Hari Ke-{i}" for i in range(1, self.total_days + 1)]

    def get_room_labels(self):
        try:
            labels = json.loads(self.room_labels_json)
            if len(labels) < self.total_rooms:
                labels.extend([f"Ruang {i}" for i in range(len(labels) + 1, self.total_rooms + 1)])
            return labels[:self.total_rooms]
        except Exception:
            return [f"Ruang {i}" for i in range(1, self.total_rooms + 1)]

    @property
    def slots_per_day(self):
        return len(self.get_slot_times())

    @property
    def total_capacity(self):
        return self.total_days * self.slots_per_day * self.total_rooms

    def __str__(self):
        return self.name


class StudentDefense(models.Model):
    session = models.ForeignKey(ScheduleSession, on_delete=models.CASCADE, related_name='students')
    no = models.CharField(max_length=20, blank=True, default='')
    periode = models.CharField(max_length=50, blank=True, default='4')
    kelompok_keahlian = models.CharField(max_length=200, blank=True, default='')
    prodi = models.CharField(max_length=200, blank=True, default='')
    nim = models.CharField(max_length=50, db_index=True)
    nama = models.CharField(max_length=255)
    judul = models.TextField(blank=True, default='')
    
    pembimbing_1 = models.CharField(max_length=50, blank=True, default='')
    pembimbing_2 = models.CharField(max_length=50, blank=True, default='')
    penguji_1 = models.CharField(max_length=50, blank=True, default='')
    penguji_2 = models.CharField(max_length=50, blank=True, default='')
    
    status_pendaftaran = models.CharField(max_length=100, blank=True, default='LENGKAP')
    note = models.TextField(blank=True, default='')
    tanggal_text = models.CharField(max_length=100, blank=True, default='')

    # Scheduling Assignment (Anonymous / Numeric)
    # day_num: 1 .. total_days, or None if unassigned/kosong
    day_num = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    # slot_num: 1 .. slots_per_day, or None if unassigned/kosong
    slot_num = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    # room_num: 1 .. total_rooms, or None if unassigned/kosong
    room_num = models.PositiveIntegerField(null=True, blank=True, db_index=True)

    # Flag for manual control and locking
    is_manual = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)

    def get_lecturers(self):
        """Returns unique non-empty lecturer codes for this defense."""
        lecs = []
        for code in [self.pembimbing_1, self.pembimbing_2, self.penguji_1, self.penguji_2]:
            c = code.strip().upper() if code else ''
            if c and c not in ['-', 'NONE', 'TIDAK ADA', 'TIDAK PERLU DIISI'] and c not in lecs:
                lecs.append(c)
        return lecs

    @property
    def is_scheduled(self):
        return (self.day_num is not None) and (self.slot_num is not None) and (self.room_num is not None)

    def get_day_display_name(self):
        if not self.day_num:
            return "Belum Terjadwal"
        labels = self.session.get_day_labels()
        if 1 <= self.day_num <= len(labels):
            return f"{labels[self.day_num - 1]} (Hari {self.day_num})"
        return f"Hari Ke-{self.day_num}"

    def get_time_display_name(self):
        if not self.slot_num:
            return "-"
        times = self.session.get_slot_times()
        if 1 <= self.slot_num <= len(times):
            return times[self.slot_num - 1]
        return f"Sesi {self.slot_num}"

    def get_room_display_name(self):
        if not self.room_num:
            return "-"
        rooms = self.session.get_room_labels()
        if 1 <= self.room_num <= len(rooms):
            return f"{rooms[self.room_num - 1]} (Ruang {self.room_num})"
        return f"Ruang {self.room_num}"

    def __str__(self):
        return f"{self.nim} - {self.nama}"


class GARunLog(models.Model):
    session = models.ForeignKey(ScheduleSession, on_delete=models.CASCADE, related_name='ga_logs')
    timestamp = models.DateTimeField(auto_now_add=True)
    generations_run = models.PositiveIntegerField(default=0)
    initial_conflicts = models.PositiveIntegerField(default=0)
    final_conflicts = models.PositiveIntegerField(default=0)
    room_conflicts = models.PositiveIntegerField(default=0)
    lecturer_conflicts = models.PositiveIntegerField(default=0)
    best_fitness = models.FloatField(default=0.0)
    execution_time_seconds = models.FloatField(default=0.0)
    message = models.CharField(max_length=255, default='Selesai')
    history_json = models.TextField(blank=True, default='[]')
