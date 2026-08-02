import subprocess
import zipfile
import time
import datetime
import shutil
from tqdm.notebook import tqdm
import os
import wget
import json

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

    with open(list_path, "w", encoding="utf-8") as f:
        f.write(f"file '{os.path.abspath(intro_path)}'\n")
        f.write(f"file '{os.path.abspath(episode_path)}'\n")

    cmd = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", list_path,
        "-map", "0",
        "-c", "copy",
        output_path
    ]
    return cmd


def get_mkv_files(root_dir):
   mkv_files = []
   for dir_, _, files in os.walk(root_dir):
       for file_name in files:
           if file_name.endswith(".mkv"):
               rel_file = os.path.relpath(os.path.join(dir_, file_name), root_dir)
               mkv_files.append(rel_file)
   return mkv_files
