# -*- coding: utf-8 -*-
"""
Created on Mon Sep 18 09:02:17 2017

@author: Mohd. Talha Pawaty
"""
from rasterstats import zonal_stats
from geopandas import GeoDataFrame
import numpy as np
import xlsxwriter, xlrd
import subprocess
import os, fnmatch, gzip, datetime
import MySQLdb

def run_win_cmd(cmd):
    result = []
    process = subprocess.Popen(cmd,
                               shell=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    for line in process.stdout:
        result.append(line)
    errcode = process.returncode
    for line in result:
        print(line)
    if errcode is not None:
        raise Exception('cmd %s failed, see above for details', cmd)
        
#Counting number of files   
nowDate = datetime.datetime(2018,6,25)
numberOfFiles = len(fnmatch.filter(os.listdir('<Path of to your .nc4 files>'), '*.nc4'))
files = (fnmatch.filter(os.listdir('<Path of to your .nc4 files>'), "*2018*"))

for i in range(numberOfFiles):          #In place of 1 we will put variable numberOfFiles so that for loop run accordingly
    nowDate += datetime.timedelta(days=1)
    date = nowDate.strftime("%Y%m%d")
    moisturedate = nowDate.strftime("%Y-%m-%d")
    fileName = files[i]
    
    #creating cmd
    vrt1 = "gdal_translate -of VRT NETCDF:"+fileName+":soil_moisture_c1 vrt1.vrt"
    #calling function which help to run terminal command
    run_win_cmd(vrt1)
    
    #creating cmd
    vrt2 = "gdal_translate -of VRT -gcp 0 0 360 -90 -gcp 1800 0 360 90 -gcp 0 3600 0 -90 -gcp 1800 3600 0 90 vrt1.vrt vrt2.vrt"
    #calling function which help to run terminal command
    run_win_cmd(vrt2)
    
    warp = "gdalwarp -r bilinear -t_srs EPSG:4326 vrt2.vrt test.tif"
    run_win_cmd(warp)
    
    proj = "gdal_translate -a_ullr -180 -90 180 90 test.tif output.tif"
    run_win_cmd(proj)
    
    reproj = "gdalwarp -t_srs WGS84 output.tif "+moisturedate+".tif"
    run_win_cmd(reproj)
    
    # applying .shp formate file on genrated .tiff file
    tif_file =  "C:/Users/Talha/Documents/districtSoil/"+moisturedate+".tif"
    stats = zonal_stats("C:\Users\Talha\Documents\districtSoil\MHshapFile\Maha_Dist_Taluka_Code.shp", "C:/Users/Talha/Documents/districtSoil/"+moisturedate+".tif",geojson_out=True)
    #storing GeoDataFrame in variable stats1
    geo_data = GeoDataFrame.from_features(stats) 
    tif_file = np.array(geo_data) 
    #converting geodata into numpy array
    geo_data_arr = np.array(tif_file[:,[0,1,2,3,7]]) #slicing array
 
    # further process is for createing xls file and writing data in it 
    xlsxName = moisturedate+".xlsx"     
    workbook = xlsxwriter.Workbook(xlsxName,{'nan_inf_to_errors': True})
    worksheet = workbook.add_worksheet()
    worksheet.write('A1', 'District Code')
    worksheet.write('B1', 'District')
    worksheet.write('C1', 'Taluka Code')
    worksheet.write('D1', 'Taluka')
    worksheet.write('E1', 'Soil Moisture')
    col = 0
    for row, data in enumerate(geo_data_arr):
        worksheet.write_row(row + 1, col, data)
    workbook.close()
    book = xlrd.open_workbook("C:/Users/Talha/Documents/districtSoil/"+xlsxName)
    sheet = book.sheet_by_name("Sheet1")
    
    # Create data base connection 
    database = MySQLdb.connect (host="localhost", user = "aasuser", passwd = "aasuser1", db="aas")
    cursor = database.cursor()

    for r in range(1, sheet.nrows):
        districtCode = sheet.cell(r,1).value
        district = sheet.cell(r,0).value
        districtName = district.strip()
        talukaCode = sheet.cell(r,3).value
        taluka = sheet.cell(r,2).value
        talukaName = taluka.strip()
        soilmoisture = sheet.cell(r,4).value
        cursor.execute("select talukacode from mastertaluka where talukaname = '"+talukaName+"'")
        res = cursor.fetchone()
        if res == None:
            print "I am absent"
            continue
        else:
            cursor.execute("INSERT INTO soilmoisture(districtcode,districtname,talukacode,soilmoisture,moisturedate) values (%s,%s,%s,%s,%s)",(districtCode,districtName,talukaCode,soilmoisture,moisturedate))
    print ("Data Successfully Inserted!!!")
    cursor.close()
    database.commit()
    database.close()
    os.remove("vrt1.vrt")
    os.remove("vrt2.vrt")
    os.remove("test.tif")
    os.remove("output.tif")
