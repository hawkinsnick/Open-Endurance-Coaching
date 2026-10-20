import argparse
import json
from .analysis import load_csv, summarize

def main():
    parser = argparse.ArgumentParser(description="Summarize authorized workout CSV")
    parser.add_argument("csv_file")
    args = parser.parse_args()
    print(json.dumps(summarize(load_csv(args.csv_file)), indent=2))

if __name__ == "__main__":
    main()
