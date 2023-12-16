#!/usr/bin/python3

import os
import tempfile
import requests
import subprocess
import toml

cfg = toml.load(open('config.toml'))
host = cfg['audiobookshelf']['host']
sync_duration = cfg['sync']['duration']

def login(username, password):
	r = requests.post(f"{host}/login", json={"username": username, "password": password})
	r.raise_for_status()
	token = r.json()['user']['token']
	return token

def download_file(url, tmpfile, **kwargs):
	response = requests.get(url, stream=True, **kwargs)
	response.raise_for_status()

	total_size = int(response.headers.get('content-length', 0))
	block_size = 1024*512

	print(f"Downloading to {tmpfile.name}:")
	total_bytes_received = 0
	for data in response.iter_content(chunk_size=block_size):
		tmpfile.file.write(data)
		total_bytes_received += len(data)
		print_progress(total_bytes_received, total_size)
	print()

def print_progress(bytes_received, total_size):
	progress = (bytes_received / total_size) * 100
	progress = min(100, progress)
	print(f"Progress: [{int(progress)}%] [{'=' * int(progress / 2)}{' ' * (50 - int(progress / 2))}]", end='\r')

def tts(text):
	ttsfile = tempfile.NamedTemporaryFile(suffix=f".tts.wav")
	subprocess.check_call(['espeak', '-vde', text, '-w', ttsfile.name])
	return ttsfile

def ffmpeg(file1, output, file1_seekto=0):
	print(f"Transcoding to {output}")
	subprocess.check_call(['ffmpeg', '-hide_banner', '-y', '-loglevel', 'error',
						   '-ss', str(file1_seekto), '-i', file1,
						   '-c:a', 'libmp3lame', '-b:a', '128k', '-ar', '44100', '-ac', '2',
						   output
	])

def ffmpeg_concat(file1, file2, output, file2_seekto=0):
	print(f"Transcoding to {output}")
	subprocess.check_call(['ffmpeg', '-hide_banner', '-y', '-loglevel', 'error', '-i', file1,
						   '-ss', str(file2_seekto), '-i', file2,
						   '-filter_complex', "[0:a][1:a]concat=n=2:v=0:a=1[out]",
						   '-map', "[out]", '-c:a', 'libmp3lame', '-b:a', '128k', '-ar', '44100', '-ac', '2',
						   output
	])

def target_mp3_file(i):
	return os.path.join(cfg['sync']['target_dir'], f"{i:03}.mp3")



token = login(cfg['audiobookshelf']['username'], cfg['audiobookshelf']['password'])
th = {"Authorization": f"Bearer {token}"}


#r = requests.get(f"{host}/api/libraries", headers=th)
#r = requests.get(f"{host}/api/me/listening-sessions", headers=th)
#last_listened = r.json()['sessions']

current_abook_id = requests.get(f"{host}/api/me/items-in-progress", headers=th).json()['libraryItems'][0]['id']
current_abook = requests.get(f"{host}/api/items/{current_abook_id}", headers=th, params={'expanded': 1}).json()
progress = requests.get(f"{host}/api/me/progress/{current_abook_id}", headers=th).json()
current_pos = progress['currentTime']
tracks = current_abook['media']['tracks']
current_track = None
for track in tracks:
	if track['startOffset'] > current_pos:
		break
	current_track = track

#XXX
# check if different abook using marker textfile
# if yes, ask user if to delete everything
# and do so

# create marker file

# delete tracks up to current track
for track in tracks[:current_track['index']]:
	trackfile = target_mp3_file(track['index'])
	if os.path.isfile(trackfile):
		print(f"Deleting {trackfile}")
		os.unlink(trackfile)

current_track_pos = current_pos - current_track['startOffset']
# sync current_track starting with current_track_pos
localfile = tempfile.NamedTemporaryFile(suffix=f".{current_track['metadata']['relPath']}")
ttsfile = tts(f"Datei, {current_track['index']}.")
download_file(f"{host}{current_track['contentUrl']}", localfile, headers=th)
ffmpeg_concat(ttsfile.name, localfile.name, target_mp3_file(current_track['index']), int(current_track_pos))

synced_duration = current_track['startOffset'] + current_track['duration'] - current_pos

for track in tracks[current_track['index']:]:
	synced_duration += track['duration']
	print(f"Synced duration: {int(synced_duration)}/{sync_duration}s - {int(100*synced_duration/sync_duration)}%")
	output = target_mp3_file(track['index'])
	if os.path.isfile(output):
		print(f"Skipped existing file {output}")
	else:
		# sync track
		localfile = tempfile.NamedTemporaryFile(suffix=f".{track['metadata']['relPath']}")
		ttsfile = tts(f"Datei, {track['index']}.")
		download_file(f"{host}{track['contentUrl']}", localfile, headers=th)
		ffmpeg_concat(ttsfile.name, localfile.name, output)
	if synced_duration > sync_duration:
		break


output = target_mp3_file(999)
if os.path.isfile(output):
	print(f"End notice {output} already present")
else:
	print(f"Regenerating end notice {output}")
	ttsfile = tts("Achtung: Ende des synchronisierten Abschnitts erreicht.")
	ffmpeg(ttsfile.name, output)

