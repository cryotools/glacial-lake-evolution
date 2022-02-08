![GLAMoR](https://cryo-tools.org/wp-content/uploads/2020/07/GLAMoR-LOGO-400px.png)
## Scripts
The code in this repository can be used to investigate the temporal and spatial
development of potential future glacial lakes. It takes outputs of a glacier
model and information on the location and morphology of subglacial overdeepenings
to determine the exposure of said overdeepenings at any point in the 21st century.

The main work is done by the python script *calculations.py*, 
which can be run for each RGI region. The results of this routine 
then can be aggregated and merged to give a better overview on 
future lake development.
For more details, please see the header of the code file.

### Required data
In order to run properly, the scripts in this repository require 
different datasets to be downloaded and prepared.  
- the OGGM results 
  (available [here](https://cluster.klima.uni-bremen.de/~fmaussion/lt_archive/run_hma_hr_cmip6_v1) at the archive of F. Maussion)
- RGI glacier outlines for the respective regions
  (downloadable from the [Randolph Glacier Inventory](https://doi.org/10.7265/N5-RGI-60))
- outlines of the selected subglacial overdeepenings, e.g., the inventory
  published by [Furian et al. (2021)](https://doi.org/10.1017/jog.2021.18)
  and available on [GitHub](https://github.com/cryotools/subglacial-overdeepenings/tree/master/data)
- a DEM of the subglacial bedrock, which can be calculated 
  by subtracting the [ice thickness](https://doi.org/10.3929/ethz-b-000315707) 
  by [Farinotti et al. (2019)](https://doi.org/10.1038/s41561-019-0300-3) 
  from the [ALOS World 3D 30m DEM](10.1109/IGARSS.2018.8518360)
- a triangular irregular network of the subglacial overdeepening  

The For more details, please see the header of the code file.

### Required software
The python script was developed relying heavily on the `arcpy` package af ArcGIS 10.7. 
Therefore, valid licences for several extensions of the ArcGIS software are needed, 
i.e. the *3D Analyst*, the *Spatial Analyst*, and the *Geostatistical Analyst*.
Therefore, in order to work with `arcpy`, the code is written in Python 2.7.

### Preprocessing
Some preprocessing steps are not included in the scripts as they heavily depend on the employed
platform, folder structure, and data. Also, some input data is not provided here
due toHowever, they are very straightforward:


- subtract the glacier ice thickness data from the DEM to get a DEM of the subglacial topography
- clip the bedrock raster of each glacier using the RGI outlines
- project to a suitable coordinate system (we used the Albers equal-area projection)

The required folder structure is described in the python script.

#### Citation
You are free to use this code and the dataset in your research. 
If you do, please refer to the release you used, e.g., for v0.1:

Furian, Wilhelm (2020): An inventory of future glacial lakes 
in High Mountain Asia in shapefile format, v0.1, Zenodo, DOI: 10.5181/zenodo.3958786

[![DOI](https://zenodo.org/badge/281966062.svg)](https://zenodo.org/badge/latestdoi/281966062)
