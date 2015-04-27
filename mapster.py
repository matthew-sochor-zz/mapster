import numpy as np
import simplejson, urllib, urllib2
import matplotlib.pyplot as plt
import pandas as pd 
from scipy.interpolate import griddata
from math import log, exp, tan, atan, pi, radians, sin, cos, atan2, sqrt
import yelp
import time
import requests
import threading
import Queue
import Image as pil

from multiprocessing import Pool

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

default_map_width = 256#640
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
    '''    
    mx = (lng * ORIGIN_SHIFT) / 180.0
    my = log(tan((90.0 + lat) * pi/360.0))/(pi/180.0)
    my = (my * ORIGIN_SHIFT) /180.0
    res = EQUATOR_CIRCUMFERENCE/google_res*2/(2.0**zoom)
    px = (mx + ORIGIN_SHIFT)/res
    py = (my + ORIGIN_SHIFT)/res'''
    px = (2.0**zoom)*(lng/720. + 0.25)*google_res
    py = (2.0**zoom)*(-1*log(tan((90.+lat)*pi/360.))/4./pi + .25)*google_res
    return int(px), int(py)
    
def latlngtotile(lat, lng, zoom):
    px = (2.0**zoom)*(lng/720. + 0.25)*google_res
    py = (2.0**zoom)*(-1*log(tan((90.+lat)*pi/360.))/4./pi + .25)*google_res
    return int(np.floor(px/256.)), int(np.floor(py/256.))

def pixelstotile(px,py):
    return int(np.floor(px/256.)), int(np.floor(py/256.))

def pixelstolatlng(px, py, zoom):
    #res = EQUATOR_CIRCUMFERENCE/google_res*2/(2**zoom)
    #mx = px * res - ORIGIN_SHIFT
    #my = py * res - ORIGIN_SHIFT
    #lat = (my / ORIGIN_SHIFT) * 180.0
    #lat = 180.0 / pi * (2.0*atan(exp(lat*pi/180.0)) - pi/2.0)
    #lng = (mx / ORIGIN_SHIFT) * 180.0
    lng = 720.0*(float(px)/(2.0**zoom)/google_res - 0.25)
    lat = (360.0/pi)*atan(exp(pi-4.0*pi*float(py)/(2.0**zoom)/google_res))-90.0
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

def test_urllib(location):
    url = "https://maps.googleapis.com/maps/api/geocode/json?address="+location.replace(' ', '+')+"&key="+google_api_key[geocode_key]
    return simplejson.load(urllib.urlopen(url))

def test_urllib2(location):
    url = "https://maps.googleapis.com/maps/api/geocode/json?address="+location.replace(' ', '+')+"&key="+google_api_key[geocode_key]
    return simplejson.load(urllib2.urlopen(url))
    
def test_request(location):
    #url = "https://maps.googleapis.com/maps/api/geocode/json?address="+location.replace(' ', '+')+"&key="+google_api_key[geocode_key]
    #geocode = simplejson.load(urllib.urlopen(url))
    userdata = {"address": location.replace(' ', '+'), "key": google_api_key[geocode_key]}
    resp = requests.get('https://maps.googleapis.com/maps/api/geocode/json', params=userdata)
    return resp.json()
    
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



def scrape_yelp(term, location, lat, lng, businessDF = None, firstRun=False):
        
    location = location.replace(',','')
    try:
        response = yelp.yelp_search(term, location)
    except:
        print 'Yelp search failed for this location: '+location
        err = {'lat':lat,'lng':lng,'search':term,'id':None, 'business name':None, 'business lat':None, 'business lng':None, 'rating':None,'oauth2-ascii-error':False, 'error':True,'error-message':'Yelp search failed'}        
        return pd.DataFrame([err,err,err]),businessDF
        
    businesses = response.get('businesses')
    if not businesses:
        print 'No businesses found for this location'
        err = {'lat':lat,'lng':lng,'search':term,'id':None, 'business name':None, 'business lat':None, 'business lng':None, 'rating':None,'oauth2-ascii-error':False, 'error':True,'error-message':'No businesses found for this location'}        
        return pd.DataFrame([err,err,err]),businessDF

    if firstRun:
        # initialize businessDF
        b = {}
        for i in xrange(3):
            print 'Adding new business: ' +businesses[i]['id']
            b[businesses[i]['id']] = yelp_business(businesses[i]['id'])
        businessDF = pd.DataFrame(b)
        
    
    business = []
    for i in xrange(3):
        try:
            business.append(businessDF[businesses[i]['id']])
        except KeyError:
            print 'Adding new business: ' +businesses[i]['id']
            bus = yelp_business(businesses[i]['id'])
            businessDF[businesses[i]['id']] = bus
            business.append(bus)
            
    df = pd.DataFrame(business)
    
    df['search'] = term
    df['lat'] = lat
    df['lng'] = lng
    return df, businessDF


    
