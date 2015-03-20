import numpy as np
import simplejson, urllib
import matplotlib.pyplot as plt
import pandas as pd
from os import listdir
from os.path import isfile, join   
from scipy.interpolate import griddata
from math import log, exp, tan, atan, pi, radians, sin, cos, atan2, sqrt
import yelp

# Keystone DI proj
google_api_key = ['AIzaSyDyodEhr_tYYr1SeBFQVWNDqJSpPqDK7HM']
# Keystone DI overflow
google_api_key.append('AIzaSyBy5yuqmfkA3_WtBYQtG8j5shZAvl0fbhU')
# Keystone DI overflow 2
google_api_key.append('AIzaSyCa0r5jNUVHa8E4xjRCB18HjhL_tMSTATQ')
# Keystone DI overflow 3
google_api_key.append('AIzaSyBLSXEseK7aPf6S1_bkzAKtrf5C7zio18I')
# overflow
google_api_key.append('AIzaSyCjD_r09oM9iKt1N0qAP-nohPO4yGNqsUc')

geocode_key = 0
distance_matrix_key = 0

default_map_width = 640
sampling = 25
map_zoom = 14
default_mode = 'walking'
px_delta = 25.0#float(default_map_width)/(sampling-1)

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

def lat_lng_from_address(location):
    global geocode_key
    url = "https://maps.googleapis.com/maps/api/geocode/json?address="+location.replace(' ', '+')+"&key="+google_api_key[geocode_key]
    geocode = simplejson.load(urllib.urlopen(url))
    if geocode.get('status') == 'OVER_QUERY_LIMIT':
        geocode_key += 1
        if geocode_key == len(google_api_key):
            print 'Out of geocode keys for the day, try again tomorrow!'
            geocode_key = 0
            return (np.NaN,np.NaN)
        else:
            url = "https://maps.googleapis.com/maps/api/geocode/json?address="+location.replace(' ', '+')+"&key="+google_api_key[geocode_key]
            geocode = simplejson.load(urllib.urlopen(url))
            if geocode.get('status') == 'OVER_QUERY_LIMIT':
                print 'Next key is also exhausted.  Ruh Roh!'
                return (np.NaN,np.NaN)
        
    lat = geocode.get('results')[0].get('geometry').get('location').get('lat')
    lng = geocode.get('results')[0].get('geometry').get('location').get('lng')
    return (lat,lng)



def scrape_yelp(term, address, mode=default_mode):
    
    #px, py = orig

    #lat,lng = pixelstolatlng(px,py,map_zoom)
    #location = address_from_lat_lng((lat,lng))
    #if location == 'ERROR':
    #    err = {'id':None, 'name':None, 'lat':None, 'lng':None, 'rating':None,'oauth2-ascii-error':False, 'error':True,'error-message':'Geocode Failed'}        
    #    return pd.DataFrame([err,err,err])
        
    location = address.replace(',','')
    try:
        response = yelp.yelp_search(term, location)
    except:
        print 'Yelp search failed for this location: '+location
        err = {'search from address':address,'search':term,'id':None, 'business name':None, 'business lat':None, 'business lng':None, 'rating':None,'oauth2-ascii-error':False, 'error':True,'error-message':'Yelp search failed'}        
        return pd.DataFrame([err,err,err])
        
    businesses = response.get('businesses')
    if not businesses:
        print 'No businesses found for this location'
        err = {'search from address':address,'search':term,'id':None, 'business name':None, 'business lat':None, 'business lng':None, 'rating':None,'oauth2-ascii-error':False, 'error':True,'error-message':'No businesses found for this location'}        
        return pd.DataFrame([err,err,err])

    business = [yelp_business(businesses[0]['id']),yelp_business(businesses[1]['id']),yelp_business(businesses[2]['id'])]
    df = pd.DataFrame(business)
    df['search'] = term
    df['search from address'] = address
    return df
    



