"""Small CSV utility that prevents spreadsheet formula injection."""
import csv
from io import StringIO


def spreadsheet_safe(value):
    text = str(value) if value is not None else ""
    if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + text
    return text


def export_csv(headers, rows):
    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows([[spreadsheet_safe(value) for value in row] for row in rows])
    return output.getvalue()
