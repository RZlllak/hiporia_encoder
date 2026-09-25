from concurrent.futures import process
import subprocess
import zipfile
import time
import datetime
import shutil
from tqdm.notebook import tqdm
import os
import json


def find_completed_file(save_path):
    EXCLUDED_FILES = {"aria2.log"}
    candidates = []
    for root, _, files in os.walk(save_path):
        for f in files:
            if f in EXCLUDED_FILES or f.endswith(".aria2"):
                continue
            full_path = os.path.join(root, f)
            control_file = full_path + ".aria2"
            if os.path.exists(control_file):
                continue  # still incomplete — has a resume control file
            candidates.append(full_path)

    if not candidates:
        return None
    candidates.sort(key=os.path.getsize, reverse=True)
    return candidates[0]

def download_torrent_aria2(torrent_link, save_path):
    os.makedirs(save_path, exist_ok=True)

    # ================= تشخیص نوع لینک =================
    is_magnet = torrent_link.startswith("magnet:")
    is_direct_link = not is_magnet

    torrent_input = torrent_link

    print(torrent_input)
    print(datetime.datetime.now())

    log_file = os.path.join(save_path, "aria2.log")

    if is_direct_link:
        print('Starting Direct Download...')
        command = [
            "aria2c",

            # ================= CONCURRENCY =================
            "-x16",
            "-s16",
            "-k4M",
            "--min-split-size=4M",

            # ================= DISK IO OPTIMIZATION =================
            "--file-allocation=trunc",
            "--enable-mmap=true",
            "--disk-cache=256M",

            # ================= FILE SAFETY =================
            # فایل قبلاً کامل دانلودشده رو overwrite/skip می‌کند به‌جای Error
            "--allow-overwrite=false",
            "--auto-file-renaming=false",
            "--continue=true",

            # ================= PROGRESS =================
            "--summary-interval=1",
            "--console-log-level=notice",
            "--human-readable=true",
            f"--log={log_file}",

            # ================= OUTPUT =================
            "--dir", save_path,

            torrent_input
        ]
    else:
        print('Starting Torrent Download...')
        command = [
            "aria2c",

            # ================= CONCURRENCY (CRITICAL) =================
            "-x16",
            "-s4",
            "-k4M",
            "--min-split-size=4M",

            # ================= DISK IO OPTIMIZATION =================
            "--file-allocation=trunc",
            "--enable-mmap=true",
            "--disk-cache=256M",
            "--stream-piece-selector=inorder",

            # ================= TORRENT OPTIMIZATION =================
            "--bt-max-peers=0",
            "--bt-request-peer-speed-limit=50M",
            "--bt-prioritize-piece=head,tail",
            "--bt-save-metadata=true",
            "--bt-load-saved-metadata=true",

            # ================= NETWORK =================
            "--enable-dht=true",
            "--enable-peer-exchange=true",
            "--bt-enable-lpd=true",

            # ================= FILE SAFETY =================
            # فایل قبلاً کامل دانلودشده رو overwrite/skip می‌کند به‌جای Error 13
            "--allow-overwrite=false",
            "--auto-file-renaming=false",

            # ================= TRACKERS =================
            "--bt-tracker=https://tracker.openbittorrent.com:443/announce",
            "--bt-tracker=https://tracker.opentrackr.org:443/announce",

            # ================= NO SEED =================
            "--seed-time=0",
            "--bt-seed-unverified=false",

            # ================= PROGRESS =================
            "--summary-interval=1",
            "--console-log-level=notice",
            "--human-readable=true",
            f"--log={log_file}",

            # ================= OUTPUT =================
            "--dir", save_path,

            torrent_input
        ]

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    pbar = tqdm(total=100)
    for line in process.stdout:
        if '(' in line and '%' in line:
            try:
                percent = line.split('%')[0].split('(')[-1]
                pbar.n = int(float(percent))
                pbar.set_postfix_str(line.strip())
                pbar.refresh()
            except:
                pass

    process.wait()
    pbar.n = 100
    pbar.refresh()
    pbar.close()

    output_file = find_completed_file(save_path)

    if process.returncode != 0 and output_file is None:
        raise RuntimeError(f"aria2c failed (exit {process.returncode}) and no completed file was found")

    if process.returncode != 0:
        print(f"⚠️ aria2c exited with code {process.returncode}, but a completed file was found — assuming already downloaded.")
    else:
        print("Download complete.")

    return output_file

