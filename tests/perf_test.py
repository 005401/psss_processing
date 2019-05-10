import unittest
from time import time

import numpy
import psss_processing.processor as processor


class ImageProcessingPerformance(unittest.TestCase):

    def test_processor_performance(self):
        # Profile only if LineProfiler present.
        # To install: conda install line_profiler
        try:
            from line_profiler import LineProfiler
        except ImportError:
            print("Please install the 'line_profiler' module first.")
            return
        
        # simulated image size
        width = 2560
        height = 2016
        
        # simulated gaussian function
        xx, yy = numpy.meshgrid(numpy.arange(width), numpy.arange(height))
        x0 = 1280 # x center
        y0 = 1300 # y center
        sx = 300  # x sigma
        sy = 150  # y sigma
        amplitude = 50
        image = amplitude * numpy.exp(-(xx-x0)**2/(2*sx**2) - (yy-y0)**2/(2*sy**2))
        noise = numpy.random.normal(scale=amplitude*0.2, size=(height, width))

        image = (image + numpy.abs(noise)).astype(dtype="uint16")
        background_image = (numpy.random.rand(2016, 2560) * 5).astype(dtype="uint16")

        roi = [900, 1600]
        axis = numpy.linspace(8980, 9020, image.shape[1])
        parameters = {"background": "in_memory", "background_data": background_image}

        profile = LineProfiler(processor.process_image)
        process_image_wrapper = profile(processor.process_image)

        # Warm-up numba.
        results = processor.process_image(image, axis, "image", roi, parameters)

        n_iterations = 1000

        start_time = time()

        for i in range(n_iterations):
            process_image_wrapper(image, axis, "image", roi, parameters)

        end_time = time()

        time_difference = end_time - start_time
        rate = n_iterations / time_difference

        print("Processing rate: ", rate)
        print("total_time: ", time_difference)
        print("n_iterations: ", n_iterations)

        profile.print_stats()


if __name__ == '__main__':
    unittest.main()
