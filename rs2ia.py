#!/usr/bin/env python3
"""
This script (or maybe scripts eventually?) will be used to transfer
assets and metadata from our local ResourceSpace to Internet Archive.
"""
import ast
import csv
import getpass
from google_drive_downloader import GoogleDriveDownloader # from https://github.com/ndrplz/google-drive-downloader/blob/master/google_drive_downloader/google_drive_downloader.py
import hashlib
from internetarchive import upload
import os.path
import re
import requests
import subprocess
import sys
import time

# # COUNTER IS FOR TESTING PURPOSES
# counter=1

class User:
	'''
	Define a user who will be connecting to
	ResourceSpace and Internet Archive.
	'''
	def __init__(self):
		self.define_rs_user()
		self.define_ia_user()

	def define_rs_user(self):
		self.rsUserName = input("enter resourcespace user name:")
		self.rsAPIkey = input("enter your resourcespace API key:")

	def define_ia_user(self):
		'''
		The Internet Archive Python library works by storing archive.org credentials
		in an initialization file at /home/.config/ia.ini. The script will look
		for that file. If it doesn't exist, it will run the Internet Archive
		CLI "configure" function to set username and password interactively.
		'''
		try:
			os.path.isfile('/home/.config/ia.ini')
		except FileNotFoundError:
			print("Your Internet Archive credentials are missing! There should be a config file at /home/.config/ia.ini.")
			print("If this script does not prompt you to enter your archive.org credentials, please exit and run `ia configure` in the terminal.")
			# not sure that below works in all cases - should run the bashCommand as defined in line below, then communicate output errors
			bashCommand = "ia configure"
			process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
			output, error = process.communicate()
		else:
			pass

class ResourceSpaceAPI:
	'''
	Define location of ResourceSpace assets
	and how to query the API. Largely based on
	https://github.com/pixuenan/RS-python-API/blob/master/RSAPI.py
	'''
	def __init__(self,_user=None):
		self.edithServer = "resourcespace.bampfa.berkeley.edu"
		self._user = _user

	def query(self, function_to_query, parameters, _user):
		'''
		Construct an RS API query:
		1. Define the query: combination of username, the ResourceSpace function,
			and the parameters of the query (e.g. ResourceSpace ID)
		2. Hash user's private API key with the query itself to create a unique
			query string ("sign")
		3. Combine the hashed query string with the query itself in a query URL
			(linked to the Edith server)
		For more detail: https://www.resourcespace.com/knowledge-base/api/
		'''
		query = "user={}&function={}&{}".format(
			_user.rsUserName,
			function_to_query,
			parameters
			)
		sign = hashlib.sha256(_user.rsAPIkey.encode()+query.encode())
		sign = sign.hexdigest()
		queryURL = "https://{}/api/?{}&sign={}".format(
			self.edithServer,
			query,
			sign
			)
		# get the result of API query, i.e. what is returned by the query URL
		# print(queryURL)
		result = requests.post(queryURL)
		# try:
		# 	# get the result of API query, i.e. what is returned by the query URL
		# 	result = queryURL
		# except (IOError, UnicodeDecodeError) as err:
		# 	print(err)
		httpStatus = result.status_code
		if httpStatus == 200:
			return result.text.replace("\\","").replace("\"","")
		else:
			return None

