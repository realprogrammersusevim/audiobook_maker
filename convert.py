import os

os.mkdir("converted")

for file in sorted(os.listdir("audio")):
    name, ext = os.path.splitext(file)
    os.system(f"ffmpeg -i audio/{file} converted/{name}.opus")
