[![Build Status](https://travis-ci.org/paulscherrerinstitute/psss_processing.svg?branch=master)](https://travis-ci.org/paulscherrerinstitute/psss_processing)

# PSSS Processing
This library is meant to be a stream device for processing images from PSSS cameras.

## Currently running

- PSSS processing is running on **sf-daqsync-02**, rest api on port **12000**.
- Images are taken over from camera SARFE10-PSSS059 (to be renamed to SARFE10-PSSS059).
- Output stream is available on **tcp://sf-daqsync-02:8889**.
- Vertical ROI definition is from PV **SARFE10-PSSS059:SPC_ROI_YMIN** and **SARFE10-PSSS059:SPC_ROI_YMAX**.
- Spectrum energy axis is from PV **SARFE10-PSSS059:SPECTRUM_X**.
- PV with the latest spectrum is **SARFE10-PSSS059:SPECTRUM_Y**.
- PV with the latest spectrum center is **SARFE10-PSSS059:SPECTRUM_CENTER**.
- PV with the latest spectrum FWHM is **SARFE10-PSSS059:SPECTRUM_FWHM**.
 
The stream is being sent to the dispatching layer for storage (original image, spectrum, processing parameters), so 
please do not connect directly to the output stream and request the data from the dispatching layer.

Current processing performance: 115Hz (all features turned on).

## Overview
The service accepts a bsread stream from a camera, it subracts a user supplied background from the picture, 
calculates the spectrum of the manipulated image and fit the spectrum using a gaussian function. 
The spectrum, together with the fitting results, the original image and the processing 
parameter are then forwarded to the output stream.

Optionally the vertical ROI, energy axis can be defined via specified PVs. The spectrum is also sent to the specified PV.

The names in the output stream are based on the PV name of the incoming camera image. For this documentation we suppose 
that the camera PV prefix is **SARFE10-PSSS059**.

### Sample interaction
The processing can be controlled via the REST Api - either directly using HTTP calls (curl), 
or by using the provided Python client.

#### Check the status
```python
from psss_processing import PsssProcessingClient

client = PsssProcessingClient()

# Get the current status of the processing.
status = client.get_status()
print(status)

# Retrieve and display current parameters.
parameters = client.get_parameters()
print(parameters)

# Get the latest processing statistics.
statistics = client.get_statistics()
print(statistics)
```

#### Upload a background image
```python
import h5py
from psss_processing import PsssProcessingClient

client = PsssProcessingClient()

# Stop the processing
client.stop()

# Read background image from an HDF5 file
filename = 'background_20190203_141516.h5'
data = h5py.File(filename)['/image'].value

# Upload the background image
client.set_background(filename, data)

# Start the processing
client.start()
```

## REST Api
In the API description, localhost and port 12000 are assumed. Please change this for your specific case.

All request return a JSON with the following fields:
- **state** - \["ok", "error"\]
- **status** - \["stopped", "processing"\]
- Optional request specific field - \["roi", "parameters", "statistics"]

**Endpoints**:

* `POST localhost:12000/start` - Start the processing of images.

* `POST localhost:12000/stop` - Stop the processing of images.

* `GET localhost:12000/status` - Get the status of the processing.

* `POST localhost:12000/background` - Set the background.

* `GET localhost:12000/parameters` - Get the currently set parameters.
    - Response specific field: "parameters".
    
* `POST localhost:12000/parameters` - Set parameters.
    - Response specific field: "parameters".

* `GET localhost:12000/statistics` - get process statistics.
    - Response specific field: "statistics" - Data about the processing.
    
    
## Output stream
The names of the parameters in the output stream are dependent on the names of the parameters in the input stream.
The prefix of parameters in the input stream are specified with the **--prefix** argument when running the server.

For this example let's assume that we use **--prefix SARFE10-PSSS059**.

In this case, the server will look for the image in the **SARFE10-PSSS059:FPICTURE** stream channel.

This means that the output stream will have the following parameters:
- SARFE10-PSSS059:FPICTURE (The original camera image)
- SARFE10-PSSS059:FPICTURE.spectrum (The spectrum, calculated after manipulating the original image)
- SARFE10-PSSS059:FPICTURE.center (Center energy of the fitted Gaussian curve)
- SARFE10-PSSS059:FPICTURE.fwhm (FHHM of the fitted Gaussian curve)
- SARFE10-PSSS059:FPICTURE.processing\_parameters (The processing parameters used to manipulate the image)

### Processing parameters format
The processing parameters are passed to the output stream as a JSON string. Example:
```
SARFE10-PSSS059:FPICTURE.processing_parameters = 
'{"background": "", "roi": [100, 200]}'
```

The ROI is in the same format as you set it:
- **\[min_y, max_y\]**


## Conda setup
If you use conda, you can create an environment with the psss\_processing library by running:

```bash
conda create -c paulscherrerinstitute --name <env_name> psss_processing
```

After that you can just source you newly created environment and start using the library.

## Local build
You can build the library by running the setup script in the root folder of the project:

```bash
python setup.py install
```

or by using the conda also from the root folder of the project:

```bash
conda build conda-recipe
conda install --use-local psss_processing
```

### Requirements
The library relies on the following packages:

- python
- pyepics
- bottle
- bsread >=1.2.0
- requests
- numba

In case you are using conda to install the packages, you might need to add the **paulscherrerinstitute** channel to 
your conda config:

```
conda config --add channels paulscherrerinstitute
```

## Docker build
**Warning**: When you build the docker image with **build.sh**, your built will be pushed to the PSI repo as the 
latest psss\_processing version. Please use the **build.sh** script only if you are sure that this is 
what you want.

To build the docker image, run the build from the **docker/** folder:
```bash
./build.sh
```

Before building the docker image, make sure the latest version of the library is available in Anaconda.

**Please note**: There is no need to build the image if you just want to run the docker container. 
Please see the **Run Docker Container** chapter.

## Run Docker Container
To execute the application inside a docker container, you must first start it (from the project root folder):
```bash
docker run --net=host -it docker.psi.ch:5000/psss_processing /bin/bash
```

Once inside the container, start the application by running (append the parameters you need.)
```bash
psss_processing
```

## Deploy in production

Before deploying in production, make sure the latest version was tagged in git (this triggers the Travis build) and 
that the Travis build completed successfully (the new psss\_processing package in available in anaconda). 
After this 2 steps, you need to build the new version of the docker image (the docker image checks out the latest 
version of psss\_processing from Anaconda). 
The docker image version and the psss\_processing version should always match - 
If they don't, something went wrong.

### Production configuration
Login to the target system, where psss\_processing will be running. 

### Setup the psss\_processing as a service
On the target system, copy all **systemd/\*.service** files into 
**/etc/systemd/system**.

Then you need to reload the systemctl daemon:
```bash
systemctl daemon-reload
```

### Run the services
Using systemctl you then run all the services:
```bash
systemctl start [name_of_the_service_file_1].service
systemctl start [name_of_the_service_file_2].service
...
```

### Inspecting service logs
To inspect the logs for each server, use journalctl:
```bash
journalctl -u [name_of_the_service_file_1].service -f
```

Note: The '-f' flag will make you follow the log file.

### Make the service run automatically
To make the service run and restart automatically, use:
```bash
systemctl enable [name_of_the_service_file_1].service
```
