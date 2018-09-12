import tempfile

import numpy
import scipy

from psss_processing import config
from matplotlib import cm


def validate_roi(roi):
    """
    Check if the ROI parameters are valid: List with 0 or 4 elements. Sizes at least 1, and offsets at least 0.
    :param roi: [offset_x, size_x, offset_y, size_y]
    :raises ValueError: When ROI is not valid, it raises a ValueError.
    """

    if not isinstance(roi, list):
        raise ValueError("ROI must be an instance of a list, but %s was given as a %s." % (roi, type(roi)))

    if len(roi) == 0:
        return

    if len(roi) != 4:
        raise ValueError("ROI must have exactly 4 elements, but %s was given." % roi)

    if roi[0] < 0 or roi[2] < 0:
        raise ValueError("ROI offsets (first and third elements) must be positive, but %s was given." % roi)

    if roi[1] < 1 or roi[3] < 1:
        raise ValueError("ROI sizes (second and fourth elements) must be at least 1, but %s was given." % roi)


def get_host_port_from_stream_address(stream_address):
    """
    Convert hostname in format tcp://127.0.0.1:8080 to host (127.0.0.1) and port (8080)
    :param stream_address: String in format tcp://XXX:XXX
    :return: String with hostname, int with port.
    """
    source_host, source_port = stream_address.rsplit(":", maxsplit=1)
    source_host = source_host.split("//")[1]

    return source_host, int(source_port)


def get_png_from_image(image_raw_bytes, scale=None, min_value=None, max_value=None, colormap_name=None):
    """
    Generate an image from the provided camera.
    :param image_raw_bytes: Image bytes to turn into PNG
    :param scale: Scale the image.
    :param min_value: Min cutoff value.
    :param max_value: Max cutoff value.
    :param colormap_name: Colormap to use. See http://matplotlib.org/examples/color/colormaps_reference.html
    :return: PNG image.
    """

    image_raw_bytes = image_raw_bytes.astype("float64")

    if scale:
        shape_0 = int(image_raw_bytes.shape[0] * scale)
        shape_1 = int(image_raw_bytes.shape[1] * scale)
        sh = shape_0, image_raw_bytes.shape[0] // shape_0, shape_1, image_raw_bytes.shape[1] // shape_1
        image_raw_bytes = image_raw_bytes.reshape(sh).mean(-1).mean(1)

    if min_value:
        image_raw_bytes -= min_value
        image_raw_bytes[image_raw_bytes < 0] = 0

    if max_value:
        image_raw_bytes[image_raw_bytes > max_value] = max_value

    try:
        colormap_name = colormap_name or config.DEFAULT_CAMERA_IMAGE_COLORMAP
        # Available colormaps http://matplotlib.org/examples/color/colormaps_reference.html
        colormap = getattr(cm, colormap_name)

        # http://stackoverflow.com/questions/10965417/how-to-convert-numpy-array-to-pil-image-applying-matplotlib-colormap
        # normalize image to range 0.0-1.0
        image_raw_bytes *= 1.0 / image_raw_bytes.max()

        image = numpy.uint8(colormap(image_raw_bytes) * 255)
    except:
        raise ValueError("Unable to apply colormap '%s'. "
                         "See http://matplotlib.org/examples/color/colormaps_reference.html for available colormaps." %
                         colormap_name)

    n_image = scipy.misc.toimage(image)

    tmp_file = tempfile.TemporaryFile()

    # https://github.com/python-pillow/Pillow/issues/1211
    # We do not use any compression for speed reasons
    # n_image.save('your_file.png', compress_level=0)
    n_image.save(tmp_file, 'png', compress_level=0)
    # n_image.save(tmp_file, 'jpeg', compress_level=0)  # jpeg seems to be faster

    tmp_file.seek(0)
    content = tmp_file.read()
    tmp_file.close()

    return content