class Asset:
	'''
	Define an asset, which could be simple (one file)
	or complex (a set of files), plus metadata
	'''
	def __init__(
		self,
		rsAssetID=None,
		# localAssetPaths=None,
		assetMetadata={},
		_user=None
		):
		self.localAssetPaths = []
		self.assetMetadata = assetMetadata
		self.rsAssetID = self.assetMetadata['Resource ID(s)'] # this value will come from a metadata CSV file
		self.collection = 'pacificfilmarchive' # IN FUTURE SHOULD BE 'TVTV' as well (once archive.org collection is created)
		self.collection2 = 'stream_only'
		#self.license = 'https://creativecommons.org/licenses/by-nc-nd/4.0/'
		self.mediatype ='movies' # archive.org media type will always be 'movies'
		self._user = _user
		self.rsAPI = ResourceSpaceAPI(_user)

	def get_local_asset_path(self,mediaType=None):
		# see https://www.resourcespace.com/knowledge-base/api/get_resource_path
		# construct parameters of API call as a string
		parameters = (
			"param1={}"
			"&param2=1"
			"&param3="
			"&param4="
			"&param5={}".format(
				self.rsAssetID,
				mediaType
				)
			)
		# query API for filepath of primary asset as hosted on ResourceSpace - COMMENTED OUT FOR TESTING
		self.primaryAssetPath = self.rsAPI.query(
			"get_resource_path",
			parameters,
			self._user
			)

		### THIS IS FAKE STUFF FOR TESTING. THERE ARE 3 FAKE FILES: 1bampfaTVTV.mp4, 2bampfaTVTV.mp4, 3bampfaTVTV.mp4
		# global counter
		# self.primaryAssetPath = os.path.join("/Users/bampfa/Documents/GitHub/rs2ia/fakes/",str(counter)+"bampfaTVTV.mp4")
		# counter += 1
		# END FAKE STUFF FOR TESTING

		print("PRIMARY ASSET PATH:")
		print(self.primaryAssetPath)
		self.localAssetPaths.append(self.primaryAssetPath)

	def get_local_alternative_asset_paths(self):
		# get filepaths for alternative files associated with the primary asset.
		# see https://www.resourcespace.com/knowledge-base/api/get_alternative_files
		# construct parameters of API call as a string
		parameters = "param1={}&param2=&param3=".format(self.rsAssetID)
		# query API; result is a dictionary of information about
		# the alternative files, but no actual filepaths
		# also, it's not a valid Python dict, it's maybe a PHP array?
		self.alternativeAssetDict = self.rsAPI.query(
			"get_alternative_files",
			parameters,
			self._user
			)
		print("ALT ASSET PATH:")
		print(self.alternativeAssetDict)
		# get the ref ID for the alternative asset and make a new query with that ID
		refNumber = re.match(r"^\[{(ref\:)([0-9]+).*", self.alternativeAssetDict).group(2)
		extension = re.match(r".*file_extension\:([0-9a-z]+).*", self.alternativeAssetDict).group(1)
		print("ALT FILE EXTENSION")
		print(extension)
		print("ALT FILE REFERENCE NUMBER")
		print(refNumber)
		new_parameters = (
			"param1={}"
			"&param2=1"
			"&param3="
			"&param4="
			"&param5={}"
			"&param6="
			"&param7="
			"&param8={}".format(
				self.rsAssetID,
				extension,
				refNumber
				)
			)
		self.alternativeAssetPaths = self.rsAPI.query(
			"get_resource_path",
			new_parameters,
			self._user
			)
		#### COMMENTED OUT FOR TESTING
		self.localAssetPaths.append(self.alternativeAssetPaths)
		print("ALL ASSET PATHS:")
		print(self.localAssetPaths)


	def post_to_ia(self):
		'''
		Use the archive.org Python Library to upload an asset to archive.org,
			accompanied by its metadata. Requires the local filepath of the
			asset, as well as a CSV holding the metadata for that asset. The CSV
			must be manually exported and normalized by the operator from a
			ResourceSpace search.
		For more info: archive.org Python Library: https://archive.org/services/docs/api/internetarchive/quickstart.html#metadata
			and archive.org metadata schema: https://archive.org/services/docs/api/metadata-schema/index.html
		'''
		try:
			identifier = os.path.splitext(self.assetMetadata['Access copy filename'])[0]
		except:
			identifier = self.assetMetadata['Access copy filename']
		md = {
			# LET'S THINK ABOUT HOW TO MAKE THIS SET OF MD MORE AGNOSTIC/GENERALIZABLE
			'collection': self.collection,
			'collection': self.collection2,
			'rights': 'This is a rights statement',
			'mediatype': self.mediatype,
			#'licenseurl': self.license,
			'creator': self.assetMetadata['Directors / Filmmakers'],
			'contributor': self.assetMetadata['Resource type'],
			'identifier': identifier,
			'title': self.assetMetadata['Title'],
			'date': self.assetMetadata['Release Date'],
			# Original columns 'Notes,' 'Alternative Title,' 'Credits' should be concatenated manually by operator into single column 'Notes'
			'description': self.assetMetadata['Notes'],
			# Original columns 'Medium of original,' 'Dimensions of original,' 'Original video standard,' 'Generation' columns should be concatenated manually by operator into single column 'Medium of original'
			'source': self.assetMetadata['Medium of original'],
			# 'frame rate' column should be normalized into numbers manually by operator
			'frames_per_second': self.assetMetadata['Frame rate'],
			# 'video size' column should be split into 'Video height' and 'Video width' numbers manually by operator
			# 'source_pixel_width': self.assetMetadata['Video height'],
			# 'source_pixel_height': self.assetMetadata['Video width'],
			# 'PFA full accession number' column should be normalized to 'urn:bampfa_accession_number:XXXX' manually by operator
			'external-identifier': self.assetMetadata['PFA full accession number'],
			'condition': self.assetMetadata['Original Material Condition'],
			'sound': self.assetMetadata['PFA item sound characteristics'],
			'color': self.assetMetadata['Color characteristics']
		}
		# get rid of empty values in the md dictionary
		md = {k: v for k, v in md.items() if v not in (None,'')}

		# archive.org Python Library, 'uploading': https://archive.org/services/docs/api/internetarchive/quickstart.html#uploading
		print("ACCESS COPY FILENAME:")
		print(identifier)
		print("LOCAL ASSET PATHS:")
		print(self.localAssetPaths)
		print("METADATA DICT:")
		print(md)
		### COMMENTED OUT FOR TESTING
		# from the ia package documentation:
		# r = upload('<identifier>', files=['foo.txt', 'bar.mov'], metadata=md)
		r = upload(identifier, files=self.localAssetPaths, metadata=md)
		# consider rewriting the below? see: https://python-forum.io/Thread-Response-200-little-help
		print(r[0].status_code)
		if r[0].status_code == 200:
			print("Uploaded")
		else:
			print("Upload failed")

