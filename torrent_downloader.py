import subprocess
import zipfile
import time
import datetime
import shutil
from tqdm.notebook import tqdm
import os
import wget

def download_torrent(torrent_link, save_path):
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



def add_subtitles(input_video, subtitle_file, encode_type='hard',
      output_encode='x264',crf=25,size_string=None,remove_sub=False):
    # Check if hard sub is requested
    sub_type = "-vf" if encode_type=='hard' else "-scodec"
    # Command to add subtitles using ffmpeg
    if encode_type=='hard':
      subtitle_file = subtitle_file.replace('\"','')
      cmd = [
          "ffmpeg",
          "-i", input_video,
          "-vf", f"\"ass={subtitle_file},ass=main.ass\""
      ]
    else:
      vmap = "-0:v" if remove_sub else "0"
      amap = "-0:a" if remove_sub else "0"
      cmd = [
          "ffmpeg",
          "-i", input_video,  # Input video file
          "-i", subtitle_file,  # Subtitle file
          "-map","1",
          "-c:s","srt",
          "-metadata:s:s:1","language=per[Persian]",
          "-vf", '"ass=main.ass"'
      ]
      
    if remove_sub:
      cmd += ["-map", "0:v", "-map", "0:a"]
    else:
      cmd += ["-map","0"]      
    if output_encode is not None:
      cmd +=["-c:v",f"lib{output_encode}", "-tune animation", "-level 4.1", "-profile high" , "-color_primaries" , "bt709" , "-color_trc bt709" , "-colorspace" , "bt709" , "-crf", str(crf), "-c:a", "aac", "-b:a", "128k"]
    if size_string is not None:
      cmd += ["-s", size_string]
    shell_cmd = ' '.join(cmd)
    return shell_cmd

def get_mkv_files(root_dir):
   mkv_files = []
   for dir_, _, files in os.walk(root_dir):
       for file_name in files:
           if file_name.endswith(".mkv"):
               rel_file = os.path.relpath(os.path.join(dir_, file_name), root_dir)
               mkv_files.append(rel_file)
   return mkv_files
