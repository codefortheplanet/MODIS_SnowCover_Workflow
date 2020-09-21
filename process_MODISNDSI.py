# -*- coding: utf-8 -*-
"""
Python script for extracting Normalized Difference Snow Index (NDSI) snow cover raster map from MODIS data 

Created on Thu Apr 16 17:09:18 2020

@author: FY
"""

from osgeo import gdal
import numpy as np
import os
import glob
import subprocess
import pandas as pd
import datetime

#This script is created to automate the process of producing NDSI snow cover map for Alaska from MODIS. The major 
#processes include the selectin of date range based on the input hdf files, extract NDSI sublayer, reproject to WGS84 GCS 
#and merge the result into one raster file for Alaska in geotiff format.     


def extract_filename(startdate_,enddate_,filetyp_,inputpath_,sensordataheader_):
    """Extract the name list of the hdf files and the GeoTiff files by the date range"""    
    #Create a pattern based on the file name to filter the results
    #e.g., MOD10A1.A2016001.h23v02.006.2016183123607.hdf: Year+Julian Day
    pattern = os.path.join(inputpath_,sensordataheader_+".A" + "{:04}" + "{:03}" + filetyp_)
    delta1=datetime.timedelta(days=1)
    delta=enddate_-startdate_
    if filetyp_=="*.hdf" and startdate_ <= enddate_:
        l=[]
        for i in range(delta.days + 1):
            date = startdate_ + i*delta1
            #Extract year and julian day           
            wildcard = pattern.format(date.year,int(date.strftime('%j')))            
            #Store the filename in a list            
            for filename in glob.glob(wildcard):
                l.append(filename)
        return (l)
    elif filetyp_=="*.tif" and startdate_ <= enddate_:
        l=[]
        dates=[]
        for i in range(delta.days + 1):
            date = startdate_ + i*delta1
            #Extract year and julian day 
            wildcard = pattern.format(date.year,int(date.strftime('%j')))
            l_1=[]
            for filename in glob.glob(wildcard):
            #Store the filename in a list (sublist is for merging the raster at the same day)
                l_1.append(filename)                
            #Exclude these days without any swath
            if len(l_1)!=0:
                l.append(l_1)
                dates.append(date)
        return (l,dates)
    else:
        print ("Please provide correct start/end data or correct file type")
        return ()

def hdf_subdataset_extraction(hdflist_, tiffoutdir_, subdataset_):
    """unpack a single subdataset from a HDF5 container and write to GeoTiff"""
    for i in hdflist_:
        # open the dataset
        hdf_ds = gdal.Open(i, gdal.GA_ReadOnly)
        band_ds = gdal.Open(hdf_ds.GetSubDatasets()[subdataset_][0], gdal.GA_ReadOnly)
        
        # read into numpy array
        band_array = band_ds.ReadAsArray().astype(np.uint8)
    
        # build output path
        band_path = os.path.join(tiffoutdir_, os.path.basename(os.path.splitext(i)[0]) + "-sd_" + str(subdataset_) + "_.tif")
    
        # write raster
        out_ds = gdal.GetDriverByName('GTiff').Create(band_path,
                                                      band_ds.RasterXSize,
                                                      band_ds.RasterYSize,
                                                      1,  #Number of bands
                                                      gdal.GDT_Byte, #Data type int8
                                                      ['COMPRESS=LZW', 'TILED=YES'])
        out_ds.SetGeoTransform(band_ds.GetGeoTransform())
        out_ds.SetProjection(band_ds.GetProjection())
        out_ds.GetRasterBand(1).WriteArray(band_array)
        out_ds.GetRasterBand(1).SetNoDataValue(255)
    
        #close dataset to write to disc
        out_ds = None
    return ()

def merge_tiff(tifffile_,tiffdate_,tiffoutdir_,tiffoutdirfinal_,proj_,sensordataheader_):
    """Merge the GeoTiff files of different swath on the same day"""   
    #Define the detailed paramters for gdal.Translate and gdal.Warp 
    kwargs0={'format' : 'GTiff', 'outputType':gdal.GDT_Byte,'creationOptions': ['COMPRESS=LZW', 'TILED=YES']}
    kwargs1 = {'dstSRS':os.path.join(os.path.dirname(proj_),os.path.basename(proj_)[:-4]+'.prj'), 'xRes': 500,'yRes': 500, 
           'multithread': True, 'format': 'GTiff',  'cutlineDSName' : proj_ , 'cropToCutline':True, 'creationOptions': ['COMPRESS=LZW', 'TILED=YES']}
    
    for i,v in enumerate(tifffile_):
        #Create a filelist to merge the tiffs on the same day (different spatial coverage)
        datestr=sensordataheader_+".A"+str(tiffdate_[i].year)+str(tiffdate_[i].month).zfill(2)+str(tiffdate_[i].day).zfill(2)
        filelist=os.path.join(tiffoutdirfinal_,datestr+'.txt')
        with open(filelist, 'w') as filehandle:
            filehandle.writelines("%s\n" % tiff for tiff in v)
            
        output_vitural=os.path.join(tiffoutdir_,datestr+'.vrt')
        output_merge=os.path.join(tiffoutdir_,datestr+'.tif')
        output_clip=os.path.join(tiffoutdirfinal_,datestr+'.tif')

        #Build a virtual raster for each date
        vrt = gdal.BuildVRT(output_vitural, [tiff for tiff in v])
        vrt = None
        #Translate the virtual raster to tiff file
        pro=gdal.Translate(output_merge, output_vitural, **kwargs0)
        pro=None
        #Reproject the virtual raster and generate tiff file (resolution 500 m) and corp the resuts to the interested region and generate output
        out=gdal.Warp(output_clip, output_merge, **kwargs1)
        out=None       
 
        #Delete the merged files (upcroped) from disk 
        os.remove(output_merge)
    return ()
   
if __name__ == '__main__':
    #User input path including the downloaded hdf files for MODIS, start date and end date YYYY-MM-DD

    inputpath='F:/modis/netcdf'
    
    startdate='2016-01-01'
    enddate='2016-01-15'
    
    #Input polygon for processing extent
    inputshp='F:/modis/crop/Alaska.shp'
    
    #Input sensor data header
    sensordataheader='MYD10A1'
    
    #Intermediate data storage path
    tiffoutdir=os.path.join(os.path.dirname(inputpath),"tiff_process")
    
    #Final data result storage path
    tiffoutdirfinal=os.path.join(os.path.dirname(inputpath),"tiff_out")

    if not os.path.exists(tiffoutdir):    
        os.mkdir(tiffoutdir)
        os.mkdir(tiffoutdirfinal)
    filetyp="*.hdf"
    
    #Subset index of HDF file for MODIS NDSI (V6)
    subdataset=0
    
    startdate=pd.to_datetime(startdate, format='%Y-%m-%d')
    enddate=pd.to_datetime(enddate, format='%Y-%m-%d')
    
    hdflist=extract_filename(startdate, enddate, filetyp, inputpath, sensordataheader)
    
    #Extract subdataset from HDF files
    hdf_subdataset_extraction(hdflist, tiffoutdir, subdataset)    
    
    #Extract the list of tiff files and corresponding dates
    tifflist,tiffdate=extract_filename(startdate,enddate,"*.tif",tiffoutdir,sensordataheader)
    
    #Merge and reproject the tiff files
    merge_tiff(tifflist,tiffdate,tiffoutdir,tiffoutdirfinal,inputshp,sensordataheader)
    
