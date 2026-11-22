from backend.models.product import CatalogRepository
from backend.services.storage_service import StorageService
from backend.services.job_worker import JobManager

# Singleton instances
_catalog_repo = CatalogRepository()
_storage_service = StorageService()
_job_manager = JobManager(storage_service=_storage_service, catalog_repo=_catalog_repo)

def get_catalog_repo() -> CatalogRepository:
    return _catalog_repo

def get_storage_service() -> StorageService:
    return _storage_service

def get_job_manager() -> JobManager:
    return _job_manager
