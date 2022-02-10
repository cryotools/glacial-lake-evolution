"""
    ##########################
    ## Future glacial lakes ##
    ##########################

    This is the main code file of the second work package of the project
    'Future glacial lakes in High Mountain Asia - Modeling and Risk Analysis' (GLAMoR).
    It was used for the main analyses of the Frontiers in Earth Science publication by Furian et al. (2022).
    The script was written by W. Furian.

    With this script, it is possible to use the results of a glacier model
    to investigate the expected exposure of subglacial overdeepenings to quantify the future
    development of glacial lake area and volume.

    In order to run properly, this script requires different datasets to be downloaded:
    - In principle, this code can be modified to use inputs of different glacier models,
      when in the appropriate format. However, we recommend using OGGM due to its ability
      to simulate glacier ice dynamics.
      OGGM can be downloaded at oggm.org and the specific OGGM runs employed by us are available here:
      https://cluster.klima.uni-bremen.de/~fmaussion/lt_archive/run_hma_hr_cmip6_v1.
    - The required glacier outlines in shapefile format are downloadable from the Randolph Glacier Inventory, v6
      (https://www.glims.org/RGI/)
    - To investigate future lake development, a dataset containing the extent of potential future lakes is needed.
      We used the dataset developed in this publication: https://doi.org/10.1017/jog.2021.18 (Furian et al., 2021).
    - Also needed is a DEM of the glacier bedrock - for studies in high mountain areas we recommend using the ALOS World 3D 30m
      DEM by JAXA and subtracting from it the ice thickness dataset by Farinotti et al. (2019).
    - With the latter input data, a triangular irregular network (TIN) can be calculated and then used
      to quantify potential lake volume.

    The required folder structure should follow these guidelines:
        - a folder containing the centerlines produced by OGGM
        - folders containing the results of the OGGM runs (one folder for each GCM)
        - a folder for every glacier with a subglacial overdeepening (named after its RGI-ID),
          containing the extracted GCM results for the respective glacier in every SSP scenario in csv-format
        - the RGI glacier shapefile
        - an empty folder for the data to be stored in (please make sure that enough disk space is available -
          depending on the RGI region several GB of data will be stored in the process)

    The model is written in Python 2.7 and has been tested with ArcGIS 10.7 and PyCharm CE 2021.2.4.
    It needs the following ArcGIS extensions to be enabled:
    3D Analyst, Spatial Analyst and Geostatistical Analyst.

    This code is available on github at https://github.com/cryotools/glacial-lake-evolution
    For more information on this work package see the README.
    For more information on the project as a whole see https://hu-berlin.de/glamor.

    You are allowed to use and modify this code in a noncommercial manner and by
    appropriately citing the above mentioned developer. If you would like to share your own improvements,
    please fork the repository on GitHub, commit your changes, and file a merge request.

    Correspondence: furiawil@geo.hu-berlin.de
"""
# imports
import os
import sys
import arcpy
from arcpy import env
from arcpy.sa import *
import pandas as pd
import re
import math
import shutil
from testing.CalculatePerpendicularLinesAtLineEndNodes import *     # tool by G. Gabrisch, Two-Bit Algorithms (2011)

# housekeeping
arcpy.env.overwriteOutput = True
arcpy.CheckOutExtension("Spatial")
arcpy.CheckOutExtension("3D")
arcpy.CheckOutExtension("GeoStats")

