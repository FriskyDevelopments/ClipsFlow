import shutil
import sys
try:
    shutil.copyfile('/Users/friskypup/Documents/Playground/ANIMATE_FOR_BOT_202604070844.mp4', '/Users/friskypup/ClipFLOW/assets/welcome_videos/ANIMATE_FOR_BOT_202604070844.mp4')
    print("Success 1")
except Exception as e:
    print("Error 1:", e)
try:
    shutil.copyfile('/Users/friskypup/Documents/Playground/READY_IMMEDIATE_DELIVERY_202604070844.mp4', '/Users/friskypup/ClipFLOW/assets/welcome_videos/READY_IMMEDIATE_DELIVERY_202604070844.mp4')
    print("Success 2")
except Exception as e:
    print("Error 2:", e)
