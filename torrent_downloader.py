import subprocess
import zipfile
import time
import datetime
import shutil
import libtorrent as lt
from tqdm.notebook import tqdm
import os

def download_torrent(torrent_link,save_path):
  params = {
      'save_path': save_path,
      'storage_mode': lt.storage_mode_t(2),
  }

  ses = lt.session()
  ses.listen_on(6881, 6891)
  # torrent_link = input("Input Torrent file link or Magnet link and Press Enter: ")

  if torrent_link.endswith('.torrent'):
    import wget
    from torf import Torrent

    if os.path.exists('torrent.torrent'):
      os.remove('torrent.torrent')

    wget.download(torrent_link, 'torrent.torrent')
    t = Torrent.read('torrent.torrent')
    torrent_link = str(t.magnet(name=True, size=False, trackers=False, tracker=False))

  print(torrent_link)
  handle = lt.add_magnet_uri(ses, torrent_link, params)
  # change the 0 to a 1 to download sequentially
  handle.set_sequential_download(0)
  ses.start_dht()
  begin = time.time()

  print(datetime.datetime.now())
  print('Downloading Metadata...')

  while not handle.has_metadata():
    time.sleep(1)

  print('Got Metadata, Starting Torrent Download...')
  print("Starting", handle.name())
  pbar = tqdm(total=100)
  while handle.status().state != lt.torrent_status.seeding:
    s = handle.status()
    pbar.set_postfix({'Progress': f'{s.progress * 100:.2f}%', 'Down': f'{s.download_rate / 1000:.1f} kb/s', 'Up': f'{s.upload_rate / 1000:.1f} kB/s', 'Peers': s.num_peers}, refresh=False)
    pbar.n = int(s.progress*100)
    pbar.refresh()
    time.sleep(10)

  end = time.time()
  print(handle.name(), " COMPLETE")
  print("Elapsed Time: ", int((end - begin) // 60), "min :", int((end - begin) % 60), "sec")
  return os.path.join(save_path,handle.name())


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
          "-vf", f"\"subtitles={subtitle_file},ass=main.ass\""
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
      cmd +=["-c:v",f"lib{output_encode}", "-tune", "ssim" , "-crf", str(crf), "-c:a", "aac", "-b:a", "80k"]
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
