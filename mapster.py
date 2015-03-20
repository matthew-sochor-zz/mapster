import numpy as np
import simplejson, urllib
import matplotlib.pyplot as plt
import pandas as pd 
from scipy.interpolate import griddata
from math import log, exp, tan, atan, pi, radians, sin, cos, atan2, sqrt
import yelp
import time

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



def scrape_yelp(term, location, lat, lng, mode=default_mode):
        
    location = location.replace(',','')
    try:
        response = yelp.yelp_search(term, location)
    except:
        print 'Yelp search failed for this location: '+location
        err = {'search':term,'id':None, 'business name':None, 'business lat':None, 'business lng':None, 'rating':None,'oauth2-ascii-error':False, 'error':True,'error-message':'Yelp search failed'}        
        return pd.DataFrame([err,err,err])
        
    businesses = response.get('businesses')
    if not businesses:
        print 'No businesses found for this location'
        err = {'search':term,'id':None, 'business name':None, 'business lat':None, 'business lng':None, 'rating':None,'oauth2-ascii-error':False, 'error':True,'error-message':'No businesses found for this location'}        
        return pd.DataFrame([err,err,err])

    business = []
    
    for i in xrange(3):
        bus = yelp_business(businesses[i]['id'])
        if not bus['error']:
            if not bus['oauth2-ascii-error']:
                bus['seconds'] = get_travel_time(lat,lng,bus['business lat'],bus['business lng'])  
                bus['score'] = bus['seconds']/(bus['rating']**2) 
            else:
                bus['seconds'] = np.NaN
                bus['score'] = np.NaN
        else:
            bus['seconds'] = np.NaN
            bus['score'] = np.NaN
            
        business.append(bus)
    df = pd.DataFrame(business)
    
    df['search'] = term
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
                         
def map_yelp(my_map_area,searches,old_map_area=None):
    if old_map_area:
        yelp_df = old_map_area.copy()
        first = False
    else:
        first = True
        
    for i in my_map_area.index:
        for search in searches:
        # i is a tuple with (px,py)
            #if old_map_area
            scrape = scrape_yelp(search,my_map_area.xs(i)['address'],my_map_area.xs(i)['lat'],my_map_area.xs(i)['lng'])
            scrape['px'] = i[0]
            scrape['py'] = i[1]
            if first:
                yelp_df = scrape.set_index(['px','py','search'])
                first = False
            else:
                yelp_df = pd.concat([yelp_df, scrape.set_index(['px','py','search'])])
                #yelp = yelp_searches(px,py,search)
    return yelp_df

def merge_yelp(my_map_area,my_map_yelp,mode='mean'):
    for i in my_map_yelp.index:
        if mode == 'mean':
            val = my_map_yelp.xs(i[:-1]).xs(i[-1])['score'].mean()
        elif mode == 'min':
            val = my_map_yelp.xs(i[:-1]).xs(i[-1])['score'].min()
        elif mode == 'max':
            val = my_map_yelp.xs(i[:-1]).xs(i[-1])['score'].max()
        elif mode == 'std':
            val = my_map_yelp.xs(i[:-1]).xs(i[-1])['score'].std()
        else:
            raise NameError
        my_map_area.loc[i[:-1],i[-1]] = val
        my_map_area.loc[i[:-1],i[-1]+'-source'] = 'yelp-'+mode


def get_travel_time(orig_lat,orig_lng,dest_lat,dest_lng,mode='walking'):
    global distance_matrix_key
    url = "https://maps.googleapis.com/maps/api/distancematrix/json?origins="+str(orig_lat)+","+str(orig_lng)+"&destinations="+str(dest_lat)+","+str(dest_lng)+"&mode="+mode+"&language=en-EN&sensor=false&key="+google_api_key[distance_matrix_key]
    try:    
        result= simplejson.load(urllib.urlopen(url))
    except IOError:
        # error that rarely occurs, and it might be because I do more than 100 calls in 10 seconds
        time.sleep(10)
        try:
            result = simplejson.load(urllib.urlopen(url))
        except IOError:
            print 'IOError for origin lat/lng: '+str(orig_lat)+' - '+str(orig_lng)
            return np.NaN
            
            
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
    xsteps_fine = 1
    ysteps_fine = 1
    x_fine,y_fine = np.mgrid[np.min(px):np.max(px):xsteps_fine,np.min(py):np.max(py):ysteps_fine]
    interp = {}
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
        if plot:
            plt.figure()
            plt.imshow(grid)
            plt.title(search)
            plt.figure()
            plt.imshow(grid_mask)
            plt.title(search+' mask')
            
    return x_fine,y_fine,interp
       