#!/usr/bin/env python3

from flask import Flask, send_file, abort
app = Flask(__name__)

import csv
import os
import re
import shutil
import requests
from lxml.etree import fromstring, XMLSyntaxError, XMLParser
from cssselect import GenericTranslator


class NotFound(Exception):
    pass


class MetadataReader:
    csv_name = "posters/posters.csv"
    delimiter = "|"

    def __init__(self):
        if not os.path.isfile(self.csv_name):
            with open(self.csv_name, 'w') as fl:
                fl.write("")

    def save_poster_meta(self, movie_name, movie_year, poster_path):
        with open(self.csv_name, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=self.delimiter)
            writer.writerow([movie_name, str(movie_year), poster_path])

    def read_poster_meta(self, movie_name, movie_year):
        with open(self.csv_name, newline='') as csvfile:
            reader = csv.reader(csvfile, delimiter=self.delimiter)
            for row in reader:
                if row[0] == movie_name and row[1] == str(movie_year):
                    print("Poster found in DB.")
                    return row
        return False


class WikipediaGrabber:
    def __init__(self, movie_name, movie_year):
        self.movie_name = movie_name.lower()
        self.movie_year = movie_year
        self.search_string = " ".join([movie_name, str(movie_year)])

        self.mr = MetadataReader()
    
    def grab(self):
        meta = self.mr.read_poster_meta(self.movie_name, self.movie_year)
        if meta:
            return meta[2]

        try:
            # Search wiki
            search_url = self.search_page()
            # Parse movie page
            poster_url = self.movie_page(search_url)
            # Save poster
            poster_path = self.download_poster(poster_url)
        except NotFound as err:
            print(err)
            return False

        self.mr.save_poster_meta(self.movie_name, self.movie_year, poster_path)
        return poster_path

    def search_page(self):
        wiki_url = "https://en.wikipedia.org"
        search_param = "+".join(self.search_string.split(" "))
        url = f"{wiki_url}/w/index.php?search={search_param}&title=Special%3ASearch&go=Go"
        out = requests.get(url)

        if "index.php?search" not in out.url:
            # If we guessed page name
            return out.url
        # text = "".join(re.split('<head>.*</head>', out.text,
        #                flags=re.IGNORECASE | re.DOTALL))

        parser = XMLParser(recover=True)
        document = fromstring(out.text, parser=parser)

        expression = GenericTranslator().css_to_xpath('.mw-search-result')
        all_results = document.xpath(expression)
        if not all_results:
            raise NotFound(url)
        first_result = all_results[0]

        link_selector = GenericTranslator().css_to_xpath('a')
        first_link = first_result.xpath(link_selector)[0]

        first_result_url = f"{wiki_url}{first_link.get('href')}"

        return first_result_url

    def movie_page(self, url):
        out = requests.get(url)
        document = fromstring(out.text)
        expression = GenericTranslator().css_to_xpath('.thumbborder')
        all_results = document.xpath(expression)
        if not all_results:
            raise NotFound(url)
        first_result = all_results[0]
        url = first_result.get("src")
        if url.startswith("//"):
            url = "https:" + url
        return url

    def download_poster(self, poster_url):
        poster_ext = poster_url.split(".")[-1]
        poster_name = "_".join([self.movie_name, str(self.movie_year)])
        poster_full_name = ".".join([poster_name, poster_ext])
        poster_path = "/".join(["posters", str(self.movie_year), poster_full_name])

        dir_path = "/".join(["posters", str(self.movie_year)])
        if not os.path.isdir(dir_path):
            os.mkdir(dir_path)

        r = requests.get(poster_url, stream=True)
        if r.status_code == 200:
            with open(poster_path, 'wb') as f:
                shutil.copyfileobj(r.raw, f)
        return poster_path


@app.route('/<string:movie>/<int:year>')
def api(movie, year):
    poster = WikipediaGrabber(movie, year).grab()
    if poster:
        return send_file(poster)
    else:
        return abort(404)
