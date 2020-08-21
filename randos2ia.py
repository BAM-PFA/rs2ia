#!/usr/bin/env python3
"""
This script (or maybe scripts eventually?) will be used to transfer
assets and metadata from our local ResourceSpace to Internet Archive.
"""
import ast
import csv
from google_drive_downloader import GoogleDriveDownloader # from https://github.com/ndrplz/google-drive-downloader/blob/master/google_drive_downloader/google_drive_downloader.py
import hashlib
from internetarchive import upload
import io
import os
import pickle
import re
import requests
import squarify
import subprocess
import sys
import time

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseDownload


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
class Asset:
	'''
	Define an asset, which must be simple (one file), 
	plus metadata
	'''
	def __init__(
		self,
		localFilepath = None,
		mediaType = None,
		assetMetadata = {},
		):
		self.localFilepath = localFilepath
		self.squarePixelFilepath = None
		self.mediaType = mediaType
		self.assetMetadata = assetMetadata
		self.identifier = None
		self.creator = None
		self.title = None
		self.date = None
		self.subject = None
		self.description = None
		self.notes = None
		self.collection = ['stream_only','pacificfilmarchive'] # collection can be an array
		#self.license = 'https://creativecommons.org/licenses/by-nc-nd/4.0/'

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
		if self.mediaType == 'mp4':
			ia_mediatype = 'movies'
		elif self.mediaType == 'mp3':
			ia_mediatype = 'audio'

		self.get_core_metadata()

		md = {
			# LET'S THINK ABOUT HOW TO MAKE THIS SET OF MD MORE AGNOSTIC/GENERALIZABLE
			'identifier': self.identifier,
			'mediatype': ia_mediatype,
			'title': self.title,
			'collection': self.collection,
			# Original CSV columns 'Notes,' 'Digitization QC note,' etc.
			# should be concatenated manually by operator into single column 'Notes'
			# 'notes': self.assetMetadata['Notes']+"\nDigitized through a generous 2018 Recordings at Risk grant from the Council on Library and Information Resources.",
			'notes': self.assetMetadata['Notes']+"\nDigitized through a 2018 Humanities Collections and Reference Resources grant from the National Endowment for the Humanities.",
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

			# Original columns 'Medium of original,' 'Dimensions of original,' 'Original video standard,' 'Generation' columns should be concatenated manually by operator into single column 'Medium of original'
			'source': self.assetMetadata['Medium of original'],
			# 'frame rate' column should be normalized into numbers manually by operator
			'frames_per_second': self.assetMetadata['Frame rate'],
			# 'video size' column should be split into 'Video height' and 'Video width' numbers manually by operator
			'source_pixel_width': self.assetMetadata['Video height'],
			'source_pixel_height': self.assetMetadata['Video width'],
			# 'PFA full accession number' column should be normalized to 'urn:bampfa_accession_number:XXXX' manually by operator
			'external-identifier': self.assetMetadata['PFA full accession number'],
			'condition': self.assetMetadata['Original Material Condition'],
			'sound': self.assetMetadata['PFA item sound characteristics'],
			'color': self.assetMetadata['Color characteristics']
		}
		# get rid of empty values in the md dictionary
		md = {k: v for k, v in md.items() if v not in (None,'')}
		# remove trailing "; " in any of the concatenated fields
		md = {k: (v.rsplit('; ',1)[0] if isinstance(v,str) and v.endswith('; ') else v) for k, v in md.items()}
		print("IDENTIFIER:")
		print(self.identifier)
		print("LOCAL ASSET PATHS:")
		print(self.squarePixelFilepath)
		print("METADATA DICT:")
		print(md)
		
		### COMMENTED OUT FOR TESTING
		# from the ia package documentation:
		# 	r = upload('<identifier>', files=['foo.txt', 'bar.mov'], metadata=md)
		# archive.org Python Library, 'uploading': https://archive.org/services/docs/api/internetarchive/quickstart.html#uploading
		result = False
		uploaded = "Didn't get to upload"
		try:
			r = upload(self.identifier, files=self.squarePixelFilepath, metadata=md)
			if r[0].status_code == 200:
				uploaded = "Uploaded"
				result = True
		except Exception as e:
			print(e)
			uploaded = "Upload failed"
		print(uploaded)
		return result

	def get_core_metadata(self):
		'''
		Try to get: Creator, Title, Date, Subject, Identifier
		These values are all potentially in multiple columns, 
		so we need to sort through the possible fields.
		'''
		# CREATOR
		directors = self.assetMetadata['Directors / Filmmakers']
		speakers = self.assetMetadata['Speaker/Interviewee']
		_creator = self.assetMetadata['Creator']

		self.creator = ''.join([x+"; " for x in (directors,speakers,_creator) if not x in (None,"")])
		self.creator = self.creator.replace("|"," ; ")
		self.creator = [x.strip() for x in self.creator.split(";")]
		self.creator = [x for x in self.creator if not x in ('',None)]

		# TITLE
		mainTitle = self.assetMetadata['Title']
		altTitle = self.assetMetadata['Alternative Title']
		eventTitle = self.assetMetadata['Event title']
		eventSeries = self.assetMetadata['Event series']
		pfaFilmSeries = self.assetMetadata['PFA film series']

		self.title = ''.join([str(x)+"; " for x in (mainTitle,altTitle,eventTitle,eventSeries,pfaFilmSeries) if not x in (None,"")])

		# DATE
		release = self.assetMetadata['Release Date']
		recordingDate = self.assetMetadata['Date of recording']
		eventYear = self.assetMetadata['Event year']
		_date = self.assetMetadata['Date']

		if release not in (None,""):
			self.date = release
		elif recordingDate not in (None,""):
			self.date = recordingDate
		elif eventYear not in (None,""):
			self.date = eventYear
		elif _date not in (None,""):
			self.date = _date

		# SUBJECT
		titleSubjects = self.assetMetadata["Subject(s): Film title(s)"].replace("|","; ")
		topics = self.assetMetadata["Subject(s): Topics(s)"]
		nameTopics = self.assetMetadata["Subject(s): Names"]

		self.subject = ''.join([str(x)+"; " for x in (titleSubjects,topics,nameTopics) if not x in (None,"")])

		# IDENTIFIER
		try:
			if not self.assetMetadata['Source canonical" name"'] in [None,'']:
				self.identifier = self.assetMetadata['Source canonical" name"']
			else:
				self.identifier = os.path.splitext(self.assetMetadata['Access copy filename'])[0]
		except:
			self.identifier = self.assetMetadata['Access copy filename']


