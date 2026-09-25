import os
import uuid
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/upload", tags=["File & Media Uploads"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".pdf"}

@router.post("/file", response_model=ApiResponse[dict])
async def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file selected")
    
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension '{ext}' not allowed. Supported: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    file_id = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, file_id)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_url = f"/uploads/{file_id}"

    return ApiResponse(
        success=True,
        statusCode=200,
        message="File uploaded successfully",
        data={
            "filename": file.filename,
            "fileId": file_id,
            "url": file_url,
            "fullUrl": f"http://localhost:8000{file_url}"
        }
    )
