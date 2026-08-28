import posixpath
import xml.etree.ElementTree as element_tree
from zipfile import ZipFile


def read_workbook(path):
    namespace = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    relationship_key = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    with ZipFile(path) as archive:
        shared = element_tree.fromstring(archive.read("xl/sharedStrings.xml"))
        strings = ["".join(node.itertext()) for node in shared]
        relationships = element_tree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {node.get("Id"): node.get("Target") for node in relationships}
        workbook = element_tree.fromstring(archive.read("xl/workbook.xml"))
        result = {}
        for sheet in workbook.find("main:sheets", namespace):
            target = targets[sheet.get(relationship_key)]
            location = posixpath.normpath(posixpath.join("xl", target))
            if target.startswith("/"):
                location = target.lstrip("/")
            root = element_tree.fromstring(archive.read(location))
            rows = {}
            for row in root.findall("main:sheetData/main:row", namespace):
                values = {}
                for cell in row:
                    value = cell.find("main:v", namespace)
                    if value is None:
                        continue
                    text = value.text
                    if cell.get("t") == "s":
                        parsed = strings[int(text)]
                    elif cell.get("t") == "str":
                        parsed = text
                    else:
                        parsed = float(text)
                    values[cell.get("r")] = parsed
                rows[int(row.get("r"))] = values
            result[sheet.get("name")] = rows
    return result


def cell_value(rows, row_number, column):
    return rows.get(row_number, {}).get(f"{column}{row_number}")
