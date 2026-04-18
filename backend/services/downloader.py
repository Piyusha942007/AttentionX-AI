"""
downloader.py — YouTube video download service using yt-dlp.

Downloads YouTube videos to the local uploads directory for processing.
Extracts title and duration metadata.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
import yt_dlp

logger = logging.getLogger(__name__)

def download_youtube_video(url: str, output_dir: str) -> dict:
    """
    Download a YouTube video and return metadata + local path.
    
    Returns:
        {
            "local_path": str,
            "title": str,
            "duration": float,
            "thumbnail": str,
        }
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': os.path.join(output_dir, '%(id)s.%(ext)s'),
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info.get('id')
            ext = info.get('ext', 'mp4')
            local_path = os.path.join(output_dir, f"{video_id}.{ext}")
            
            return {
                "local_path": local_path,
                "title": info.get('title', 'YouTube Video'),
                "duration": float(info.get('duration', 0)),
                "thumbnail": info.get('thumbnail', ''),
                "filename": f"{video_id}.{ext}"
            }
    except Exception as e:
        logger.error(f"YouTube download failed: {e}")
        raise Exception(f"Failed to download YouTube video: {str(e)}")