######
###### THIS SECTION DEALS WITH THE ACTUAL FILES FROM DRIVE
######

SCOPES = [
	'https://www.googleapis.com/auth/documents',
	'https://www.googleapis.com/auth/drive',
	"https://www.googleapis.com/auth/drive.file",
	"https://www.googleapis.com/auth/drive.metadata"
	]


def login():
	# Do some login stuff
	# Return live services for Docs and Drive APIs
	creds = None

	if os.path.exists('secrets/token.pickle'):
		with open('secrets/token.pickle', 'rb') as token:
			creds = pickle.load(token)
	# If there are no (valid) credentials available, let the user log in.
	if not creds or not creds.valid:
		if creds and creds.expired and creds.refresh_token:
			creds.refresh(Request())
		else:
			flow = InstalledAppFlow.from_client_secrets_file(
				'secrets/credentials.json', SCOPES)
			creds = flow.run_local_server(port=0)
		# Save the credentials for the next run
		with open('secrets/token.pickle', 'wb') as token:
			pickle.dump(creds, token)

	g_docs = build('docs', 'v1', credentials=creds)
	g_drive = build('drive','v3',credentials=creds)

	return g_docs, g_drive

def get_drive_file_info(folder_id,*fields):
	# *fields should be a list of fields required for whatever you're doing
	g_docs, g_drive = login()
	page_token = None

	print(fields)

	print(folder_id)
	print("* "*50)
	response_dict = {}
	# id and name will be hardcoded in query
	fields = [x for x in fields if not x in ('id','name')]

	if not fields == []:
		queryFields = 'nextPageToken, files(id, name, {})'.format(', '.join(fields))
	else:
		queryFields = 'nextPageToken, files(*)'
	while True:
		query = "'{}' in parents".format(folder_id)
		print(query)
		response = g_drive.files().list(q=query,
			spaces='drive',
			fields=queryFields,
			pageToken=page_token,
			supportsAllDrives='true',
			includeItemsFromAllDrives='true').execute()
		# print(response)

		for _file in response.get('files', []):
			file_id = _file.get('id')
			name = _file.get('name')
			response_dict[file_id] = {}
			response_dict[file_id]['name'] = name
			for field in fields:
				response_dict[file_id][field] = _file.get(field)
			

		page_token = response.get('nextPageToken', None)
		if page_token is None:
			break

	return response_dict

