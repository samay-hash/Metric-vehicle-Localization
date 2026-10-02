import asyncio
import time
import cv2
import psutil
import argparse
from datetime import datetime
import sys
import os

# Must add parent dir to path so it can import services
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.video_pipeline import VideoPipeline, get_yolo
from data.database import add_event

try:
    import pynvml
    pynvml.nvmlInit()
    HAS_NVML = True
except ImportError:
    HAS_NVML = False

def get_gpu_stats():
    if not HAS_NVML:
        return 0, 0
    try:
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        gpu_util = pynvml.nvmlDeviceGetUtilizationRates(handle).gpu
        mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        mem_util = (mem_info.used / mem_info.total) * 100
        return gpu_util, mem_util
    except Exception:
        return 0, 0

async def dummy_on_event(event_data):
    # Mock event handler so we don't spam the actual database during stress tests
    pass

async def run_benchmark(num_streams: int, duration_sec: int):
    print(f"==================================================")
    print(f"🚀 Starting Stress Test: {num_streams} Concurrent Streams")
    print(f"⏱️  Duration: {duration_sec} seconds")
    print(f"==================================================")
    
    # Pre-load models to ensure they are in memory before timing
    get_yolo()
    
    class DummyCap:
        def __init__(self, fps=25):
            self.fps = fps
            
        def isOpened(self): return True
        def read(self):
            # Generate random noise to simulate motion so YOLO actually runs
            import numpy as np
            frame = np.random.randint(0, 255, (360, 640, 3), dtype=np.uint8)
            return True, frame
        def get(self, propId):
            if propId == cv2.CAP_PROP_FPS: return self.fps
            if propId == cv2.CAP_PROP_FRAME_WIDTH: return 640
            if propId == cv2.CAP_PROP_FRAME_HEIGHT: return 360
            if propId == cv2.CAP_PROP_FRAME_COUNT: return 99999
            return 0
        def release(self): pass

    pipelines = [VideoPipeline(output_dir=f"clips_bench_{i}") for i in range(num_streams)]
    start_time = time.time()
    
    # Override VideoCapture in the pipeline for this test
    original_vidcap = cv2.VideoCapture
    cv2.VideoCapture = lambda x: DummyCap()
    
    tasks = []
    for i, p in enumerate(pipelines):
        tasks.append(asyncio.create_task(p.process_video(f"dummy_{i}.mp4", dummy_on_event, f"CAM_BENCH_{i}")))
        
    print(f"[Benchmark] {num_streams} pipeline(s) launched. Monitoring resources...")
    
    results = []
    try:
        while time.time() - start_time < duration_sec:
            await asyncio.sleep(1.0)
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            gpu_u, gpu_m = get_gpu_stats()
            print(f"[Stats] CPU: {cpu}% | RAM: {ram}% | GPU Util: {gpu_u}% | GPU Mem: {gpu_m:.1f}%")
            results.append({"time": time.time()-start_time, "cpu": cpu, "ram": ram, "gpu": gpu_u})
    finally:
        print("[Benchmark] Stopping pipelines...")
        for p in pipelines:
            p.is_running = False
        cv2.VideoCapture = original_vidcap
        await asyncio.gather(*tasks, return_exceptions=True)
        
        print("==================================================")
        print("✅ Stress Test Complete")
        avg_cpu = sum(r["cpu"] for r in results) / max(1, len(results))
        avg_gpu = sum(r["gpu"] for r in results) / max(1, len(results))
        print(f"📊 Average CPU: {avg_cpu:.1f}%")
        print(f"📊 Average GPU: {avg_gpu:.1f}%")
        print(f"📊 Tested Streams: {num_streams}")
        print("==================================================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--streams", type=int, default=1, help="Number of concurrent streams")
    parser.add_argument("--duration", type=int, default=30, help="Test duration in seconds")
    args = parser.parse_args()
    asyncio.run(run_benchmark(args.streams, args.duration))
