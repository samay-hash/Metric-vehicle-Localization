import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from services.video_pipeline import VideoPipeline
async def mock_on_event(event_data):
    print("\n" + "="*50)
    print("🚨 NEW EVENT GENERATED FROM PIPELINE 🚨")
    print("="*50)
    import json
    print(json.dumps(event_data, indent=2))
    print("="*50 + "\n")
    pipeline.is_running = False
async def main():
    video_file = "/Users/samaysamrat/bankcctv/test_cctv.mov"
    if not os.path.exists(video_file):
        print(f"Error: {video_file} not found.")
        return
    print(f"Starting test pipeline on {video_file}...")
    global pipeline
    pipeline = VideoPipeline(output_dir="clips")
    await pipeline.process_video(video_file, mock_on_event)
    print("Test finished.")
if __name__ == "__main__":
    asyncio.run(main())