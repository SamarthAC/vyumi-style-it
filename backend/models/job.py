from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class GenerateRequest(BaseModel):
    user_image_id: str = Field(..., description="Uploaded user photo ID", min_length=1)
    product_id: str = Field(..., description="Target catalog product ID", min_length=1)

class GenerateResponse(BaseModel):
    job_id: str = Field(..., description="Created job unique identifier")
    status: JobStatus = Field(JobStatus.PENDING, description="Initial job status")

class JobStatusResponse(BaseModel):
    status: JobStatus = Field(..., description="Current status of the try-on job")
    result_image_url: Optional[str] = Field(None, description="URL to download or view try-on result")
    error_code: Optional[str] = Field(None, description="Error code if job failed")
    message: Optional[str] = Field(None, description="Human-readable error or status message")
    job_id: Optional[str] = Field(None, description="Job identifier")

    model_config = {"use_enum_values": True}