def yelp_business(business_id):
    try:
        response = yelp.yelp_get_business(business_id)
    except:   
        # problem is in yelp, it uses oauth2 to call api and that can't handle non ascii
        print 'Oauth2 error on the following business: ' + business_id
        return {'id':business_id, 'business name':None, 'business lat':None, 'business lng':None, 'rating':None,'oauth2-ascii-error':True, 'error':False, 'error-message':'oauth2 cannot handle non-ascii characters (like accented e)'}
    
    if response.get('error') is None:
        lat = response.get('location').get('coordinate').get('latitude')
        lng = response.get('location').get('coordinate').get('longitude')  
        name = response.get('name')
        rating = response.get('rating')
        return {'id':business_id, 'business name':name, 'business lat':lat, 'business lng':lng, 'rating':rating,'oauth2-ascii-error':False, 'error':False,'error-message':None}
    else:
        print response.get('error').get('id')
        return {'id':business_id, 'business name':None, 'business lat':None, 'business lng':None, 'rating':None,'oauth2-ascii-error':False, 'error':True,'error-message':response.get('error').get('id')}

def address_from_lat_lng(lat_lng,tolerance=0.25):
    global geocode_key
    lat, lng = lat_lng
    url = "https://maps.googleapis.com/maps/api/geocode/json?latlng="+str(lat)+","+str(lng)+"&key="+google_api_key[geocode_key]
    geocode = simplejson.load(urllib.urlopen(url))
    if geocode.get('status') == 'OVER_QUERY_LIMIT':
        geocode_key += 1
        if geocode_key == len(google_api_key):
            print 'Out of geocode keys for the day, try again tomorrow!'
            geocode_key = 0
            return (np.NaN,np.NaN)
        else:
            url = "https://maps.googleapis.com/maps/api/geocode/json?latlng="+str(lat)+","+str(lng)+"&key="+google_api_key[geocode_key]
            geocode = simplejson.load(urllib.urlopen(url))
            if geocode.get('status') == 'OVER_QUERY_LIMIT':
                print 'Next key is also exhausted.  Ruh Roh!'
                return (np.NaN,np.NaN)
            
    if geocode.get('status')=='OK':        
        lat_out = geocode.get('results')[0].get('geometry').get('location').get('lat')
        lng_out = geocode.get('results')[0].get('geometry').get('location').get('lng')
        px,py = latlngtopixels(lat,lng,map_zoom)
        px_out,py_out = latlngtopixels(lat_out,lng_out,map_zoom)
        geocode_x_err = np.abs(px-px_out)/px_delta
        geocode_y_err = np.abs(py-py_out)/px_delta
        if (geocode_x_err < tolerance) and (geocode_y_err < tolerance):
            return geocode.get('results')[0].get('formatted_address')            
        else:
            print 'Error: Geocoded address > ' + str(tolerance*100) + '% away from starting lat/lng'
            #return 'ERROR'
            return None
    else:
        print "Geocoding failed:"
        print geocode.get('status')
        #return 'ERROR'
        return None
    
def yelp_save(yelp_dict,save_dir):
    # dict should be dictionary of panels
    keys = yelp_dict.keys()
    for k in keys:
        y = yelp_dict[k]
        y.to_pickle(save_dir+k+'.pkl')

    
def yelp_read(save_dir):    
    yelp_dict = {}
    for f in listdir(save_dir):
        if isfile(join(save_dir,f)):
            latlng = f.split('.pkl')[0]
            yelp_dict[latlng] = pd.read_pickle(save_dir+f)
            
    return yelp_dict

def map_area(minlatlng,maxlatlng,old_map=None):
    # For the starting latlng, snap it to the grid, work out from there
    '''
    ox,oy = latlngtopixels(latlng[0],latlng[1],map_zoom)
    ox = np.floor(ox/px_delta)*px_delta
    oy = np.floor(oy/px_delta)*px_delta
    lat,lng = pixelstolatlng(ox,oy,map_zoom)
    address = address_from_lat_lng((lat,lng),tolerance=0.25)
    if not address:
        print 'Start from a real location, jerk.  Like anywhere else'
        return None
    else:
    map_address = [address]
    map_px = [ox]
    map_py = [oy]
    map_lat = [lat]
    map_lng = [lng]
    '''
    minpx,minpy = latlngtopixels(minlatlng[0],minlatlng[1],map_zoom)
    minpx = np.floor(minpx/px_delta)*px_delta
    minpy = np.floor(minpy/px_delta)*px_delta
    maxpx,maxpy = latlngtopixels(maxlatlng[0],maxlatlng[1],map_zoom)
    maxpx = np.floor(maxpx/px_delta)*px_delta
    maxpy = np.floor(maxpy/px_delta)*px_delta
    map_address = []
    map_px = []
    map_py = []
    map_lat = []
    map_lng = []
    
    for px in np.mgrid[minpx:maxpx+1:px_delta]:
        for py in np.mgrid[minpy:maxpy+1:px_delta]:
            if old_map:
                try:
                    old_map((px,py))
                    present = True
                except KeyError:
                    present = False
                except:
                    raise
            else:
                present = False
                
            if not present:
                
                #px = ox+x*px_delta
                #py = oy+y*px_delta
                lat,lng = pixelstolatlng(px,py,map_zoom)
                address = address_from_lat_lng((lat,lng),tolerance=0.25)
                if address:
                    # if geocoding fails, address will be None, otherwise get in here
                    map_address.append(address)
                    map_px.append(px)
                    map_py.append(py)
                    map_lat.append(lat)
                    map_lng.append(lng)
            
    df = pd.DataFrame({'address':map_address,
                         'px': map_px,
                         'py': map_py,
                         'lat': map_lat,
                         'lng': map_lng})
    df_indexed = df.set_index(['px','py'])
    if old_map:
        return pd.concat([old_map,df_indexed])
    else:
        return df_indexed
                         
