# June 11, 2021
# Ross Wardrup - rwardrup@congruex.com

import os
import sys
from datetime import datetime
import shutil
import zipfile

import osr
from gdal import ogr

# Global variables

"""
The user will need to set USERNAME to their Windows username. The DELIVERABLE_SHAPEFILES array may change, depending on
which files CGIS needs. Modify accordingly.
"""
USERNAME = "rwardrup"
DESKTOP = f"C:\\Users\\{USERNAME}\\OneDrive - Congruex\\Desktop"
DOWNLOADS = f"C:\\Users\\{USERNAME}\\Downloads"  # Shape data are extracted from here
DOCUMENTS = f"C:\\Users\\{USERNAME}\\Documents"  # Location where shape data is stored before QGIS import
WORKSPACES = f"C:\\Users\\{USERNAME}\\OneDrive - Congruex\\Desktop\\Workspaces\\"  # Location of Comsof workspaces

if not os.path.exists(DESKTOP) or not os.path.exists(DOWNLOADS) or not os.path.exists(DOCUMENTS) \
        or not os.path.exists(WORKSPACES):
    print("***A system path wasn't found***\n"
          "You must configure the USERNAME variable in the Python script\n"
          "Also, make sure the 'Workspaces' directory exists on your Desktop")
    sys.exit()

# Shapefiles that will be copied from extracted directory into the DOCUMENTS path.
DELIVERABLE_SHAPEFILES = ("OUT_AccessStructures",
                          "OUT_Closures",
                          "OUT_DistributionCables",
                          "OUT_DropCables",
                          "OUT_DropClusters",
                          "OUT_FeederCables")

INTERMEDIATE_SHAPEFILES = ("span_length",
                           "fdt_boundary")

# Get the current date in YYYYMMDD format, for timestamping output directory names
now = datetime.now()
date = now.strftime("%Y%m%d")

choice = input("1 - Set up working environment\n"
               "2 - Intermediate Comsof Shapefile Setup\n"
               "3 - Create deliverable package\n"
               "Q/q - Quit\n"
               "------------------------------\n-> ")

while choice.lower() != 'q' and (not choice.isnumeric() or int(choice) not in (1, 2, 3)):
    choice = input("1 - Set up working environment\n"
                   "2 - Intermediate Comsof Shapefile Setup\n"
                   "3 - Create deliverable package\n"
                   "Q/q - Quit\n"
                   "------------------------------\n-> ")

if choice.lower() == 'q':
    sys.exit()

job_number = input("Job number: ")

if choice == '1':  # Set up working environment
    state = input("State name: ")
    city = input("City name: ")

    for download_root, _, downloaded_files in os.walk(DOWNLOADS):
        for downloaded_file in downloaded_files:
            if job_number in downloaded_file:  # Check if job number is in filename
                source_path = os.path.join(download_root, downloaded_file)

                # Create temp directory to extract zip to
                tmp_name = os.path.splitext(downloaded_file)[0] + '_tmp'
                tmp_path = os.path.join(download_root, tmp_name)

                # Pre-QGIS ingestion shapefile path, up to state & city level
                root_dest_path = os.path.join(DOCUMENTS, os.path.join(state, city))

                # Comsof workspace path
                workspace_path = os.path.join(WORKSPACES, os.path.join(state, os.path.join(city,
                                                                                           f"{date}-{job_number}")))

                with zipfile.ZipFile(source_path, 'r') as zip_ref:
                    zip_ref.extractall(tmp_path)

                # job_dir_path is the scratch location where shapefiles are stored when initially importing into QGIS
                job_dir_path = os.path.join(root_dest_path, f"{date}-{job_number}")

                if not os.path.exists(job_dir_path):
                    os.mkdir(job_dir_path)

                else:
                    print(f"Error: {job_dir_path} already exists. Remove if necessary.\nClosing.")
                    shutil.rmtree(tmp_path)
                    sys.exit()

                # Iterate through shapefiles in tmp directory and copy them into
                # the pre-QGIS ingestion shapefile path
                for tmp_root, _, tmp_filenames in os.walk(tmp_path):
                    for shapefile_part in tmp_filenames:
                        dest_path = os.path.join(job_dir_path, shapefile_part)
                        file_path = os.path.join(tmp_root, shapefile_part)
                        shutil.copy(file_path, dest_path)

                # Remove tmp path and create reprojection and workspace directories.
                shutil.rmtree(tmp_path)
                os.makedirs(os.path.join(job_dir_path, "reprojected"))
                os.makedirs(workspace_path)

                # Add _ to end of zip file to flag it as having been processed
                os.rename(source_path, os.path.join(download_root, os.path.splitext(downloaded_file)[0] + '_.zip'))