def yelp_business(business_id):
    try:
        response = yelp.yelp_get_business(business_id)
    except:   
        # problem is in yelp, it uses oauth2 to call api and that can't handle non ascii
        print 'Oauth2 error on the following business: ' + business_id
        return pd.Series({'id':business_id, 'business name':None, 'business lat':None, 'business lng':None, 'rating':None,'oauth2-ascii-error':True, 'error':False, 'error-message':'oauth2 cannot handle non-ascii characters (like accented e)'})
    
    if response.get('error') is None:
        lat = response.get('location').get('coordinate').get('latitude')
        lng = response.get('location').get('coordinate').get('longitude')  
        name = response.get('name')
        rating = response.get('rating')
        return pd.Series({'id':business_id, 'business name':name, 'business lat':lat, 'business lng':lng, 'rating':rating,'oauth2-ascii-error':False, 'error':False,'error-message':None})
    else:
        print response.get('error').get('id')
        return pd.Series({'id':business_id, 'business name':None, 'business lat':None, 'business lng':None, 'rating':None,'oauth2-ascii-error':False, 'error':True,'error-message':response.get('error').get('id')})

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
            #print 'Error: Geocoded address > ' + str(tolerance*100) + '% away from starting lat/lng'
            #return 'ERROR'
            return None
    else:
        print "Geocoding failed:"
        print geocode.get('status')
        #return 'ERROR'
        return None
    


def map_area(minlatlng,maxlatlng,old_map=None):
    # For the starting latlng, snap it to the grid, work out from there

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
                lat,lng = pixelstolatlng(px,py,map_zoom)
                address = address_from_lat_lng((lat,lng),tolerance=0.25)
                if address:
                    # if geocoding fails, address will be None, otherwise get in here
                    map_address.append(address)
                    map_px.append(px)
                    map_py.append(py)
                    map_lat.append(lat)
                    map_lng.append(lng)

    tile = [(pixelstotile(px,py)) for px,py in zip(map_px,map_py)] 
    tx,ty = zip(*tile)
    df = pd.DataFrame({'address':map_address,
                         'px': map_px,
                         'py': map_py,
                         'tx': tx,
                         'ty': ty,
                         'zoom': map_zoom,
                         'lat': map_lat,
                         'lng': map_lng})
    #df_indexed = df.set_index(['px','py'])
    if old_map:
        #return pd.concat([old_map,df_indexed])
        return pd.concat([old_map,df])
    else:
        #return df_indexed
        return df

def map_yelp_unique(outer_map_area,inner_map_area):
    imap = inner_map_area.set_index(['px','py'])
    between_map_area = outer_map_area.copy()
    for i in outer_map_area.index:
        try:
            imap.ix[outer_map_area.loc[i]['px'],outer_map_area.loc[i]['py']]
            #print 'point is in the map: ',outer_map_area.loc[i]['px'],outer_map_area.loc[i]['py']
            between_map_area = between_map_area.drop(i)
        except:
            do = 'nothing'

            #print 'point is NOT in the map: ',outer_map_area.loc[i]['px'],outer_map_area.loc[i]['py']
    return between_map_area
                         