def map_yelp_new(my_map_area,searches,old_map_area=None):
    if old_map_area:
        yelp_df = old_map_area.copy()
        first = False
    else:
        first = True
        
    for i in my_map_area.index:
        for search in searches:
        # i is a tuple with (px,py)
            #if old_map_area
            scrape = scrape_yelp(search,my_map_area.xs(i)['address'])
            scrape['px'] = i[0]
            scrape['py'] = i[1]
            scrape['search from lat'] = my_map_area.xs(i)['lat']
            scrape['search from lng'] = my_map_area.xs(i)['lng']
            if first:
                yelp_df = scrape.set_index(['px','py','search'])
                first = False
            else:
                yelp_df = pd.concat([yelp_df, scrape.set_index(['px','py','search'])])
                #yelp = yelp_searches(px,py,search)
    return yelp_df

def map_yelp(latlng,searches,update=False,search_range=[3,3,3,3],start_map=None):
    north,south,east,west = search_range
    
    ox,oy = latlngtopixels(latlng[0],latlng[1],map_zoom)
    ox = np.floor(ox/px_delta)*px_delta
    oy = np.floor(oy/px_delta)*px_delta
    if start_map is None:
        yelp_map = {}
        update = False
    else:
        yelp_map = start_map
    
    for n in xrange(north):
        for w in xrange(west):
            latlng_str = str(ox+n*px_delta)+':'+str(oy-w*px_delta)
            if latlng_str in yelp_map:
                if update:           
                    yelp = yelp_update_searches(yelp_map[latlng_str],ox+n*px_delta,oy-w*px_delta,searches)
                    yelp_map[latlng_str] = yelp
                else:
                    yelp = yelp_no_update_searches(yelp_map[latlng_str],ox+n*px_delta,oy-w*px_delta,searches)
                    yelp_map[latlng_str] = yelp
            else:
                yelp = yelp_searches(ox+n*px_delta,oy-w*px_delta,searches)
                yelp_map[latlng_str] = yelp
                
        for e in xrange(east):
            latlng_str = str(ox+n*px_delta)+':'+str(oy+e*px_delta)
            if latlng_str in yelp_map:
                if update:           
                    yelp = yelp_update_searches(yelp_map[latlng_str],ox+n*px_delta,oy+e*px_delta,searches)
                    yelp_map[latlng_str] = yelp
                else:
                    yelp = yelp_no_update_searches(yelp_map[latlng_str],ox+n*px_delta,oy+e*px_delta,searches)
                    yelp_map[latlng_str] = yelp
                    
            else:
                yelp = yelp_searches(ox+n*px_delta,oy+e*px_delta,searches)
                yelp_map[latlng_str] = yelp
           
    for n in xrange(south):
        for w in xrange(west):
            latlng_str = str(ox-n*px_delta)+':'+str(oy-w*px_delta)
            if latlng_str in yelp_map:
                if update:           
                    yelp = yelp_update_searches(yelp_map[latlng_str],ox-n*px_delta,oy-w*px_delta,searches)
                    yelp_map[latlng_str] = yelp
                else:
                    yelp = yelp_no_update_searches(yelp_map[latlng_str],ox-n*px_delta,oy-w*px_delta,searches)
                    yelp_map[latlng_str] = yelp
            else:
                yelp = yelp_searches(ox-n*px_delta,oy-w*px_delta,searches)
                yelp_map[latlng_str] = yelp
        for e in xrange(east):
            latlng_str = str(ox-n*px_delta)+':'+str(oy+e*px_delta)
            if latlng_str in yelp_map:
                if update:           
                    yelp = yelp_update_searches(yelp_map[latlng_str],ox-n*px_delta,oy+e*px_delta,searches)
                    yelp_map[latlng_str] = yelp
                else:
                    yelp = yelp_no_update_searches(yelp_map[latlng_str],ox-n*px_delta,oy-w*px_delta,searches)
                    yelp_map[latlng_str] = yelp
            else:
                yelp = yelp_searches(ox-n*px_delta,oy+e*px_delta,searches)
                yelp_map[latlng_str] = yelp
    
    return yelp_map

