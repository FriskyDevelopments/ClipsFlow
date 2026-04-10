import subprocess
import os

source_file = "ANIMATE_FOR_BOT_202604070844.mp4"
dest_dir = "/Users/friskypup/ClipFLOW/assets/welcome_videos/"
dest_file = os.path.join(dest_dir, source_file)

try:
    with open(dest_file, "wb") as f:
        print("Opened file for writing")
        subprocess.run(["git", "show", f"HEAD:{source_file}"], cwd="/Users/friskypup/Documents/Playground", stdout=f, check=True)
    print("Success writing!")
except Exception as e:
    print("Error:", e)
