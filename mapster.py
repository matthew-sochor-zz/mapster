import numpy as np
import simplejson, urllib
import matplotlib.pyplot as plt
import sys
import pandas as pd
from os import listdir
from os.path import isfile, join   
from scipy.interpolate import griddata
sys.path.append('/home/matt/python')

import yelp
import mercator
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



def scrape_yelp(term, orig, mode=default_mode):
    
    px, py = orig

    lat,lon = mercator.pixelstolatlon(px,py,map_zoom)
    location = address_from_lat_lng((lat,lon))
    if location == 'ERROR':
        err = {'id':None, 'name':None, 'lat':None, 'lng':None, 'rating':None,'oauth2-ascii-error':False, 'error':True,'error-message':'Geocode Failed'}        
        return pd.DataFrame([err,err,err])
        
    location = location.replace(',','')
    try:
        response = yelp.yelp_search(term, location)
    except:
        print 'Yelp search failed for this location: '+location
        err = {'id':None, 'name':None, 'lat':None, 'lng':None, 'rating':None,'oauth2-ascii-error':False, 'error':True,'error-message':'Yelp search failed'}        
        return pd.DataFrame([err,err,err])
        
    businesses = response.get('businesses')
    if not businesses:
        print 'No businesses found for this location'
        err = {'id':None, 'name':None, 'lat':None, 'lng':None, 'rating':None,'oauth2-ascii-error':False, 'error':True,'error-message':'No businesses found for this location'}        
        return pd.DataFrame([err,err,err])

    business = [yelp_business(businesses[0]['id']),yelp_business(businesses[1]['id']),yelp_business(businesses[2]['id'])]
            
    return pd.DataFrame(business)
    



def yelp_business(business_id):
    try:
        response = yelp.yelp_get_business(business_id)
    except:   
        # problem is in yelp, it uses oauth2 to call api and that can't handle non ascii
        print 'Oauth2 error on the following business: ' + business_id
        return {'id':business_id, 'name':None, 'lat':None, 'lng':None, 'rating':None,'oauth2-ascii-error':True, 'error':False, 'error-message':'oauth2 cannot handle non-ascii characters (like accented e)'}
    
    if response.get('error') is None:
        lat = response.get('location').get('coordinate').get('latitude')
        lng = response.get('location').get('coordinate').get('longitude')  
        name = response.get('name')
        rating = response.get('rating')
        return {'id':business_id, 'name':name, 'lat':lat, 'lng':lng, 'rating':rating,'oauth2-ascii-error':False, 'error':False,'error-message':None}
    else:
        print response.get('error').get('id')
        return {'id':business_id, 'name':None, 'lat':None, 'lng':None, 'rating':None,'oauth2-ascii-error':False, 'error':True,'error-message':response.get('error').get('id')}

def address_from_lat_lng(lat_lng):
    global geocode_key
    tolerance = 0.25
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
        px,py = mercator.latlontopixels(lat,lng,map_zoom)
        px_out,py_out = mercator.latlontopixels(lat_out,lng_out,map_zoom)
        geocode_x_err = np.abs(px-px_out)/px_delta
        geocode_y_err = np.abs(py-py_out)/px_delta
        if (geocode_x_err < tolerance) and (geocode_y_err < tolerance):
            return geocode.get('results')[0].get('formatted_address')            
        else:
            print 'Error: Geocoded address > ' + str(tolerance*100) + '% away from starting lat/lng'
            return 'ERROR'
    else:
        print "Geocoding failed:"
        print geocode.get('status')
        return 'ERROR'
    
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
            latlon = f.split('.pkl')[0]
            yelp_dict[latlon] = pd.read_pickle(save_dir+f)
            
    return yelp_dict

