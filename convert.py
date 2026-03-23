import argparse
import os
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--input", default="audio")
parser.add_argument("-o", "--output", default="converted")
args = parser.parse_args()

os.makedirs(args.output, exist_ok=True)

for file in sorted(os.listdir(args.input)):
    source_path = os.path.join(args.input, file)
    if not os.path.isfile(source_path):
        continue

    name, ext = os.path.splitext(file)
    dest_path = os.path.join(args.output, f"{name}.opus")
    if os.path.exists(dest_path):
        continue

    subprocess.run(["ffmpeg", "-i", source_path, dest_path], check=True)