def yelp_no_update_searches(panel,x,y,searches):
    yelp = panel
    for s in searches:
        if not any(panel.items == s):
            #print 'Adding search for :' +str((x,y))+ ' - '+s
            scrape = scrape_yelp(s,(x,y))
            yelp = pd.concat([yelp, pd.Panel({s:scrape})])
    
    return yelp

def yelp_update_searches(panel,x,y,searches):
    yelp = panel
    for s in searches:
        
        #if any(panel.items == s):
            #print 'Updating search for :' +str((x,y))+ ' - '+s
        
        scrape = scrape_yelp(s,(x,y))
        yelp = pd.concat([yelp, pd.Panel({s:scrape})])
    
    return yelp

def yelp_searches(x,y,searches):
    yelp = pd.Panel()
    for s in searches:
        #print 'Initial search for :' +str((x,y))+ ' - '+s
        scrape = scrape_yelp(s,(x,y))
        yelp = pd.concat([yelp, pd.Panel({s:scrape})])
    
    return yelp

def fill_in_yelp_map(yelp_map):
    stats = map_stats(yelp_map,verbose=False)
    keys = yelp_map.keys()
    for key in keys:
        pstr = key.split(':')
        pan = yelp_map[key]
        items = pan.items
        if pan[items[0]]['error'][0]:
            if pan[items[0]]['error-message'][2] == 'Geocode Failed':
                # might be due to overused google key
                print 'Re-doing where geocode previously failed'
                new_panel = yelp_searches(float(pstr[0]),float(pstr[1]),stats['searches'])
                yelp_map[key] = new_panel
                
        else:
            new_panel = yelp_no_update_searches(pan,float(pstr[0]),float(pstr[1]),stats['searches'])
            yelp_map[key] = new_panel



def add_search_to_yelp_map(yelp_map,new_searches):
    #searches,lat_range,lng_range,addresses = map_stats(yelp_map,api_key)
    keys = yelp_map.keys()
    for key in keys:
        pstr = key.split(':')
        pan = yelp_map[key]
        
        new_panel = yelp_no_update_searches(pan,float(pstr[0]),float(pstr[1]),new_searches)
        yelp_map[key] = new_panel
    

def expand_north(yelp_map):
    print 'Expanding map north'
    stats = map_stats(yelp_map,verbose=False)
    keys = yelp_map.keys()
    for key in keys:
        pstr = key.split(':')
        if float(pstr[1]) == stats['maxpy']:
            y = yelp_searches(float(pstr[0]),float(pstr[1])+px_delta,stats['searches'])
            newkey = pstr[0] +':'+str(float(pstr[1])+px_delta)
            yelp_map[newkey] = y
            
def expand_south(yelp_map):
    print 'Expanding map south'
    stats = map_stats(yelp_map,verbose=False)
    keys = yelp_map.keys()
    for key in keys:
        pstr = key.split(':')
        if float(pstr[1]) == stats['minpy']:
            y = yelp_searches(float(pstr[0]),float(pstr[1])-px_delta,stats['searches'])
            newkey = pstr[0] +':'+str(float(pstr[1])-px_delta)
            yelp_map[newkey] = y   

def expand_east(yelp_map):
    print 'Expanding map east'
    stats = map_stats(yelp_map,verbose=False)
    keys = yelp_map.keys()
    for key in keys:
        pstr = key.split(':')
        if float(pstr[0]) == stats['maxpx']:
            y = yelp_searches(float(pstr[0])+px_delta,float(pstr[1]),stats['searches'])
            newkey = str(float(pstr[0])+px_delta) +':'+pstr[1]
            yelp_map[newkey] = y 

