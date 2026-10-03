from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import HTTPException, status


CHUNK_SIZE = 1024 * 1024


def parse_range(range_header: str | None, file_size: int) -> tuple[int, int, int]:
    if not range_header:
        return 0, file_size - 1, 200
    if not range_header.startswith("bytes=") or "," in range_header:
        raise HTTPException(status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE, detail="Invalid byte range")
    start_text, _, end_text = range_header[6:].partition("-")
    try:
        if start_text:
            start = int(start_text)
            end = int(end_text) if end_text else file_size - 1
        else:
            suffix = int(end_text)
            start, end = max(file_size - suffix, 0), file_size - 1
    except ValueError as exc:
        raise HTTPException(status_code=416, detail="Invalid byte range") from exc
    if start < 0 or start >= file_size or end < start:
        raise HTTPException(status_code=416, detail="Requested range is not satisfiable")
    return start, min(end, file_size - 1), 206


async def file_chunks(path: Path, start: int, end: int) -> AsyncIterator[bytes]:
    remaining = end - start + 1
    with path.open("rb") as file_handle:
        file_handle.seek(start)
        while remaining:
            chunk = file_handle.read(min(CHUNK_SIZE, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk
