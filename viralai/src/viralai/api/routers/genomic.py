from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from time import time
from typing import cast
import json

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse

from viralai.api.auth import require_role
from viralai.api.dependencies import get_audit_logger, get_data_root
from viralai.api.schemas import (
    GenomicImportResponse,
    GenomicLibraryEntry,
    GenomicSearchResult,
    GenomicUploadResponse,
)
from viralai.security.api_keys import APIKeyRecord
from viralai.security.audit import AuditLogger
from viralai.security.roles import Role

router = APIRouter(prefix="/genomic", tags=["genomic"])

NCBI_ESearch_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
NCBI_ESummary_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
NCBI_EFetch_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def _safe_filename(filename: str) -> str:
    name = Path(filename).name
    safe = "".join(ch for ch in name if ch.isalnum() or ch in {"-", "_", "."})
    if not safe:
        safe = "uploaded_sequence.fasta"
    return safe


_NCBI_RATE_LIMIT_WINDOW_SECONDS = 60
_NCBI_RATE_LIMIT_MAX_REQUESTS = 10
_NCBI_RATE_LIMIT_TIMESTAMPS: list[float] = []
_NCBI_RATE_LIMIT_LOCK = Lock()


def _throttle_ncbi_request() -> None:
    now = time()
    window_start = now - _NCBI_RATE_LIMIT_WINDOW_SECONDS
    with _NCBI_RATE_LIMIT_LOCK:
        while _NCBI_RATE_LIMIT_TIMESTAMPS and _NCBI_RATE_LIMIT_TIMESTAMPS[0] < window_start:
            _NCBI_RATE_LIMIT_TIMESTAMPS.pop(0)
        if len(_NCBI_RATE_LIMIT_TIMESTAMPS) >= _NCBI_RATE_LIMIT_MAX_REQUESTS:
            raise HTTPException(
                status_code=429,
                detail="NCBI request rate limit exceeded. Try again later.",
            )
        _NCBI_RATE_LIMIT_TIMESTAMPS.append(now)


def _fasta_data_dir(data_root: Path) -> Path:
    path = data_root / "genomic_data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _library_dir(data_root: Path) -> Path:
    path = data_root / "genomic_data" / "library"
    path.mkdir(parents=True, exist_ok=True)
    return path


async def _ncbi_get_json(url: str, params: dict[str, str]) -> dict:
    _throttle_ncbi_request()
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()


async def _ncbi_get_text(url: str, params: dict[str, str]) -> str:
    _throttle_ncbi_request()
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.text


def _save_library_record(data_root: Path, filename: str, metadata: dict[str, object]) -> None:
    path = _library_dir(data_root) / f"{filename}.json"
    with path.open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, indent=2)


