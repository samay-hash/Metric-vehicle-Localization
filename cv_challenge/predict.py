import argparse
import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.pipeline import run_evaluation

def main():
    parser = argparse.ArgumentParser(description="Roostr CV Challenge Predictor")
    parser.add_argument("--images", required=True, help="Path to images directory")
    parser.add_argument("--targets", required=True, help="Path to targets.csv")
    parser.add_argument("--calibration", required=True, help="Path to calibration.csv")
    parser.add_argument("--output", required=True, help="Path to output predictions.csv")
    
    args = parser.parse_args()
    
    # Run the pipeline
    run_evaluation(args.images, args.targets, args.calibration, args.output)

if __name__ == "__main__":
    main()