def expand_west(yelp_map):
    print 'Expanding map west'
    stats = map_stats(yelp_map,verbose=False)
    keys = yelp_map.keys()
    for key in keys:
        pstr = key.split(':')
        if float(pstr[0]) == stats['minpx']:
            y = yelp_searches(float(pstr[0])-px_delta,float(pstr[1]),stats['searches'])
            newkey = str(float(pstr[0])-px_delta) +':'+pstr[1]
            yelp_map[newkey] = y 

def expand_map(yelp_map):
    expand_north(yelp_map)
    expand_south(yelp_map)
    expand_east(yelp_map)
    expand_west(yelp_map)

def map_stats(yelp_map,verbose=True):
    keys = yelp_map.keys()
    pixels = keys[0].split(':')
    px = float(pixels[0])
    py = float(pixels[1])
    minlat,minlng = pixelstolatlng(px,py,map_zoom)
    maxlat = minlat
    maxlng = minlng
    maxpx = px
    minpx = px
    maxpy = py
    minpy = py
    searches = {}
    for key in keys:
        pixels = key.split(':')
        px = float(pixels[0])
        py = float(pixels[1])
        lat,lng = pixelstolatlng(px,py,map_zoom)
        if lat > maxlat:
            maxlat = lat
            maxpy=py
        if lat < minlat:
            minlat = lat
            minpy = py
        if lng > maxlng:
            maxlng = lng
            maxpx = px
        if lng < minlng:
            minlng = lng
            minpx = px
        items = yelp_map[key].items
        for item in items:
            if not item in searches:
                searches[item] = True
    out = {}
    out['searches'] = searches
    out['minlat'] = minlat
    out['maxlat'] = maxlat
    out['minlng'] = minlng
    out['maxlng'] = maxlng
    out['minpx'] = minpx
    out['maxpx'] = maxpx
    out['minpy'] = minpy
    out['maxpy'] = maxpy
    upper_left_address = address_from_lat_lng([maxlat,minlng])
    upper_right_address = address_from_lat_lng([maxlat,maxlng])
    lower_left_address = address_from_lat_lng([minlat,minlng])
    lower_right_address = address_from_lat_lng([minlat,maxlng])
    addresses = [upper_left_address,upper_right_address,lower_left_address,lower_right_address]
    out['addresses'] = addresses
    if verbose:
        print addresses
        print searches
        print 'lat range: ' +str(minlat)+' - '+str(maxlat)
        print 'lng range: ' +str(minlng)+' - '+str(maxlng)
        print 'px range: ' +str(minpx)+' - '+str(maxpx)
        print 'py range: ' +str(minpy)+' - '+str(maxpy)
    return out
            

def get_travel_time(orig_lat,orig_lng,dest_lat,dest_lng,mode='walking'):
    global distance_matrix_key
    url = "https://maps.googleapis.com/maps/api/distancematrix/json?origins="+str(orig_lat)+","+str(orig_lng)+"&destinations="+str(dest_lat)+","+str(dest_lng)+"&mode="+mode+"&language=en-EN&sensor=false&key="+google_api_key[distance_matrix_key]
    result= simplejson.load(urllib.urlopen(url))
    if result.get('status') == 'OVER_QUERY_LIMIT':
        print 'Exhausted distance matrix key: '+str(distance_matrix_key)
        distance_matrix_key += 1
        
        if distance_matrix_key == len(google_api_key):
            print 'Out of distance matrix keys for the day, try again tomorrow!'
            distance_matrix_key = 0
            return np.NaN
        else:
            url = "https://maps.googleapis.com/maps/api/distancematrix/json?origins="+str(orig_lat)+","+str(orig_lng)+"&destinations="+str(dest_lat)+","+str(dest_lng)+"&mode="+mode+"&language=en-EN&sensor=false&key="+google_api_key[distance_matrix_key]
            result= simplejson.load(urllib.urlopen(url))
            if result.get('status') == 'OVER_QUERY_LIMIT':
                print 'Next key is also exhausted.  Ruh Roh!'
                return np.NaN
    seconds = result.get('rows')[0].get('elements')[0].get('duration').get('value')
    
    return seconds

