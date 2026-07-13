import asyncio
import os
import sys
from pathlib import Path
import cv2
import numpy as np
import subprocess

from backend.services.caption_burner import CaptionBurner

async def run_test():
    video_path = Path("temp/test_heroku.mp4")
    video_path.parent.mkdir(exist_ok=True)
    
    # 1. Create a dummy video
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=blue:s=640x360:d=5",
        "-f", "lavfi", "-i", "anullsrc=cl=mono:r=16000",
        "-t", "5",
        str(video_path)
    ]
    print("Creating dummy video on Heroku...")
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # 2. Burn text
    burner = CaptionBurner()
    output_path = Path("temp/test_heroku_burned.mp4")
    caption_text = "Testing caption overlay on Heroku dyno."
    
    print("Running burn_single...")
    await burner.burn_single(
        video_path=video_path,
        output_path=output_path,
        caption_text=caption_text,
        video_width=640,
        video_height=360,
        max_chars_per_line=30
    )
    
    # 3. Analyze pixels
    cap = cv2.VideoCapture(str(output_path))
    frame_count = 0
    has_non_blue = False
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame_count += 1
        h, w, c = frame.shape
        lower_third = frame[int(h*0.7):, :, :]
        # Check for non-blue pixels
        non_bg = np.sum((lower_third[:, :, 1] > 20) | (lower_third[:, :, 2] > 20) | (lower_third[:, :, 0] < 200))
        if non_bg > 50:
            has_non_blue = True
            print(f"Frame {frame_count}: detected {non_bg} non-background pixels in lower third! Sample color: {lower_third[0, 0]}")
            break
            
    cap.release()
    print("VERIFICATION RESULT: Has captions burned on Heroku =", has_non_blue)

if __name__ == "__main__":
    asyncio.run(run_test())
