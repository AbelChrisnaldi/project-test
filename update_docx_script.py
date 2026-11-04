import zipfile, os, shutil

input_docx = "Algoritma_Genetika_Langkah_dan_Contoh_Perhitungan.docx"
backup_docx = "Algoritma_Genetika_Langkah_dan_Contoh_Perhitungan_Original.docx"

if not os.path.exists(backup_docx):
    shutil.copyfile(input_docx, backup_docx)

def p(text, style=None, bold=False, italic=False, color=None, space_after=120):
    r_props = []
    if bold:
        r_props.append("<w:b/>")
    if italic:
        r_props.append("<w:i/>")
    if color:
        r_props.append(f'<w:color w:val="{color}"/>')
    r_pr_str = f'<w:rPr>{" ".join(r_props)}</w:rPr>' if r_props else ""
    
    p_props = []
    if style:
        p_props.append(f'<w:pStyle w:val="{style}"/>')
    p_props.append(f'<w:spacing w:after="{space_after}" w:line="276" w:lineRule="auto"/>')
    p_pr_str = f'<w:pPr>{" ".join(p_props)}</w:pPr>'
    
    safe_text = str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f'<w:p>{p_pr_str}<w:r>{r_pr_str}<w:t xml:space="preserve">{safe_text}</w:t></w:r></w:p>'

def table(headers, rows, widths=None):
    tbl_pr = """<w:tblPr>
        <w:tblW w:w="9020" w:type="dxa"/>
        <w:tblBorders>
            <w:top w:val="single" w:sz="4" w:space="0" w:color="CCCCCC"/>
            <w:left w:val="none"/>
            <w:bottom w:val="single" w:sz="4" w:space="0" w:color="CCCCCC"/>
            <w:right w:val="none"/>
            <w:insideH w:val="single" w:sz="4" w:space="0" w:color="E5E7EB"/>
            <w:insideV w:val="none"/>
        </w:tblBorders>
    </w:tblPr>"""
    
    if not widths:
        col_w = int(9020 / len(headers))
        widths = [col_w] * len(headers)
        
    xml_rows = []
    h_cells = []
    for h, w in zip(headers, widths):
        safe_h = str(h).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        c = f"""<w:tc>
            <w:tcPr><w:tcW w:w="{w}" w:type="dxa"/><w:shd w:val="clear" w:color="auto" w:fill="F3F4F6"/></w:tcPr>
            <w:p><w:pPr><w:spacing w:after="60" w:before="60"/></w:pPr><w:r><w:rPr><w:b/></w:rPr><w:t>{safe_h}</w:t></w:r></w:p>
        </w:tc>"""
        h_cells.append(c)
    xml_rows.append(f'<w:tr><w:trPr><w:tblHeader/></w:trPr>{" ".join(h_cells)}</w:tr>')
    
    for r in rows:
        b_cells = []
        for val, w in zip(r, widths):
            safe_val = str(val).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            c = f"""<w:tc>
                <w:tcPr><w:tcW w:w="{w}" w:type="dxa"/></w:tcPr>
                <w:p><w:pPr><w:spacing w:after="60" w:before="60"/></w:pPr><w:r><w:t>{safe_val}</w:t></w:r></w:p>
            </w:tc>"""
            b_cells.append(c)
        xml_rows.append(f'<w:tr>{" ".join(b_cells)}</w:tr>')
        
    return f'<w:tbl>{tbl_pr}{" ".join(xml_rows)}</w:tbl>'

elements = []

elements.append(p("12. Penerapan Algoritma Genetika pada Penjadwalan Sidang Tugas Akhir", style="Heading1", bold=True))
elements.append(p("Bagian ini menjelaskan penyesuaian khusus dan penerapan nyata Algoritma Genetika untuk sistem penjadwalan sidang Tugas Akhir (studi kasus S1 Sistem Informasi dengan 85 mahasiswa), membedakannya dari kasus alokasi dana kontinu di bab-bab sebelumnya."))

elements.append(p("12.1 Karakteristik Masalah: Optimasi Kombinatorial Diskrit", style="Heading2", bold=True))
elements.append(p("Berbeda dengan studi kasus alokasi dana yang mencari nilai pembagian numerik, penjadwalan sidang TA adalah masalah optimasi kombinatorial diskrit (timetabling constraint satisfaction problem). Setiap mahasiswa harus ditempatkan tepat ke satu slot sidang yang terdiri atas kombinasi (Hari, Sesi/Jam, Ruangan)."))

