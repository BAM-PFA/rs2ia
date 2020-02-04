#!/usr/bin/env python3
"""
This script (or maybe scripts eventually?) will be used to transfer
assets and metadata from our local ResourceSpace to Internet Archive.
"""
import csv
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
		rsAssetID = None,
		# localAssetPaths=None,
		assetMetadata = {},
		_user = None,
		mediaType = None
		):
		self.localAssetPaths = []
		self.assetMetadata = assetMetadata
		self.mediaType = mediaType
		self.rsAssetID = self.assetMetadata['Resource ID(s)'] # this value will come from a metadata CSV file
		self.collection = 'pacificfilmarchive' # IN FUTURE SHOULD BE 'TVTV' as well (once archive.org collection is created)
		self.collection2 = 'stream_only'
		#self.license = 'https://creativecommons.org/licenses/by-nc-nd/4.0/'
		self._user = _user
		self.rsAPI = ResourceSpaceAPI(_user)

		# initializing metadata attributes required/desired by IA that don't appear in RS
		self.description = ""
		self.source = ""
		self.externalidentifier = ""
		self.date = ""

	def get_local_asset_path(self):
		# see https://www.resourcespace.com/knowledge-base/api/get_resource_path
		# construct parameters of API call as a string
		parameters = (
			"param1={}"
			"&param2=1"
			"&param3="
			"&param4="
			"&param5={}".format(
				self.rsAssetID,
				self.mediaType
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

		if self.mediaType == 'mp4':
			ia_mediatype = 'movies'
		elif self.mediaType == 'mp3':
			ia_mediatype = 'audio'

		'''
		Normalizing columns from csv for use in metadata dict.
			This is required because the RS and IA metadata fields do not directly
			map to each other. Each field is initialized to "" so that the metadata
			dict doesn't complain that it's missing; blank fields will be removed later.
		'''
		# concatenate 'description' fields
		if self.assetMetadata['Notes'] : # if the metadata field exists (as a string), then add it to the dictionary value
			self.description = "Notes: " + self.assetMetadata['Notes'] + ". "
		if self.assetMetadata['Description'] :
			self.description = "Description: " + self.assetMetadata['Description'] + ". "
		if self.assetMetadata['Alternative Title'] :
			self.description += "Alternative Title: " + self.assetMetadata['Alternative Title'] + ". "
		if self.assetMetadata['Credits'] :
			self.description += "Credits: " + self.assetMetadata['Credits']
		# concatenate 'source' fields
		if self.assetMetadata['Medium of original'] :
			self.source = "Medium of original: " + self.assetMetadata['Medium of original'] + ". "
		if self.assetMetadata['Dimensions of original'] :
			self.source += "Dimensions of original: " + self.assetMetadata['Dimensions of original'] + ". "
		# add 'urn:bampfa_accession_number:' to accession # (this conforms to IA style guide)
		if self.assetMetadata['PFA full accession number'] :
			self.externalidentifier = "urn:bampfa_accession_number:" + self.assetMetadata['PFA full accession number']
		if self.assetMetadata['Date of recording'] :
			self.date = self.assetMetadata['Date of recording']
		elif self.assetMetadata['Release Date'] :
			self.date = self.assetMetadata['Release Date']
		# audio- and video-specific fields
		if ia_mediatype == 'movies' :
			if self.assetMetadata['Original video format'] :
				self.source += "Original video format: " + self.assetMetadata['Original video format'] + ". "
			if self.assetMetadata['Original video standard'] :
				self.source += "Original video standard: " + self.assetMetadata['Original video standard'] + ". "
			if self.assetMetadata['Generation'] :
				self.source += "Generation: " + self.assetMetadata['Generation']
		elif ia_mediatype == 'audio' :
			if self.assetMetadata['PFA film series'] :
				self.description = "Pacific Film Archive film series: " + self.assetMetadata['PFA film series'] + ". "
			if self.assetMetadata['Event title'] :
				self.description = "Event title: " + self.assetMetadata['Event title'] + ". "
			if self.assetMetadata['Speaker/Interviewee'] :
				self.description = "Speaker/Interviewee: " + self.assetMetadata['Speaker/Interviewee'] + ". "
			if self.assetMetadata['Subject(s): Film title(s)'] :
				self.description = "Subject(s): Film title(s): " + self.assetMetadata['Subject(s): Film title(s)'] + ". "
			if self.assetMetadata['Subject(s): Topics(s)'] :
				self.description = "Subject(s): Topics(s): " + self.assetMetadata['Subject(s): Topics(s)'] + ". "

		# general MD dict
		general_md = {
			'collection': self.collection,
			'collection': self.collection2, # this overrides the previous line
			'rights': self.assetMetadata['Copyright statement'],
			'mediatype': ia_mediatype,
			#'licenseurl': self.license,
			'contributor': self.assetMetadata['Resource type'],
			'identifier': identifier,
			'external-identifier': self.externalidentifier,
			'title': self.assetMetadata['Title'],
			'date': self.date,
			'description': self.description,
			'source': self.source,
			'language': self.assetMetadata['Language']
		}
		movies_md = {
			'sound': self.assetMetadata['PFA item sound characteristics'],
			'color': self.assetMetadata['Color characteristics'],
			'creator': self.assetMetadata['Directors / Filmmakers'],
		}
		# audio_md = {
		# 	# need appropriate creator field for audio; will all audio be PFA lecture series?
		# }

		# concatenate dictionaries
		if ia_mediatype == 'movies' :
			md = dict(general_md)
			md.update(movies_md)
		elif ia_mediatype == 'audio' :
			md = dict(general_md)

		# get rid of empty values in the md dictionary
		md = {k: v for k, v in md.items() if v not in (None,'')}
		# remove line breaks that display as literal "<br/>"
		md = {v.replace('<br/>', ' '): k
			for k, v in md.items()}
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
				_user=_user,
				mediaType=mediaType
				)
			# get_local_asset_path uses the rsAssetID to find the local filepath of the asset
			currentAsset.get_local_asset_path()
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
		print("YOU CHOSE AUDIO! SUPER! THANKS!")
	elif mediaType == 'v':
		mediaType = 'mp4'
		print("YOU CHOSE VIDEO! SUPER! THANKS!")
	else:
		print("YOU ENTERED AN INVALID MEDIA TYPE! JUST TYPE a OR v")
		sys.exit()
	print(mediaType)
	parse_resourcespace_csv(csvPath,_user,mediaType)

if __name__ == "__main__":
	main()