def map_yelp(my_map_area,searches,old_map_area=None):
    if isinstance(searches,str):
        searches = [searches]
    try:
        businessDF = pd.read_pickle('./pickles/businessDF.pkl')
        firstRun = False
    except IOError:
        firstRun = True
        
    if old_map_area:
        yelp_df = old_map_area.copy()
        first = False
    else:
        first = True
    #for i in my_map_area.index:    
    for px,py,lat,lng,address in zip(my_map_area['px'],my_map_area['py'],my_map_area['lat'],my_map_area['lng'],my_map_area['address']):
        for search in searches:
        # i is a tuple with (px,py)
            #if old_map_area
            if firstRun:
                #scrape, businessDF = scrape_yelp(search,my_map_area.xs(i)['address'],my_map_area.xs(i)['lat'],my_map_area.xs(i)['lng'],firstRun=True)             
                scrape, businessDF = scrape_yelp(search,address,lat,lng,firstRun=True)             
                                
                firstRun = False
            else:
                #scrape, businessDF = scrape_yelp(search,my_map_area.xs(i)['address'],my_map_area.xs(i)['lat'],my_map_area.xs(i)['lng'],businessDF = businessDF)
                scrape, businessDF = scrape_yelp(search,address,lat,lng,businessDF = businessDF)
                        
            scrape['px'] = px
            scrape['py'] = py
            if first:
                yelp_df = scrape
                first = False
            else:
                #yelp_df = pd.concat([yelp_df, scrape.set_index(['px','py','search'])])
                yelp_df = pd.concat([yelp_df, scrape])
                #yelp = yelp_searches(px,py,search)
    businessDF.to_pickle('./pickles/businessDF.pkl')
    yelp_df = yelp_df.reset_index()
    return map_yelp_travel_time(yelp_df)

def run_parallel_in_threads(target, args_list):
    result = Queue.Queue()
    # wrapper to collect return value in a Queue
    def task_wrapper(*args):
        result.put(target(*args))
    threads = [threading.Thread(target=task_wrapper, args=args) for args in args_list]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return result

def travel_time_wrapper(bus,key):

    if not bus['error']:
        if not bus['oauth2-ascii-error']:
            seconds = get_travel_time(bus['lat'],bus['lng'],bus['business lat'],bus['business lng'],key=key)  
            if seconds:
                score = seconds/(bus['rating']**2) 
            else:
                seconds = np.NaN
                score = np.NaN
        else:
            seconds = np.NaN
            score = np.NaN
    else:
        seconds = np.NaN
        score = np.NaN
        
    return (bus['ind'],seconds,score)
     
    
def map_yelp_travel_time(map_yelp_DF,group=None):
    if not group:
        group = 100
        
    df = map_yelp_DF.copy()
    df['ind'] = df.index
    searching =True
    key = 0  
    results = []
    busses = [df.loc[i] for i in df.index]
    #busses = [df[key] for key in df.keys]
    #return busses
    ind =0
    while searching:
        if test_key(key):
            # split into groups of size group
            if ind+group >= len(busses):
                mini_bus = busses[ind:]
                bus_group = [(bus, key) for bus in mini_bus]
                searching = False
            else:
                mini_bus = busses[ind:ind+group]
                bus_group = [(bus, key) for bus in mini_bus]
            # run parallel on that group
            q = run_parallel_in_threads(travel_time_wrapper, bus_group) 
            flag = True
            keyerr = False
            result = []
            while flag:
                out = q.get()
                if out:
                    result.append(out)
                else:
                    flag = False
                    keyerr = True
                if q.empty():
                    flag = False
            if not keyerr:       
                # only take the results if the entire group finished correctly
                ind += group
                results += result
            else:
                print 'Exhausted distance matrix key: '+str(key)
                key += 1
                if key == 5:
                    print 'No keys left'
                    searching = False
                # keep the index where it is at, we want to re-run that group
        else:
            # key is exhausted
            key += 1
            if key == 5:
                print 'No keys left'
                searching = False
    # note there is probably a much more elegant way of doing this  
    
    resultsDF = pd.DataFrame(results,columns=['ind','seconds','score'])
    # need to sort because the parallel threading screws up the order
    resultsDF = resultsDF.sort(resultsDF.keys()[0])
    #print resultsDF
    #resultsDF = resultsDF.set_index(resultsDF.keys()[0])
    # dfout doesn't have the 'ind' field,  I think there is a more elegant way to drop a single column
    #dfout['seconds'] = resultsDF[resultsDF.keys()[0]]
    #dfout['score'] = resultsDF[resultsDF.keys()[1]]
    df['seconds'] = resultsDF['seconds']
    df['score'] = resultsDF['score']
    #return dfout.set_index(['px','py','search'])   
    # clean up our DataFrame a bit
    del df['ind']
    df['id'] = df['index']
    del df['index']
    return df #.drop('ind')

