import os

os.makedirs("converted", exist_ok=True)

for file in sorted(os.listdir("audio")):
    source_path = os.path.join("audio", file)
    if not os.path.isfile(source_path):
        continue

    name, ext = os.path.splitext(file)
    dest_path = os.path.join("converted", f"{name}.opus")
    if os.path.exists(dest_path):
        continue

    os.system(f"ffmpeg -i {source_path} {dest_path}")
