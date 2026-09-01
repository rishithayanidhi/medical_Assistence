import os
import uuid
from fastapi import UploadFile, HTTPException

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "pdf"}
UPLOAD_DIR = "uploads"

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def save_uploaded_file(file: UploadFile) -> str:
    """Validates and saves uploaded file to local disk, returning file path."""
    
    # Extract file extension
    file_ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
    
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file format '.{file_ext}'. Allowed formats: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Generate unique filename to avoid overwriting existing files
    unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    # Save file to disk asynchronously
    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)
        
    return file_path