import random
import time
from collections import defaultdict, Counter


def check_conflicts(students_list, total_days, slots_per_day, total_rooms):
    """
    Evaluates hard conflicts for a list of students with day_num, slot_num, room_num.
    Supports both dicts and model instances safely.
    Returns:
    {
        'room_conflicts': list of dicts,
        'lecturer_conflicts': list of dicts,
        'total_conflicts': int,
        'scheduled_count': int,
        'unscheduled_count': int
    }
    """
    def get_attr(obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def get_lecs(obj):
        if isinstance(obj, dict):
            return obj.get('lecturers', [])
        if hasattr(obj, 'get_lecturers'):
            return obj.get_lecturers()
        return getattr(obj, 'lecturers', [])

    room_map = defaultdict(list)
    lecturer_map = defaultdict(list)
    
    scheduled_count = 0
    unscheduled_count = 0

    for s in students_list:
        d = get_attr(s, 'day_num')
        sl = get_attr(s, 'slot_num')
        r = get_attr(s, 'room_num')

        if d and sl and r:
            scheduled_count += 1
            room_key = (d, sl, r)
            room_map[room_key].append(s)

            period_key = (d, sl)
            # Ensure unique lecturers per student in same defense
            unique_lecs = set(lec for lec in get_lecs(s) if lec)
            for lec in unique_lecs:
                lecturer_map[(period_key, lec)].append(s)
        else:
            unscheduled_count += 1

    room_conflicts = []
    for (d, sl, r), s_list in room_map.items():
        if len(s_list) > 1:
            msg = f"Bentrok Ruangan: Ada {len(s_list)} mahasiswa di Hari {d}, Sesi {sl}, Ruang {r}"
            room_conflicts.append({
                'day': d,
                'slot': sl,
                'room': r,
                'count': len(s_list),
                'students': [{'id': get_attr(s, 'id'), 'nim': get_attr(s, 'nim'), 'nama': get_attr(s, 'nama')} for s in s_list],
                'message': msg,
                'description': msg
            })

    lecturer_conflicts = []
    for ((d, sl), lec), s_list in lecturer_map.items():
        if len(s_list) > 1:
            rooms = list(set([get_attr(s, 'room_num') for s in s_list]))
            msg = f"Bentrok Dosen [{lec}]: Terjadwal di {len(s_list)} ruangan sekaligus pada Hari {d}, Sesi {sl}"
            lecturer_conflicts.append({
                'day': d,
                'slot': sl,
                'lecturer': lec,
                'count': len(s_list),
                'rooms': rooms,
                'students': [{'id': get_attr(s, 'id'), 'nim': get_attr(s, 'nim'), 'nama': get_attr(s, 'nama'), 'room': get_attr(s, 'room_num')} for s in s_list],
                'message': msg,
                'description': msg
            })

    total_conflicts = len(room_conflicts) + len(lecturer_conflicts)
    return {
        'room_conflicts': room_conflicts,
        'lecturer_conflicts': lecturer_conflicts,
        'total_conflicts': total_conflicts,
        'scheduled_count': scheduled_count,
        'unscheduled_count': unscheduled_count
    }


class GeneticScheduler:
    def __init__(self, students, total_days, slots_per_day, total_rooms,
                 pop_size=50, max_generations=120, crossover_rate=0.8, mutation_rate=0.3):
        self.students = students
        self.total_days = total_days
        self.slots_per_day = slots_per_day
        self.total_rooms = total_rooms
        self.pop_size = max(20, pop_size)
        self.max_generations = max(10, max_generations)
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate

        self.all_slots = []
        for d in range(1, self.total_days + 1):
            for s in range(1, self.slots_per_day + 1):
                for r in range(1, self.total_rooms + 1):
                    self.all_slots.append((d, s, r))

        self.locked_students = [s for s in students if s.get('is_locked') and s.get('day_num') and s.get('slot_num') and s.get('room_num')]
        self.unlocked_students = [s for s in students if s not in self.locked_students]

        self.locked_slots = set((s['day_num'], s['slot_num'], s['room_num']) for s in self.locked_students)
        self.available_slots = [slot for slot in self.all_slots if slot not in self.locked_slots]

    def evaluate_chromosome(self, chromosome):
        """
        chromosome: list of (d, s, r) slots corresponding to self.unlocked_students.
        Returns: (fitness, lecturer_clash_count, room_clash_count, clashing_indices)
        """
        lecturer_time_map = defaultdict(list)
        room_time_map = defaultdict(list)
        clashing_unlocked_indices = set()

        # 1. Register locked students
        for s in self.locked_students:
            slot = (s['day_num'], s['slot_num'], s['room_num'])
            d, sl, r = slot
            room_time_map[slot].append(-1)
            for lec in s.get('lecturers', []):
                if lec:
                    lecturer_time_map[((d, sl), lec)].append(-1)

        # 2. Register unlocked students from chromosome
        for idx, (slot, s) in enumerate(zip(chromosome, self.unlocked_students)):
            d, sl, r = slot
            room_time_map[slot].append(idx)
            for lec in s.get('lecturers', []):
                if lec:
                    lecturer_time_map[((d, sl), lec)].append(idx)

        # 3. Calculate room clashes
        room_clashes = 0
        for slot, occupants in room_time_map.items():
            if len(occupants) > 1:
                room_clashes += (len(occupants) - 1)
                for occ in occupants:
                    if occ >= 0:
                        clashing_unlocked_indices.add(occ)

        # 4. Calculate lecturer clashes
        lecturer_clashes = 0
        for ((d, sl), lec), occupants in lecturer_time_map.items():
            if len(occupants) > 1:
                lecturer_clashes += (len(occupants) - 1)
                for occ in occupants:
                    if occ >= 0:
                        clashing_unlocked_indices.add(occ)

        # Soft objective: distribute load across days
        day_counts = Counter(slot[0] for slot in chromosome)
        day_variance = 0
        if day_counts:
            avg_per_day = len(chromosome) / max(1, self.total_days)
            day_variance = sum(abs(c - avg_per_day) for c in day_counts.values())

        fitness = 1.0 / (1.0 + (room_clashes * 100) + (lecturer_clashes * 25) + (day_variance * 0.05))
        return fitness, lecturer_clashes, room_clashes, clashing_unlocked_indices

    def create_individual(self):
        """Creates a randomized valid assignment without room clashes."""
        shuffled_slots = list(self.available_slots)
        random.shuffle(shuffled_slots)
        return shuffled_slots[:len(self.unlocked_students)]

    def create_heuristic_individual(self):
        """Greedy heuristic prioritizing students whose lecturers appear frequently."""
        occupied_slots = set(self.locked_slots)
        lecturer_time_occupancy = defaultdict(set)

        for s in self.locked_students:
            period = (s['day_num'], s['slot_num'])
            for lec in s.get('lecturers', []):
                lecturer_time_occupancy[period].add(lec)

        # Count lecturer frequencies to prioritize harder students
        lec_counts = defaultdict(int)
        for s in self.unlocked_students:
            for l in s.get('lecturers', []):
                lec_counts[l] += 1

        indexed_students = list(enumerate(self.unlocked_students))
        indexed_students.sort(
            key=lambda item: (
                sum(lec_counts[l] for l in item[1].get('lecturers', [])),
                len(item[1].get('lecturers', []))
            ),
            reverse=True
        )

        candidate_slots = list(self.available_slots)
        random.shuffle(candidate_slots)

        result_chromosome = [None] * len(self.unlocked_students)

        for orig_idx, student in indexed_students:
            st_lecs = set(student.get('lecturers', []))
            best_slot = None
            min_clashes = 9999

            for slot in candidate_slots:
                if slot in occupied_slots:
                    continue
                d, sl, r = slot
                period = (d, sl)
                current_lecs = lecturer_time_occupancy[period]
                clashes = len(st_lecs.intersection(current_lecs))
                if clashes == 0:
                    best_slot = slot
                    min_clashes = 0
                    break
                elif clashes < min_clashes:
                    min_clashes = clashes
                    best_slot = slot

            if not best_slot:
                for slot in candidate_slots:
                    if slot not in occupied_slots:
                        best_slot = slot
                        break

            if best_slot:
                occupied_slots.add(best_slot)
                if best_slot in candidate_slots:
                    candidate_slots.remove(best_slot)
                result_chromosome[orig_idx] = best_slot
                d, sl, r = best_slot
                for lec in st_lecs:
                    lecturer_time_occupancy[(d, sl)].add(lec)

        leftover = [s for s in self.available_slots if s not in occupied_slots]
        for idx in range(len(result_chromosome)):
            if result_chromosome[idx] is None:
                if leftover:
                    result_chromosome[idx] = leftover.pop()
                else:
                    result_chromosome[idx] = random.choice(self.available_slots)

        return result_chromosome

    def local_search_repair(self, chromosome, clashing_indices):
        """
        Actively finds swaps or free slots that decrease conflicts for clashing students.
        """
        used_slots = set(chromosome)
        free_slots = [slot for slot in self.available_slots if slot not in used_slots]
        
        current_fit, current_lec, current_room, current_clashes = self.evaluate_chromosome(chromosome)
        if current_lec + current_room == 0:
            return chromosome

        candidate_indices = list(clashing_indices)
        random.shuffle(candidate_indices)

        for idx in candidate_indices:
            # 1. Try moving to free slots
            for free_s in list(free_slots):
                old_slot = chromosome[idx]
                chromosome[idx] = free_s
                new_fit, new_lec, new_room, new_clash_set = self.evaluate_chromosome(chromosome)
                if (new_lec + new_room) < (current_lec + current_room):
                    free_slots.remove(free_s)
                    free_slots.append(old_slot)
                    current_lec, current_room = new_lec, new_room
                    if current_lec + current_room == 0:
                        return chromosome
                    break
                else:
                    chromosome[idx] = old_slot

            # 2. Try swapping with other students
            all_indices = list(range(len(chromosome)))
            random.shuffle(all_indices)
            for other_idx in all_indices:
                if other_idx == idx:
                    continue
                chromosome[idx], chromosome[other_idx] = chromosome[other_idx], chromosome[idx]
                new_fit, new_lec, new_room, new_clash_set = self.evaluate_chromosome(chromosome)
                if (new_lec + new_room) < (current_lec + current_room):
                    current_lec, current_room = new_lec, new_room
                    if current_lec + current_room == 0:
                        return chromosome
                    break
                else:
                    chromosome[idx], chromosome[other_idx] = chromosome[other_idx], chromosome[idx]

        return chromosome

    def mutate(self, chromosome, clashing_indices):
        """Targeted and swap mutation."""
        used_slots = set(chromosome)
        free_slots = [slot for slot in self.available_slots if slot not in used_slots]

        candidates = list(clashing_indices) if clashing_indices else list(range(len(chromosome)))
        if not candidates:
            return chromosome

        mutate_count = max(1, int(len(candidates) * 0.25))
        chosen_indices = random.sample(candidates, min(mutate_count, len(candidates)))

        for idx in chosen_indices:
            if free_slots and random.random() < 0.6:
                new_slot = random.choice(free_slots)
                free_slots.remove(new_slot)
                free_slots.append(chromosome[idx])
                chromosome[idx] = new_slot
            else:
                other_idx = random.randint(0, len(chromosome) - 1)
                chromosome[idx], chromosome[other_idx] = chromosome[other_idx], chromosome[idx]

        return chromosome

    def crossover(self, parent1, parent2):
        """Order/Position crossover preserving slot uniqueness."""
        size = len(parent1)
        if size <= 2:
            return parent1[:]

        cp1 = random.randint(0, size - 2)
        cp2 = random.randint(cp1 + 1, size - 1)

        child = [None] * size
        child[cp1:cp2] = parent1[cp1:cp2]

        used_slots = set(s for s in child if s is not None)
        p2_slots = [s for s in parent2 if s not in used_slots]

        for i in range(size):
            if child[i] is None:
                if p2_slots:
                    child[i] = p2_slots.pop(0)
                else:
                    unused = [s for s in self.available_slots if s not in used_slots]
                    if unused:
                        pick = random.choice(unused)
                        child[i] = pick
                        used_slots.add(pick)
                    else:
                        child[i] = parent1[i]

        return child

    def run(self, progress_callback=None):
        start_time = time.time()
        
        needed = len(self.unlocked_students)
        available = len(self.available_slots)
        if available < needed:
            return {
                'success': False,
                'message': f"Kapasitas slot tidak mencukupi! Tersedia {available} slot, dibutuhkan {needed} slot mahasiswa.",
                'final_conflicts': 999,
                'generations_run': 0,
                'history': []
            }

        population = []
        heuristic_count = min(20, self.pop_size // 2)
        for _ in range(heuristic_count):
            population.append(self.create_heuristic_individual())
        for _ in range(self.pop_size - heuristic_count):
            population.append(self.create_individual())

        best_chromosome = None
        best_fitness = -1.0
        best_conflicts = 9999
        best_lec_clashes = 9999
        best_room_clashes = 9999
        initial_conflicts = None

        history = []

        for gen in range(1, self.max_generations + 1):
            evaluated = []
            for indiv in population:
                fit, lec_c, room_c, clash_idxs = self.evaluate_chromosome(indiv)
                total_c = lec_c + room_c
                evaluated.append((fit, indiv, total_c, lec_c, room_c, clash_idxs))

                if fit > best_fitness:
                    best_fitness = fit
                    best_chromosome = indiv[:]
                    best_conflicts = total_c
                    best_lec_clashes = lec_c
                    best_room_clashes = room_c

            if initial_conflicts is None:
                initial_conflicts = best_conflicts

            # If close to solution, apply local search repair to the best individual
            if best_conflicts > 0 and (best_conflicts <= 6 or gen % 10 == 0):
                _, _, _, clashing_idxs = self.evaluate_chromosome(best_chromosome)
                best_chromosome = self.local_search_repair(best_chromosome, clashing_idxs)
                fit, lec_c, room_c, _ = self.evaluate_chromosome(best_chromosome)
                if fit > best_fitness:
                    best_fitness = fit
                    best_conflicts = lec_c + room_c
                    best_lec_clashes = lec_c
                    best_room_clashes = room_c

            history.append({
                'generation': gen,
                'best_conflicts': best_conflicts,
                'lecturer_conflicts': best_lec_clashes,
                'room_conflicts': best_room_clashes,
                'best_fitness': round(best_fitness, 5)
            })

            if progress_callback and (gen % 5 == 0 or gen == 1 or best_conflicts == 0):
                progress_callback(gen, best_conflicts, best_fitness)

            # Early termination when 0 conflicts reached
            if best_conflicts == 0:
                break

            # Selection (Tournament of 3)
            evaluated.sort(key=lambda x: x[0], reverse=True)
            new_population = [evaluated[0][1][:], best_chromosome[:]]

            while len(new_population) < self.pop_size:
                cand1 = random.sample(evaluated, 3)
                p1 = max(cand1, key=lambda x: x[0])[1]

                cand2 = random.sample(evaluated, 3)
                p2 = max(cand2, key=lambda x: x[0])[1]

                if random.random() < self.crossover_rate:
                    child = self.crossover(p1, p2)
                else:
                    child = p1[:]

                if random.random() < self.mutation_rate:
                    _, _, _, clash_indices = self.evaluate_chromosome(child)
                    child = self.mutate(child, clash_indices)

                new_population.append(child)

            population = new_population

        assigned_results = []
        for s in self.locked_students:
            assigned_results.append({
                'id': s['id'],
                'nim': s['nim'],
                'nama': s['nama'],
                'day_num': s['day_num'],
                'slot_num': s['slot_num'],
                'room_num': s['room_num'],
                'is_locked': True,
                'is_manual': s.get('is_manual', False)
            })

        for slot, s in zip(best_chromosome, self.unlocked_students):
            assigned_results.append({
                'id': s['id'],
                'nim': s['nim'],
                'nama': s['nama'],
                'day_num': slot[0],
                'slot_num': slot[1],
                'room_num': slot[2],
                'is_locked': False,
                'is_manual': False
            })

        duration = time.time() - start_time
        return {
            'success': True,
            'message': f"Algoritma Genetika selesai dalam {len(history)} generasi ({duration:.2f} detik) dengan {best_conflicts} bentrok.",
            'initial_conflicts': initial_conflicts,
            'final_conflicts': best_conflicts,
            'room_conflicts': best_room_clashes,
            'lecturer_conflicts': best_lec_clashes,
            'best_fitness': best_fitness,
            'generations_run': len(history),
            'execution_time_seconds': duration,
            'assignments': assigned_results,
            'history': history
        }
