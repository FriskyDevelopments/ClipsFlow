import os
import subprocess
import math

def chunk_video(input_path: str, max_mb: int = 40) -> list:
    '''Chunks a video using ffmpeg ensuring target size limits by dynamically estimating duration.'''
    probe_cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", input_path
    ]
    try:
        duration_str = subprocess.check_output(probe_cmd).decode('utf-8').strip()
        duration = float(duration_str)
    except Exception:
        duration = 180.0

    size_bytes = os.path.getsize(input_path)
    # Target 30MB parts to conservatively stay under 50MB telegram limit due to keyframe padding
    target_bytes = 30 * 1024 * 1024 
    
    num_chunks = math.ceil(size_bytes / target_bytes)
    if num_chunks <= 1:
        num_chunks = 2

    target_seconds = max(10, math.floor(duration / num_chunks))
    
    output_pattern = input_path + "_part%03d.mp4"
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-c", "copy",
        "-f", "segment",
        "-segment_time", str(target_seconds),
        "-reset_timestamps", "1",
        output_pattern
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    directory = os.path.dirname(input_path)
    base = os.path.basename(input_path) + "_part"
    return sorted([os.path.join(directory, f) for f in os.listdir(directory) if f.startswith(base)])
