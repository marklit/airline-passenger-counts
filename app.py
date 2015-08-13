#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
"""
Commercial Airline Passenger Numbers Tool

Usage:
    ./app.py get_wikipedia_content <output_file>
    ./app.py pluck_airport_meta_data <input_file> <output_file> [--start=<line>]
    ./app.py test
    ./app.py (-h | --help)

Options:
    -h, --help      Show this screen and exit.
    --start=<line>  Line number to start from (1 is the first line) [Default: 1]
"""
import bz2
import codecs
from collections import Counter
from glob import glob
from hashlib import sha1
from itertools import chain
import json
import os
import re
import sys
import tempfile
from urllib import quote

from bs4 import BeautifulSoup
from creole import Parser
from creole.html_emitter import HtmlEmitter
from docopt import docopt
from LatLon import string2latlon
from lxml import etree
import ratelim
import redis
import requests
import sh
from sh import pandoc
from unidecode import unidecode


"""
Web scraping methods
"""
@ratelim.greedy(3, 10) # 3 calls / 10 seconds
def get_wikipedia_page_from_internet(url_suffix):
    url = 'https://en.wikipedia.org%s' % url_suffix
    resp = requests.get(url)
    assert resp.status_code == 200, (resp, url)
    return resp.content


def get_wikipedia_page(url_suffix):
    redis_con = redis.StrictRedis()
    redis_key = 'wikipedia_%s' % sha1(url_suffix).hexdigest()[:6]
    resp = redis_con.get(redis_key)

    if resp is not None:
        return resp

    html = get_wikipedia_page_from_internet(url_suffix)
    redis_con.set(redis_key, html)
    
    return html


"""
Markdown-related methods
"""
def markdown_to_html_pandocs(text):
    """
    This works well on some South American airports
    """
    output_file = tempfile.NamedTemporaryFile(delete=False)
    file_name = output_file.name
    output_file.close()

    with codecs.open(file_name, 'w+b', encoding='utf-8') as write_file:
        write_file.write(text)

    html = str(pandoc('-f',
                      'markdown_phpextra',
                      '-t',
                      'html',
                      output_file.name))
    os.unlink(file_name)

    return html


def slugify(val):
    return quote(unidecode(val.replace(' ', '_')))


class WikiLinkHtmlEmitter(HtmlEmitter):
    
    def link_emit(self, node):
        target = node.content

        if node.children:
            inside = self.emit_children(node)
        else:
            inside = self.html_escape(target)

        m = self.link_rules.addr_re.match(target)

        if m:
            if m.group('extern_addr'):
                return u'<a href="%s">%s</a>' % (self.attr_escape(target),
                                                 inside)
            elif m.group('inter_wiki'):
                return u'<a href="%s">%s</a>' % (slugify(target), inside)

        if re.match(r'^\S+@\S+$', target):
            target = 'mailto:%s' % target
            return u'<a href="%s">%s</a>' % (
                self.attr_escape(target), inside)

        target = '/wiki/' + slugify(target)

        classes = ''

        return u'<a href="%s" class="%s">%s</a>' % (
            self.attr_escape(target), classes, inside)

    def image_emit(self, node):
        target = node.content
        text = self.get_text(node)
        m = self.link_rules.addr_re.match(target)
        if m:
            if m.group('extern_addr'):
                return u'<img src="%s" alt="%s">' % (
                    self.attr_escape(target), self.attr_escape(text))
            elif m.group('inter_wiki'):
                return '' # No need for images
        return u'<img src="%s" alt="%s">' % (
            self.attr_escape(target), self.attr_escape(text))

    def table_emit(self, node):
        return u'''
        <table class="wikitable sortable">
            \n%s
        </table>\n''' % self.emit_children(node)


"""
Property plucking methods
"""
def parse_property(soup, prop_name):
    prop_name = prop_name.lower()
    props = [td.text.split('=')[1].strip()
             for td in soup.find_all('td')
             if '%s=' % prop_name in td.text.lower().replace(' ', '') and
                len(td.text.split('=')) == 2]
    return props[0] if any(props) else None


def get_airport_meta_data(soup):
    """
    This works well for many Asia and some European airports.
    """
    props = {}

    for prop in ('name', 'IATA', 'ICAO', 
                 'latd', 'latm', 'lats', 'latNS', 
                 'longd', 'longm', 'longs', 'longEW',):
        props[prop] = parse_property(soup, prop)

    return props


def get_href(cell):
    cells = [cell
             for cell in cell.find_all('a')
             if 'Airport' in cell.get('href', '')]
    return cells[0].get('href') if len(cells) else None


