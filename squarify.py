'''
Transcode the files... 
to 720x520 and SAR=1:1
'''

import os
import subprocess
import sys

def transcode(local_filepath):
	# ffmpeg -i local_filepath -vf scale=720x540,setsar=1:1 local_filepath_sq.mp4
	# delete original
	# return temp_vids/transcoded_filepath
	transcoded_filepath = False
	splitpath = list(os.path.splitext(local_filepath))
	splitpath.insert(1,"_square-pixel")
	transcoded_filepath = ''.join(splitpath)
	command = "ffmpeg -i {} -vf scale=720x540,setsar=1:1 {}".format(local_filepath,transcoded_filepath).split()
	output = subprocess.run(
		command, 
		stdout=subprocess.PIPE, 
		stderr=subprocess.PIPE)
	# print(output.stdout.decode('utf-8'))
	print(output.stderr.decode('utf-8'))

	if os.path.isfile(transcoded_filepath):
		pass
	else:
		transcoded_filepath = False

	return transcoded_filepath

def main(local_filepath):
	transcoded_filepath = transcode(local_filepath)

	return transcoded_filepath
	

if __name__ == "__main__":
	main()