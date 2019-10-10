#!/usr/bin/env python3
"""
This script (or maybe scripts eventually?) will be used to transfer
assets and metadata from our local ResourceSpace to Internet Archive.
"""
import requests
import getpass


class User:
	'''
	Define a user who will be connecting to 
	ResourceSpace and/or Internet Archive
	'''
	def __init__(self,rsUserName=None,rsAPIkey=None):
		self.define_user()

	def define_user(self):
		self.rsUserName = input("enter resourcespace user name:")
		self.rsAPIkey = input("enter your resourcespace API key:")
		self.iaUserName = input("enter archive.org user name:")
		self.iaPassword = getpass.getpass(prompt='enter your archive.org password:')

class Asset:
	'''
	Define an asset, which could be simple (one file)
	or complex (a set of files), plus metadata
	'''
	def __init__(
		self,
		localPaths=[],
		metadata={}
		):
		self.localPaths = localPath
		self.metadata = metadata

def main():
	currentUser = User()
	print("Hello, "+currentUser.rsUserName)


if __name__ == "__main__":
	main()