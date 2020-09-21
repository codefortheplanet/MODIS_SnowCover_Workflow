# -*- coding: utf-8 -*-
"""
Created on Fri Mar 20 17:24:18 2020

@author: FY
"""
#This script is created to minimize the cloud effect of NDSI from MODIS Terra data by fusion with MODIS Aqua 
#The basic approach is to fill the "holes" where the majority of the neiboring pixels for a cloud pixel are visible
#Then, this pixel is calculated by averaging the NDSI values of the neiboring pixels     

import os
import glob
import numpy as np
from osgeo import gdal
from scipy.signal import convolve2d


def ta_merge(outpath_,filelist_):    

    for i in filelist_:
        terra=i[0]
        aqua=i[1]
        outputImage = os.path.join(outpath_,os.path.basename(terra[:-4])+"_fusion.tif")        
        raster1 = gdal.Open(terra, gdal.GA_ReadOnly)
        raster2 = gdal.Open(aqua, gdal.GA_ReadOnly)
        #Driver = gdal.GetDriverByName(raster1.GetDriver().ShortName)
        #X_Size = raster1.RasterXSize
        #Y_Size = raster1.RasterYSize
        #Projection = raster1.GetProjectionRef()
        #GeoTransform = raster1.GetGeoTransform()
        
        # Read the first band as a numpy array
        band1 = raster1.GetRasterBand(1).ReadAsArray()
        band2 = raster2.GetRasterBand(1).ReadAsArray()
        
        # Create a new array of the same shape and fill with zeros
        newClass1 = np.zeros_like(band1).astype('uint8')
        newClass2 = np.zeros_like(band2).astype('uint8')
        
        # Reclassify the pixels based on the interpretation of Terra and Aqua NDSI values for further processing 
        
        newClass1 = np.where(((band1 == 211) | (band1 == 250)), 1, newClass1) # Reclassify night and cloud pixel as 1
        newClass1 = np.where(((band1 == 200) | (band1 == 254) | (band1 == 255)), 2, newClass1) # Reclassify missing and other defected pixel as 2
        newClass1 = np.where(((band1 <= 100)), 3, newClass1) # Reclassify NDSI snow cover pixel as 3
        newClass1 = np.where(((band1 == 237) | (band1 == 239)), 4, newClass1) # Reclassify water pixel as 4
        newClass1 = np.where(((band1 == 201)), 5, newClass1) # Reclassify not classified pixel as 5
        
        newClass2 = np.where(((band2 == 211) | (band2 == 250)), 1, newClass2) # Reclassify night and cloud pixel as 1
        newClass2 = np.where(((band2 == 200) | (band2 == 254) | (band2 == 255)), 2, newClass2) # Reclassify missing and other defected pixel as 2
        newClass2 = np.where(((band2 <= 100)), 3, newClass2) # Reclassify NDSI snow cover pixel as 3
        newClass2 = np.where(((band2 == 237) | (band2 == 239)), 4, newClass2) # Reclassify water pixel as 4
        newClass2 = np.where(((band2 == 201)), 5, newClass2) # Reclassify not classified pixel as 5
        
        #Create a mask for the pixels of 1, 2, 5 in terra but pixels of 3 (snow) in aqua
        newClass1[((newClass1==1) | (newClass1==2) | (newClass1==5)) & (newClass2==3)]=30
        
        #newClass1[(newClass1==1) | (newClass1==2) | (newClass1==5) & ((newClass2!=3) & (newClass2!=4))]=1
        #Update aqua NDSI snow cover pixels to terra (exclude water pixel), or change pixels of cloud, missing or unassigned in Terra to available values in Aqua

        band1=np.where(newClass1==30,band2,band1)
 
        #Convert the mask of snow from aqua back to 3
        newClass1[newClass1==30]=3
        
        #Convolution operator on the mask for assigning the majority of neighboring pixels of clould, error or missing to snow
        newClass1=fill_pixel(newClass1)
               
        #Calculate the new snow pixel NDSI based on the average of neighboring NDSI
        band1=ave_NDSI(newClass1,band1)
              
        #Export the updated values to raster:
        outImage = gdal.GetDriverByName('GTiff').Create(outputImage,
                                                      raster1.RasterXSize,
                                                      raster1.RasterYSize,
                                                      1,  #Number of bands
                                                      gdal.GDT_Byte, #Data type int8
                                                      ['COMPRESS=LZW', 'TILED=YES'])
        outImage.SetProjection(raster1.GetProjectionRef())
        outImage.SetGeoTransform(raster1.GetGeoTransform())
        outBand = outImage.GetRasterBand(1)
        outBand.SetNoDataValue(255)
        outBand.WriteArray(band1)
        outImage = None
    #del NewClass
    #print("Done.")
    return()


def fill_pixel(pixelclass):
    # Mask of NaNs
    nan_mask = (pixelclass==1) | (pixelclass==2) | (pixelclass==4) | (pixelclass==5)  
    pixelclass3=(pixelclass==3)*1
    # Convolution kernel. Center cell is set to zero to exclude from the calculation.
    kernel = np.ones((3,3),dtype='uint8')
    kernel[1,1]=0

    # Get count of 3s for each kernel window
    ones_count = convolve2d(np.where(nan_mask,0,pixelclass3),kernel,'same')

    # Get count of valid elements per window in the input mask and hence non NaNs count
    n_elem = convolve2d(np.ones(pixelclass.shape,dtype=int),kernel,'same')
    nonNaNs_count = n_elem - convolve2d(nan_mask,kernel,'same')

    # Compare 1s count against half of nonNaNs_count for the first mask.
    # This tells us if 1s are majority among non-NaNs population.
    # Second mask would be for pixels with values of 1, 2 and 5. Use Combined mask to set the locations that need update.
    final_mask = (ones_count > nonNaNs_count/2.0) & ((pixelclass==1) | (pixelclass==2) | (pixelclass==5))
    return (np.where(final_mask,33,pixelclass))

def ave_NDSI(pixelclass,data):
    #Compute the avarage value of the filled pixel of snow by its neiboring pixels
    kernel = np.ones((3, 3))
    kernel[1, 1] = 0
    x=data*(pixelclass==3)
    y=(pixelclass==3)*1
    neighbor_sum = convolve2d(x, kernel, mode='same', boundary='fill', fillvalue=0)
    num_neighbor = convolve2d(y, kernel, mode='same', boundary='fill', fillvalue=0)   
    data1 = np.where ((pixelclass==33),(neighbor_sum / num_neighbor),data) 

    return (data1)

if __name__ == '__main__':
    #File path including both MODIS Terra and Auqa
    filepath='F:/modis/tiff_out'    
    filelistTerra=glob.glob(os.path.join(filepath,"MOD10A1*.tif"))
    filelistAqua=glob.glob(os.path.join(filepath,"MYD10A1*.tif"))    
    filelist = [list(a) for a in zip(filelistTerra, filelistAqua)]
    outpath=os.path.join(os.path.join(filepath, os.pardir),'fusion')
    if not os.path.exists(outpath):    
        os.mkdir(outpath)
    ta_merge(outpath,filelist)