def parse_resourcespace_csv(csvPath,_user, mediaType):
	'''
	1. Interpret metadata CSV as a 'key:value' dictionary, using the first row
		as the 'key', using DictReader
	2. Assign the correct CSV row of metadata 'values' to the current asset
	3. Post asset with metadata to archive.org (using post_to_ia, defined above)
	'''
	with open(csvPath) as file:
		records = csv.DictReader(file)
		for row in records:
			# the Asset class __init__ function defines the asset's rsAssetID, which will be stored in the same CSV row as the rest of the metadata
			currentAsset = Asset(
				assetMetadata=row,
				_user=_user
				)
			# get_local_asset_path uses the rsAssetID to find the local filepath of the asset
			currentAsset.get_local_asset_path(mediaType)
			try:
				currentAsset.get_local_alternative_asset_paths()
			except:
				pass
			print(
				currentAsset.rsAssetID,
				currentAsset.localAssetPaths
				)
			currentAsset.post_to_ia()
			del currentAsset

def parse_drive_url(url):
	try:
		file_google_id = re.match(
			r"(https:\/\/drive\.google\.com\/file\/d\/)([A-Za-z0-9-_]+)(\/.*)",
			url
			).group(2)
		timestamp = time.strftime("%Y-%m-%dT%H-%M-%S")
		dest_path = 'csvs/'+timestamp+'.csv'
		GoogleDriveDownloader.download_file_from_google_drive(
			file_id=file_google_id,
			dest_path= 'csvs/'+timestamp+'.csv'
			)
		time.sleep(2)
		local_csv_path = dest_path
	except:
		local_csv_path =  None

	print("LOCAL CSV PATH")
	print(local_csv_path)

	return local_csv_path

def define_resourcespace_csv():
	csvPath = input("drag and drop path to CSV with ResourceSpace metadata, or paste a Google Drive link here:")
	if not csvPath.startswith("https://drive"):
		pass
	else:
		csvPath = parse_drive_url(csvPath)
		if not csvPath:
			print("YOU MESSED UP! SOMETHINGS UP WITH THE DRIVE LINK OR THE LOCAL FILEPATH")
			sys.exit()
		else:
			pass

	return csvPath

def main():
	_user = User()
	print("Hello, "+_user.rsUserName)
	csvPath = define_resourcespace_csv()
	mediaType = input("You want audio or video? Type 'a' for audio or 'v' for video: ")
	if mediaType == 'a':
		mediaType = 'mp3'
	elif mediaType == 'v':
		mediaType = 'mp4'
	else:
		print("YOU ENTERED AN INVALID MEDIA TYPE! JUST TYPE a OR v DUMMIE")
		sys.exit()
	parse_resourcespace_csv(csvPath,_user,mediaType)

if __name__ == "__main__":
	main()
