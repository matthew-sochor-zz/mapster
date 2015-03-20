# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>
# just adding a stupid thing here
# <codecell>
# second thing test

import numpy as np
from math import log, exp, tan, atan, pi, ceil, radians, sin, cos, atan2, sqrt

EARTH_RADIUS = 6378137
EQUATOR_CIRCUMFERENCE = 2 * pi * EARTH_RADIUS
ORIGIN_SHIFT = EQUATOR_CIRCUMFERENCE / 2.0
google_res = 512

# comment down here

def great_circle_distance(latlng_a, latlng_b):

    lat1, lng1 = latlng_a
    lat2, lng2 = latlng_b
     
    dLat = radians(lat2 - lat1)
    dLng = radians(lng2 - lng1)
    a = (sin(dLat / 2) * sin(dLat / 2) +
    cos(radians(lat1)) * cos(radians(lat2)) *
    sin(dLng / 2) * sin(dLng / 2))
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    d = EARTH_RADIUS * c
    return d 

def latlngtopixels(lat, lng, zoom):
    mx = (lng * ORIGIN_SHIFT) / 180.0
    my = log(tan((90.0 + lat) * pi/360.0))/(pi/180.0)
    my = (my * ORIGIN_SHIFT) /180.0
    res = EQUATOR_CIRCUMFERENCE/google_res*2/(2.0**zoom)
    px = (mx + ORIGIN_SHIFT)/res
    py = (my + ORIGIN_SHIFT)/res
    return px, py

def pixelstolatlng(px, py, zoom):
    res = EQUATOR_CIRCUMFERENCE/google_res*2/(2**zoom)
    mx = px * res - ORIGIN_SHIFT
    my = py * res - ORIGIN_SHIFT
    lat = (my / ORIGIN_SHIFT) * 180.0
    lat = 180.0 / pi * (2.0*atan(exp(lat*pi/180.0)) - pi/2.0)
    lng = (mx / ORIGIN_SHIFT) * 180.0
    return lat, lng

def pixelstolat(py, zoom):
    res = EQUATOR_CIRCUMFERENCE/google_res*2/(2**zoom)
    my = py * res - ORIGIN_SHIFT
    lat = (my / ORIGIN_SHIFT) * 180.0
    lat = 180 / pi * (2*atan(exp(lat*pi/180.0)) - pi/2.0)
    return lat

def pixelstolng(px, zoom):
    res = EQUATOR_CIRCUMFERENCE/google_res*2/(2**zoom)
    mx = px * res - ORIGIN_SHIFT
    lng = (mx / ORIGIN_SHIFT) * 180.0
    return lng

