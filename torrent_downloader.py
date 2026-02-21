import subprocess
import libtorrent as lt
import zipfile
import time
import datetime
import shutil
from tqdm.notebook import tqdm
import os
import wget
import json

def download_torrent_aria2(torrent_link, save_path):
    os.makedirs(save_path, exist_ok=True)

    # اگر لینک torrent file باشه، دانلودش کن
    if torrent_link.endswith('.torrent'):
        torrent_file = os.path.join(save_path, "temp.torrent")
        if os.path.exists(torrent_file):
            os.remove(torrent_file)
        wget.download(torrent_link, torrent_file)
        torrent_input = torrent_file
    else:
        torrent_input = torrent_link  # magnet

    print(torrent_input)
    print(datetime.datetime.now())
    print('Starting Torrent Download...')

    log_file = os.path.join(save_path, "aria2.log")

    command = [
        "aria2c",

        # ================= CONCURRENCY (CRITICAL) =================
        "-x16",                 # connections per server
        "-s4",                  # LOW split = faster torrents
        "-k4M",                 # request bigger pieces
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
        "--auto-file-renaming=false",
        "--allow-overwrite=false",

        # ================= TRACKERS =================
        "--bt-tracker=https://tracker.openbittorrent.com:443/announce",
        "--bt-tracker=https://tracker.opentrackr.org:443/announce",
        "--bt-tracker=https://tracker.leechers-paradise.org:6969/announce",

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

    print("Download complete.")

    # پیدا کردن بزرگ‌ترین فایل دانلودشده
    downloaded_files = [
        f for f in os.listdir(save_path)
        if os.path.isfile(os.path.join(save_path, f))
    ]

    if not downloaded_files:
        print("No files found.")
        return None

    downloaded_files.sort(
        key=lambda f: os.path.getsize(os.path.join(save_path, f)),
        reverse=True
    )

    output_file = downloaded_files[0]
    return os.path.join(save_path, output_file)

def download_torrent_libtorrent(torrent_link, save_path):
    
    os.makedirs(save_path, exist_ok=True)

    # اگر لینک torrent file باشه
    if torrent_link.endswith('.torrent'):
        torrent_file = os.path.join(save_path, "temp.torrent")
        if os.path.exists(torrent_file):
            os.remove(torrent_file)
        wget.download(torrent_link, torrent_file)
        torrent_input = torrent_file
        is_magnet = False
    else:
        torrent_input = torrent_link
        is_magnet = True

    print(torrent_input)
    print(datetime.datetime.now())
    print("Starting Torrent Download (libtorrent)...")

    # ================= SESSION SETUP =================
    ses = lt.session()
    ses.listen_on(6881, 6891)

    settings = {
        'download_rate_limit': 0,
        'upload_rate_limit': 0,

        'connections_limit': 500,
        'active_downloads': 10,
        'active_seeds': 10,
        'active_limit': 100,

        'request_timeout': 10,
        'peer_timeout': 10,
        'inactivity_timeout': 30,

        'enable_dht': True,
        'enable_lsd': True,
        'enable_upnp': True,
        'enable_natpmp': True,

        'cache_size': 32 * 1024 * 1024,  # 32MB
        'disk_io_write_mode': 1,          # write-through
        'strict_end_game_mode': False,
        'seed_time_limit': 0,
    }

    ses.apply_settings(settings)

    # ================= ADD TORRENT =================
    params = {
        'save_path': save_path,
        'storage_mode': lt.storage_mode_t.storage_mode_sparse,
    }

    if is_magnet:
        params['url'] = torrent_input
    else:
        params['ti'] = lt.torrent_info(torrent_input)

    handle = ses.add_torrent(params)

    # ================= WAIT FOR METADATA =================
    if is_magnet:
        print("⏳ Waiting for metadata...")
        while not handle.has_metadata():
            time.sleep(1)
        print("✅ Metadata received")

    # ================= FILE PRIORITY =================
    ti = handle.get_torrent_info()
    files = ti.files()

    sizes = [(i, files.file_size(i)) for i in range(ti.num_files())]
    sizes.sort(key=lambda x: x[1], reverse=True)

    for idx, size in sizes:
        handle.file_priority(idx, 7 if size > 0 else 1)

    # ================= DOWNLOAD LOOP =================#
    pbar = tqdm(total=100)

    while not handle.status().is_seeding:
        try:
            s = handle.status()

            if s.total_wanted > 0:
                percent = (s.total_wanted_done / s.total_wanted) * 100
            else:
                percent = 0

            # شبیه‌سازی خروجی aria2
            line = (
                f"[#libtorrent "
                f"{s.total_wanted_done/1024/1024:.0f}MiB/"
                f"{s.total_wanted/1024/1024:.0f}MiB"
                f"({percent:.0f}%) "
                f"CN:{s.num_peers} "
                f"DL:{s.download_rate/1024/1024:.2f}MiB "
                f"ETA:{int((s.total_wanted - s.total_wanted_done) / (s.download_rate + 1))}s]"
            )

            # === همون منطق aria2 ===
            if '(' in line and '%' in line:
                percent = line.split('%')[0].split('(')[-1]
                pbar.n = int(float(percent))
                pbar.set_postfix_str(line.strip())
                pbar.refresh()

            time.sleep(1)

        except:
            pass

    pbar.n = 100
    pbar.refresh()
    pbar.close()

    # ================= FIND LARGEST FILE =================
    downloaded_files = [
        f for f in os.listdir(save_path)
        if os.path.isfile(os.path.join(save_path, f))
    ]

    if not downloaded_files:
        print("No files found.")
        return None

    downloaded_files.sort(
        key=lambda f: os.path.getsize(os.path.join(save_path, f)),
        reverse=True
    )

    output_file = downloaded_files[0]
    return os.path.join(save_path, output_file)

def encode_intro(
    main_video_path,
    resolution,
    crf=23,
    preset="medium"
):

    intro_input = "/content/torrent_downloader/intro/Intro.mp4"
    intro_output = "/content/temp_files/intro.mkv"

    os.makedirs(os.path.dirname(intro_output), exist_ok=True)

    # گرفتن FPS از ویدیوی اصلی
    probe_cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate",
        "-of", "json",
        main_video_path
    ]

    probe_result = subprocess.run(
        probe_cmd,
        capture_output=True,
        text=True
    )

    video_info = json.loads(probe_result.stdout)
    fps_fraction = video_info["streams"][0]["r_frame_rate"]

    # تبدیل کسر به عدد اعشاری و گرد کردن تا 3 رقم
    num, den = map(int, fps_fraction.split("/"))
    fps = round(num / den, 3)

    cmd = [
        "ffmpeg",
        "-y",
        "-i", intro_input,
        "-vf", f"fps={fps},scale={resolution}",
        "-c:v", "libx264",
        "-preset", preset,
        "-tune", "animation",
        "-profile:v", "high",
        "-level", "4.1",
        "-color_primaries", "bt709",
        "-color_trc", "bt709",
        "-colorspace", "bt709",
        "-c:a", "aac",
        "-b:a", "128k"
        "-crf", str(crf),
        intro_output
    ]

    return " ".join(cmd)

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
        "-i", input_video,
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

    cmd.append(output_video)

    return " ".join(cmd)

def concat_videos(intro_path, episode_path, output_path):
    """
    Concatenate two videos using ffmpeg without re-encoding (-c copy).

    Parameters:
        intro_path (str): Path to encoded intro video
        episode_path (str): Path to encoded episode video
        output_path (str): Path to final output video
    """

    # فایل لیست برای concat
    list_file = "/content/temp_files/list.txt"
    os.makedirs(os.path.dirname(list_file), exist_ok=True)

    with open(list_file, "w") as f:
        f.write(f"file '{intro_path}'\n")
        f.write(f"file '{episode_path}'\n")

    # دستور concat
    cmd = [
        "ffmpeg",
        "-f", "concat",
        "-safe", "0",
        "-i", list_file,
        "-c", "copy",
        output_path
    ]

    return " ".join(cmd)

def get_mkv_files(root_dir):
   mkv_files = []
   for dir_, _, files in os.walk(root_dir):
       for file_name in files:
           if file_name.endswith(".mkv"):
               rel_file = os.path.relpath(os.path.join(dir_, file_name), root_dir)
               mkv_files.append(rel_file)
   return mkv_files
