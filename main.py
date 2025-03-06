import yt_dlp
import ffmpeg
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import shutil

app = FastAPI()

# Temporary folder for storing videos
TEMP_DIR = "/tmp/downloads"

# Ensure the temporary directory exists
os.makedirs(TEMP_DIR, exist_ok=True)

# Function to download and process video
def download_video(url: str, format: str):
    # Ensure only supported formats are used
    if format not in ["mp4", "mp3"]:
        raise ValueError("Only mp4 and mp3 formats are supported.")

    # yt-dlp options
    ydl_opts = {
        'format': 'best',
        'noplaylist': True,
        'outtmpl': f'{TEMP_DIR}/video.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': format,  # Convert to mp4/mp3
        }],
        'postprocessor_args': ['-vf', 'fps=25,scale=-1:720'],  # Optional: remove watermarks by scaling
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        file_ext = 'mp4' if format == 'mp4' else 'mp3'
        return f"{TEMP_DIR}/video.{file_ext}"

# Endpoint to download media from TikTok or Instagram
@app.get("/download/{platform}")
async def download(platform: str, url: str, format: str = "mp4"):
    # Validate platform
    if platform not in ["tiktok", "instagram"]:
        raise HTTPException(status_code=400, detail="Invalid platform")
    
    # Validate the format
    if format not in ["mp4", "mp3"]:
        raise HTTPException(status_code=400, detail="Invalid format, only 'mp4' or 'mp3' are supported.")

    try:
        video_path = download_video(url, format)
        return {
            "status": "success",
            "url": f"/download/{os.path.basename(video_path)}",
            "format": format,
            "platform": platform,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading video: {str(e)}")

# Endpoint to serve downloaded files (static files)
@app.get("/download/{file_path:path}")
async def serve_file(file_path: str):
    file_path_full = os.path.join(TEMP_DIR, file_path)
    
    # Check if the file exists
    if not os.path.exists(file_path_full):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_path_full)

# Optional: Rate limit protection
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["yourdomain.com", "*.vercel.app"])
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