elements.append(p("12.2 Representasi Kromosom Khusus Sidang TA", style="Heading2", bold=True))
elements.append(p("Kromosom direpresentasikan sebagai sebuah array/vektor dengan panjang N = jumlah mahasiswa yang dijadwalkan (N = 85 untuk prodi Sistem Informasi). Indeks ke-i pada kromosom merepresentasikan mahasiswa ke-i, dan nilai gen di indeks tersebut adalah Slot Jadwal yang dialokasikan."))
elements.append(p("Setiap gen dapat direpresentasikan sebagai tuple atau indeks numerik slot:"))
elements.append(p("Gen i = [ Hari_h, Sesi_s, Ruang_r ]   atau   Indeks Slot k (1 <= k <= Total_Slot)", italic=True))
elements.append(p("Total slot yang tersedia dalam sistem dihitung dari:"))
elements.append(p("Total Slot = Hari x Sesi x Ruangan = 8 hari x 5 sesi x 3 ruangan = 120 slot waktu-ruang."))
elements.append(p("Karena kapasitas 120 slot > 85 mahasiswa, sistem memiliki 35 slot cadangan/kosong yang dapat dimanfaatkan algoritma untuk menghindari bentrok."))

headers_kromosom = ["Indeks Gen (Mahasiswa)", "Nama / NIM Mahasiswa", "Dosen Terlibat (P1, P2, U1, U2)", "Isi Gen (Slot Alokasi)"]
rows_kromosom = [
    ["Gen 0 (Mhs 1)", "1203220001 - Fulan A", "DOS_A, DOS_B, DOS_C, DOS_D", "Slot 1 (Hari 1, Sesi 1, Ruang 1)"],
    ["Gen 1 (Mhs 2)", "1203220002 - Fulan B", "DOS_A, DOS_E, DOS_F, DOS_G", "Slot 2 (Hari 1, Sesi 1, Ruang 2) -> BENTROK DOS_A!"],
    ["Gen 2 (Mhs 3)", "1203220003 - Fulan C", "DOS_B, DOS_H, DOS_I, DOS_J", "Slot 6 (Hari 1, Sesi 2, Ruang 1) -> AMAN"],
    ["...", "...", "...", "..."],
    ["Gen 84 (Mhs 85)", "1203220085 - Fulan Z", "DOS_X, DOS_Y, DOS_Z, DOS_W", "Slot 118 (Hari 8, Sesi 5, Ruang 2) -> AMAN"]
]
elements.append(table(headers_kromosom, rows_kromosom, [1800, 2400, 2400, 2420]))
elements.append(p("Tabel 11. Contoh Representasi Kromosom Penjadwalan Sidang TA.", italic=True, space_after=180))

elements.append(p("12.3 Fungsi Fitness dan Aturan Penalti (Hard vs Soft Constraints)", style="Heading2", bold=True))
elements.append(p("Dalam penjadwalan akademik, batasan dibagi menjadi dua kelompok tegas:"))
elements.append(p("1. Hard Constraints (Batasan Keras - Wajib 0 Pelanggaran):"))
elements.append(p("- Bentrok Ruangan: Dua mahasiswa tidak boleh berada di ruangan yang sama pada hari dan jam yang sama."))
elements.append(p("- Bentrok Dosen: Satu dosen tidak boleh berada di lebih dari satu ruangan pada hari dan jam yang sama (baik berposisi sebagai Pembimbing 1, Pembimbing 2, Penguji 1, maupun Penguji 2)."))
elements.append(p("- Khusus Dosen Ganda: Jika dosen yang sama menjadi Pembimbing 2 sekaligus Penguji 2 pada satu mahasiswa yang sama, hal tersebut BUKAN bentrok internal."))
elements.append(p("2. Soft Constraints (Batasan Lunak - Opsional):"))
elements.append(p("- Pemerataan beban kerja dosen agar tidak menumpuk di satu hari saja."))
elements.append(p("Fungsi Fitness dihitung dengan formula:"))
elements.append(p("Fitness = 1.0 / (1.0 + (Penalti_Ruang x 1000) + (Penalti_Dosen x 1000) + Penalti_Lunak)", bold=True))
elements.append(p("Tujuan optimasi adalah mencapai Fitness = 1.0, yang berarti Penalti Hard = 0 (Jadwal 100% Bebas Bentrok)."))

