# ResourceSpace 2 Internet Archive 

This script (potentially to be added to...) will take files from a locally-hosted instance of [ResourceSpace](https://www.resourcespace.com/) and publish them to [archive.org](https://archive.org). It will include a subset of metadata collected from RS, along with any [alternative files](https://www.resourcespace.com/knowledge-base/user/alternative-files) associated with the item in RS. In our initial use case, this means a video file transferred from 1/2" open reel video will also include JPG images of the container captured by our vendor, and also any technical/administrative metadata  textfiles that get stored in RS alongside the video (e.g., vendor-supplied transfer notes).

Currently it is designed around a specific collection of video materials, but it will also be used for a large collection of audio material as well. ResourceSpace can also handle lots of other file types so presumably it could be amended to suit any sort of media.

## Usage

This is now designed to run from the server hosting the RS instance. 

First, you should create a [collection](https://www.resourcespace.com/knowledge-base/collections-public-and-themes) in ResourceSpace that contains the batch of items you wish to publish. Download a metadata CSV to your local computer, then either copy it to the RS hosting server, or add it to Google Drive and set the sharing permissions to "Anyone with the link can edit." This creates the correct URL syntax for the script to parse.

From Terminal, SSH into the RS server and run `python3 /path/to/rs2ia.py`. You will be promted for a valid **RS username**, a corresponding **RS API key**, and either the **local path on the server to the metadata csv** or the **link to the csv in Google Drive**, with the appropriate permissions set. 

If all goes well, you should see your items on archive.org in a few minutes!

## Dependencies

* Locally hosted ResourceSpace on a server with SSH access
* Archive.org account
* Google account (optional?)

* python3
* [internetarchive](https://archive.org/services/docs/api/internetarchive/) python library (`pip3 install internetarchive`)
* requests (`pip3 install requests`)
* google_drive_downloader (`pip3 install googledrivedownloader`)

## Setup

Install the dependencies above.

Run `ia configure` to set up the credentials for connecting to archive.org. You will be prompted for the email and password for an account that will be publishing to your desired IA collection.

`git clone` this repo to a convenient place on the RS server. 

You should be good to go!

## Current assumptions and unknowns

Currently there are a lot of hard-coded assumptions about the media type expected (video) and the default collection on IA that we'll be loading to ("stream_only", which disables download). 

It's not 100% clear yet how to add things to multiple collections. Gotta ask for some advice there.
