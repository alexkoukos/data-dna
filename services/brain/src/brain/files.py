"""Company Chat file upload: read an attached file into text, nothing else.

`POST /v1/files/extract` takes one file and returns its text. It does not decide anything and it
never calls a model: the chat puts the text inside the message, and the gateway sends that message
through `/v1/inspect` like typed text, so the usual five outcomes apply to the file too. The bytes
and the text are not stored or logged.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException, Response, UploadFile
from pydantic import BaseModel

from brain.config import settings
from brain.documents.chat_files import read_chat_file, suffixes
from brain.documents.extract import ExtractError

log = logging.getLogger(__name__)
router = APIRouter()

# Few workers on purpose: a file that takes too long is given up on (its thread finishes in the
# background, bounded by the page and size caps) and cannot start an unbounded number of threads.
_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="chat-file")


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


def _refuse(status: int, filename: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"filename": filename, "message": message})


@router.post("/v1/files/extract", response_model=ExtractedFile)
async def extract_file(file: UploadFile, response: Response) -> ExtractedFile:
    """Read one file attached in Company Chat. Errors say what happened and what to do next."""
    name = (file.filename or "file").replace("\\", "/").rsplit("/", 1)[-1][:200] or "file"
    data = await file.read(settings.file_max_bytes + 1)
    response.headers["Cache-Control"] = "no-store"
    loop = asyncio.get_running_loop()
    try:
        out = await asyncio.wait_for(
            loop.run_in_executor(
                _pool,
                lambda: read_chat_file(
                    name,
                    data,
                    max_bytes=settings.file_max_bytes,
                    max_chars=settings.file_max_chars,
                ),
            ),
            timeout=settings.file_extract_timeout,
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
