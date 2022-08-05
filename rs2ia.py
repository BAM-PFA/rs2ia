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

rightsStatement = """Copyright ©TVTV. This work is protected by U.S. Copyright Law \
(Title 17, U.S.C.). In addition, its reproduction may be restricted by terms \
of gift or purchase agreements, donor restrictions, privacy and publicity \
rights, licensing and trademarks. This work is made accessible ONLY for purposes of \
education and research. Transmission or reproduction of works protected by \
copyright beyond that allowed by fair use requires the written permission \
of the copyright owners. Works not in the public domain may not be \
commercially exploited without permission of the copyright owner. \
Responsibility for any use rests exclusively with the user.\n
Please send questions and comments to bampfa@berkeley.edu.
"""
# rightsStatement = """This work may be protected by the U.S. Copyright Law \
# (Title 17, U.S.C.). In addition, its reproduction may be restricted by terms \
# of gift or purchase agreements, donor restrictions, privacy and publicity \
# rights, licensing and trademarks. This work is made accessible ONLY for purposes of \
# education and research. Transmission or reproduction of works protected by \
# copyright beyond that allowed by fair use requires the written permission \
# of the copyright owners. Works not in the public domain may not be \
# commercially exploited without permission of the copyright owner. \
# Responsibility for any use rests exclusively with the user.\n
# Berkeley Art Museum and Pacific Film Archive has made efforts in all \
# cases to secure permission to display copyrighted works from rights owners; \
# we are eager to hear from rights owners with any questions or concerns \
# regarding this display.\n
# If you are a legitimate copyright holder to this work and \
# would like to discuss removing it from public display, please send requests \
# to bampfa@berkeley.edu.
# """

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
		self.identifier = None
		self.creator = None
		self.title = None
		self.date = None
		self.subject = None
		self.description = None
		self.notes = None
		self.mediaType = mediaType
		self.rsAssetID = self.assetMetadata['Resource ID(s)'] # this value will come from a metadata CSV file
		self.collection = ['stream_only','pacificfilmarchive'] # collection can be an array
		#self.license = 'https://creativecommons.org/licenses/by-nc-nd/4.0/'
		self._user = _user
		self.rsAPI = ResourceSpaceAPI(_user)

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
		print("ALT ASSETS FROM RS:")
		print(self.alternativeAssetDict)

		# get the ref ID for each alternative asset and make a new query with that ID
		# there should be a 1:1 relationship between
		# the matched ref #'s and file extensions
		alts = {}
		refNumbers = [ref[1] for ref in re.findall(r"({ref\:)([0-9]+)",self.alternativeAssetDict)]
		extensions = [ext[1] for ext in re.findall(r"(,file_extension:)(\w{0,4})",self.alternativeAssetDict)]
		if not len(refNumbers) == len(extensions):
			print("ALTERNATIVE FILE MISMATCH BTW EXTENSIONS AND NUM OF FILES")
			sys.exit
		for ref in refNumbers:
			alts[ref] = extensions[refNumbers.index(ref)]

		for ref, ext in alts.items():
			# print("ALT FILE EXTENSION")
			# print(ext)
			# print("ALT FILE REFERENCE NUMBER")
			# print(ref)
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
					ext,
					ref
					)
				)
			alternativeAssetPath = self.rsAPI.query(
				"get_resource_path",
				new_parameters,
				self._user
				)
			self.localAssetPaths.append(alternativeAssetPath)

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
		self.get_core_metadata(self.assetMetadata)

		md = {
			# LET'S THINK ABOUT HOW TO MAKE THIS SET OF MD MORE AGNOSTIC/GENERALIZABLE
			'identifier': self.identifier,
			'title': self.title,
			'collection': self.collection,
			# Original CSV columns 'Notes,' 'Digitization QC note,' etc.
			# should be concatenated manually by operator into single column 'Notes'
			'notes': self.assetMetadata['Notes']+"\nDigitized through a generous 2018 Recordings at Risk grant from the Council on Library and Information Resources.",
			# 'notes': self.assetMetadata['Notes']+"\nDigitized through a generous 2018 Humanities Collections and Reference Resources grant from the National Endowment for the Humanities.",
			# Description -> description
			'description': self.assetMetadata['Description'],
			'subject': self.subject,
			'date': self.date,
			# contributor: The person or organization that provided the physical or digital media.
			'contributor': self.assetMetadata['Resource type'],
			'creator': self.creator,
			'language': self.assetMetadata['Language'],
			'rights': rightsStatement,
			#'licenseurl': self.license,
			'coverage': self.assetMetadata['Location of recording'],
			'identifier': self.identifier,
			'condition': self.assetMetadata['Original Material Condition'],
			# Original columns 'Medium of original,' 'Dimensions of original,' 'Original video standard,' 'Generation' columns should be concatenated manually by operator into single column 'Medium of original'
			'source': self.assetMetadata['Medium of original']
		}

		if self.mediaType == 'mp4':
			md['mediatype'] = 'movies'
			# 'frame rate' column should be normalized into numbers manually by operator
			md['frames_per_second'] = self.assetMetadata['Frame rate']
			# 'video size' column should be split into 'Video height' and 'Video width' numbers manually by operator
			md['source_pixel_width'] = self.assetMetadata['Video height']
			md['source_pixel_height'] = self.assetMetadata['Video width'],
			# 'PFA full accession number' column should be normalized to 'urn:bampfa_accession_number:XXXX' manually by operator
			md['external-identifier'] = self.assetMetadata['PFA full accession number'],
			md['sound'] = self.assetMetadata['PFA item sound characteristics'],
			md['color'] = self.assetMetadata['Color characteristics']
		elif self.mediaType == 'mp3':
			md['mediatype'] = 'audio'

		# get rid of empty values in the md dictionary
		md = {k: v for k, v in md.items() if v not in (None,'')}
		# remove trailing "; " in any of the concatenated fields
		md = {k: (v.rsplit('; ',1)[0] if isinstance(v,str) and v.endswith('; ') else v) for k, v in md.items()}
		print("IDENTIFIER:")
		print(self.identifier)
		print("LOCAL ASSET PATHS:")
		print(self.localAssetPaths)
		print("METADATA DICT:")
		print(md)
		### COMMENTED OUT FOR TESTING
		# from the ia package documentation:
		# r = upload('<identifier>', files=['foo.txt', 'bar.mov'], metadata=md)
		# archive.org Python Library, 'uploading': https://archive.org/services/docs/api/internetarchive/quickstart.html#uploading
		result = False
		uploaded = "Didn't get to upload"
		try:
			r = upload(self.identifier, files=self.localAssetPaths, metadata=md)
			if r[0].status_code == 200:
				uploaded = "Uploaded"
				result = True
		except Exception as e:
			print(e)
			uploaded = "Upload failed"
		print(uploaded)
		return result

	def get_core_metadata(self,assetMetadata):
		'''
		Try to get: Creator, Title, Date, Subject, Identifier
		These values are all potentially in multiple columns,
		so we need to sort through the possible fields.
		'''
		# CREATOR
		directors = assetMetadata['Directors / Filmmakers']
		speakers = assetMetadata['Speaker/Interviewee']
		_creator = assetMetadata['Creator']

		self.creator = ''.join([x+"; " for x in (directors,speakers,_creator) if not x in (None,"")])
		self.creator = self.creator.replace("|"," ; ")
		self.creator = [x.strip() for x in self.creator.split(";")]
		self.creator = [x for x in self.creator if not x in ('',None)]

		# TITLE
		mainTitle = assetMetadata['Title']
		altTitle = assetMetadata['Alternative Title']
		eventTitle = assetMetadata['Event title']
		eventSeries = assetMetadata['Event series']
		pfaFilmSeries = assetMetadata['PFA film series']

		self.title = ''.join([str(x)+"; " for x in (mainTitle,altTitle,eventTitle,eventSeries,pfaFilmSeries) if not x in (None,"")])

		# DATE
		release = assetMetadata['Release Date']
		recordingDate = assetMetadata['Date of recording']
		eventYear = assetMetadata['Event year']
		_date = assetMetadata['Date']

		if release not in (None,""):
			self.date = release
		elif recordingDate not in (None,""):
			self.date = recordingDate
		elif eventYear not in (None,""):
			self.date = eventYear
		elif _date not in (None,""):
			self.date = _date

		# SUBJECT
		titleSubjects = assetMetadata["Subject(s): Film title(s)"].replace("|","; ")
		topics = assetMetadata["Subject(s): Topics(s)"]
		nameTopics = assetMetadata["Subject(s): Names"]

		self.subject = ''.join([str(x)+"; " for x in (titleSubjects,topics,nameTopics) if not x in (None,"")])

		# IDENTIFIER
		try:
			if not assetMetadata['Source canonical" name"'] in [None,'']:
				self.identifier = assetMetadata['Source canonical" name"']
			else:
				self.identifier = os.path.splitext(self.assetMetadata['Access copy filename'])[0]
		except:
			self.identifier = self.assetMetadata['Access copy filename']

