import logging
import queue
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, Optional, Any

from backend.models.job import JobStatus
from backend.services.storage_service import StorageService
from backend.models.product import CatalogRepository, get_cloth_type_for_category
from backend.services.tryon_service import run_tryon, TryOnError, is_engine_ready, get_engine_error

logger = logging.getLogger("vyumi.jobs")

class JobManager:
    def __init__(self, storage_service: StorageService, catalog_repo: CatalogRepository):
        self.storage_service = storage_service
        self.catalog_repo = catalog_repo
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._queue: queue.Queue = queue.Queue()
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def start_worker(self):
        """Start background consumer thread if not running."""
        with self._lock:
            if self._worker_thread is None or not self._worker_thread.is_alive():
                self._stop_event.clear()
                self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name="TryOnWorkerThread")
                self._worker_thread.start()

    def stop_worker(self):
        """Gracefully stop background worker thread."""
        self._stop_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.0)

    def create_job(self, user_image_id: str, product_id: str) -> Dict[str, Any]:
        """Validate request and register a new pending job."""
        user_img_path = self.storage_service.get_user_image_path(user_image_id)
        if not user_img_path:
            raise ValueError(f"User image '{user_image_id}' not found or invalid.")

        product = self.catalog_repo.get_product(product_id)
        if not product:
            raise ValueError(f"Product '{product_id}' not found in catalog.")

        cloth_type = product.cloth_type or get_cloth_type_for_category(product.category)
        if not cloth_type:
            raise ValueError(f"Unsupported product category '{product.category}'. Only shirts, tops, and dresses are supported.")

        job_id = uuid.uuid4().hex
        job_record = {
            "id": job_id,
            "user_image_id": user_image_id,
            "product_id": product_id,
            "cloth_type": cloth_type,
            "status": JobStatus.PENDING,
            "result_image_url": None,
            "error_code": None,
            "message": None,
            "created_at": time.time(),
            "completed_at": None,
        }

        with self._lock:
            self._jobs[job_id] = job_record

        # Enqueue job for serialized processing
        self._queue.put(job_id)
        return job_record

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            return dict(job)

    def _worker_loop(self):
        """Worker thread processing one inference job at a time."""
        while not self._stop_event.is_set():
            try:
                job_id = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue

            try:
                self._process_job(job_id)
            except Exception as e:
                logger.error(f"Error processing job {job_id}: {e}", exc_info=True)
            finally:
                self._queue.task_done()

    def _process_job(self, job_id: str):
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job["status"] = JobStatus.PROCESSING

        user_image_id = job["user_image_id"]
        product_id = job["product_id"]
        cloth_type = job["cloth_type"]

        user_img_path = self.storage_service.get_user_image_path(user_image_id)
        product_img_path = self.catalog_repo.get_product_image_path(product_id)

        # Pre-check engine readiness
        if not is_engine_ready():
            err = get_engine_error()
            err_code = err.code if err else "ENGINE_UNAVAILABLE"
            err_msg = err.message if err else "Try-on engine is not available."
            with self._lock:
                job["status"] = JobStatus.FAILED
                job["error_code"] = err_code
                job["message"] = err_msg
                job["completed_at"] = time.time()
            return

        if not product_img_path or not product_img_path.exists():
            with self._lock:
                job["status"] = JobStatus.FAILED
                job["error_code"] = "PRODUCT_IMAGE_MISSING"
                job["message"] = f"Product image for '{product_id}' is unavailable."
                job["completed_at"] = time.time()
            return

        # Execute run_tryon (serialized via tryon_service._lock and single worker)
        try:
            result_path = run_tryon(
                person_path=str(user_img_path),
                garment_path=str(product_img_path),
                cloth_type=cloth_type,
            )

            filename = Path(result_path).name
            with self._lock:
                job["status"] = JobStatus.COMPLETED
                job["result_image_url"] = f"/style-it/results/{filename}"
                job["completed_at"] = time.time()

        except TryOnError as e:
            with self._lock:
                job["status"] = JobStatus.FAILED
                job["error_code"] = e.code
                job["message"] = e.message
                job["completed_at"] = time.time()

        except Exception as e:
            logger.error(f"Unexpected generation failure for job {job_id}: {e}", exc_info=True)
            with self._lock:
                job["status"] = JobStatus.FAILED
                job["error_code"] = "INTERNAL_ERROR"
                job["message"] = "We could not generate the result. Try another image or product."
                job["completed_at"] = time.time()