def is_parseable_number(value):
    try:
        _ = float(re.sub('[^0-9\.]*', '', value))
        return True
    except:
        return False


def is_possible_number(value):
    if type(value) not in (str, unicode):
        return False

    value = value.strip()

    if len(re.sub('[0-9\.\,\ ]*', '', value)):
        return False

    return is_parseable_number(value)


def pluck_passenger_numbers(soup):
    """
    This works well for many Asia and some European airports.

    Pluck all table cells into a grid. Pair links with their linking values.
    """
    rows = [[(cell.text, get_href(cell))
             for cell in tr.find_all(['th', 'td'])]
            for tr in soup.find_all('tr')
            if len(tr.find_all('td'))]

    passenger_numbers = {}

    for row in rows:
        found_airport = any([True
                             for cell in row
                             if cell[1] is not None and
                                '/wiki/' in cell[1] and 
                                'Airport' in cell[1]])
        found_amount = any([True
                            for cell in row
                            if is_possible_number(cell[0]) and 
                               # 2020 so that years aren't mistaken for
                               # passenger numbers
                               float(re.sub('[^0-9\.]*', '', cell[0])) > 2020])

        if found_airport and found_amount:
            airport = [cell[1]
                       for cell in row
                       if cell[1] is not None and
                          '/wiki/' in cell[1] and 
                          'Airport' in cell[1]][0]
            amount = [float(re.sub('[^0-9\.]*', '', cell[0]))
                                for cell in row
                                if is_possible_number(cell[0]) and 
                                   float(re.sub('[^0-9\.]*',
                                                '', 
                                                cell[0])) > 1000][0]
            passenger_numbers[airport] = long(amount)

    return passenger_numbers


def get_airport_meta_data2(soup):
    """
    This works well on some South American airports
    """
    pairs = [pair
             for pair in chain(*[line.split('|')
                                 for line in 
                                    str(soup).split('}}')[0].split('\n')
                                 if '|' in line])
             if '=' in pair and len(pair.split('=')) == 2]

    _props = {}

    for pair in pairs:
        key, val = pair.split('=')
        key, val = key.strip().lower(), val.strip()
        _props[key] = val

    props = {}

    for prop in ('name', 'IATA', 'ICAO', 
                 'lat_deg', 'lat_min', 'lat_sec', 'lat_dir', 
                 'lon_deg', 'lon_min', 'lon_sec', 'lon_dir'):

        prop = prop.lower()
        if prop in _props:
            props[prop] = _props[prop]

    # Rename properties to match other meta data plucker
    renaming = [('iata', 'IATA'), 
                ('icao', 'ICAO'), 
                ('lat_deg', 'latNS'), 
                ('lat_dir', 'latd'), 
                ('lat_min', 'latm'), 
                ('lat_sec', 'lats'), 
                ('lon_dir', 'longEW'), 
                ('lon_deg', 'longd'), 
                ('lon_min', 'longm'), 
                ('lon_sec', 'longs'),]

    for old_key, new_key in renaming:
        if old_key not in props:
            continue

        props[new_key] = props[old_key]
        props.pop(old_key)

    return props


def get_lat_long(airport_metrics):
    required_keys = ('latd', 'latm', 'lats', 'latNS', 
                     'longd', 'longm', 'longs', 'longEW')

    for key in required_keys:
        if key not in airport_metrics or airport_metrics[key] is None:
            return None

    try:
        return string2latlon('%s %s %s %s' % (airport_metrics['latd'],
                                              airport_metrics['latm'],
                                              airport_metrics['lats'],
                                              airport_metrics['latNS']),
                             '%s %s %s %s' % (airport_metrics['longd'],
                                              airport_metrics['longm'],
                                              airport_metrics['longs'],
                                              airport_metrics['longEW']),
                             'd% %m% %S% %H')
    except ValueError:
        return None