elif choice == '2':  # Intermediate shapefile setup
    src_shp_path = None
    workspace_path = None

    # Get src path
    for root, dirnames, filenames in os.walk(DOCUMENTS):
        for dir in dirnames:
            dir_path = os.path.join(root, dir)
            if job_number in dir_path and 'reprojected' in dir_path.lower() and "ready" not in dir_path.lower():
                src_shp_path = dir_path

    # Get workspace path
    for root, dirnames, filenames in os.walk(WORKSPACES):
        for dir in dirnames:
            dir_path = os.path.join(root, dir)
            if job_number in dir_path and "input" not in dir_path.lower() and "saved states" not in dir_path.lower() \
                    and "output" not in dir_path.lower():
                workspace_path = dir_path

    if src_shp_path is None:
        print("Could not find source shapefile path. Exiting")
        sys.exit()
    elif workspace_path is None:
        print("Could not find workspace path. Exiting")
        sys.exit()

    workspace_input_path = os.path.join(workspace_path, "input")  # Span length goes here
    workspace_calc_input_path = os.path.join(workspace_input_path, "CalculationInput")  # FDT boundary goes here

    # Read the shapefiles
    driver = ogr.GetDriverByName("ESRI Shapefile")
    ready_path = os.path.join(src_shp_path, "ready")
    if not os.path.exists(ready_path):
        os.makedirs(os.path.join(ready_path))

    demand_points_path = os.path.join(src_shp_path, "addresses.dbf")
    access_structs_path = os.path.join(src_shp_path, "access_point.dbf")
    poles_path = os.path.join(src_shp_path, "pole.dbf")
    aerials_path = os.path.join(src_shp_path, "span_length.dbf")
    fdc_path = os.path.join(src_shp_path, "fdt_boundary.dbf")

    # Demand points / addresses
    dp_ds = driver.Open(demand_points_path, 1)
    dp_lyr = dp_ds.GetLayer()

    pon_homes_def = ogr.FieldDefn("PON_HOMES", ogr.OFTInteger)
    streetname_def = ogr.FieldDefn("STREETNAME", ogr.OFTString)
    streetname_def.SetWidth(254)
    dp_lyr.CreateField(pon_homes_def)
    dp_lyr.CreateField(streetname_def)

    for feat in dp_lyr:
        streetname = feat.GetField("street")

        try:  # Handle blank streetnames
            streetname = streetname.upper()
        except AttributeError:
            streetname = ''

        feat.SetField("PON_HOMES", 1)
        feat.SetField("STREETNAME", streetname)
        dp_lyr.SetFeature(feat)
    dp_ds.Destroy()

    # Access Points
    ap_ds = driver.Open(access_structs_path, 1)
    ap_lyr = ap_ds.GetLayer()

    type_def = ogr.FieldDefn("TYPE", ogr.OFTString)
    type_def.SetWidth(254)
    ap_lyr.CreateField(type_def)

    for ap_feat in ap_lyr:
        type = ap_feat.GetField('structur_1')
        type_string = f"HANDHOLE{{{type}}}"
        ap_feat.SetField("TYPE", type_string)
        ap_lyr.SetFeature(ap_feat)
    ap_ds.Destroy()

    # Copy to the comsof workspace directory
    for root, dirnames, filenames in os.walk(src_shp_path):
        for file in filenames:
            original_path = os.path.join(root, file)
            src_filename = os.path.splitext(file)[0].lower()
            src_ext = os.path.splitext(file)[1].lower()
            if src_filename == "span_length":
                new_filename = f"IN_AerialConnections" + src_ext
                new_path = os.path.join(workspace_input_path, new_filename)
                shutil.copy(original_path, new_path)

            if src_filename == "fdt_boundary":
                new_filename = f"IN_ForcedDropClusters" + src_ext
                new_path = os.path.join(workspace_calc_input_path,  new_filename)
                shutil.copy(original_path, new_path)


elif choice == '3':  # Create deliverable package
    copied_counter = 0
    input_path = input("Comsof workspace output path: ")
    state = input("State: ")
    city = input("City: ")

    # Output path should be similar to C:\Users\USERNAME\Desktop\Deliverables\Washington\Oak Harbor\20210612-550491
    deliverable_path = os.path.join(state, city)
    output_path = os.path.join(DESKTOP, os.path.join("Deliverables", os.path.join(deliverable_path,
                                                                                  f"{date}-{job_number}")))

    if not os.path.exists(output_path):
        os.makedirs(output_path)
    else:
        print(f"Output path {output_path} already exists. Closing to avoid data loss. Remove directory and rerun if"
              f"necessary.")

    input(f"Creating deliverable archive at {output_path}.zip ... Press enter to continue.")

    # Iterate through Comsof shapefile output and copy files to deliverable path if the shapefile is in
    # DELIVERABLE_SHAPEFILES tuple
    for workspace_output_root, _, workspace_files in os.walk(input_path):
        for output_shapefile in workspace_files:
            if os.path.splitext(output_shapefile)[0] in DELIVERABLE_SHAPEFILES:

                # Add job number to filenames. This assumes that the first three characters of the shapefile name are
                # junk. Currently, the shapefiles are named like "OUT_AerialDropConnection.shp". This places the job
                # number between OUT_ and AerialDropConnection, so that it looks like OUT_12345_AerialDropConnection.shp
                new_filename = output_shapefile[:3] + f"_{job_number}" + output_shapefile[3:]
                src_path = os.path.join(workspace_output_root, output_shapefile)

                dst_path = os.path.join(output_path, new_filename)

                shutil.copy(src_path, dst_path)
                copied_counter += 1

    if copied_counter == 30:
        zip_file_path = output_path + ".zip"
        shutil.make_archive(zip_file_path, 'zip', output_path)
        shutil.rmtree(output_path)
    else:  # Didn't copy all of the files (if any)
        print("Error: didn't copy correct number of files. Check output path")
