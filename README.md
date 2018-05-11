[![Build Status](https://travis-ci.org/paulscherrerinstitute/psen_processing.svg?branch=master)](https://travis-ci.org/paulscherrerinstitute/psen_processing)

# PSEN Processing
This library is meant to be a stream device for processing images from PSEN cameras.

## REST Api
In the API description, localhost and port 10000 are assumed. Please change this for your specific case.

### ROI format
Both ROIs (background, signal) are defined in the following format:
- **\[offset_x, size_x, offset_y, size_y\]** - the offsets are calculated from the top left corner of the image.

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
- Optional request specific field - \["roi_background", "roi_signal", "statistics"]

**Endpoints**:

* `POST localhost:10000/start` - Start the processing of images.

* `POST localhost:10000/stop` - Stop the processing of images.

* `GET localhost:10000/status` - Get the status of the processing.

* `GET localhost:10000/roi_background` - Get the currently set background ROI.
    - Response specific field: "roi_background" - ROI for the background.
    
* `POST localhost:10000/roi_background` - Set background ROI.
    - Response specific field: "roi_background" - ROI for the background.
    
* `GET localhost:10000/roi_signal` - Get the currently set signal ROI.
    - Response specific field: "roi_signal" - ROI for the signal.
    
* `POST localhost:10000/roi_signal` - Set signal ROI.
    - Response specific field: "roi_signal" - ROI for the signal.

* `GET localhost:10000/statistics` - get process statistics.
    - Response specific field: "statistics" - Data about the processing.
    
### Python client
The rest API is also wrapped in a Python client. To use it:
```python

from psen_processing import PsenProcessingClient
client = PsenProcessingClient(address="http://sf-daqsync-02:10000/")
```

Class definition:
```
class PsenProcessingClient(builtins.object)

    __init__(self, address='http://sf-daqsync-02:10000/')
        :param address: Address of the PSEN Processing service, e.g. http://localhost:10000
  
    get_address(self)
        Return the REST api endpoint address.
  
    get_roi_background(self)
        Get the ROI for the background.
        :return: Background ROI as a list.
  
    get_roi_signal(self)
        Get the ROI for the signal.
        :return: Signal ROI as a list.
  
    get_statistics(self)
        Get the statistics of the processing.
        :return: Server statistics.
  
    get_status(self)
        Get the status of the processing.
        :return: Server status.
  
    set_roi_background(self, roi)
        Set the ROI for the background.
        :param roi: List of 4 elements: [offset_x, size_x, offset_y, size_y] or [] or None.
        :return: Background ROI as a list.
  
    set_roi_signal(self, roi)
        Set the ROI for the signal.
        :param roi: List of 4 elements: [offset_x, size_x, offset_y, size_y] or [] or None.
        :return: Signal ROI as a list.
  
    start(self)
        Start the processing.
        :return: Server status.
  
    stop(self)
        Stop the processing.
        :return: Server status.
```


## Conda setup
If you use conda, you can create an environment with the psen_processing library by running:

```bash
conda create -c paulscherrerinstitute --name <env_name> psen_processing
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
conda install --use-local psen_processing
```

### Requirements
The library relies on the following packages:

- python
- bottle
- bsread
- requests

In case you are using conda to install the packages, you might need to add the **paulscherrerinstitute** channel to 
your conda config:

```
conda config --add channels paulscherrerinstitute
```

## Docker build
**Warning**: When you build the docker image with **build.sh**, your built will be pushed to the PSI repo as the 
latest frontend_digitizers_calibration version. Please use the **build.sh** script only if you are sure that this is 
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
docker run --net=host -it docker.psi.ch:5000/psen_processing /bin/bash
```

Once inside the container, start the application by running (append the parameters you need.)
```bash
psen_processing
```

## Deploy in production

Before deploying in production, make sure the latest version was tagged in git (this triggers the Travis build) and 
that the Travis build completed successfully (the new psen_processing package in available in anaconda). 
After this 2 steps, you need to build the new version of the docker image (the docker image checks out the latest 
version of psen_processing from Anaconda). 
The docker image version and the psen_processing version should always match - 
If they don't, something went wrong.

### Production configuration
Login to the target system, where psen_processing will be running. 

### Setup the psen_processing as a service
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