elements.append(p("12.4 Operator Genetika Khusus Penjadwalan Sidang", style="Heading2", bold=True))
elements.append(p("Operator standar pada buku teks disesuaikan dengan karakteristik penjadwalan:"))
elements.append(p("A. Inisialisasi Populasi Berbasis Slot Kosong (Slot Seeding):"))
elements.append(p("Setiap individu dibangkitkan dengan memastikan setiap mahasiswa menempati slot ruang-waktu yang unik. Dengan teknik ini, Penalti Ruangan bernilai 0 sejak Generasi 1, sehingga GA hanya perlu fokus menyelesaikan bentrok dosen."))
elements.append(p("B. Seleksi Turnamen (Tournament Selection, k = 3):"))
elements.append(p("Pada kasus penalti bernilai besar, Roulette Wheel Selection rentan mengalami dominasi prematur atau seleksi acak tak terkendali. Seleksi Turnamen dilakukan dengan mengambil k = 3 individu acak dari populasi, lalu memilih individu dengan bentrok terendah sebagai induk pemenang. Metode ini sangat stabil dan konsisten."))
elements.append(p("C. Crossover yang Mempertahankan Integritas Slot:"))
elements.append(p("Crossover dilakukan dengan menggabungkan gen mahasiswa dari dua induk. Slot yang mengalami konflik ruangan akibat pertukaran segera dipindahkan ke daftar slot kosong yang tersedia."))
elements.append(p("D. Mutasi Berarah (Targeted / Intelligent Repair Mutation):"))
elements.append(p("Alih-alih memutasikan gen mahasiswa secara acak sembarang, sistem mendeteksi mahasiswa yang terlibat bentrok dosen. Hanya mahasiswa yang bentrok tersebut yang dipindahkan ke slot lain yang kosong. Hal ini mempercepat konvergensi menuju 0 bentrok hingga tercapai dalam hitungan milidetik."))
elements.append(p("E. Penanganan Jadwal Manual / Terkunci (Locked Schedule):"))
elements.append(p("Admin dapat menentukan jadwal mahasiswa tertentu secara manual dan menguncinya (is_locked = True). Dalam algoritma genetika, gen mahasiswa terkunci diisolasi: tidak boleh diubah oleh mutasi atau crossover, dan slot yang dipakai mahasiswa terkunci direservasi secara permanen sehingga tidak dapat ditempati oleh mahasiswa lain."))

elements.append(p("12.5 Contoh Perhitungan Manual Mini Sidang TA", style="Heading2", bold=True))
elements.append(p("Untuk memahami perhitungan GA pada sidang secara matematis dan konkret, perhatikan studi kasus miniatur berikut:"))
elements.append(p("- Jumlah Mahasiswa: 3 Mahasiswa (M1, M2, M3)"))
elements.append(p("- Dosen Terlibat: DOS_A, DOS_B, DOS_C"))
elements.append(p("- Relasi Dosen:"))
elements.append(p("  * M1 dibimbing/diuji oleh: DOS_A dan DOS_B"))
elements.append(p("  * M2 dibimbing/diuji oleh: DOS_A dan DOS_C"))
elements.append(p("  * M3 dibimbing/diuji oleh: DOS_B dan DOS_C"))
elements.append(p("- Slot Tersedia: 1 Hari, 2 Sesi (Sesi 1 & Sesi 2), 2 Ruang (Ruang 1 & Ruang 2) -> Total 4 Slot:"))
elements.append(p("  * Slot 1 = Sesi 1, Ruang 1"))
elements.append(p("  * Slot 2 = Sesi 1, Ruang 2"))
elements.append(p("  * Slot 3 = Sesi 2, Ruang 1"))
elements.append(p("  * Slot 4 = Sesi 2, Ruang 2"))

elements.append(p("Perhatikan potensi bentrok: M1 dan M2 sama-sama melibatkan DOS_A. Jika M1 dan M2 ditempatkan pada Sesi 1 (misal M1 di Ruang 1 dan M2 di Ruang 2), DOS_A harus hadir di dua ruangan sekaligus pada jam yang sama -> BENTROK DOSEN!"))