def update_score(yelp_map,old_score):
    #keys = yelp_map.keys()
    # note not all keys might be in old_score if the map is expanded
    mapkeys = yelp_map.keys()
    #print len(mapkeys)
    scorekeys = old_score.keys()
    #print len(scorekeys)
    unscored_keys = [key for key in mapkeys if not key in scorekeys]
    #print unscored_keys
    scored_keys = [key for key in mapkeys if key in scorekeys]
    #print scored_keys
    mapsearches = list(set([search for key in mapkeys for search in yelp_map[key].keys()]))
    
    
    mode = 'walking'
    modes = [mode for search in mapsearches]
    #print 'unscored keys: ' 
    #print unscored_keys
    for key in unscored_keys:
        orig = key.split(':')
        orig_lat,orig_lng = pixelstolatlng(float(orig[0]),float(orig[1]),map_zoom)
        search_rating = {}
        for s,search in enumerate(mapsearches):
            err_count = 0
            yelp_rating = []
            for i in xrange(3):               
                if not yelp_map[key][search]['error'][i]:
                    if not yelp_map[key][search]['oauth2-ascii-error'][i]:
                        rating = yelp_map[key][search]['rating'][i]
                        lat = yelp_map[key][search]['lat'][i]
                        lng = yelp_map[key][search]['lng'][i]
                        seconds = get_travel_time(orig_lat,orig_lng,lat,lng,mode=modes[s])
                        yelp_rating.append(seconds/(rating**2))
                    else:
                        err_count += 1
                else:
                    err_count += 1
            if err_count < 3:
                search_rating[search] = np.mean(yelp_rating)
            else:
                search_rating[search] = np.NaN
        old_score[key] = pd.Series(search_rating)
    for key in scored_keys:
        # fix broken entries
        scored_searches = old_score[key].keys()
        for s,search in enumerate(scored_searches):
            if np.isnan(old_score[key][search]):

                orig = key.split(':')
                orig_lat,orig_lng = pixelstolatlng(float(orig[0]),float(orig[1]),map_zoom)

                err_count = 0
                yelp_rating = []
                for i in xrange(3):               
                    if not yelp_map[key][search]['error'][i]:
                        if not yelp_map[key][search]['oauth2-ascii-error'][i]:
                            rating = yelp_map[key][search]['rating'][i]
                            lat = yelp_map[key][search]['lat'][i]
                            lng = yelp_map[key][search]['lng'][i]
                            seconds = get_travel_time(orig_lat,orig_lng,lat,lng,mode=modes[s])
                            yelp_rating.append(seconds/(rating**2))
                        else:
                            err_count += 1
                    else:
                        err_count += 1
                if err_count < 3:
                    old_score[key][search] = np.mean(yelp_rating)
                else:
                    old_score[key][search] = np.NaN
       
        unscored_searches = [search for search in mapsearches if not search in scored_searches]
        
     
        if unscored_searches:
            # add missing entries
            orig = key.split(':')
            orig_lat,orig_lng = pixelstolatlng(float(orig[0]),float(orig[1]),map_zoom)
            #search_rating = {}
            for search in unscored_searches:
            #for s,search in enumerate(searches):
                #if not search in scored_searches:
                err_count = 0
                yelp_rating = []
                for i in xrange(3):               
                    if not yelp_map[key][search]['error'][i]:
                        if not yelp_map[key][search]['oauth2-ascii-error'][i]:
                            rating = yelp_map[key][search]['rating'][i]
                            lat = yelp_map[key][search]['lat'][i]
                            lng = yelp_map[key][search]['lng'][i]
                            seconds = get_travel_time(orig_lat,orig_lng,lat,lng,mode=modes[s])
                            yelp_rating.append(seconds/(rating**2))
                        else:
                            err_count += 1
                    else:
                        err_count += 1
                if err_count < 3:
                    old_score[key][search] = np.mean(yelp_rating)
                else:
                    old_score[key][search] = np.NaN
                #else:
                #    search_rating[search] = old_score[key][search]
                    
                #old_score[key] = pd.Series(search_rating)
                
