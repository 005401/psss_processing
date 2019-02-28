import unittest
from time import time

import numpy
import psss_processing.processor as processor

import h5py

class ImageProcessingPerformance(unittest.TestCase):

    def test_processor_performance(self):
        # Profile only if LineProfiler present.
        # To install: conda install line_profiler
        try:
            from line_profiler import LineProfiler
        except ImportError:
            print("Please install the 'line_profiler' module first.")
            return

        #image = (numpy.random.rand(2016, 2560) * 200).astype(dtype="uint16")
        #background_image = (numpy.random.rand(2016, 2560) * 10).astype(dtype="uint16")
        f = h5py.File('/afs/psi.ch/user/w/wang_x1/background.h5')
        background_image = f['/image'].value

        images = []
        for i in range(50):
            images.append(h5py.File('/afs/psi.ch/user/w/wang_x1/%d.h5'%i)['/image'].value)

        image = images[0]

        roi = [900, 1600]
        axis = numpy.linspace(9100, 9200, image.shape[1])
        parameters = {"background": "in_memory", "background_data": background_image}

        profile = LineProfiler(processor.process_image)
        process_image_wrapper = profile(processor.process_image)

        # Warm-up numba.
        process_image_wrapper(image, axis, "image", roi, parameters)

        n_iterations = 1000

        start_time = time()

        for i in range(n_iterations):
            image = images[i%len(images)]
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