def get_file_from_drive(file_id,name):
	_, g_drive = login()
	temp_path = os.path.join('temp_vids',name)

	request = g_drive.files().get_media(fileId=file_id,supportsAllDrives=True)
	fh = io.FileIO(temp_path, mode='wb')
	downloader = MediaIoBaseDownload(fh, request)
	done = False

	while done is False:
		status, done = downloader.next_chunk()
		print("Download %d%%." % int(status.progress() * 100))

	if os.path.isfile(temp_path):
		return temp_path
	else:
		return False

######
###### END SECTION FOR ACTUAL FILES FROM DRIVE
######



def parse_metadata_csv(csvPath):
	metaDict = {}
	tempCSVpath = "{}_tempCSV{}".format(
		os.path.splitext(csvPath)[0],
		os.path.splitext(csvPath)[1])
	with open(csvPath) as f:
		reader = csv.DictReader(f)
		for row in reader:
			_id = row['item id'] # this is the accession number
			metaDict[_id] = {}
			for key in row.keys():
				if not key == 'item id':
					metaDict[_id][key] = row[key]


	return metaDict

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

def declare_metadata_csv():
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
	folders = sys.argv[1:]
	# four_more_years_folder = "1ieh8vZz03D-4RooY3AdJTYpMNZIrwYv6"
	# gerald_ford_folder="1KApPObPVoCa7WSZ7HbHjj1FlhLuc0jYu"
	# tv_studio_folder="1U25W5MLbx9ZkTQ5jnmilrfjQGyZj6cm8"
	# test = "1VHrkfz1WcN9vffm0nuqUeLhqovMp6J7A"
	print(folders)

	print("Hello, please gimme metadata: ")
	csvPath = declare_metadata_csv()

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

	### PARSE METADATA INTO A DICT ###
	metaDict = parse_metadata_csv(csvPath)
	failures = []
	
	for folder in folders:
		print(folder)
		print("* "*50)
		files = get_drive_file_info(folder,'id','name')
		for file_id, details in files.items():
			localFilepath = get_file_from_drive(file_id,files[file_id]['name'])
			print(localFilepath)
			if not localFilepath.endswith(mediaType):
				os.remove(localFilepath)
				continue
			currentAssetID = re.match('(.+_)(\d{5})(_.+)',localFilepath).group(2)
			for k,v in metaDict.items():
				if k == currentAssetID:
					assetMetadata = v
					v['ia_url'] = ''

			currentAsset = Asset(localFilepath,mediaType,assetMetadata)
			currentAsset.get_core_metadata()
			squarePixelFilepath = squarify.main(currentAsset.localFilepath)
			if os.path.isfile(squarePixelFilepath):
				currentAsset.squarePixelFilepath = squarePixelFilepath
			result = currentAsset.post_to_ia()
			if result != False:
				os.remove(localFilepath)
				os.remove(squarePixelFilepath)
				iaEmbed = "https://archive.org/embed/{}".format(localFilepath)
				metaDict[currentAssetID]['ia_url'] = iaEmbed
			else:
				try:
					os.remove(squarePixelFilepath)
				except:
					pass
				failures.append(localFilepath)

	if failures != []:
		print("*** THE FOLLOWING FILES DIDN'T MAKE IT TO IA FOR SOME RESON ***\n")
		for x in failures:
			print(x)
	with open('uploaded.csv','w+') as f:
		fieldnames = ['item id','ia_url','description']
		writer = csv.DictWriter(f,fieldnames=fieldnames)
		writer.writeheader()
		for k,v in metaDict.items():
			row = {"item id":k,"ia_url":v['ia_url'],"description":v['description']}
			writer.writerow(row)



if __name__ == "__main__":
	main()