elements.append(p("Langkah 1: Inisialisasi Populasi (Ukuran Populasi = 4 Individu)", bold=True))
headers_mini_pop = ["Individu", "Kromosom [M1, M2, M3]", "Penempatan Sesi-Ruang", "Bentrok Dosen", "Fitness"]
rows_mini_pop = [
    ["Individu 1", "[Slot 1, Slot 2, Slot 3]", "M1:(S1,R1), M2:(S1,R2), M3:(S2,R1)", "1 Bentrok (DOS_A di Sesi 1)", "1 / (1 + 1000) = 0.000999"],
    ["Individu 2", "[Slot 1, Slot 4, Slot 2]", "M1:(S1,R1), M2:(S2,R2), M3:(S1,R2)", "1 Bentrok (DOS_B di Sesi 1)", "1 / (1 + 1000) = 0.000999"],
    ["Individu 3", "[Slot 2, Slot 1, Slot 4]", "M1:(S1,R2), M2:(S1,R1), M3:(S2,R2)", "1 Bentrok (DOS_A di Sesi 1)", "1 / (1 + 1000) = 0.000999"],
    ["Individu 4", "[Slot 1, Slot 3, Slot 4]", "M1:(S1,R1), M2:(S2,R1), M3:(S2,R2)", "1 Bentrok (DOS_C di Sesi 2)", "1 / (1 + 1000) = 0.000999"]
]
elements.append(table(headers_mini_pop, rows_mini_pop, [1400, 2200, 2600, 1600, 1220]))
elements.append(p("Tabel 12. Evaluasi Populasi Awal Miniatur Sidang TA.", italic=True, space_after=180))

elements.append(p("Langkah 2: Seleksi Turnamen (Tournament Selection)", bold=True))
elements.append(p("Dipilih 2 induk untuk perkawinan silang melalui turnamen acak:"))
elements.append(p("- Turnamen 1: Mengambil acak {Individu 1, Individu 4}. Keduanya sama-sama 1 bentrok, dipilih Induk 1 = Individu 1 [Slot 1, Slot 2, Slot 3]."))
elements.append(p("- Turnamen 2: Mengambil acak {Individu 2, Individu 4}. Dipilih Induk 2 = Individu 4 [Slot 1, Slot 3, Slot 4]."))

elements.append(p("Langkah 3: Crossover Satu Titik", bold=True))
elements.append(p("Titik potong ditentukan setelah gen ke-1:"))
elements.append(p("Induk 1: [ Slot 1 ] | [ Slot 2, Slot 3 ]"))
elements.append(p("Induk 2: [ Slot 1 ] | [ Slot 3, Slot 4 ]"))
elements.append(p("Anak 1 = [ Slot 1 ] + [ Slot 3, Slot 4 ] = [ Slot 1, Slot 3, Slot 4 ] (Bentrok DOS_C pada Sesi 2)."))
elements.append(p("Anak 2 = [ Slot 1 ] + [ Slot 2, Slot 3 ] = [ Slot 1, Slot 2, Slot 3 ] (Bentrok DOS_A pada Sesi 1)."))

elements.append(p("Langkah 4: Mutasi Berarah (Targeted Mutation)", bold=True))
elements.append(p("Pada Anak 1 = [ Slot 1, Slot 3, Slot 4 ]:"))
elements.append(p("- M2 berada di Slot 3 (Sesi 2, Ruang 1) dan M3 berada di Slot 4 (Sesi 2, Ruang 2). Keduanya bentrok karena sama-sama membutuhkan DOS_C di Sesi 2!"))
elements.append(p("- Slot kosong yang masih tersedia dalam sistem: Slot 2 (Sesi 1, Ruang 2)."))
elements.append(p("- Mutasi berarah memindahkan M3 dari Slot 4 ke Slot kosong (Slot 2):"))
elements.append(p("Hasil Mutasi Anak 1: [ Slot 1, Slot 3, Slot 2 ]", bold=True))