def score_yelp_map(yelp_map,searches=None,modes=None):
   
    keys = yelp_map.keys()
    if searches is None:
        #search_dict = map_searches(yelp_map)
        #searches = search_dict.keys()
        
        searches = list(set([search for key in keys for search in yelp_map[key].keys()]))
    if modes is None:
        mode = 'walking'
        modes = [mode for search in searches]
    #if old_score is None:
    pixel_dict = {}
    for key in keys:
        #print 'Scoring: ' + key
        orig = key.split(':')
        orig_lat,orig_lng = pixelstolatlng(float(orig[0]),float(orig[1]),map_zoom)
        search_rating = {}
        for s,search in enumerate(searches):
            err_count = 0
            yelp_rating = []
            for i in xrange(3):               
                if not yelp_map[key][search]['error'][i]:
                    if not yelp_map[key][search]['oauth2-ascii-error'][i]:
                        rating = yelp_map[key][search]['rating'][i]
                        lat = yelp_map[key][search]['lat'][i]
                        lng = yelp_map[key][search]['lng'][i]
                        seconds = get_travel_time(orig_lat,orig_lng,lat,lng,mode=modes[s])
                        yelp_rating.append(seconds/(rating**2))
                    else:
                        err_count += 1
                else:
                    err_count += 1
            if err_count < 3:
                search_rating[search] = np.mean(yelp_rating)
            else:
                search_rating[search] = np.NaN
        pixel_dict[key] = pd.Series(search_rating)
    
    return pd.DataFrame(pixel_dict)
    '''
    else:
        for key in keys:
            flag = False
            for s,search in enumerate(searches):
                if np.isnan(old_score[key][search]):
                    flag = True
            if flag:
                orig = key.split(':')
                orig_lat,orig_lng = pixelstolatlng(float(orig[0]),float(orig[1]),map_zoom)
                search_rating = {}
                for s,search in enumerate(searches):
                    err_count = 0
                    yelp_rating = []
                    for i in xrange(3):               
                        if not yelp_map[key][search]['error'][i]:
                            if not yelp_map[key][search]['oauth2-ascii-error'][i]:
                                rating = yelp_map[key][search]['rating'][i]
                                lat = yelp_map[key][search]['lat'][i]
                                lng = yelp_map[key][search]['lng'][i]
                                seconds = get_travel_time(orig_lat,orig_lng,lat,lng,mode=modes[s])
                                yelp_rating.append(seconds/(rating**2))
                            else:
                                err_count += 1
                        else:
                            err_count += 1
                    if err_count < 3:
                        search_rating[search] = np.mean(yelp_rating)
                    else:
                        search_rating[search] = np.NaN
                old_score[key] = pd.Series(search_rating)    
        return old_score
        '''
    
def score_save(score_DF,save_dir,save_name='scored-yelp'):
    # dict should be dictionary of panels
    score_DF.to_pickle(save_dir+save_name+'.pkl')    

def score_read(save_dir,save_name='scored-yelp'):
    return pd.read_pickle(save_dir+save_name)

def interpolate_yelp_score(scores,plot=False,method='nearest'):
    pixels = scores.keys()
    searches = scores.index
    px = []
    py = []
    for pixel in pixels:
        pix = pixel.split(':')
        px.append(float(pix[0]))
        py.append(float(pix[1]))
    #xsteps = 25
    #ysteps = 25
    xsteps_fine = 1
    ysteps_fine = 1
    #x,y = np.mgrid[np.min(px):np.max(px):xsteps,np.min(py):np.max(py):ysteps]
    x_fine,y_fine = np.mgrid[np.min(px):np.max(px):xsteps_fine,np.min(py):np.max(py):ysteps_fine]
    interp = {}
    #x_pos = {}
    #y_pos = {}
    #mask = {}
    for search in searches: 
        points = [[]]
        mask_points = [[]]
        values = []
        mask_values = []
        mask_flag=True
        for i,x in enumerate(px):
            if mask_flag:
                mask_points = [[x,py[i]]]
            else:
                mask_points.append([x,py[i]])
            if not np.isnan(scores[pixels[i]][search]):
                if mask_flag:
                    mask_values=[128]
                    mask_flag = False
                else:
                    mask_values.append(128)
                    
                if len(points[0]) == 0:
                    points = [[x,py[i]]]
                    values = [scores[pixels[i]][search]]
                else:
                    points.append([x,py[i]])
                    values.append(scores[pixels[i]][search])
            else:
                if mask_flag:
                    mask_values=[0]
                    mask_flag = False
                else:
                    mask_values.append(0)
                
        grid = griddata(np.matrix(points), np.array(values), (x_fine, y_fine), method)
        grid_mask = griddata(np.matrix(mask_points), np.array(mask_values), (x_fine, y_fine), method)
        interp[search] = grid.T
        #x_pos[search]= x_fine
        #y_pos[search] = y_fine
        if plot:
            plt.figure()
            plt.imshow(grid)
            plt.title(search)
            plt.figure()
            plt.imshow(grid_mask)
            plt.title(search+' mask')
            
    return x_fine,y_fine,interp
       