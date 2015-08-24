#!/usr/bin/env python3

import bs4
import os
import requests
import sys
from glob import glob
from urllib.parse import parse_qs as parse_qs


requests.Response.document = lambda self: bs4.BeautifulSoup(self.content)


def solve_link(base, relative):
    if relative.startswith('http://') or relative.startswith('https://'):
        return relative

    protocol, url = base.split('//', 1)
    domain, path = url.split('/', 1)

    if relative.startswith('/'):
        return '%s//%s%s' % (protocol, domain, relative)
    else:
        path = path.split('/')
        base_path = path[:-1]
        return '%s//%s/%s' % (protocol, domain, '/'.join(base_path) + relative)


def basename(url):
    return url.split('/')[-1].split('?', 1)[0]


def extract_series_episode(url):
    q = parse_qs(url.split('?', 1)[1])
    keys = [ 'title_no', 'episode_no' ]
    return tuple( int(q[key][0]) for key in keys )


def grab_images(url):
    doc = requests.get(url).document()

    for img in doc.select('#_imageList img._images'):
        yield img['data-url']


def index(start_url):
    url = start_url

    while True:
        doc = requests.get(url).document()

        subjects = doc.select('.detail_lst a .subj')
        links = ( next(subj.parents) for subj in subjects )
        for link in links:
            yield solve_link(url, link['href'])

        orig_links = [ a['href'] for a in doc.select('.paginate a') ]
        try:
            i = orig_links.index('#')
            url = solve_link(url, orig_links[i + 1])
        except IndexError:
            break
        except ValueError:
            print('ValueError')
            break


def download(url):
    for page_url in index(url):
        series, episode = extract_series_episode(page_url)
        name_prefix = '%.4d_%.4d' % (series, episode)

        if glob('downloads/%s*' % name_prefix):  # skip existed file
            continue

        session = requests.Session()
        session.headers['Referer'] = url

        for i, img_url in enumerate(grab_images(page_url)):
            filename = '%s_%.2d_%s' % (name_prefix, i, basename(img_url))
            response = session.get(img_url)
            with open('downloads/%s' % filename, 'wb') as fo:
                fo.write(response.content)
            print('Downloaded: %s' % filename)


if __name__ == '__main__':
    if len(sys.argv) < 2 or '-h' in sys.argv or '--help' in sys.argv:
        print('Usage: %s webtoon-url ...' % sys.argv[0])
        exit(1)

    os.makedirs('downloads', 0o755, True)

    for url in sys.argv[1:]:
        download(url)
