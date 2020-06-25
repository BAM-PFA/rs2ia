# ResourceSpace 2 Internet Archive

This script (potentially to be added to...) will take files from a locally-hosted instance of [ResourceSpace](https://www.resourcespace.com/) and publish them to [archive.org](https://archive.org). It will include a subset of metadata collected from RS, along with any [alternative files](https://www.resourcespace.com/knowledge-base/user/alternative-files) associated with the item in RS. In our initial use case, this means a video file transferred from 1/2" open reel video will also include JPG images of the container captured by our vendor, and also any technical/administrative metadata  textfiles that get stored in RS alongside the video (e.g., vendor-supplied transfer notes).

Currently it is designed around a specific collection of video materials, but it will also be used for a large collection of audio material as well. ResourceSpace can also handle lots of other file types so presumably it could be amended to suit any sort of media.

## Usage

This is now designed to run from the server hosting the RS instance. 

You might (probably!) need to run the script using `sudo` to take into account ResourceSpace privileges under `/var/www/...`

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

Run `ia configure` to set up the credentials for connecting to archive.org. You will be prompted for the email and password for an account that will be publishing to your desired IA collection. The utility will automatically generate a config file for you. 

`git clone` this repo to a convenient place on the RS server.

You should be good to go!

## Requirements for the metadata CSV

The metadata CSV requires some finicky manual processing before it's usable. Following the steps below should get you there.

Creating and downloading the spreadsheet:
  1. Add the objects you want to work with to a "collection" on ResourceSpace.
  2. In the dark "My collections" menu (at the bottom of the screen), select your collection in "Current collection:" (the leftmost drop-down bar). In "Actions" (the rightmost drop-down bar), select "Advanced -> CSV export - metadata."
  3. On the "CSV export - metadata" page, check "Include data from all accessible fields." Click Download.


Normalizing the spreadsheet:

**IMPORTANT:** When you open the CSV (ideally in Open Office or Libre Office not Excel!), you'll want to mark any columns containing leading zeros in numbers as "text" as opposed to "number" or any default, otherwise you will lose the leading zeros when you open the file.

In the downloaded CSV, combine or split up the following fields:
  * Combine the columns 'Notes,' 'Description,' 'Credits,' 'QC Notes' into a single column 'Notes' (=CONCATENATE(AD2;" ; ";V2, etc. ))
  * Combine the columns 'Medium of original,' 'Dimensions of original,' 'Original video standard,' 'Generation' columns into a single column 'Medium of original'
  * Normalize the 'frame rate' column into numbers only (e.g., remove the word 'fps')
  * Split the 'video size' column into 'Video height' and 'Video width'; only use numbers (e.g., turn '640x480' into '640' and '480')
  * Add 'urn:bampfa_accession_number:' (no quotes) before each the accession number in the 'PFA full accession number' column


Uploading the spreadsheet (optional):  
You can point the script to the CSV's local path or to a Google Drive path. If you do the former, make sure the spreadsheet is a CSV, not any other file format (such as .xlsx). If you do the latter, follow these steps to make sure the script can access the data:
  * Upload the CSV to a central location in Google Drive (e.g., for TVTV it would be TVTV/Internet Archive/CSVs for Internet Archive).
  * In that location, right-click on your CSV and select "Share." Sharing settings should be "Anyone with the link can view." Copy the link in the box; it should start with 'https://drive.google.com/file/d/' and end with 'view?usp=sharing'. This is the version of the link that will work with the script.
  * Do not open the CSV in Google Sheets (this converts it to an unusable file format).

## Current assumptions and unknowns

Currently there are a lot of hard-coded assumptions about the media type expected (video) and the default collection on IA that we'll be loading to ("stream_only", which disables download).

It's not 100% clear yet how to add things to multiple collections. Gotta ask for some advice there.

Ideally the metadata fields would be configurable instead of hard-coded to BAMPFA's ResourceSpace setup. 
