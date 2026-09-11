"""Generate a deterministic, searchable PDF from the fictional clinical note."""

from pathlib import Path
import textwrap


def pdf_string(text):
    result = bytearray()
    for value in text.encode("cp1252"):
        if value in b"\\()":
            result.extend(b"\\" + bytes([value]))
        elif value < 32 or value > 126:
            result.extend(f"\\{value:03o}".encode("ascii"))
        else:
            result.append(value)
    return b"(" + result + b")"


def make_pdf(text):
    lines = []
    for line in text.splitlines():
        lines.extend(textwrap.wrap(line, width=82, break_long_words=False) or [""])
    if len(lines) > 48:
        raise ValueError("The example must fit on one page")
    commands = [b"BT /F1 11 Tf 14 TL 45 795 Td"]
    for index, line in enumerate(lines):
        if index:
            commands.append(b"T*")
        commands.append(pdf_string(line) + b" Tj")
    commands.append(b"ET")
    stream = b"\n".join(commands)
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    document = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(len(document))
        document.extend(f"{index} 0 obj\n".encode("ascii") + body + b"\nendobj\n")
    xref = len(document)
    document.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode("ascii"))
    for offset in offsets[1:]:
        document.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    document.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii")
    )
    return bytes(document)


if __name__ == "__main__":
    source = Path(__file__).parent / "clinical-note.txt"
    destination = source.with_suffix(".pdf")
    destination.write_bytes(make_pdf(source.read_text(encoding="utf-8")))
    print(destination)