def parse_resourcespace_csv(csvPath,_user, mediaType):
	'''
	1. Interpret metadata CSV as a 'key:value' dictionary, using the first row
		as the 'key', using DictReader
	2. Assign the correct CSV row of metadata 'values' to the current asset
	3. Post asset with metadata to archive.org (using post_to_ia, defined above)
	'''
	failed_to_redo = []
	tempCSVpath = "{}_tempCSV{}".format(
		os.path.splitext(csvPath)[0],
		os.path.splitext(csvPath)[1])
	with open(csvPath) as _file:
		records = csv.DictReader(_file)
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
			result = currentAsset.post_to_ia()
			if result:
				del currentAsset
			else:
				failed_to_redo.append(row)

	if len(failed_to_redo) > 0:
		with open(tempCSVpath,'w') as f:
			writer = csv.DictWriter(f,failed_to_redo[0].keys())
			writer.writeheader()
			for record in failed_to_redo:
				print("FAILED TO UPLOAD TO ARCHIVE.ORG:")
				print(record['Resource ID(s)'])
				writer.writerow(record)
		os.remove(csvPath)
		csvPath = tempCSVpath.replace("_tempCSV",'')
		result = csvPath
	else:
		result = False

	return result

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
	mediaType = input("You want audio or video? "
		"Type 'a' for audio or 'v' for video: ")
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
	result = parse_resourcespace_csv(csvPath,_user,mediaType)
	if result != False:
		# i.e., if a csv of records to redo gets returned
		redo = input("Some records failed to load. If you want to redo, "
			"type 'r' and enter, otherwise just hit enter and I will quit.")
		if redo == 'r':
			parse_resourcespace_csv(result,_user,mediaType)
		else:
			print("BYE!")

if __name__ == "__main__":
	main()
