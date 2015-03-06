# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>
# just adding a stupid thing here
# <codecell>

import numpy as np
from math import log, exp, tan, atan, pi, ceil, radians, sin, cos, atan2, sqrt

EARTH_RADIUS = 6378137
EQUATOR_CIRCUMFERENCE = 2 * pi * EARTH_RADIUS
ORIGIN_SHIFT = EQUATOR_CIRCUMFERENCE / 2.0
google_res = 512

def great_circle_distance(latlong_a, latlong_b):

    lat1, lon1 = latlong_a
    lat2, lon2 = latlong_b
     
    dLat = radians(lat2 - lat1)
    dLon = radians(lon2 - lon1)
    a = (sin(dLat / 2) * sin(dLat / 2) +
    cos(radians(lat1)) * cos(radians(lat2)) *
    sin(dLon / 2) * sin(dLon / 2))
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    d = EARTH_RADIUS * c
    return d 

def latlontopixels(lat, lon, zoom):
    mx = (lon * ORIGIN_SHIFT) / 180.0
    my = log(tan((90.0 + lat) * pi/360.0))/(pi/180.0)
    my = (my * ORIGIN_SHIFT) /180.0
    res = EQUATOR_CIRCUMFERENCE/google_res*2/(2.0**zoom)
    px = (mx + ORIGIN_SHIFT)/res
    py = (my + ORIGIN_SHIFT)/res
    return px, py

def pixelstolatlon(px, py, zoom):
    res = EQUATOR_CIRCUMFERENCE/google_res*2/(2**zoom)
    mx = px * res - ORIGIN_SHIFT
    my = py * res - ORIGIN_SHIFT
    lat = (my / ORIGIN_SHIFT) * 180.0
    lat = 180.0 / pi * (2.0*atan(exp(lat*pi/180.0)) - pi/2.0)
    lon = (mx / ORIGIN_SHIFT) * 180.0
    return lat, lon

def pixelstolat(py, zoom):
    res = EQUATOR_CIRCUMFERENCE/google_res*2/(2**zoom)
    my = py * res - ORIGIN_SHIFT
    lat = (my / ORIGIN_SHIFT) * 180.0
    lat = 180 / pi * (2*atan(exp(lat*pi/180.0)) - pi/2.0)
    return lat

def pixelstolon(px, zoom):
    res = EQUATOR_CIRCUMFERENCE/google_res*2/(2**zoom)
    mx = px * res - ORIGIN_SHIFT
    lon = (mx / ORIGIN_SHIFT) * 180.0
    return lon

