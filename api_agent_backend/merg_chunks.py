
import time
from pathlib import Path
import subprocess
import ffmpeg
from decouple import config


UPLOAD_ROOT = Path(config('UPLOAD_ROOT'))
OUTPUT_ROOT = Path(config('OUTPUT_ROOT'))

def has_audio(file_path: Path) -> bool:
    try:
        probe = ffmpeg.probe(str(file_path))
        streams = probe.get("streams", [])
        for stream in streams:
            if stream.get("codec_type") == "audio":
                return True
        return False
    except Exception:
        return False


def normalize_chunk(chunk_path: Path, output_path: Path):
    """
    Normalize video resolution, fps, and codec for safe merging.
    """
    command = [
        "ffmpeg", "-y", "-i", str(chunk_path),
        "-vf", "scale=1600:900,fps=15",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "ultrafast",
        str(output_path)
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to normalize {chunk_path.name}: {result.stderr.decode()}")



def merge_chunks(input_folder: Path, output_path: Path):
    original_chunks = sorted(
        input_folder.glob("chunk*.mp4"),
        key=lambda f: int(''.join(filter(str.isdigit, f.stem)))
    )

    if not original_chunks:
        return False, f"No chunks found in {input_folder}"

    print(f"Merging {input_folder} into {output_path}")

    audio_present = has_audio(original_chunks[0])
    normalized_chunks = []

    try:
        for i, chunk in enumerate(original_chunks):
            norm_path = input_folder / f"norm_{i}.mp4"
            normalize_chunk(chunk, norm_path)
            normalized_chunks.append(norm_path)
    except Exception as e:
        return False, str(e)

    input_args = []
    filter_complex = ""

    for idx, chunk in enumerate(normalized_chunks):
        input_args.extend(["-i", str(chunk)])
        if audio_present:
            filter_complex += f"[{idx}:v:0][{idx}:a:0]"
        else:
            filter_complex += f"[{idx}:v:0]"

    filter_complex += f"concat=n={len(normalized_chunks)}:v=1"
    filter_complex += ":a=1[outv][outa]" if audio_present else ":a=0[outv]"

    command = [
        "ffmpeg",
        *input_args,
        "-filter_complex", filter_complex,
        "-map", "[outv]"
    ]

    if audio_present:
        command.extend(["-map", "[outa]"])

    command.extend([
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-y",  
        str(output_path)
    ])

    result = subprocess.run(command, cwd=input_folder, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    
    for file in normalized_chunks:
        file.unlink()

    if result.returncode != 0:
        return False, result.stderr.decode()

    
    for file in original_chunks:
        file.unlink()

    done_file = input_folder / "done.txt"
    if done_file.exists():
        done_file.unlink()

    return True, f"Merged successfully to {output_path}"


def monitor_and_merge():
    while True:
        print("Scanning for ready-to-merge folders...")
        for user_folder in UPLOAD_ROOT.glob("user_*"):
            if not user_folder.is_dir():
                continue

            done_file = user_folder / "done.txt"
            merged_file = OUTPUT_ROOT / f"{user_folder.name}_merged.mp4"

            if done_file.exists() and not merged_file.exists():
                success, message = merge_chunks(user_folder, merged_file)
                if success:
                    print(f" {message}")
                else:
                    print(f" Merge failed: {message}")

        time.sleep(10)  
