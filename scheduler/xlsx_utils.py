import io, re, zipfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape as xml_escape

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PKG_REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"

def col_letter_to_index(col_str):
    num = 0
    for c in col_str.upper():
        if 'A' <= c <= 'Z':
            num = num * 26 + (ord(c) - ord('A')) + 1
    return max(0, num - 1)

def index_to_col_letter(col_idx):
    res = ''
    col_idx += 1
    while col_idx > 0:
        col_idx, rem = divmod(col_idx - 1, 26)
        res = chr(65 + rem) + res
    return res

def read_xlsx(file_source):
    if isinstance(file_source, (bytes, bytearray)):
        file_obj = io.BytesIO(file_source)
    elif hasattr(file_source, 'read'):
        content = file_source.read()
        file_obj = io.BytesIO(content)
    else:
        file_obj = open(file_source, 'rb')

    sheets = {}
    with zipfile.ZipFile(file_obj, 'r') as z:
        shared_strings = []
        if 'xl/sharedStrings.xml' in z.namelist():
            sst = ET.fromstring(z.read('xl/sharedStrings.xml'))
            for si in sst.findall(f'{NS}si'):
                t_elems = si.findall(f'.//{NS}t')
                text_val = ''.join([t.text or '' for t in t_elems])
                shared_strings.append(text_val)

        rel_map = {}
        if 'xl/_rels/workbook.xml.rels' in z.namelist():
            rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
            for r in rels:
                r_id = r.attrib.get('Id')
                target = r.attrib.get('Target', '')
                if not target.startswith('xl/'):
                    target = 'xl/' + target
                rel_map[r_id] = target

        if 'xl/workbook.xml' in z.namelist():
            wb = ET.fromstring(z.read('xl/workbook.xml'))
            for s in wb.findall(f'{NS}sheets/{NS}sheet'):
                sheet_name = s.attrib.get('name', 'Sheet')
                r_id = s.attrib.get(f'{REL_NS}id')
                sheet_path = rel_map.get(r_id)
                if not sheet_path or sheet_path not in z.namelist():
                    continue

                sheet_xml = ET.fromstring(z.read(sheet_path))
                rows_data = []

                for row in sheet_xml.findall(f'{NS}sheetData/{NS}row'):
                    cols_dict = {}
                    max_col = -1
                    for c in row.findall(f'{NS}c'):
                        r_ref = c.attrib.get('r', '')
                        col_letters = re.sub(r'[^A-Za-z]', '', r_ref)
                        if not col_letters:
                            continue
                        c_idx = col_letter_to_index(col_letters)
                        if c_idx > max_col:
                            max_col = c_idx

                        cell_type = c.attrib.get('t', '')
                        val_elem = c.find(f'{NS}v')
                        val = val_elem.text if val_elem is not None and val_elem.text is not None else ''

                        if cell_type == 's' and val.isdigit():
                            idx = int(val)
                            val = shared_strings[idx] if idx < len(shared_strings) else ''
                        elif cell_type == 'inlineStr':
                            is_elem = c.find(f'{NS}is')
                            if is_elem is not None:
                                val = ''.join([t.text or '' for t in is_elem.findall(f'.//{NS}t')])
                        elif cell_type == 'b':
                            val = 'TRUE' if val == '1' else 'FALSE'

                        cols_dict[c_idx] = val

                    if max_col >= 0:
                        row_vals = [cols_dict.get(i, '').strip() for i in range(max_col + 1)]
                    else:
                        row_vals = []
                    rows_data.append(row_vals)

                sheets[sheet_name] = rows_data

    return sheets

def write_xlsx(sheets_dict):
    output = io.BytesIO()
    sheet_names = list(sheets_dict.keys())
    if not sheet_names:
        sheet_names = ['Sheet1']
        sheets_dict = {'Sheet1': {'headers': [], 'rows': []}}

    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as z:
        sheet_overrides = []
        for i in range(1, len(sheet_names) + 1):
            sheet_overrides.append(
                f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            )

        content_types = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
  <Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>
  {''.join(sheet_overrides)}