def map_yelp(latlon,searches,update=False,search_range=[3,3,3,3],start_map=None):
    north,south,east,west = search_range
    
    ox,oy = mercator.latlontopixels(latlon[0],latlon[1],map_zoom)
    ox = np.floor(ox/px_delta)*px_delta
    oy = np.floor(oy/px_delta)*px_delta
    if start_map is None:
        yelp_map = {}
        update = False
    else:
        yelp_map = start_map
    
    for n in xrange(north):
        for w in xrange(west):
            latlon_str = str(ox+n*px_delta)+':'+str(oy-w*px_delta)
            if latlon_str in yelp_map:
                if update:           
                    yelp = yelp_update_searches(yelp_map[latlon_str],ox+n*px_delta,oy-w*px_delta,searches)
                    yelp_map[latlon_str] = yelp
                else:
                    yelp = yelp_no_update_searches(yelp_map[latlon_str],ox+n*px_delta,oy-w*px_delta,searches)
                    yelp_map[latlon_str] = yelp
            else:
                yelp = yelp_searches(ox+n*px_delta,oy-w*px_delta,searches)
                yelp_map[latlon_str] = yelp
                
        for e in xrange(east):
            latlon_str = str(ox+n*px_delta)+':'+str(oy+e*px_delta)
            if latlon_str in yelp_map:
                if update:           
                    yelp = yelp_update_searches(yelp_map[latlon_str],ox+n*px_delta,oy+e*px_delta,searches)
                    yelp_map[latlon_str] = yelp
                else:
                    yelp = yelp_no_update_searches(yelp_map[latlon_str],ox+n*px_delta,oy+e*px_delta,searches)
                    yelp_map[latlon_str] = yelp
                    
            else:
                yelp = yelp_searches(ox+n*px_delta,oy+e*px_delta,searches)
                yelp_map[latlon_str] = yelp
           
    for n in xrange(south):
        for w in xrange(west):
            latlon_str = str(ox-n*px_delta)+':'+str(oy-w*px_delta)
            if latlon_str in yelp_map:
                if update:           
                    yelp = yelp_update_searches(yelp_map[latlon_str],ox-n*px_delta,oy-w*px_delta,searches)
                    yelp_map[latlon_str] = yelp
                else:
                    yelp = yelp_no_update_searches(yelp_map[latlon_str],ox-n*px_delta,oy-w*px_delta,searches)
                    yelp_map[latlon_str] = yelp
            else:
                yelp = yelp_searches(ox-n*px_delta,oy-w*px_delta,searches)
                yelp_map[latlon_str] = yelp
        for e in xrange(east):
            latlon_str = str(ox-n*px_delta)+':'+str(oy+e*px_delta)
            if latlon_str in yelp_map:
                if update:           
                    yelp = yelp_update_searches(yelp_map[latlon_str],ox-n*px_delta,oy+e*px_delta,searches)
                    yelp_map[latlon_str] = yelp
                else:
                    yelp = yelp_no_update_searches(yelp_map[latlon_str],ox-n*px_delta,oy-w*px_delta,searches)
                    yelp_map[latlon_str] = yelp
            else:
                yelp = yelp_searches(ox-n*px_delta,oy+e*px_delta,searches)
                yelp_map[latlon_str] = yelp
    
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
    #searches,lat_range,lon_range,addresses = map_stats(yelp_map,api_key)
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
    minlat,minlon = mercator.pixelstolatlon(px,py,map_zoom)
    maxlat = minlat
    maxlon = minlon
    maxpx = px
    minpx = px
    maxpy = py
    minpy = py
    searches = {}
    for key in keys:
        pixels = key.split(':')
        px = float(pixels[0])
        py = float(pixels[1])
        lat,lon = mercator.pixelstolatlon(px,py,map_zoom)
        if lat > maxlat:
            maxlat = lat
            maxpy=py
        if lat < minlat:
            minlat = lat
            minpy = py
        if lon > maxlon:
            maxlon = lon
            maxpx = px
        if lon < minlon:
            minlon = lon
            minpx = px
        items = yelp_map[key].items
        for item in items:
            if not item in searches:
                searches[item] = True
    out = {}
    out['searches'] = searches
    out['minlat'] = minlat
    out['maxlat'] = maxlat
    out['minlon'] = minlon
    out['maxlon'] = maxlon
    out['minpx'] = minpx
    out['maxpx'] = maxpx
    out['minpy'] = minpy
    out['maxpy'] = maxpy
    upper_left_address = address_from_lat_lng([maxlat,minlon])
    upper_right_address = address_from_lat_lng([maxlat,maxlon])
    lower_left_address = address_from_lat_lng([minlat,minlon])
    lower_right_address = address_from_lat_lng([minlat,maxlon])
    addresses = [upper_left_address,upper_right_address,lower_left_address,lower_right_address]
    out['addresses'] = addresses
    if verbose:
        print addresses
        print searches
        print 'lat range: ' +str(minlat)+' - '+str(maxlat)
        print 'lon range: ' +str(minlon)+' - '+str(maxlon)
        print 'px range: ' +str(minpx)+' - '+str(maxpx)
        print 'py range: ' +str(minpy)+' - '+str(maxpy)
    return out
            
'''
def map_searches(yelp_map):
    keys = yelp_map.keys()
    searches = {}
    for key in keys:
        items = yelp_map[key].items
        for item in items:
            if not item in searches:
                searches[item] = True
    return searches    
   ''' 
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
        orig_lat,orig_lng = mercator.pixelstolatlon(float(orig[0]),float(orig[1]),map_zoom)
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
                orig_lat,orig_lng = mercator.pixelstolatlon(float(orig[0]),float(orig[1]),map_zoom)

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
        
        #print 'unscored searches: '
        #print unscored_searches
        if unscored_searches:
            # add missing entries
            orig = key.split(':')
            orig_lat,orig_lng = mercator.pixelstolatlon(float(orig[0]),float(orig[1]),map_zoom)
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
        orig_lat,orig_lng = mercator.pixelstolatlon(float(orig[0]),float(orig[1]),map_zoom)
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
                orig_lat,orig_lng = mercator.pixelstolatlon(float(orig[0]),float(orig[1]),map_zoom)
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

def interpolate_yelp_score(scores,plot=False,method='nearest'):
    pixels = scores.keys()
    searches = scores.index
    px = []
    py = []
    for pixel in pixels:
        pix = pixel.split(':')
        px.append(float(pix[0]))
        py.append(float(pix[1]))
    
    x,y = np.mgrid[np.min(px):np.max(px):xsteps,np.min(py):np.max(py):ysteps]
    x_fine,y_fine = np.mgrid[np.min(px):np.max(px):xsteps_fine,np.min(py):np.max(py):ysteps_fine]
    interp = {}
    x_pos = {}
    y_pos = {}
    mask = {}
    for search in searches: 
        points = [[]]
        mask_points = [[]]
        values = []
        mask_values = []
        mask_flag=True
        for i,p in enumerate(px):
            if mask_flag:
                mask_points = [[p,py[i]]]
            else:
                mask_points.append([p,py[i]])
            if not np.isnan(scores[pixels[i]][search]):
                if mask_flag:
                    mask_values=[128]
                    mask_flag = False
                else:
                    mask_values.append(128)
                    
                if len(points[0]) == 0:
                    points = [[p,py[i]]]
                    values = [scores[pixels[i]][search]]
                else:
                    points.append([p,py[i]])
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
        x_pos[search]= x_fine
        y_pos[search] = y_fine
        if plot:
            plt.figure()
            plt.imshow(grid)
            plt.title(search)
            plt.figure()
            plt.imshow(grid_mask)
            plt.title(search+' mask')
            
    return x_pos,y_pos,interp
       