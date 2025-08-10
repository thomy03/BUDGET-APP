def from_buffer(buf: bytes, mime: bool = True) -> str:
    b = bytes(buf or b"")
    if len(b) >= 4 and b[:4] == b"PK\x03\x04":
        return "application/zip"
    if len(b) >= 2 and b[:2] == b"MZ":
        return "application/x-executable"
    if len(b) >= 4 and b[:4] == b"\xd0\xcf\x11\xe0":
        return "application/vnd.ms-excel"
    head = b[:256].decode("utf-8", errors="ignore").lower()
    if "," in head or ";" in head or "\t" in head or head.startswith(("dateop", "date")):
        return "text/csv"
    return "text/plain"