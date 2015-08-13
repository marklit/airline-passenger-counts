#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
"""
Commercial Airline Passenger Numbers Rendering Tool

Usage:
    ./plot.py render <stats_file> <image_file>
    ./plot.py (-h | --help)

Options:
    -h, --help   Show this screen and exit.
"""
import matplotlib as mpl


mpl.use('Agg') # This needs to be called before mpl_toolkits is imported


from docopt import docopt
from mpl_toolkits.basemap import Basemap
import numpy as np
import matplotlib.pyplot as plt

import codecs
import json
import math
import sys


def load_airports(file_name):
    """
    :param str file_name: JSON file of airport metrics and passenger statistics
    :returns: airport metrics and passenger statistics
    :rtype: list
    """
    with codecs.open(file_name, 'r+b', 'utf8') as airports_file:
        airports = [json.loads(line)
                    for line in airports_file.read().strip().split('\n')]

    return airports


def get_pairs_and_volumes(airports):
    """
    :param dict airports: airport metrics and passenger statistics
    :returns: IATA pairs lists with passenger counts and IATA lookup list
    :rtype: tuple

    A pair is two airports and the volume is the number of passengers travelling
    between these two airports over the course of the latest year reported.
    """
    wikiurls = {airport['url']: (airport['iata'],
                                 airport['latitude'],
                                 airport['longitude'])
                for airport in airports
                if airport['iata'] and len(airport['iata']) == 3}

    iatas = {airport['iata']: (airport['latitude'],
                               airport['longitude'])
             for airport in airports
             if airport['iata'] and len(airport['iata']) == 3}

    pairs = {}

    for airport in airports:
        if 'passengers' not in airport:
            continue

        for url, passenger_count in airport['passengers'].iteritems():
            if url not in wikiurls:
                continue

            pair = sorted([airport['iata'], wikiurls[url][0]])

            if not pair[0] or \
               not pair[1] or \
               len(pair[0]) != 3 or \
               len(pair[1]) != 3:
                continue

            pairs['%s-%s' % (pair[0], pair[1])] = passenger_count

    return pairs, iatas


def prepare_graphing_data(pairs, iatas):
    """
    Build a list of flight path lines with a line width and colour 
    representative of the number of passengers travelling on that route in the
    latest year reported on.

    :param list pairs: passenger counts for various flight routes.
    :param list iatas: IATA lookup list

    :returns: list of flight path lines
    :rtype: list
    """
    routes = []

    display_params = (
        # color   alpha  width threshold
        ('#e5cccf', 0.3, 0.2, 0),
        ('#f7c4b1', 0.4, 0.3, 250000),
        ('#ed8d75', 0.5, 0.4, 500000),
        ('#ef684b', 0.6, 0.6, 1000000),
        ('#e93a27', 0.7, 0.8, 2000000),
    )

    for iata_pair, passenger_count in pairs.iteritems():
        colour, alpha, linewidth, _ = display_params[0]

        for _colour, _alpha, _linewidth, _threshold in display_params:
            if _threshold > passenger_count:
                break

            colour, alpha, linewidth = _colour, _alpha, _linewidth

        iata1, iata2 = iata_pair.split('-')

        routes.append((colour, 
                       alpha,
                       linewidth,
                       iatas[iata1][0],
                       iatas[iata1][1],
                       iatas[iata2][0],
                       iatas[iata2][1]))

    return routes


def save_map(routes, file_name):
    """
    Render flight routes to an image file.

    :param list routes: flight path lines
    :param str file_name: image output file name
    """
    fig = plt.figure(figsize=(7.195, 3.841), dpi=100)
    m = Basemap(projection='cyl', lon_0=0, resolution='c')
    ax = plt.Axes(fig, [0., 0., 1., 1.])
    ax.set_axis_off()
    fig.add_axes(ax)

    for (colour, alpha, linewidth, lat1, long1, lat2, long2) in sorted(routes):
        """
        Cannot handle situations in which the great circle intersects the 
        edge of the map projection domain, and then re-enters the domain.

        Fix from: http://stackoverflow.com/questions/13888566/
        """
        line, = m.drawgreatcircle(long1, lat1, long2, lat2,
                                  linewidth=linewidth,
                                  color=colour,
                                  alpha=alpha,
                                  solid_capstyle='round')

        p = line.get_path()

        # Find the index which crosses the dateline (the delta is large)
        cut_point = np.where(np.abs(np.diff(p.vertices[:, 0])) > 200)[0]

        if cut_point:
            cut_point = cut_point[0]

            # Create new vertices with a nan in between and set 
            # those as the path's vertices
            new_verts = np.concatenate([p.vertices[:cut_point, :], 
                                        [[np.nan, np.nan]], 
                                        p.vertices[cut_point+1:, :]])
            p.codes = None
            p.vertices = new_verts

    m.warpimage(image="earth_lights_lrg.jpg")
    plt.savefig(file_name, dpi=1000)


"""
Application control methods
"""
def main(argv):
    """
    :param dict argv: command line arguments
    """
    opt = docopt(__doc__, argv)

    if opt['render']:
        airports = load_airports(opt['<stats_file>'])
        pairs, iatas = get_pairs_and_volumes(airports)
        routes = prepare_graphing_data(pairs, iatas)
        save_map(routes, opt['<image_file>'])


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except KeyboardInterrupt:
        pass
