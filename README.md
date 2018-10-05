[![Build Status](https://travis-ci.org/paulscherrerinstitute/psss_processing.svg?branch=master)](https://travis-ci.org/paulscherrerinstitute/psss_processing)

# PSSS Processing
This library is meant to be a stream device for processing images from PSSS cameras.

## Currently running

- PSSS processing is running on **sf-daqsync-02**, rest api on port **12000**.
- Images are taken over from camera SARFE10-PSSS055 (to be renamed to SARFE10-PSSS059).
- Output stream is available on **tcp://sf-daqsync-02:8889**.
- PV with the latest spectrum is **SARFE10-PSSS059:SPECTRUM**.

The stream is being sent to the dispatching layer for storage (original image, spectrum, processing parameters), so 
please do not connect directly to the output stream and request the data from the dispatching layer.

Current processing performance:

- Without rotation: 35Hz
- With rotation: 1.5Hz

**WARNING**: It is not advisable to use rotation if you need live shot to shot data.

## Overview
The service accepts a bsread stream from a camera, it manipulates the picture based on the current settings, 
and calculates the spectrum of the manipulated image. The spectrum, together with the original image and the processing 
parameter are then forwarded to the output stream. The spectrum is also sent to the specified PV.

The names in the output stream are based on the PV name of the incoming camera image. For this documentation we suppose 
that the camera PV prefix is **SARFE10-PSSS055**.

Output stream contains:
- SARFE10-PSSS055:FPICTURE (The original camera image)
- SARFE10-PSSS055:FPICTURE.spectrum (The spectrum, calculated after manipulating the original image)
- SARFE10-PSSS055:FPICTURE.processing_parameters (The processing parameters used to manipulate the image)

The manipulated image (rotated and thresholded) is not included in the output stream.

The setting with which to manipulate the image can be set via the REST Api - either directly using HTTP calls (curl), 
or by using the provided Python client.

### Sample interaction

#### Configuration retrieval
```python
from psss_processing import PsssProcessingClient

client = PsssProcessingClient()

# Get the current status of the processing.
status = client.get_status()
print(status)

# Retrieve and display current parameters.
parameters = client.get_parameters()
print(parameters)

# Retrieve and display the current roi.
roi = client.get_roi()
print(roi)

# Get the latest processing statistics.
statistics = client.get_statistics()
print(statistics)
```

#### Set configuration
In the example below we stop the processing before applying new settings - this is not needed as new settings 
can be applied without restarting the processing. 

```python
from psss_processing import PsssProcessingClient

client = PsssProcessingClient()

# Stop the processing. THIS IS NOT NEEDED - just for demonstration.
client.stop()

parameters = {
    "min_threshold": 10,
    "max_threshold": 1200,
    "rotation": 0
}

client.set_parameters(parameters)

roi = [
    100,  # offset_x
    2048, # size_x
    500,  # offset_y
    1000  # size_y
]

client.set_roi(roi)

# Start the processing.
client.start()
```

### Available parameters

You can set the following parameters via the **/parameters** rest endpoint:

- **min\_threshold** (Default: 0) If min_threshold>0, each pixel below this value will be set to 0.
- **max\_threshold** (Default: 0) If max_threshold>0, each pixel above this value will be set to 0.
- **rotation** (Default: 0) If rotation>0, the image will be rotated for the value in degrees.

Example:
```python
from psss_processing import PsssProcessingClient

client = PsssProcessingClient()

parameters = {
    "min_threshold": 10,
    "max_threshold": 90,
    "rotation": 0
}

client.set_parameters(parameters)
```

In addition, you can also set the ROI (region of interest) via the **/roi** rest endpoint:

- **\[offset_x, size_x, offset_y, size_y\]** (Default is None)

Example:
```python
from psss_processing import PsssProcessingClient

client = PsssProcessingClient()


roi = [
    100,  # offset_x
    2048, # size_x
    500,  # offset_y
    1000  # size_y
]

client.set_roi(roi)
```

#### Order of image manipulation

The image is manipulated in the following order:

- Apply the **roi** to the received image.
- Apply **min\_threshold** (Every pixel below this value is set to 0)
- Apply **max\_threshold** (Every pixel above this value is set to 0)
- Rotate the image for the **rotation** angle in degrees

After the roi has been applied, we proceed to calculate the spectrum of the new image.

## REST Api
In the API description, localhost and port 12000 are assumed. Please change this for your specific case.

### ROI format
ROI is defined in the following format:
- **\[offset_x, size_x, offset_y, size_y\]** - the offsets are calculated from the top left corner of the image.

The ROI is applied only if it is valid. ROI is valid if:

- Is None (no processing).
- Is [] - empty list (no processing).
- Is a list with 4 values (offset_x, size_x, offset_y, size_y):
    - Offsets cannot be negative.
    - Sizes must be larger than 0.
    - Offset + size must be smaller than the image size.

### REST Interface
All request return a JSON with the following fields:
- **state** - \["ok", "error"\]
- **status** - \["stopped", "processing"\]
- Optional request specific field - \["roi", "parameters", "statistics"]

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
    - Response specific field: "parameters".

* `GET localhost:12000/statistics` - get process statistics.
    - Response specific field: "statistics" - Data about the processing.
    
    
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
The names of the parameters in the output stream are dependent on the names of the parameters in the input stream.
The prefix of parameters in the input stream are specified with the **--prefix** argument when running the server.

For this example let's assume that we use **--prefix SARFE10-PSSS055**.

In this case, the server will look for the image in the **SARFE10-PSSS055:FPICTURE** stream channel.

This means that the output stream will have the following parameters:
- SARFE10-PSSS055:FPICTURE
- SARFE10-PSSS055:FPICTURE.specturm (X profile of the processed image)
- SARFE10-PSSS055:FPICTURE.processing_parameters (Parameters used for processing the image)

### Processing parameters format
The processing parameters are passed to the output stream as a JSON string. Example:
```
SARFE10-PSSS055:FPICTURE.processing_parameters = 
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