def _load_library_record(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


@router.get("/search", response_model=list[GenomicSearchResult])
async def search_genomic_sources(
    term: str = Query(..., min_length=1, description="Search term or accession"),
    databases: str | None = Query(None, description="Comma-separated sources: ncbi,ena,ddbj,ebisearch"),
) -> list[GenomicSearchResult]:
    selected_sources = [source.strip().lower() for source in (databases or "ncbi").split(",") if source.strip()]
    if not selected_sources:
        selected_sources = ["ncbi"]

    results: list[GenomicSearchResult] = []
    if "ncbi" in selected_sources:
        search_result = await _ncbi_get_json(
            NCBI_ESearch_URL,
            {"db": "nucleotide", "term": term, "retmode": "json", "retmax": "10"},
        )
        ids = search_result.get("esearchresult", {}).get("idlist", [])
        if ids:
            summary_result = await _ncbi_get_json(
                NCBI_ESummary_URL,
                {"db": "nucleotide", "id": ",".join(ids), "retmode": "json"},
            )
            summary = summary_result.get("result", {})
            for uid in summary.get("uids", []):
                entry = summary.get(uid, {})
                accession = cast(str, entry.get("accessionversion") or entry.get("caption") or "")
                results.append(
                    GenomicSearchResult(
                        uid=str(uid),
                        accession=accession,
                        title=cast(str, entry.get("title") or ""),
                        organism=cast(str, entry.get("organism") or None),
                        taxonomy_id=cast(int, entry.get("taxid") or None),
                        sequence_length=cast(int, entry.get("slen") or None),
                        pubdate=cast(str, entry.get("pubdate") or None),
                        update_date=cast(str, entry.get("updatedate") or None),
                        source="NCBI",
                        source_url=f"https://www.ncbi.nlm.nih.gov/nuccore/{accession}" if accession else "https://www.ncbi.nlm.nih.gov/",
                        database="nucleotide",
                        download_url=f"/genomic/download?accession={accession}",
                    )
                )

    if "ena" in selected_sources:
        results.append(
            GenomicSearchResult(
                uid=term.lower().replace(" ", "-"),
                accession=term.upper(),
                title=f"ENA entry for {term}",
                organism=None,
                taxonomy_id=None,
                sequence_length=None,
                pubdate=None,
                update_date=None,
                source="ENA",
                source_url=f"https://www.ebi.ac.uk/ena/browser/search?query={term}",
                database="ena",
                download_url=f"https://www.ebi.ac.uk/ena/browser/view/{term}",
            )
        )

    if "ddbj" in selected_sources:
        results.append(
            GenomicSearchResult(
                uid=term.lower().replace(" ", "-"),
                accession=term.upper(),
                title=f"DDBJ entry for {term}",
                organism=None,
                taxonomy_id=None,
                sequence_length=None,
                pubdate=None,
                update_date=None,
                source="DDBJ",
                source_url=f"https://ddbj.nig.ac.jp/search?query={term}",
                database="ddbj",
                download_url=f"https://ddbj.nig.ac.jp/entry/{term}",
            )
        )

    if "ebisearch" in selected_sources:
        results.append(
            GenomicSearchResult(
                uid=term.lower().replace(" ", "-"),
                accession=term.upper(),
                title=f"EBI Search entry for {term}",
                organism=None,
                taxonomy_id=None,
                sequence_length=None,
                pubdate=None,
                update_date=None,
                source="EBI Search",
                source_url=f"https://www.ebi.ac.uk/ebisearch/search.ebi?db=allebi&request={term}",
                database="ebisearch",
                download_url=f"https://www.ebi.ac.uk/ebisearch/search.ebi?db=allebi&request={term}",
            )
        )

    return results


@router.get("/download", response_class=PlainTextResponse)
async def download_ncbi_fasta(
    accession: str | None = Query(None, description="NCBI accession or sequence ID"),
    uid: str | None = Query(None, description="NCBI unique identifier"),
    format: str = Query("fasta", pattern="^(fasta|genbank)$"),
) -> PlainTextResponse:
    identifier = accession or uid
    if not identifier:
        raise HTTPException(status_code=400, detail="Provide 'accession' or 'uid' to download sequence data.")

    rettype = "gb" if format == "genbank" else "fasta"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            NCBI_EFetch_URL,
            params={"db": "nucleotide", "id": identifier, "rettype": rettype, "retmode": "text"},
        )
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail=f"NCBI fetch failed: {response.status_code}")
        if not response.text.strip():
            raise HTTPException(status_code=404, detail="No sequence data returned from NCBI.")
        return PlainTextResponse(response.text, media_type="text/plain")


@router.post("/import", response_model=GenomicImportResponse)
async def import_ncbi_sequence(
    accession: str = Query(..., min_length=1, description="NCBI accession or sequence ID to import"),
    data_root: Path = Depends(get_data_root),
    api_key: APIKeyRecord = Depends(require_role(Role.RESEARCHER)),
    audit: AuditLogger = Depends(get_audit_logger),
) -> GenomicImportResponse:
    fasta_text = await _ncbi_get_text(
        NCBI_EFetch_URL,
        {"db": "nucleotide", "id": accession, "rettype": "fasta", "retmode": "text"},
    )

    if not fasta_text.strip():
        raise HTTPException(status_code=404, detail="No FASTA data returned from NCBI.")

    library_dir = _library_dir(data_root)
    filename = _safe_filename(f"{accession}.fasta")
    sequence_path = library_dir / filename
    sequence_path.write_text(fasta_text, encoding="utf-8")

    summary_result = await _ncbi_get_json(
        NCBI_ESummary_URL,
        {"db": "nucleotide", "id": accession, "retmode": "json"},
    )
    summary = summary_result.get("result", {})
    entry = summary.get(str(accession), {}) if str(accession) in summary else {}
    metadata = {
        "filename": filename,
        "path": str(sequence_path.relative_to(data_root)),
        "download_url": f"/genomic/library/{filename}",
        "accession": accession,
        "uid": str(entry.get("uid") or ""),
        "organism": entry.get("organism"),
        "title": entry.get("title"),
        "imported_at": datetime.now(timezone.utc).isoformat(),
        "message": "Imported FASTA from NCBI into the local genomic library.",
        "size_bytes": len(fasta_text.encode("utf-8")),
    }
    metadata_basename = Path(filename).stem
    _save_library_record(data_root, metadata_basename, metadata)

    return GenomicImportResponse(**metadata)