# starting the analysis
rgi = "14"  # enter the respective RGI region number
data_path = "E:~{}".format(rgi)
for root, directories, files in os.walk(data_path):
    for folder in directories:
        if folder.startswith("RGI60-{}".format(rgi)):
            rgiid = folder
            glacier_path = os.path.join(data_path, rgiid)
            # read centerline, give appropriate coordinate system
            centerline = os.path.join(glacier_path, "centerline.shp")
            centerline_proj = os.path.join(glacier_path, "centerline_proj.shp")
            for row in arcpy.da.SearchCursor(centerline, ["RGIID"]):
                rgiid = row[0]
            coor_path = "~".format(rgi, rgiid)
            out_coor = arcpy.Describe(coor_path).spatialReference
            arcpy.Project_management(in_dataset=centerline,
                                     out_dataset=centerline_proj,
                                     out_coor_system=out_coor)
            # project glacier shp
            arcpy.Project_management(in_dataset=os.path.join(glacier_path, "glacier_noproj.shp"),
                                     out_dataset=os.path.join(glacier_path, "glacier.shp"),
                                     out_coor_system=out_coor)

            # get relevant sinks
            sinks = "~"  # give the path to the shapefile containing the different subglacial overdeepenings
            arcpy.Clip_analysis(in_features=sinks,
                                clip_features=os.path.join(glacier_path, "glacier.shp"),
                                out_feature_class=os.path.join(glacier_path, "sinks.shp"))

            #######################
            # make calculations for all GCM runs
            path = "~{}".format(rgi)  # give the path to the folder with the different GCM runs
            # list all GCM run folders
            folders = [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
            gcm_overfolder = os.path.join(glacier_path, "GCM_results")
            try:
                os.mkdir(gcm_overfolder)
            except OSError:
                pass
            # loop through all the GCMs
            for i in folders:
                GCM_run = i
                GCM_path = "~{}/{}".format(rgi, GCM_run)  # give the path to the individual GCM folder
                # list all available SSP scenarios for the current GCM
                ssp_list = []
                for f in os.listdir(GCM_path):
                    for number in ["126", "245", "370", "585"]:  # take only the four chosen SSP scenarios
                        if f.endswith(number + ".nc"):
                            ssp_list.append(f[-9:-3])
                # create GCM folder in glacier folder
                gcm_folder = os.path.join(gcm_overfolder, "{}".format(i))
                try:
                    os.mkdir(gcm_folder)
                except OSError:
                    pass
                TINerror = False
                # loop through all SSP scenarios for each GCM
                for ssp in ssp_list:
                    if TINerror:
                        break
                    ssp_folder = os.path.join(gcm_folder, "{}".format(ssp))
                    try:
                        os.mkdir(ssp_folder)
                    except OSError:
                        pass
                    tmp_folder = os.path.join(ssp_folder, "tmp")
                    try:
                        os.mkdir(tmp_folder)
                    except OSError:
                        pass
                    perp_folder = os.path.join(ssp_folder, "perpendiculars")
                    try:
                        os.mkdir(perp_folder)
                    except OSError:
                        pass
                    point_folder = os.path.join(ssp_folder, "front_points")
                    try:
                        os.mkdir(point_folder)
                    except OSError:
                        pass

                    # calculate new length of centerline / calculate amount of glacier retreat depending on RCP
                    # take the csv-file of the current GCM and the current SSP
                    GCM_csv = os.path.join(glacier_path, "GCM_runs", GCM_run, GCM_run + "_" + ssp + ".csv")
                    GCM_data = pd.read_csv(GCM_csv)
                    GCM_data["length"].to_csv(os.path.join(ssp_folder, "lengths.csv"),
                                              header="length", index=False)
                    GCM_data["calendar_year"].to_csv(os.path.join(ssp_folder, "years.csv"),
                                                     header="year", index=False)
                    GCM_data["terminus_thick_0"].to_csv(os.path.join(ssp_folder, "terminus_thick_0.csv"),
                                                        header="terminus_thick_0", index=False)
                    # load csv files
                    data = pd.read_csv(os.path.join(ssp_folder, "years.csv"), names=["year"])
                    data1 = pd.read_csv(os.path.join(ssp_folder, "lengths.csv"), names=["length"])
                    TT_0 = pd.read_csv(os.path.join(ssp_folder, "terminus_thick_0.csv"), names=["terminus_thick_0"])
                    # select every nth year (here: n=10)
                    years = data["year"][1:].tolist()[11::10]
                    years = years[:8]  # exclude all years after 2100
                    length = data1["length"][1:].tolist()[1::10]
                    length = length[:9]  # exclude the length of all years after 2100
                    # extract glacier ice thickness directly above terminus
                    TT_0 = TT_0["terminus_thick_0"][1:].tolist()[1::10]
                    del data, data1

                    # check for empty GCM csv files which indicate error in the OGGM routines
                    glacier_error = False
                    check = float(length[0])
                    if math.isnan(check):
                        print "========\nAn error occurred.\nSkipping GCM: {}!\n========".format(GCM_run)
                        error_folder = os.path.join(glacier_path, "GCM_error")
                        try:
                            os.mkdir(error_folder)
                        except OSError:
                            pass
                        shutil.move(gcm_folder, os.path.join(error_folder, GCM_run))
                        break
                    else:
                        # calculate length of current glacier
                        current_length = [f[0] for f in arcpy.da.SearchCursor(centerline_proj, 'SHAPE@LENGTH')][0]
                        print "==       calculate frontal points"
                        for j in range(len(length))[:-1]:
                            year = years[j]
                            ablation = float(length[0]) - float(length[j + 1])
                            distance = current_length - ablation
                            if round(distance, 0) >= round(current_length, 0):
                                print "====       Glacier either stationary or growing!\n" \
                                      "====       Skipping {}!\n\n".format(str(year))
                                continue

                            if length[j] == "0.0":
                                print "====       Glacier is completely gone! All sinks are exposed.\n"
                                sink_folder = os.path.join(ssp_folder, "icefree_sinks")
                                sink_folder_year = os.path.join(sink_folder, "{}".format(year))
                                try:
                                    os.mkdir(sink_folder)
                                except OSError:
                                    pass
                                try:
                                    os.mkdir(sink_folder_year)
                                except OSError:
                                    pass
                                all_sinks = os.path.join(sink_folder_year, "VOL_all_sinks.shp")
                                arcpy.CopyFeatures_management(os.path.join(glacier_path, "sinks.shp"),
                                                              all_sinks)
                                continue

                            arcpy.CreateFeatureclass_management(out_path=point_folder,
                                                                out_name="front_point{}.shp".format(str(year)),
                                                                geometry_type="POINT",
                                                                spatial_reference=out_coor)
                            for row in arcpy.da.SearchCursor(centerline_proj, ["SHAPE@"], spatial_reference=out_coor):
                                point = row[0].positionAlongLine(distance, False)
                                cursor = arcpy.da.InsertCursor(os.path.join(point_folder,
                                                                            "front_point{}.shp".format(str(year))),
                                                               ["SHAPE@"])
                                cursor.insertRow([point])
                                del cursor

                        arcpy.FeatureVerticesToPoints_management(in_features=centerline_proj,
                                                                 out_feature_class=os.path.join(ssp_folder,
                                                                                                "centerpoints.shp"))

                        point_folder = os.path.join(ssp_folder, "front_points")
                        centerpoints = os.path.join(ssp_folder, "centerpoints.shp")
                        for filename in os.listdir(point_folder):
                            if filename.endswith("shp") and filename.startswith("front"):
                                year = str(re.findall(r'\d+', filename)[0])
                                arcpy.Near_analysis(in_features=centerpoints,
                                                    near_features=os.path.join(point_folder, filename))
                                with arcpy.da.SearchCursor(centerpoints, ["NEAR_DIST"]) as cursor:
                                    min = sorted({row[0] for row in cursor})[:1]
                                for row in arcpy.da.SearchCursor(centerpoints, ["NEAR_DIST", "FID"]):
                                    if row[0] == min[0]:
                                        id = row[1]
                                arcpy.CopyFeatures_management(os.path.join(point_folder, filename),
                                                              os.path.join(tmp_folder, "line_point1.shp"))
                                arcpy.Select_analysis(centerpoints, os.path.join(tmp_folder, "line_point2.shp"),
                                                      where_clause="FID = {}".format(id - 5))
                                if int(arcpy.GetCount_management(os.path.join(tmp_folder, "line_point2.shp"))[0]) == 0:
                                    arcpy.Select_analysis(centerpoints, os.path.join(tmp_folder, "line_point2.shp"),
                                                          where_clause="FID = {}".format(
                                                              id + 5))
                                arcpy.Merge_management(inputs=[os.path.join(tmp_folder, "line_point2.shp"),
                                                               os.path.join(tmp_folder, "line_point1.shp")],
                                                       output=os.path.join(tmp_folder, "points.shp"))
                                arcpy.PointsToLine_management(Input_Features=os.path.join(tmp_folder, "points.shp"),
                                                              Output_Feature_Class=os.path.join(tmp_folder, "line.shp"))
                                perp_line = os.path.join(perp_folder, "frontline{}.shp".format(year))
                                perpendicularLine(infc=os.path.join(tmp_folder, "line.shp"),
                                                  outfc=perp_line)

                                sink_folder = os.path.join(ssp_folder, "icefree_sinks")
                                sink_folder_year = os.path.join(sink_folder, "{}".format(year))
                                try:
                                    os.mkdir(sink_folder)
                                except OSError:
                                    pass
                                try:
                                    os.mkdir(sink_folder_year)
                                except OSError:
                                    pass
                                arcpy.Near_analysis(in_features=os.path.join(glacier_path, "sinks.shp"),
                                                    near_features=os.path.join(point_folder, filename))

                                frontal_sink = False
                                with arcpy.da.SearchCursor(os.path.join(glacier_path, "sinks.shp"),
                                                           ["NEAR_DIST", "sinkNr"]) as cursor:
                                    for row in cursor:
                                        if row[0] == 0:
                                            sinkNr = str(row[1])
                                            partial_sink = os.path.join(sink_folder_year, "partial_sink.shp")
                                            arcpy.Select_analysis(in_features=os.path.join(glacier_path, "sinks.shp"),
                                                                  out_feature_class=partial_sink,
                                                                  where_clause="NEAR_DIST = {}".format(row[0]))
                                            frontal_sink = True

                                            # get lake depth at frontal_point
                                            bedrock = Raster("~")   # provide path to a DEM (e.g., AW3D30)
                                            ExtractValuesToPoints(in_point_features=os.path.join(point_folder,
                                                                                                 filename),
                                                                  in_raster=bedrock,
                                                                  out_point_features=os.path.join(tmp_folder,
                                                                                                  "elevation.shp"))
                                            with arcpy.da.SearchCursor(partial_sink, "MAX") as cursor:
                                                for row in cursor:
                                                    max_elevation = row[0]
                                            with arcpy.da.SearchCursor(os.path.join(tmp_folder, "elevation.shp"),
                                                                       "RASTERVALU") as cursor:
                                                for row in cursor:
                                                    min_elevation = row[0]
                                            del cursor
                                            depth = max_elevation - min_elevation

                                            def new_frontal_point(run_nr):
                                                if float(TT_0[run_nr]) > depth:
                                                    print "{} > {}".format(TT_0[run_nr], depth)
                                                    print "continuing with normal routine"
                                                    pass
                                                elif float(TT_0[run_nr]) < depth:
                                                    print "{} < {}".format(TT_0[run_nr], depth)
                                                    print "create new perpendicular line 50m (1 point) up the glacier"
                                                    arcpy.CreateFeatureclass_management(out_path=tmp_folder,
                                                                                        out_name="new_line.shp",
                                                                                        geometry_type="POLYLINE",
                                                                                        spatial_reference=out_coor)
                                                    line = os.path.join(tmp_folder, "line.shp")
                                                    line_length = \
                                                    [l[0] for l in arcpy.da.SearchCursor(line, 'SHAPE@LENGTH')][0]
                                                    for row in arcpy.da.UpdateCursor(line, "SHAPE@",
                                                                                     spatial_reference=out_coor):
                                                        new_line = row[0].segmentAlongLine(0, line_length - 50, False)
                                                        cursor1 = arcpy.da.InsertCursor(os.path.join(tmp_folder,
                                                                                                     "new_line.shp"),
                                                                                        ["SHAPE@"])
                                                        cursor1.insertRow([new_line])
                                                        del cursor1
                                                    global new_perp_line
                                                    new_perp_line = os.path.join(perp_folder,
                                                                                 "new_frontline{}.shp".format(year))
                                                    perpendicularLine(infc=os.path.join(tmp_folder, "new_line.shp"),
                                                                      outfc=new_perp_line)
                                                    arcpy.Intersect_analysis(
                                                        in_features=[os.path.join(tmp_folder, "new_line.shp"),
                                                                     partial_sink],
                                                        out_feature_class=os.path.join(tmp_folder, "intersect.shp"))
                                                    if int(arcpy.GetCount_management(
                                                            os.path.join(tmp_folder, "intersect.shp"))[0]) == 0:
                                                        frontal_sink = False
                                            if year == "2030":
                                                new_frontal_point(1)
                                            elif year == "2040":
                                                new_frontal_point(2)
                                            elif year == "2050":
                                                new_frontal_point(3)
                                            elif year == "2060":
                                                new_frontal_point(4)
                                            elif year == "2070":
                                                new_frontal_point(5)
                                            elif year == "2080":
                                                new_frontal_point(6)
                                            elif year == "2090":
                                                new_frontal_point(7)
                                            elif year == "2100":
                                                new_frontal_point(8)

                                new_line = False
                                for filename1 in os.listdir(perp_folder):
                                    if filename1.endswith("{}.shp".format(year)) and filename1.startswith("new"):
                                        new_line = True
                                if frontal_sink:
                                    output = os.path.join(tmp_folder, "clipped_lake.shp")
                                    if new_line:
                                        arcpy.FeatureToPolygon_management(in_features=[new_perp_line, partial_sink],
                                                                          out_feature_class=output,
                                                                          attributes="ATTRIBUTES")
                                    arcpy.FeatureToPolygon_management(in_features=[perp_line, partial_sink],
                                                                      out_feature_class=output,
                                                                      attributes="ATTRIBUTES")
                                    arcpy.DeleteField_management(in_table=output,
                                                                 drop_field=["AREA", "MIN", "MAX", "RANGE", "MEAN",
                                                                             "SUM", "MAX_round", "Volume", "SArea"])
                                    output2 = os.path.join(tmp_folder, "clipped_lake2.shp")
                                    arcpy.Identity_analysis(in_features=output,
                                                            identity_features=partial_sink,
                                                            out_feature_class=output2)
                                    with arcpy.da.SearchCursor(output2, ["FID", "FID_part_1"]) as cursor:
                                        n = 1
                                        for row in cursor:
                                            if row[1] >= 0:
                                                FID = row[0]
                                                sinkpart = os.path.join(tmp_folder, "sinkpart{}.shp".format(str(n)))
                                                arcpy.Select_analysis(output2, sinkpart,
                                                                      where_clause="FID = {}".format(FID))
                                                n = n + 1
                                    arcpy.Near_analysis(in_features=os.path.join(tmp_folder, "line_point2.shp"),
                                                        near_features=os.path.join(tmp_folder, "sinkpart1.shp"))
                                    with arcpy.da.SearchCursor(os.path.join(tmp_folder, "line_point2.shp"),
                                                               ["NEAR_DIST"]) as cursor:
                                        for row in cursor:
                                            distance_lakepart1 = row[0]
                                    arcpy.Near_analysis(in_features=os.path.join(tmp_folder, "line_point2.shp"),
                                                        near_features=os.path.join(tmp_folder, "sinkpart2.shp"))
                                    with arcpy.da.SearchCursor(os.path.join(tmp_folder, "line_point2.shp"),
                                                               ["NEAR_DIST"]) as cursor:
                                        for row in cursor:
                                            distance_lakepart2 = row[0]
                                    del cursor
                                    partial_sink_clip = os.path.join(sink_folder_year, "VOL_partial_sink.shp")
                                    if distance_lakepart1 > distance_lakepart2:
                                        arcpy.CopyFeatures_management(os.path.join(tmp_folder, "sinkpart1.shp"),
                                                                      partial_sink_clip)
                                    elif distance_lakepart2 > distance_lakepart1:
                                        arcpy.CopyFeatures_management(os.path.join(tmp_folder, "sinkpart2.shp"),
                                                                      partial_sink_clip)

                                    TIN_folder = os.path.join(ssp_folder, "TINs")
                                    try:
                                        os.mkdir(TIN_folder)
                                    except OSError:
                                        pass
                                    TIN_folder_year = os.path.join(TIN_folder, "{}".format(year))
                                    try:
                                        os.mkdir(TIN_folder_year)
                                    except OSError:
                                        pass

                                    TIN_in = "~"    # provide a path to a TIN of the overdeepening
                                    TIN_out = os.path.join(TIN_folder_year, "TIN{}".format(sinkNr))
                                    arcpy.CopyTin_3d(in_tin=TIN_in,
                                                     out_tin=TIN_out)
                                    arcpy.DeleteField_management(in_table=partial_sink_clip,
                                                                 drop_field=["Volume", "SArea"])
                                    try:
                                        arcpy.PolygonVolume_3d(in_surface=TIN_out,
                                                               in_feature_class=partial_sink_clip,
                                                               in_height_field="MAX",
                                                               reference_plane="BELOW",
                                                               out_volume_field="Volume",
                                                               surface_area_field="SArea",
                                                               pyramid_level_resolution="0")
                                    except arcpy.ExecuteError:
                                        gdb_sink_clip = "~"
                                        arcpy.CopyFeatures_management(partial_sink_clip,
                                                                      gdb_sink_clip)
                                        try:
                                            arcpy.PolygonVolume_3d(in_surface=TIN_out,
                                                                   in_feature_class=gdb_sink_clip,
                                                                   in_height_field="MAX",
                                                                   reference_plane="BELOW",
                                                                   out_volume_field="Volume",
                                                                   surface_area_field="SArea",
                                                                   pyramid_level_resolution="0")
                                            arcpy.Delete_management(partial_sink_clip)
                                            arcpy.CopyFeatures_management(gdb_sink_clip,
                                                                          partial_sink_clip)
                                        except arcpy.ExecuteError:
                                            TINerror = True
                                            TINerror_folder = os.path.join(glacier_path, "GCM_TIN_error")
                                            try:
                                                os.mkdir(TINerror_folder)
                                            except OSError:
                                                pass
                                            shutil.move(gcm_folder, os.path.join(TINerror_folder, GCM_run))
                                            break

                                elif not frontal_sink:
                                    print "=       No sink found at glacier front."
                                if frontal_sink:
                                    for row in arcpy.da.SearchCursor(partial_sink_clip, ["MAX_round", "sinkNr_1"]):
                                        altitude_lake = row[0]
                                        sinkNr = row[1]
                                    for row in arcpy.da.SearchCursor(os.path.join(glacier_path, "sinks.shp"),
                                                                     ["MAX_round", "sinkNr"]):
                                        if row[0] < altitude_lake and row[1] != sinkNr:
                                            sinkID = row[1]
                                            print "=        Melting has exposed sink Nr {}".format(sinkID)
                                            exposed_sinks_new = os.path.join(sink_folder_year,
                                                                             "VOLsink_{}.shp".format(sinkID))
                                            arcpy.Select_analysis(os.path.join(glacier_path, "sinks.shp"),
                                                                  exposed_sinks_new,
                                                                  where_clause="sinkNr = '{}'".format(sinkID))

                                elif not frontal_sink:
                                    bedrock = os.path.join("E:/01_Daten_Paper01/01_sink_volume/RGI60-{}/"
                                                           "wz_Dummies".format(rgi),
                                                           rgiid.replace(".", "_"), "area_bedrock.tif")
                                    if new_line:
                                        midpoint = os.path.join(point_folder, "newest_front_point{}.shp".format(
                                            str(year)))
                                        arcpy.FeatureVerticesToPoints_management(new_perp_line, midpoint, "MID")
                                        # avoiding ArcInfo license:
                                        # midpoint = os.path.join(point_folder, "new_front_point{}.shp".format(
                                        #                                         str(year)))
                                        # arcpy.CreateFeatureclass_management(out_path=point_folder,
                                        #                                     out_name="new_front_point{}.shp".format(
                                        #                                         str(year)),
                                        #                                     geometry_type="POINT",
                                        #                                     spatial_reference=out_coor)
                                        # with arcpy.da.SearchCursor(new_perp_line, "SHAPE@") as in_cursor, \
                                        #         arcpy.da.InsertCursor(midpoint, "SHAPE@") as out_cursor:
                                        #     for row in in_cursor:
                                        #         midpoint = row[0].positionAlongLine(0.50, True).firstPoint
                                        #         out_cursor.insertRow([midpoint])
                                        # del in_cursor
                                        # del out_cursor
                                        ExtractValuesToPoints(in_point_features=midpoint,
                                                              in_raster=bedrock,
                                                              out_point_features=os.path.join(tmp_folder,
                                                                                              "altitudeFront.shp"))

                                    ExtractValuesToPoints(in_point_features=os.path.join(point_folder, filename),
                                                          in_raster=bedrock,
                                                          out_point_features=os.path.join(tmp_folder,
                                                                                          "altitudeFront.shp"))
                                    for row in arcpy.da.SearchCursor(os.path.join(tmp_folder, "altitudeFront.shp"),
                                                                     ["RASTERVALU"]):
                                        altitude_front = int(math.floor(row[0]))
                                    for row in arcpy.da.SearchCursor(os.path.join(glacier_path, "sinks.shp"),
                                                                     ["MAX_round", "sinkNr"]):
                                        if int(row[0]) < altitude_front:
                                            # if sinks are at a lower altitude than the glacier front, they are exposed
                                            sinkID = row[1]
                                            print "=        Melting has exposed sink Nr {}".format(sinkID)
                                            exposed_sinks_new = os.path.join(sink_folder_year,
                                                                             "VOLsink_{}.shp".format(sinkID))
                                            arcpy.Select_analysis(os.path.join(glacier_path, "sinks.shp"),
                                                                  exposed_sinks_new,
                                                                  where_clause="sinkNr = '{}'".format(sinkID))
                continue