#start_time = time.time()
#tech_details = workers.map(get_tech_details, tech_links)
def travel_time_wrapper2(bus,key=0):

    if not bus['error']:
        if not bus['oauth2-ascii-error']:
            seconds = get_travel_time(bus['lat'],bus['lng'],bus['business lat'],bus['business lng'],key=key)  
            if seconds:
                score = seconds/(bus['rating']**2) 
            else:
                #return None
                seconds = np.NaN
                score = np.NaN
        else:
            seconds = np.NaN
            score = np.NaN
    else:
        seconds = np.NaN
        score = np.NaN
        
    return (bus['ind'],seconds,score)
from functools import partial

 
    
def map_yelp_travel_time_keyed(map_yelp_DF,group=None,key=None):
    if not group:
        group = 100
    if not key:
        keyflag = True
        key = 0
        while keyflag:
            if test_key(key):
                keyflag = False
            else:
                key = key+1
                if key ==5:
                    print 'Out of keys today, try again tomorrow'
                    return None
                 
    df = map_yelp_DF.copy()
    df['ind'] = df.index
    
    results = []
    busses = [df.loc[i] for i in df.index]
    #busses = [df[key] for key in df.keys]
    #return busses
    
    workers = Pool(group)  # 30 worker processes
    travel_time_wrapper2_keyed = partial(travel_time_wrapper2, key=key)
    results = workers.map(travel_time_wrapper2_keyed, busses) 
    workers.close()
    workers.join()
    #return results
    # note there is probably a much more elegant way of doing this  
    try:
        resultsDF = pd.DataFrame(results,columns=['ind','seconds','score'])
    except:
        print 'PANDAS ERROR!'
        return results
    #print resultsDF
    # need to sort because the parallel threading screws up the order
    resultsDF = resultsDF.sort(resultsDF.keys()[0])

    df['seconds'] = resultsDF['seconds']
    df['score'] = resultsDF['score']
    #return dfout.set_index(['px','py','search'])   
    # clean up our DataFrame a bit
    del df['ind']
    df['id'] = df['index']
    del df['index']
    return df #.drop('ind')


def test_key(key):
    return get_travel_time(42.381119, -71.115189, 42.383610, -71.133680,key=key)


def score_map_yelp(my_map_area,my_map_yelp,mode='min'):
    
    if mode == 'mean':
        val = my_map_yelp.groupby(['px','py','search'])['score'].mean()
    elif mode == 'min':
        val = my_map_yelp.groupby(['px','py','search'])['score'].min()
    elif mode == 'max':
        val = my_map_yelp.groupby(['px','py','search'])['score'].max()
    elif mode == 'std':
        val = my_map_yelp.groupby(['px','py','search'])['score'].std()
    else:
        raise NameError
    
    val = val.reset_index()
    my_map_area.sort(['px','py'])
    val.sort(['px','py'])
    #return val
    searches = list(set(val['search']))
    for search in searches:
        my_map_area[search] = list(val[val['search']==search]['score'])

def merge_map_yelp(map_yelp_1,map_yelp_2):
    
    df = pd.concat([map_yelp_1,map_yelp_2])
    return df.sort(['px','py','search'])

def merge_map_area(map_area_1,map_area_2):
    df = pd.concat([map_area_1,map_area_2])
    return df.sort(['px','py'])