@router.get("/library", response_model=list[GenomicLibraryEntry])
def list_genomic_library(data_root: Path = Depends(get_data_root)) -> list[GenomicLibraryEntry]:
    library_dir = _library_dir(data_root)
    entries: list[GenomicLibraryEntry] = []
    for meta_file in sorted(library_dir.glob("*.json")):
        record = _load_library_record(meta_file)
        if not record:
            continue
        record["download_url"] = f"/genomic/library/{record['filename']}"
        entries.append(GenomicLibraryEntry(**record))
    return entries


@router.get("/library/{filename}", response_class=FileResponse)
def download_library_entry(filename: str, data_root: Path = Depends(get_data_root)) -> FileResponse:
    library_dir = _library_dir(data_root)
    requested = library_dir / _safe_filename(filename)
    if not requested.exists() or not requested.is_file():
        raise HTTPException(status_code=404, detail=f"Library entry '{filename}' not found.")
    return FileResponse(requested, media_type="application/octet-stream", filename=requested.name)


@router.get("/library/metadata", response_model=list[GenomicLibraryEntry])
def list_genomic_library_metadata(data_root: Path = Depends(get_data_root)) -> list[GenomicLibraryEntry]:
    library_dir = _library_dir(data_root)
    entries: list[GenomicLibraryEntry] = []
    for meta_file in sorted(library_dir.glob("*.json")):
        record = _load_library_record(meta_file)
        if not record:
            continue
        record["download_url"] = f"/genomic/library/{record['filename']}"
        entries.append(GenomicLibraryEntry(**record))
    return entries


@router.post("/upload", response_model=GenomicUploadResponse)
async def upload_genomic_file(
    file: UploadFile = File(...),
    data_root: Path = Depends(get_data_root),
    api_key: APIKeyRecord = Depends(require_role(Role.RESEARCHER)),
    audit: AuditLogger = Depends(get_audit_logger),
) -> GenomicUploadResponse:
    filename = _safe_filename(file.filename)
    if not filename.lower().endswith((".fasta", ".fa", ".txt")):
        audit.record(actor=api_key.label, action="genomic.upload", resource=filename, outcome="denied", details={"reason": "invalid_extension"})
        raise HTTPException(status_code=400, detail="Only .fasta, .fa, or .txt files are accepted.")

    content = await file.read()
    if len(content) > 5_000_000:
        audit.record(actor=api_key.label, action="genomic.upload", resource=filename, outcome="denied", details={"size_bytes": len(content)})
        raise HTTPException(status_code=413, detail="Uploaded file exceeds the 5MB size limit.")

    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        audit.record(actor=api_key.label, action="genomic.upload", resource=filename, outcome="error", details={"reason": "invalid_encoding"})
        raise HTTPException(status_code=400, detail="Uploaded file must be UTF-8 encoded text.") from exc

    if ">" not in text:
        audit.record(actor=api_key.label, action="genomic.upload", resource=filename, outcome="denied", details={"reason": "not_fasta"})
        raise HTTPException(status_code=400, detail="Uploaded file does not appear to contain FASTA sequence data.")

    out_dir = _fasta_data_dir(data_root)
    out_path = out_dir / filename
    with out_path.open("w", encoding="utf-8") as handle:
        handle.write(text)

    audit.record(actor=api_key.label, action="genomic.upload", resource=filename, details={"size_bytes": len(content)})
    return GenomicUploadResponse(
        filename=filename,
        path=str(out_path.relative_to(data_root)),
        download_url=f"/genomic/uploads/{filename}",
        message="Genomic FASTA uploaded successfully.",
        size_bytes=len(content),
    )


@router.get("/uploads", response_model=list[GenomicUploadResponse])
def list_uploaded_genomes(data_root: Path = Depends(get_data_root)) -> list[GenomicUploadResponse]:
    upload_dir = _fasta_data_dir(data_root)
    uploads: list[GenomicUploadResponse] = []
    for path in sorted(upload_dir.iterdir()):
        if path.is_file():
            uploads.append(
                GenomicUploadResponse(
                    filename=path.name,
                    path=str(path.relative_to(data_root)),
                    download_url=f"/genomic/uploads/{path.name}",
                    message="Uploaded genomic FASTA file.",
                    size_bytes=path.stat().st_size,
                )
            )
    return uploads


@router.get("/uploads/{filename}", response_class=FileResponse)
def download_uploaded_genome(filename: str, data_root: Path = Depends(get_data_root)) -> FileResponse:
    upload_dir = _fasta_data_dir(data_root)
    requested = upload_dir / _safe_filename(filename)
    if not requested.exists() or not requested.is_file():
        raise HTTPException(status_code=404, detail=f"Uploaded file '{filename}' not found.")
    return FileResponse(requested, media_type="application/octet-stream", filename=requested.name)
