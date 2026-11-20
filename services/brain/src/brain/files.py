"""Company Chat file upload: read an attached file into text, nothing else.

`POST /v1/files/extract` takes one file and returns its text. It does not decide anything and it
never calls a model: the chat puts the text inside the message, and the gateway sends that message
through `/v1/inspect` like typed text, so the usual five outcomes apply to the file too. The bytes
and the text are not stored or logged.
"""

import asyncio
import logging
import threading
from concurrent.futures import Future, ThreadPoolExecutor

from fastapi import APIRouter, HTTPException, Response, UploadFile
from pydantic import BaseModel

from brain.config import settings
from brain.documents.chat_files import ChatFile, read_chat_file, suffixes
from brain.documents.extract import ExtractError

log = logging.getLogger(__name__)
router = APIRouter()

# Few workers on purpose. A thread cannot be stopped, so a file that takes too long is given up on
# while its thread keeps running (bounded by the page and size caps). The slots count running
# threads, not waiting requests: a slot is freed when the thread ends, never when the request gives
# up, so slow files can never queue up behind each other and tie the pool up. When every slot is
# taken a new file is refused straight away with 503.
_WORKERS = 2
_pool = ThreadPoolExecutor(max_workers=_WORKERS, thread_name_prefix="chat-file")
_slots = threading.BoundedSemaphore(_WORKERS)


class FileLimits(BaseModel):
    max_bytes: int
    max_files: int
    max_chars: int
    types: list[str]


class ExtractedFile(BaseModel):
    filename: str
    kind: str
    text: str
    chars: int
    truncated: bool


@router.get("/v1/files/limits", response_model=FileLimits)
def file_limits() -> FileLimits:
    return FileLimits(
        max_bytes=settings.file_max_bytes,
        max_files=settings.file_max_count,
        max_chars=settings.file_max_chars,
        types=suffixes(),
    )


def _refuse(
    status: int, filename: str, message: str, headers: dict[str, str] | None = None
) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail={"filename": filename, "message": message},
        headers=headers,
    )


@router.post("/v1/files/extract", response_model=ExtractedFile)
async def extract_file(file: UploadFile, response: Response) -> ExtractedFile:
    """Read one file attached in Company Chat. Errors say what happened and what to do next."""
    name = (file.filename or "file").replace("\\", "/").rsplit("/", 1)[-1][:200] or "file"
    data = await file.read(settings.file_max_bytes + 1)
    response.headers["Cache-Control"] = "no-store"
    if not _slots.acquire(blocking=False):
        raise _refuse(
            503,
            name,
            "The server is busy reading other files. Wait a few seconds and attach it again.",
            {"Retry-After": "5", "Cache-Control": "no-store"},
        )

    # The slot is tied to the future, not to the function body: a done callback also runs when the
    # future is cancelled before its thread starts (a client that hangs up), so a slot cannot leak.
    try:
        job = _pool.submit(
            read_chat_file,
            name,
            data,
            max_bytes=settings.file_max_bytes,
            max_chars=settings.file_max_chars,
        )
    except BaseException:
        _slots.release()
        raise

    def finished(done: "Future[ChatFile]") -> None:
        _slots.release()
        if not done.cancelled():
            done.exception()  # read it, so a late failure is not reported as never retrieved

    job.add_done_callback(finished)
    try:
        # shield: a timeout or a hang-up must not cancel the job, or its result would be thrown away
        # while its thread (if already running) carries on.
        out = await asyncio.wait_for(
            asyncio.shield(asyncio.wrap_future(job)), timeout=settings.file_extract_timeout
        )
    except TimeoutError as err:
        raise _refuse(
            422,
            name,
            "This file took too long to read. Attach a shorter file or only the pages you need.",
        ) from err
    except ExtractError as err:
        status = 413 if "larger than" in str(err) else 422
        raise _refuse(status, name, str(err)) from err
    # Only the kind and size are logged, never the name or the text.
    log.info("chat file read: kind=%s chars=%d truncated=%s", out.kind, out.chars, out.truncated)
    return ExtractedFile(
        filename=out.filename,
        kind=out.kind,
        text=out.text,
        chars=out.chars,
        truncated=out.truncated,
    )