</Types>'''
        z.writestr('[Content_Types].xml', content_types)

        root_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>'''
        z.writestr('_rels/.rels', root_rels)

        sheet_rels = []
        wb_sheets = []
        for i, sname in enumerate(sheet_names, start=1):
            rid = f"rId{i}"
            wb_sheets.append(f'<sheet name="{xml_escape(sname)}" sheetId="{i}" r:id="{rid}"/>')
            sheet_rels.append(f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>')

        styles_rid = f"rId{len(sheet_names) + 1}"
        sheet_rels.append(f'<Relationship Id="{styles_rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>')

        shared_rid = f"rId{len(sheet_names) + 2}"
        sheet_rels.append(f'<Relationship Id="{shared_rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>')

        wb_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    {''.join(wb_sheets)}
  </sheets>
</workbook>'''
        z.writestr('xl/workbook.xml', wb_xml)

        wb_rels = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  {''.join(sheet_rels)}
</Relationships>'''
        z.writestr('xl/_rels/workbook.xml.rels', wb_rels)

        styles_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="5">
    <!-- 0: Standard Body Text -->
    <font><sz val="9.5"/><name val="Segoe UI"/><color rgb="FF1E293B"/></font>
    <!-- 1: Header Text Bold White -->
    <font><b/><sz val="10.5"/><name val="Segoe UI"/><color rgb="FFFFFFFF"/></font>
    <!-- 2: Title Banner Bold White -->
    <font><b/><sz val="13"/><name val="Segoe UI"/><color rgb="FFFFFFFF"/></font>
    <!-- 3: Subtitle White Soft -->
    <font><sz val="9.5"/><name val="Segoe UI"/><color rgb="FFE0E7FF"/></font>
    <!-- 4: Gray Info -->
    <font><sz val="9"/><name val="Segoe UI"/><color rgb="FF475569"/></font>
  </fonts>
  <fills count="7">
    <!-- 0: None -->
    <fill><patternFill patternType="none"/></fill>
    <!-- 1: Gray125 -->
    <fill><patternFill patternType="gray125"/></fill>
    <!-- 2: Dark Navy Header (#1E3A8A) -->
    <fill><patternFill patternType="solid"><fgColor rgb="FF1E3A8A"/></fill></fill>
    <!-- 3: Alternate Row Very Soft Blue (#F8FAFC) -->
    <fill><patternFill patternType="solid"><fgColor rgb="FFF8FAFC"/></fill></fill>
    <!-- 4: Title Banner Royal Blue (#1D4ED8) -->
    <fill><patternFill patternType="solid"><fgColor rgb="FF1D4ED8"/></fill></fill>
    <!-- 5: Subtitle Fill (#2563EB) -->
    <fill><patternFill patternType="solid"><fgColor rgb="FF2563EB"/></fill></fill>
    <!-- 6: Accent Header Blue (#2563EB) -->
    <fill><patternFill patternType="solid"><fgColor rgb="FF2563EB"/></fill></fill>
  </fills>
  <borders count="3">
    <!-- 0: Empty -->
    <border><left/><right/><top/><bottom/></border>
    <!-- 1: Soft Table Border -->
    <border>
      <left style="thin"><color rgb="FFCBD5E1"/></left>
      <right style="thin"><color rgb="FFCBD5E1"/></right>
      <top style="thin"><color rgb="FFCBD5E1"/></top>
      <bottom style="thin"><color rgb="FFCBD5E1"/></bottom>
    </border>
    <!-- 2: Header Border -->
    <border>
      <left style="thin"><color rgb="FF1E293B"/></left>
      <right style="thin"><color rgb="FF1E293B"/></right>
      <top style="medium"><color rgb="FF0F172A"/></top>
      <bottom style="medium"><color rgb="FF0F172A"/></bottom>
    </border>
  </borders>
  <cellXfs count="9">
    <!-- 0: Regular Left -->
    <xf fontId="0" fillId="0" borderId="1" applyFont="1" applyBorder="1" applyAlignment="1">
      <alignment horizontal="left" vertical="center" wrapText="1"/>
    </xf>
    <!-- 1: Table Header Navy White Bold (Centered) -->
    <xf fontId="1" fillId="2" borderId="2" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1">
      <alignment horizontal="center" vertical="center" wrapText="1"/>
    </xf>
    <!-- 2: Regular Center -->
    <xf fontId="0" fillId="0" borderId="1" applyFont="1" applyBorder="1" applyAlignment="1">
      <alignment horizontal="center" vertical="center"/>
    </xf>
    <!-- 3: Alternate Row Left -->
    <xf fontId="0" fillId="3" borderId="1" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1">
      <alignment horizontal="left" vertical="center" wrapText="1"/>
    </xf>
    <!-- 4: Alternate Row Center -->
    <xf fontId="0" fillId="3" borderId="1" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1">
      <alignment horizontal="center" vertical="center"/>
    </xf>
    <!-- 5: Title Banner Center (Merged) -->
    <xf fontId="2" fillId="4" borderId="0" applyFont="1" applyFill="1" applyAlignment="1">
      <alignment horizontal="center" vertical="center"/>
    </xf>
    <!-- 6: Title Sub-Banner Center -->
    <xf fontId="3" fillId="5" borderId="0" applyFont="1" applyFill="1" applyAlignment="1">
      <alignment horizontal="center" vertical="center"/>
    </xf>
    <!-- 7: Matrix Card Cell -->
    <xf fontId="0" fillId="0" borderId="1" applyFont="1" applyBorder="1" applyAlignment="1">
      <alignment horizontal="center" vertical="center" wrapText="1"/>
    </xf>
    <!-- 8: Title Banner Cell Outline (for merged block) -->
    <xf fontId="2" fillId="4" borderId="0" applyFont="1" applyFill="1" applyAlignment="1">
      <alignment horizontal="center" vertical="center"/>
    </xf>
  </cellXfs>
</styleSheet>'''
        z.writestr('xl/styles.xml', styles_xml)

        strings_list = []
        strings_dict = {}

        def get_string_index(s):
            val_str = str(s) if s is not None else ''
            if val_str not in strings_dict:
                strings_dict[val_str] = len(strings_list)
                strings_list.append(val_str)
            return strings_dict[val_str]

        for i, sname in enumerate(sheet_names, start=1):
            sheet_data = sheets_dict[sname]
            headers = sheet_data.get('headers', [])
            rows = sheet_data.get('rows', [])
            col_widths = sheet_data.get('col_widths', [])
            center_cols = set(sheet_data.get('center_cols', []))
            title = sheet_data.get('title', '')
            total_cols = max(len(headers), 1)

            # Generate cols width XML
            cols_xml = []
            if not col_widths and headers:
                col_widths = [14] * len(headers)
            if col_widths:
                cols_xml = ['<cols>']
                for c_idx, width in enumerate(col_widths, start=1):
                    cols_xml.append(f'<col min="{c_idx}" max="{c_idx}" width="{width}" customWidth="1"/>')
                cols_xml.append('</cols>')
                cols_str = ''.join(cols_xml)
            else:
                cols_str = ''

            rows_xml = []
            merge_cells = []
            cur_row = 1

            # Title Header at Top (Centered across all columns with Fill Color)
            if title:
                last_col_letter = index_to_col_letter(total_cols - 1)
                t_idx = get_string_index(title)
                
                # Main Title Row with Royal Blue Background
                t_cells = []
                for c in range(total_cols):
                    col_ref = f'{index_to_col_letter(c)}{cur_row}'
                    if c == 0:
                        t_cells.append(f'<c r="{col_ref}" t="s" s="5"><v>{t_idx}</v></c>')
                    else:
                        t_cells.append(f'<c r="{col_ref}" s="5"/>')
                rows_xml.append(f'<row r="{cur_row}" ht="34" customHeight="1">{"".join(t_cells)}</row>')
                merge_cells.append(f'<mergeCell ref="A{cur_row}:{last_col_letter}{cur_row}"/>')
                cur_row += 1

                # Small spacing row
                rows_xml.append(f'<row r="{cur_row}" ht="10" customHeight="1"/>')
                cur_row += 1

            # Headers (Dark Navy Fill Color, White Bold Text, Centered)
            if headers:
                h_cells = []
                for col_idx, h_text in enumerate(headers):
                    col_ref = f'{index_to_col_letter(col_idx)}{cur_row}'
                    s_idx = get_string_index(h_text)
                    h_cells.append(f'<c r="{col_ref}" t="s" s="1"><v>{s_idx}</v></c>')
                rows_xml.append(f'<row r="{cur_row}" ht="30" customHeight="1">' + ''.join(h_cells) + '</row>')
                cur_row += 1

            # Data rows
            for r_val_idx, r_values in enumerate(rows):
                is_alt = (r_val_idx % 2 == 1)
                c_cells = []
                for col_idx, val in enumerate(r_values):
                    col_ref = f'{index_to_col_letter(col_idx)}{cur_row}'
                    s_idx = get_string_index(val)

                    if col_idx in center_cols:
                        style_idx = 4 if is_alt else 2
                    else:
                        style_idx = 3 if is_alt else 0

                    c_cells.append(f'<c r="{col_ref}" t="s" s="{style_idx}"><v>{s_idx}</v></c>')

                # Multiline row height
                has_multiline = any(chr(10) in str(v) for v in r_values)
                row_ht = 44 if has_multiline else 22
                rows_xml.append(f'<row r="{cur_row}" ht="{row_ht}" customHeight="1">' + ''.join(c_cells) + '</row>')
                cur_row += 1

            # MergeCells XML
            merge_xml = ""
            if merge_cells:
                merge_xml = f'<mergeCells count="{len(merge_cells)}">{"".join(merge_cells)}</mergeCells>'

            ws_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetViews><sheetView tabSelected="1" workbookViewId="0"/></sheetViews>
  <sheetFormatPr defaultRowHeight="20"/>
  {cols_str}
  <sheetData>{''.join(rows_xml)}</sheetData>
  {merge_xml}
</worksheet>'''
            z.writestr(f'xl/worksheets/sheet{i}.xml', ws_xml)

        escaped_si = []
        for s in strings_list:
            escaped_si.append(f'<si><t>{xml_escape(s)}</t></si>')
        sst_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="{len(strings_list)}" uniqueCount="{len(strings_list)}">
{''.join(escaped_si)}
</sst>'''
        z.writestr('xl/sharedStrings.xml', sst_xml)

    output.seek(0)
    return output.getvalue()
