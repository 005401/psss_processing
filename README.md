[![Build Status](https://travis-ci.org/paulscherrerinstitute/psss_processing.svg?branch=master)](https://travis-ci.org/paulscherrerinstitute/psss_processing)

# PSSS Processing
This library is meant to be a stream device for processing images from PSSS cameras.

## Overview
The service accepts a bsread stream from a camera, it manipulates the picture based on the current settings, 
and calculates the spectrum of the manipulated image. The spectrum, together with the original image and the processing 
parameter are then forwarded to the output stream. The spectrum is also sent to the specified PV.

The names in the output stream are based on the PV name of the incoming camera image. For this documentation we suppose 
that the camera image PV name is **CAMERA:FPICTURE**.

Output stream contains:
- CAMERA:FPICTURE (The original camera image)
- CAMERA:FPICTURE.spectrum (The spectrum, calculated after manipulating the original image)
- CAMERA:FPICTURE.processing_parameters (The processing parameters used to manipulate the image)

The manipulated image (rotated and thresholded) is not included in the output stream.

The setting with which to manipulate the image can be set via the REST Api - either directly using HTTP calls (curl), 
or by using the provided Python client.

### Sample interaction
TODO: Write how to easily do something.

### Available parameters


### Order of image manipulation

The image is manipulated in the following order:

- Apply **min\_threshold** (Every pixel below this value is set to 0)
- Apply **max\_threshold** (Every pixel above this value is set to 0)
- Rotate the image for the **rotation** angle in degrees
- Apply the **roi** to the rotated image.

After the roi has been applied, we proceed to calculate the spectrum of the new image.

## REST Api
In the API description, localhost and port 12000 are assumed. Please change this for your specific case.

### ROI format
ROI is defined in the following format:
- **\[offset_x, size_x, offset_y, size_y\]** - the offsets are calculated from the top left corner of the image.

The ROI is applied 

ROI is valid if:
- Is None (no processing for this ROI).
- Is [] - empty list (no processing for this ROI).
- Is a list with 4 values (offset_x, size_x, offset_y, size_y):
    - Offsets cannot be negative.
    - Sizes must be larger than 0.
    - Offset + size must be smaller than the image size.

### REST Interface
All request return a JSON with the following fields:
- **state** - \["ok", "error"\]
- **status** - \["stopped", "processing"\]
- Optional request specific field - \["roi", "parameters"]

**Endpoints**:

* `POST localhost:12000/start` - Start the processing of images.

* `POST localhost:12000/stop` - Stop the processing of images.

* `GET localhost:12000/status` - Get the status of the processing.

* `GET localhost:12000/roi` - Get the currently set ROI.
    - Response specific field: "roi" - ROI in above described format.
    
* `POST localhost:12000/roi` - Set ROI.
    - Response specific field: "roi" - ROI in above described format.
    
* `GET localhost:12000/parameters` - Get the currently set parameters.
    - Response specific field: "parameters".
    
* `POST localhost:12000/parameters` - Set parameters.
    - Response specific field: "parameters" - ROI for the signal.

* `GET localhost:12000/statistics` - get process statistics.
    - Response specific field: "statistics" - Data about the processing.
    
* `GET localhost:12000/image` - get the last processed image in PNG format.
    - This is the image used for the spectrum calculation, not the original image sent in the output stream.
    
### Python client
The rest API is also wrapped in a Python client. To use it:
```python

from psss_processing import PsssProcessingClient
client = PsssProcessingClient(address="http://sf-daqsync-02:12000/")
```

Class definition:
```
class PsssProcessingClient(builtins.object)
 |  Methods defined here:
 |  
 |  __init__(self, address='http://sf-daqsync-02:12000/')
 |      :param address: Address of the PSSS Processing service, e.g. http://localhost:12000
 |  
 |  get_address(self)
 |      Return the REST api endpoint address.
 |  
 |  get_parameters(self)
 |      Get the processing parameters
 |      :return: Processing parameters as a dictionary.
 |  
 |  get_roi(self)
 |      Get the ROI.
 |      :return: ROI as a list.
 |  
 |  get_statistics(self)
 |      Get the statistics of the processing.
 |      :return: Server statistics.
 |  
 |  get_status(self)
 |      Get the status of the processing.
 |      :return: Server status.
 |  
 |  set_parameters(self, parameters)
 |      Set the processing parameters
 |      :param parameters: Dictionary with 3 elements: min_threshold, max_threshold, rotation
 |      :return: Set parameters.
 |  
 |  set_roi(self, roi)
 |      Set the ROI.
 |      :param roi: List of 4 elements: [offset_x, size_x, offset_y, size_y] or [] or None.
 |      :return: ROI as a list.
 |  
 |  start(self)
 |      Start the processing.
 |      :return: Server status.
 |  
 |  stop(self)
 |      Stop the processing.
 |      :return: Server status.
 |  

```

## Output stream
The names of the new parameters in the output stream are dependent on the names of the parameters in the input stream.
The prefix of parameters in the input stream are specified with the **--prefix** argument when running the server.

For this example let's assume that we use **--prefix SLAAR21-LCAM-C561**.

In this case, the server will look for the image in the **SLAAR21-LCAM-C561:FPICTURE** parameter.

This means that the output stream will have this additional parameters:
- SLAAR21-LCAM-C561:FPICTURE
- SLAAR21-LCAM-C561:FPICTURE.specturm (X profile of the processed image)
- SLAAR21-LCAM-C561:FPICTURE.processing_parameters (Parameters used for processing the image)

### Processing parameters format
The processing parameters are passed to the output stream as a JSON string. Example:
```
SLAAR21-LCAM-C561:FPICTURE.processing_parameters = 
'{"min_threashold": 0, "max_threashold": 0, "roi": [100, 200, 100, 200]}'
```

The ROI is in the same format as you set it:
- **\[offset_x, size_x, offset_y, size_y\]**


## Conda setup
If you use conda, you can create an environment with the psss_processing library by running:

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

- cam_server
- scipy
- pyepics
- bottle
- bsread >=1.2.0
- requests
- matplotlib
- pillow

In case you are using conda to install the packages, you might need to add the **paulscherrerinstitute** channel to 
your conda config:

```
conda config --add channels paulscherrerinstitute
```

## Docker build
**Warning**: When you build the docker image with **build.sh**, your built will be pushed to the PSI repo as the 
latest psss_processing version. Please use the **build.sh** script only if you are sure that this is 
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
that the Travis build completed successfully (the new psss_processing package in available in anaconda). 
After this 2 steps, you need to build the new version of the docker image (the docker image checks out the latest 
version of psss_processing from Anaconda). 
The docker image version and the psss_processing version should always match - 
If they don't, something went wrong.

### Production configuration
Login to the target system, where psss_processing will be running. 

### Setup the psss_processing as a service
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
