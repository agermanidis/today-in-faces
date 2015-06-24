import datetime
import math
import os
import sys
import tempfile
import urllib2
import uuid
from operator import itemgetter
from urlparse import urlparse

import boto
import bs4
import cv2
import requests
from PIL import Image

from db import db

S3_URL = "http://{bucket}.s3.amazonaws.com/{key}"

ARTICLE_TITLE_SELECTOR = ".esc-lead-article-title-wrapper h2 a"

CASCADE_PATH_FACE = 'haarcascade_frontalface_default.xml'
GOOGLE_NEWS_TOPICS = ['n', 'w', 'b', 'tc', 'e', 's', 'snc', 'm', 'ir']
GOOGLE_NEWS_URL = 'https://news.google.com/news/section'

USER_AGENT = "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36"

face_classifier = cv2.CascadeClassifier(CASCADE_PATH_FACE)

s3_conn = boto.connect_s3(os.environ['AWS_ACCESS_KEY'], os.environ['AWS_SECRET_KEY'])
bucket = s3_conn.get_bucket("todayinfaces")

def build_url(url):
    if url.startswith("http"): return url
    if url.startswith("//"): return "http:" + url
    return "http://" + url

def upload_file(local_filename):
    k = bucket.new_key(os.path.basename(local_filename))
    k.set_contents_from_filename(local_filename)
    k.make_public()
    return S3_URL.format(bucket=bucket.name, key=k.key)

def get_image_url(url):
    resp = requests.get(url, headers={'User-Agent': USER_AGENT})
    soup = bs4.BeautifulSoup(resp.content)
    els = soup.findAll(attrs={'property': 'og:image'})
    try:
        return els[0].attrs['content']
    except:
        return None

def get_article_urls():
    urls = []
    for topic in TOPICS:
        resp = requests.get(GOOGLE_NEWS_URL, params={'topic': topic}, headers={'User-Agent': USER_AGENT})
        soup = bs4.BeautifulSoup(resp.content)
        els = soup.select(ARTICLE_TITLE_SELECTOR)
        urls += map(lambda el: build_url(el.attrs['href']), els)
    return urls

def download(url):
    _, ext = os.path.splitext(urlparse(url).path)
    tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
    resp = requests.get(url, headers={'User-Agent': USER_AGENT})
    tmp.write(resp.content)
    return tmp.name

def get_faces(im):
    grayscale = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    return face_classifier.detectMultiScale(grayscale, 1.3, 5)

def crop_faces(filename, size = (200, 200)):
    im = cv2.imread(filename)
    faces = get_faces(im)
    ret = []
    for face_rect in faces:
        x, y, w, h = face_rect
        cropped = im[y:y+h, x:x+w]
        resized = cv2.resize(cropped, size)
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        cv2.imwrite(tmp.name, resized)
        ret.append(tmp.name)
    return ret

def main():
    article_urls = get_article_urls()
    for url in article_urls:
        doc = {'url': url, 't': datetime.datetime.now(), 'faces': []}
        image_url = get_image_url(url)
        if not image_url: continue
        filename = download(build_url(image_url))
        for face_filename in crop_faces(filename):
            face_url = upload_file(face_filename)
            doc['faces'].append(face_url)
            os.remove(face_filename)
        db.articles.insert(doc)
        os.remove(filename)
    return 0

if __name__ == '__main__':
    sys.exit(main())