def encode_intro(
    main_video_path,
    resolution,
    preset="medium"
):

    intro_input = "/content/torrent_downloader/intro/Intro.mp4"
    intro_output = "/content/temp_files/intro.mkv"

    os.makedirs(os.path.dirname(intro_output), exist_ok=True)

    # دریافت اطلاعات ویدیو و صدا از فایل اصلی
    probe_cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries",
        "stream=index,codec_type,r_frame_rate,sample_rate,channels:stream_tags=language,title",
        "-of", "json",
        main_video_path
    ]

    probe = subprocess.run(
        probe_cmd,
        capture_output=True,
        text=True,
        check=True
    )

    info = json.loads(probe.stdout)

    video_stream = next(s for s in info["streams"] if s["codec_type"] == "video")
    audio_streams = [s for s in info["streams"] if s["codec_type"] == "audio"]

    # FPS
    fps_fraction = video_stream["r_frame_rate"]
    num, den = map(int, fps_fraction.split("/"))
    fps = round(num / den, 3)

    # مشخصات اولین ترک صوتی
    sample_rate = audio_streams[0]["sample_rate"]
    channels = audio_streams[0]["channels"]

    cmd = [
        "ffmpeg",
        "-y",
        "-i", intro_input,

        # Stream Mapping
        "-map", "0:v:0",
    ]

    # به تعداد ترک‌های صوتی فایل اصلی، صدای Intro را اضافه کن
    for _ in audio_streams:
        cmd += ["-map", "0:a:0"]

    # Video Encoding
    cmd += [
        "-vf", f"fps={fps},scale={resolution}",

        "-c:v", "libx264",
        "-preset", preset,
        "-tune", "animation",
        "-profile:v", "high",
        "-level", "4.1",
        "-color_primaries", "bt709",
        "-color_trc", "bt709",
        "-colorspace", "bt709",
        "-crf", "23",

        # Audio Encoding
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", str(sample_rate),
        "-ac", str(channels),
    ]

    # Metadata
    for i, stream in enumerate(audio_streams):

        tags = stream.get("tags", {})

        if "language" in tags:
            cmd += [
                f"-metadata:s:a:{i}",
                f"language={tags['language']}"
            ]

        if "title" in tags:
            cmd += [
                f"-metadata:s:a:{i}",
                f"title={tags['title']}"
            ]

        cmd += [
            f"-disposition:a:{i}",
            "default" if i == 0 else "0"
        ]

    cmd.append(intro_output)

    return cmd

def add_subtitles(
    input_video,
    episode_subtitle,
    output_video,
    crf=23,
    resolution=None,
    remove_original_subs=True,
    channel_subtitle="main.ass"
):
    """
    Hardcode two ASS subtitles into video using libx264.
    
    Parameters:
        input_video (str): Path to input video
        episode_subtitle (str): Episode-specific .ass file
        output_video (str): Path to final encoded output
        crf (int): Quality factor (lower = better quality)
        resolution (str): Optional resolution like "1920x1080"
        remove_original_subs (bool): Remove existing subtitle streams
        channel_subtitle (str): Channel tag subtitle (default: main.ass)
    """

    # ساخت فیلتر هاردساب با دو فایل ASS
    subtitle_filter = f"ass={episode_subtitle},ass={channel_subtitle}"

    cmd = [
        "ffmpeg",
        "-i", f'{input_video}',
        "-vf", subtitle_filter,
    ]

    # Stream mapping
    if remove_original_subs:
        cmd += ["-map", "0:v", "-map", "0:a"]
    else:
        cmd += ["-map", "0"]

    # Video encoding (libx264 ثابت)
    cmd += [
        "-c:v", "libx264",
        "-preset", "medium",
        "-tune", "animation",
        "-profile:v", "high",
        "-level", "4.1",
        "-color_primaries", "bt709",
        "-color_trc", "bt709",
        "-colorspace", "bt709",
        "-crf", str(crf),
    ]

    # Audio encoding
    cmd += [
        "-c:a", "aac",
        "-b:a", "128k"
    ]

    # Optional resolution
    if resolution:
        cmd += ["-s", resolution]

    cmd.append(f'{output_video}')

    return cmd

def concat_videos(intro_path, episode_path, output_path):
    temp_dir = "/content/concat_temp"
    os.makedirs(temp_dir, exist_ok=True)
    list_path = os.path.join(temp_dir, "list.txt")

    def esc(p):
        return os.path.abspath(p).replace("'", r"'\''")

    with open(list_path, "w", encoding="utf-8") as f:
        f.write(f"file '{esc(intro_path)}'\n")
        f.write(f"file '{esc(episode_path)}'\n")

    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path,
           "-map", "0", "-c", "copy", output_path]
    return cmd


def get_mkv_files(root_dir):
   mkv_files = []
   for dir_, _, files in os.walk(root_dir):
       for file_name in files:
           if file_name.endswith(".mkv"):
               rel_file = os.path.relpath(os.path.join(dir_, file_name), root_dir)
               mkv_files.append(rel_file)
   return mkv_files
