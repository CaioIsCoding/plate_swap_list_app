from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List
from pydantic import BaseModel
import shutil
import os
import tempfile
from .core import parse_3mf, generate_swap_file

router = APIRouter()

class PlateItem(BaseModel):
    id: str
    filename: str
    plate_index: int
    image_url: str
    print_time: int
    weight: float
    file_path: str # Validation? Internal use.
    # We will use this to track how many copies user wants
    count: int = 1

class GenerateRequest(BaseModel):
    playlist: List[PlateItem]

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Save uploaded file to temp
    temp_dir = tempfile.mkdtemp(prefix="swap_upload_")
    file_path = os.path.join(temp_dir, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Parse 3MF/Gcode and return metadata
    try:
        plates = parse_3mf(file_path)
        return {"plates": plates, "temp_id": temp_dir}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/generate")
async def generate_swap(request: GenerateRequest):
    # Call core logic to generate swap file
    try:
        download_url = generate_swap_file(request.playlist)
        return {"download_url": download_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
