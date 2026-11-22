from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse, JSONResponse

from backend.api.deps import get_storage_service, get_job_manager
from backend.models.job import GenerateRequest, GenerateResponse, JobStatusResponse, JobStatus
from backend.services.storage_service import StorageService, StorageError
from backend.services.job_worker import JobManager
from backend.services.tryon_service import is_engine_ready, get_engine_error

router = APIRouter(prefix="/style-it", tags=["style-it"])

@router.post("/upload")
async def upload_user_image(
    file: UploadFile = File(...),
    storage: StorageService = Depends(get_storage_service)
):
    """
    Securely upload a user photo for virtual try-on.
    Validates file format, size, and content integrity.
    """
    try:
        content = await file.read()
        image_id = storage.save_user_image(
            file_bytes=content,
            original_filename=file.filename,
            content_type=file.content_type
        )
        return {"user_image_id": image_id}
    except StorageError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process upload: {str(e)}")

@router.post("/generate", response_model=GenerateResponse, status_code=status.HTTP_202_ACCEPTED)
def generate_tryon(
    payload: GenerateRequest,
    job_mgr: JobManager = Depends(get_job_manager)
):
    """
    Submit a virtual try-on job for processing.
    Validates user image and product availability.
    """
    # Reject generation requests if try-on engine is not ready
    if not is_engine_ready():
        err = get_engine_error()
        err_msg = err.message if err else "Try-on engine is unavailable."
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Try-on engine unavailable: {err_msg}"
        )

    try:
        job = job_mgr.create_job(
            user_image_id=payload.user_image_id,
            product_id=payload.product_id
        )
        return GenerateResponse(job_id=job["id"], status=job["status"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/jobs/{job_id}")
def get_job_status(
    job_id: str,
    job_mgr: JobManager = Depends(get_job_manager)
):
    """
    Poll the status of a try-on job.
    Matches the required engine error contract:
    - failed: { "status": "failed", "error_code": "...", "message": "..." }
    - completed: { "status": "completed", "result_image_url": "..." }
    - pending: { "status": "pending" }
    """
    job = job_mgr.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job_status = job["status"]

    if job_status == JobStatus.FAILED:
        return JSONResponse(
            status_code=200,
            content={
                "status": "failed",
                "error_code": job.get("error_code") or "UNKNOWN_ERROR",
                "message": job.get("message") or "Generation failed"
            }
        )
    elif job_status == JobStatus.COMPLETED:
        return {
            "status": "completed",
            "result_image_url": job.get("result_image_url")
        }
    else:
        return {
            "status": "pending" if job_status == JobStatus.PENDING else "processing"
        }

@router.get("/results/{filename}")
def get_result_image(
    filename: str,
    storage: StorageService = Depends(get_storage_service)
):
    """Safely retrieve a generated try-on result image."""
    result_path = storage.get_result_image_path(filename)
    if not result_path:
        raise HTTPException(status_code=404, detail="Result image not found")
    return FileResponse(str(result_path), media_type="image/png")
