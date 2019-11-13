#!/usr/bin/env python3
"""
This script (or maybe scripts eventually?) will be used to transfer
assets and metadata from our local ResourceSpace to Internet Archive.
"""
import os.path
import requests
import getpass
import subprocess
import hashlib
import csv
from internetarchive import upload

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
			command = ["ia","configure"]
			ia configure
		else:
			pass

class ResourceSpaceAPI:
	'''
	Define location of ResourceSpace assets
	and how to query the API. Largely based on
	https://github.com/pixuenan/RS-python-API/blob/master/RSAPI.py
	'''
	def __init__(self,_user=None):
		self.edithServer = "136.152.253.235"
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
		query = "user={}&function={}&{}".format(_user.rsUserName, function_to_query, parameters)
		sign = hashlib.sha256(User.rsAPIkey+query).hexdigest()
		queryURL = "http://{}/api/index.php?{}&sign={}".format(self.edithServer, query, sign)
		try:
			# get the result of API query, i.e. what is returned by the query URL
			result = queryURL
		except (IOError, UnicodeDecodeError) as err:
			print(err)
		else:
		    return result

class Asset:
	'''
	Define an asset, which could be simple (one file)
	or complex (a set of files), plus metadata
	'''
	def __init__(
		self,
		rsAssetID=None,
		localAssetPaths=[],
		assetMetadata={},
		_user=None
		):
		self.localAssetPaths = localAssetPaths
		self.assetMetadata = assetMetadata
		self.rsAssetID = self.assetMetadata['Resource ID(s)'] # this value will come from a metadata CSV file
		self.collection='TVTV', # archive.org collection will always be 'TVTV'
		self.mediatype='movies', # archive.org media type will always be 'movies'

	def get_local_asset_path(self):
		# see https://www.resourcespace.com/knowledge-base/api/get_resource_path
		self.primaryAssetPath = ResourceSpaceAPI.query("get_resource_path",self.rsAssetID,self._user)
		self.localAssetPaths = primaryAssetPath

	def get_local_alternative_asset_paths(self):
		# get filepaths for alternative files associated with the primary asset. see https://www.resourcespace.com/knowledge-base/api/get_alternative_files
		self.alternativeAssetPaths = ResourceSpaceAPI.query("get_alternative_files",self.rsAssetID,self._user)
		self.localAssetPaths += alternativeAssetPaths

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
		md = {
			'collection': self.collection,
			'mediatype': self.mediatype,
			'creator': self.assetMetadata['Directors / Filmmakers'],
			'contributor': self.assetMetadata['Resource type'],
			'identifier': self.assetMetadata['Access copy filename'],
			'title': self.assetMetadata['Title'],
			'date': self.assetMetadata['Release Date'],
			# Original columns 'Notes,' 'Alternative Title,' 'Credits' should be concatenated manually by operator
			'description': self.assetMetadata['Notes'],
			# Original columns 'Medium of original,' 'Dimensions of original,' 'Original video standard,' 'Generation' columns should be concatenated manually by operator
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
		# archive.org Python Library, 'uploading': https://archive.org/services/docs/api/internetarchive/quickstart.html#uploading
		r = upload(self.assetMetadata['Access copy filename'], files=self.localAssetPaths, metadata=md)
		# consider rewriting the below? see: https://python-forum.io/Thread-Response-200-little-help
		if r[0].status_code == 200:
			print("Uploaded")
		else:
			print("Upload failed")

def parse_resourcespace_csv(csvPath):
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
			currentAsset.get_local_asset_path()
			currentAsset.get_local_alternative_asset_paths()
			print(rsAssetID,currentAsset.localAssetPath)
			currentAsset.post_to_ia()

def define_resourcespace_csv():
	csvPath = input("drag and drop path to CSV with ResourceSpace metadata:")
	return csvPath

def main():
	_user = User()
	rsAPI = ResourceSpaceAPI(_user)
	print("Hello, "+_user.rsUserName)
	csvPath = define_resourcespace_csv()
	parse_resourcespace_csv(csvPath,_user)

if __name__ == "__main__":
	main()