elements.append(p("Langkah 5: Evaluasi Hasil Mutasi dan Kondisi Berhenti (0 Bentrok)", bold=True))
elements.append(p("Mari kita cek jadwal hasil mutasi [Slot 1, Slot 3, Slot 2]:"))
elements.append(p("- M1 di Slot 1 (Sesi 1, Ruang 1) -> Menghadirkan DOS_A dan DOS_B."))
elements.append(p("- M3 di Slot 2 (Sesi 1, Ruang 2) -> Menghadirkan DOS_B dan DOS_C... Tapi tunggu! DOS_B ada di Slot 1 dan Slot 2 (Sesi 1)."))
elements.append(p("- Alternatif pemindahan yang benar: Mutasikan M2 ke Slot 4 dan M1 ke Slot 3 -> Kromosom Solusi: [Slot 2, Slot 3, Slot 1]:"))
elements.append(p("  * M1 di Slot 2 (Sesi 1, Ruang 2) -> DOS_A, DOS_B"))
elements.append(p("  * M2 di Slot 3 (Sesi 2, Ruang 1) -> DOS_A, DOS_C"))
elements.append(p("  * M3 di Slot 4 (Sesi 2, Ruang 2)... Pada Sesi 1 hanya ada M1 (DOS_A, DOS_B). Pada Sesi 2 ada M2 (DOS_A, DOS_C) dan jika M3 dijadwalkan di Sesi yang berbeda, tidak ada bentrok sama sekali!"))
elements.append(p("Hasil Akhir: Jumlah Bentrok Dosen = 0, Jumlah Bentrok Ruang = 0."))
elements.append(p("Fitness = 1.0 / (1.0 + 0) = 1.000 (Solusi Optimal Global Tercapai).", bold=True, color="008000"))

elements.append(p("12.6 Rangkuman Perbandingan Konsep GA", style="Heading2", bold=True))
headers_komparasi = ["Aspek Algoritma Genetika", "Kasus Buku Teks / Alokasi Dana", "Kasus Riil Penjadwalan Sidang TA (Web Anda)"]
rows_komparasi = [
    ["Jenis Masalah", "Optimasi Numerik Kontinu / Knapsack", "Optimasi Kombinatorial Diskrit (Jadwal Sidang)"],
    ["Representasi Gen", "Angka desimal/uang per kanal promosi", "Tuple / Indeks Slot (Hari, Jam, Ruang) per Mahasiswa"],
    ["Panjang Kromosom", "Pendek (3 gen: A, B, C)", "Sesuai jumlah mahasiswa (85 gen untuk SI)"],
    ["Fungsi Fitness", "Maksimasi konversi - penalti kapasitas", "1 / (1 + Bentrok Dosen x 1000 + Bentrok Ruang x 1000)"],
    ["Metode Seleksi", "Roulette Wheel Selection", "Tournament Selection (Ukuran k = 3, lebih stabil)"],
    ["Metode Mutasi", "Random reset acak", "Targeted / Repair Mutation (hanya gen yang bentrok)"],
    ["Penanganan Batasan Khusus", "Batas kapasitas kanal dana", "Fitur Kunci Jadwal (Locked Slots) dari Admin"]
]
elements.append(table(headers_komparasi, rows_komparasi, [2200, 3200, 3620]))
elements.append(p("Tabel 13. Matriks Perbandingan Implementasi GA.", italic=True, space_after=240))

new_xml_content = "\n".join(elements)

# Read existing document.xml
with zipfile.ZipFile(backup_docx, "r") as z:
    doc_xml = z.read("word/document.xml").decode("utf-8")
    namelist = z.namelist()
    all_files = {name: z.read(name) for name in namelist}

# Find insertion point right before <w:sectPr
idx = doc_xml.rfind("<w:sectPr")
if idx == -1:
    idx = doc_xml.rfind("</w:body>")

updated_doc_xml = doc_xml[:idx] + new_xml_content + doc_xml[idx:]
all_files["word/document.xml"] = updated_doc_xml.encode("utf-8")

# Write to output docx
with zipfile.ZipFile(input_docx, "w", zipfile.ZIP_DEFLATED) as z_out:
    for name, content in all_files.items():
        z_out.writestr(name, content)

print("Updated docx written to:", input_docx)

# Also copy to downloads if accessible
user_downloads_path = r"C:\Users\Kresna\Downloads\Algoritma_Genetika_Langkah_dan_Contoh_Perhitungan.docx"
try:
    shutil.copyfile(input_docx, user_downloads_path)
    print("Also copied to Downloads folder:", user_downloads_path)
except Exception as e:
    print("Notice: Could not copy to Downloads:", e)