def pluck_airport_meta_data(in_file, out_file, start_on_line=1):
    with codecs.open(in_file, 'r+b', 'utf8') as f:
        wikipedia_pages = [json.loads(line)
                           for line in f.read().strip().split('\n')]

    with codecs.open(out_file, 'a+b', 'utf8') as f:
        for index, (title, markdown) in enumerate(wikipedia_pages, start=1):
            if index < start_on_line:
                continue
            
            if index and not index % 100:
                print '%d of %d' % (index, len(wikipedia_pages))

            document = Parser(markdown).parse()

            html = WikiLinkHtmlEmitter(document).emit()

            try:
                soup = BeautifulSoup(html, "html5lib")
            except RuntimeError as exc:
                if 'maximum recursion depth exceeded' in exc.message:
                    soup = None
                else:
                    raise exc

            if soup is None:
                continue

            try:
                airport = get_airport_meta_data(soup)
            except RuntimeError as exc:
                if 'maximum recursion depth exceeded' in exc.message:
                    airport = {}
                else:
                    raise exc

            if not airport:
                continue

            # If too much meta data wasn't collected then try the alternative
            # meta data plucker. Seems to work better with South American 
            # airports.
            if len([1 for val in airport.values() if val is None]) > 6:
                try:
                    _html = markdown_to_html_pandocs(markdown)
                except (sh.ErrorReturnCode_2):
                    _html = ''

                try:
                    _soup = BeautifulSoup(_html, "html5lib")
                    airport = get_airport_meta_data2(_soup)
                except RuntimeError as exc:
                    if 'maximum recursion depth exceeded' in exc.message:
                        airport = {}
                    else:
                        raise exc

            if 'name' not in airport or not airport['name']:
                continue

            lat_long = get_lat_long(airport)

            if not lat_long:
                continue

            url_key = '/wiki/' + slugify(airport['name'])
            _airport = {
                "airport_name": airport['name'],
                "iata": airport['IATA'],
                "latitude": float(lat_long.lat),
                "longitude": float(lat_long.lon),
                'url': url_key,
            }

            try:
                passenger_numbers = pluck_passenger_numbers(soup)
            except RuntimeError as exc:
                if 'maximum recursion depth exceeded' in exc.message:
                    passenger_numbers = {}
                else:
                    raise exc

            # Try and get the real HTML from Wikipedia to see if it parses any
            # better than the markdown generated in this script
            if not passenger_numbers:
                try:
                    html = get_wikipedia_page(url_key)
                except (AssertionError, requests.exceptions.ConnectionError):
                    pass # Some pages link to 404s, just move on...
                else:
                    try:
                        soup = BeautifulSoup(html, "html5lib")
                        passenger_numbers = pluck_passenger_numbers(soup)
                    except RuntimeError as exc:
                        if 'maximum recursion depth exceeded' in exc.message:
                            passenger_numbers = {}
                        else:
                            raise exc

            if passenger_numbers:
                _airport['passengers'] = passenger_numbers

            f.write(json.dumps(_airport, sort_keys=True))
            f.write('\n')


"""
Data harvesting methods
"""
def get_parser(filename):
    ns_token        = '{http://www.mediawiki.org/xml/export-0.10/}ns'
    title_token     = '{http://www.mediawiki.org/xml/export-0.10/}title'
    revision_token  = '{http://www.mediawiki.org/xml/export-0.10/}revision'
    text_token      = '{http://www.mediawiki.org/xml/export-0.10/}text'

    with bz2.BZ2File(filename, 'r+b') as bz2_file:
        for event, element in etree.iterparse(bz2_file, events=('end',)):
            if element.tag.endswith('page'):
                namespace_tag = element.find(ns_token)

                if namespace_tag.text == '0':
                    title_tag = element.find(title_token)
                    text_tag = element.find(revision_token).find(text_token)
                    yield title_tag.text, text_tag.text

                element.clear()


def pluck_wikipedia_titles_text(pattern='enwiki-*-pages-articles*.xml-*.bz2',
                               out_file='airport_markdown.json'):
    with codecs.open(out_file, 'a+b', 'utf8') as out_file:
        for bz2_filename in sorted(glob(pattern),
                                   key=lambda a: int(
                                        a.split('articles')[1].split('.')[0]),
                                   reverse=True):
            print bz2_filename
            parser = get_parser(bz2_filename)

            for title, text in parser:
                if 'airport' in title.lower():
                    out_file.write(json.dumps([title, text],
                                              ensure_ascii=False))
                    out_file.write('\n')


"""
Application control methods
"""
def main(argv):
    """
    :param dict argv: command line arguments
    """
    opt = docopt(__doc__, argv)

    if opt['test']:
        import doctest
        doctest.testmod()
        return

    if opt['get_wikipedia_content']:
        pluck_wikipedia_titles_text(out_file=opt['<output_file>'])
        return

    if opt['pluck_airport_meta_data']:
        pluck_airport_meta_data(in_file=opt['<input_file>'],
                                out_file=opt['<output_file>'],
                                start_on_line=int(opt['--start']))
        return


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except KeyboardInterrupt:
        pass
