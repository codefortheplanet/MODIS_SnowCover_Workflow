# -*- coding: utf-8 -*-
"""
Created on Sat Mar 21 14:47:35 2020

@author: FY
"""

from osgeo import gdal
import pandas as pd
import glob
import numpy as np
import seaborn as sns
import os
import matplotlib.pyplot as plt
#import matplotlib.pyplot as plot
#from matplotlib.ticker import (AutoMinorLocator, MultipleLocator)

#import Terra and Fusion datase
filepathTerra='F:/modis/tiff_out'
filepathFusion='F:/modis/fusion'
fileheader="MOD10A1*.tif"
filelistTerra=glob.glob(os.path.join(filepathTerra,fileheader))
filelistFusion=glob.glob(os.path.join(filepathFusion,fileheader))    
filelist = [list(a) for a in zip(filelistTerra, filelistFusion)]
array1=np.zeros((len(filelist),9))
array2=np.zeros((len(filelist),9))
name1=[]
name2=[]

for i,file in enumerate(filelist):
    raster1 = gdal.Open(file[0], gdal.GA_ReadOnly)
    raster2 = gdal.Open(file[1], gdal.GA_ReadOnly)
    #Driver = gdal.GetDriverByName(raster1.GetDriver().ShortName)
    #X_Size = raster1.RasterXSize
    #Y_Size = raster1.RasterYSize
    #Projection = raster1.GetProjectionRef()
    #GeoTransform = raster1.GetGeoTransform()
    
    # Read the first band as a numpy array
    band1 = raster1.GetRasterBand(1).ReadAsArray()
    band2 = raster2.GetRasterBand(1).ReadAsArray()
   
    # extract the values of the masked array
    bins=np.array([0,100.001,200.001,201.001,211.001,237.001,239.001,250.001,254.001,255.001])
    his1,inter1=np.histogram(band1,bins=bins)
    his2,inter2=np.histogram(band2,bins=bins)
    array1[i,:]=his1
    array2[i,:]=his2
    name1.append(os.path.basename(file[0]))
    name2.append(os.path.basename(file[1]))
    #his_stat=pd.DataFrame(empty2,columns=["snow","missing_nodecision","other_LU","cloud","no_data"])
header=["SENSOR","NAME","NDSI_SNOW_COVER","MISSING_DATA","NO_DECISION","NIGHT","INLAND_WATER","OCEAN","CLOUD","DETECTOR_SATURATED","FILL"]
his_stat1=pd.DataFrame(array1,columns=header[2:])
his_stat1[header[1]]=name1
his_stat1[header[0]]="Terra"
his_stat2=pd.DataFrame(array2,columns=header[2:])
his_stat2[header[1]]=name2
his_stat2[header[0]]="Fusion"   
    
histogram=pd.concat([his_stat1, his_stat2], axis=0, ignore_index=True)
histogram_melt = histogram.melt(id_vars = header[0],
                  value_vars = header[2:-2],
                  var_name = 'columns')
plt.figure(figsize=(40,20))
b = sns.boxplot(data = histogram_melt,
                hue = header[0], # different colors for different 'cls'
                x = 'columns',
                y = 'value',
                order = header[2:-2])
_, ylabels = plt.yticks()
_, xlabels = plt.xticks()
#b.set_yticklabels(ylabels, size=15)
b.set_xticklabels(xlabels, size=25)
plt.legend(fontsize='40', title_fontsize='40')
#sns.title('Boxplot grouped by process types') # You can change the title here
plt.show()