#!/usr/bin/env python3

# Arun Debray
# 13 October 2019

# I prefer to cite arXiv articles with a slightly different style than the default available on arXiv.
# This program takes an arXiv identifier and returns its citation data, suitable for use with BibTeX.

# Caveat: as with BibTeX in general, any math in paper titles must be manually escaped. The same goes
# for capital letters in acronyms or proper nouns: many BibTeX style files will set them to lowercase
# unless escaped.

import argparse
import collections
import re
import subprocess
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

CitationData = collections.namedtuple('CitationData', ['author', 'title', 'year', 'link'])

# for parsing the command-line arguments
parser = argparse.ArgumentParser(
	prog='cite_ariv_article.py',
	usage = '\033[32m./cite_arxiv_article.py\033[0m \033[33m<article identifier>\033[0m, e.g.\n       \033[32m./cite_arxiv_article.py\033[0m \033[33m1312.7188\033[0m',
	epilog = 'For older articles where the full URL includes the subfield,\ninclude the subfield as follows:\nhttps://arxiv.org/abs/hep-th/0605198 -> \033[32m./cite_arxiv_article.py\033[0m \033[33mhep-th/0605198\033[0m'
)
parser.add_argument('--SPIRES', help='flag for SPIRES citation style', action='store_true')
parser.add_argument('--copy', help='copies the output to the clipboard', action='store_true')
parser.add_argument('identifier', help='arXiv article identifier', action='store', nargs=1)

# copies the string xs to the clipboard
# NOTE: this works on ubuntu and probably doesn't work on other systems
# if you are using this program and need this functionality on a non-Ubuntu system,
# please write to me
def copy_to_clipboard(xs: str):
	copier = subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=subprocess.PIPE)
	copier.communicate(bytes(xs, encoding='utf8')) # NOTE: will this cause problems with Unicode?

# builds the URL which makes the API request
def make_url(identifier: str) -> str:
	return 'http://export.arxiv.org/api/query?id_list=%s' % identifier

# makes the request, returns the response
def get_data_from_arXiv(url: str) -> str:
	try:
		return urllib.request.urlopen(url).read()
	except urllib.error.URLError:
		print('Error: something went wrong when using the arXiv API.', file=sys.stderr)
		print('URL: %s' % url, file=sys.stderr)
		exit(-1)

# Goal: replace http://arxiv.org/abs/1312.7188v2 with https://arxiv.org/abs/1312.7188
# First, if there's a second 'v' in the string, remove it and everything following
# Then, change 'http' to 'https'
def fix_abstract_url(url: str) -> str:
	if url.count('v') > 1:
		url = url[:url.rfind('v')]
	url = url.replace('http', 'https')
	return url

# returns a namedtuple with the following fields:
#	- author (if multiple authors, includes all of them)
#	- title
#	- year
#	- link (to abstract)
def parse_response(response: str) -> CitationData:
	xmlstring = response.decode('utf-8')
	xmlstring = re.sub(' xmlns="[^"]+"', '', xmlstring, count=1) # namespaces begone
	root = ET.fromstring(xmlstring).find('entry')

	# get authors, separated by ' and '
	author = ' and '.join(map(lambda a: a.find('name').text, root.findall('author')))
	# get title
	title = root.find('title').text
	# get year
	year = root.find('published').text[:4]
	# get link
	article_links = list(filter(lambda x: x.get('type') == 'text/html', root.findall('link')))
	if len(article_links) != 1:
		raise ValueError('Something weird happened: %d PDF links' % len(article_links))
	link = fix_abstract_url(article_links[0].get('href'))
	
	return CitationData(author, title, year, link)

# produce the tag (e.g. KT90 or Wit16) for use by \ref or \cref
# since this is so context-sensitive, it won't be perfect
# (e.g. von Neumann would be N not vN)
def make_tag(cd: CitationData) -> str:
	multiple_authors = ' and ' in cd.author
	if multiple_authors:
		author_list = cd.author.split(' and ')
		# initials + year
		return ''.join(author.split()[-1][0] for author in author_list) + cd.year[-2:]
	else:
		surname = cd.author.split()[-1]
		# first 3 letters of surname + year
		return surname[:3] + cd.year[-2:]

def format_citation_data(cd: CitationData, identifier: str, spire_style: bool) -> str:
	tag = make_tag(cd)
	if spire_style:
		return ('@article{%s,\n\tauthor = {%s},\n\tyear = {%s},\n\ttitle = {%s},\n\teprint = {%s},\n\tarchivePrefix = "arXiv"\n}' % (tag, cd.author, cd.year, cd.title, identifier))
	else:
		return ('@article{%s,\n\tauthor = {%s},\n\ttitle = {%s},\n\tyear = {%s},\n\tnote = {\\url{%s}}\n}' %
			(tag, cd.author, cd.title, cd.year, cd.link))

def main():
	args = parser.parse_args()
	bibtex_output = format_citation_data(
		parse_response(
			get_data_from_arXiv(
				make_url(args.identifier[0])
			)
		), args.identifier[0], spire_style=args.SPIRES
	)
	print(bibtex_output)
	if args.copy:
		copy_to_clipboard(bibtex_output)

if __name__ == '__main__':
	main()