def get_travel_time(orig_lat,orig_lng,dest_lat,dest_lng,mode='walking',key=None):
    if not key:
        key = 0
        
    #global distance_matrix_key
    url = "https://maps.googleapis.com/maps/api/distancematrix/json?origins="+str(orig_lat)+","+str(orig_lng)+"&destinations="+str(dest_lat)+","+str(dest_lng)+"&mode="+mode+"&language=en-EN&sensor=false&key="+google_api_key[key]
    try:    
        result= simplejson.load(urllib.urlopen(url))
    except IOError:
        # error that rarely occurs, and it might be because I do more than 100 calls in 10 seconds
        print 'IO Error, sleeping for 1 second'
        time.sleep(1)
        try:
            result = simplejson.load(urllib.urlopen(url))
        except IOError:
            print 'IOError for origin lat/lng: '+str(orig_lat)+' - '+str(orig_lng)
            return np.NaN
            
            
    if result.get('status') == 'OVER_QUERY_LIMIT':
        #print 'Exhausted distance matrix key: '+str(key)
        return None
    
    try:
        seconds = result.get('rows')[0].get('elements')[0].get('duration').get('value')
        #print seconds
    except IndexError:
        print 'Index Error for: '+str(orig_lat)+' - '+str(orig_lng)+ ' to '+str(dest_lat)+' - '+str(dest_lng)
        seconds = np.NaN
        
    return seconds
    
def draw_mapster(map_area,searches,mode='linear',alpha=128,plot=False):
    if isinstance(searches,str):
        searches = [searches]
    map_area = map_area.sort(['px','py'])
    px = map_area['px']
    py = map_area['py']
    tx = list(set(map_area['tx']))
    ty = list(set(map_area['ty']))
    
    x_fine,y_fine = np.mgrid[np.min(px):np.max(px):1,np.min(py):np.max(py):1]

    points = np.matrix([[x,y] for x,y in zip(px,py)])
    first = True
    
    for search in searches:
        if first:
            values = np.array(map_area[search])
            first = False
            im_name = search
        else:
            values += np.array(map_area[search])
            im_name += '_'+search
    
    values = values/len(searches)
    grid = griddata(points,values,(x_fine,y_fine),mode)
    if plot:
        plt.imshow(grid)
    
    gmax = max([max(g) for g in grid])
    gnorm = grid.T/gmax

    im = pil.fromarray(np.uint8(plt.cm.jet(gnorm)*255))
    
    mintile = get_tile_pixels(min(tx),min(ty))
    maxtile = get_tile_pixels(max(tx),max(ty))

    x_off,y_off = int(min(px) - mintile[0]),int(min(py)-mintile[1])
    bigmap = np.zeros((maxtile[3]-mintile[1],maxtile[2]-mintile[0]))
    
    bigmap[y_off:y_off+len(gnorm),x_off:x_off+len(gnorm[0])] = gnorm
    im = pil.fromarray(np.uint8(plt.cm.jet(bigmap)*255))
    alpha_layer = np.zeros((maxtile[3]-mintile[1],maxtile[2]-mintile[0]))
    alpha_layer[bigmap > 0] = alpha
    alpha_im = pil.fromarray(alpha_layer)
    alpha_im = alpha_im.convert('L')
    r,g,b,a = im.split()

    final_im = pil.merge('RGBA',(r,g,b,alpha_im))
    make_tiles(tx,ty,final_im,im_name)
    #return grid

    
def get_tile_pixels(tx,ty):
    return (tx*256,ty*256,tx*256+256,ty*256+256)

def make_tiles(tilex,tiley,im,name):
    xoff = min(tilex)*256
    yoff = min(tiley)*256
    #im = im.transpose(pil.ROTATE_90)
    for tx in tilex:
        for ty in tiley:
            pixels = get_tile_pixels(tx,ty)
            box = (pixels[0]-xoff,pixels[1]-yoff,pixels[2]-xoff,pixels[3]-yoff)
            region = im.crop(box)
            fname = './tiles/'+name+'_'+str(tx)+'_'+str(ty)+'.png'
            region.save(fname)