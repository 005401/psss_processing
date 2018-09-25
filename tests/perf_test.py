import unittest
from time import time

import numpy

from psss_processing.processor import process_image, get_spectrum, calculate_summation_matrix, get_summation_matrix


class ImageProcessingPerformance(unittest.TestCase):

    def test_processor_performance(self):
        # Profile only if LineProfiler present.
        # To install: conda install line_profiler
        try:
            from line_profiler import LineProfiler
        except ImportError:
            print("Please install the 'line_profiler' module first.")
            return

        image = (numpy.random.rand(2048, 2048) * 100).astype(dtype="uint16")

        roi = [100, 1848, 0, 2048]
        min_threshold = 5
        max_threshold = 70
        rotation = 45

        profile = LineProfiler(process_image)
        process_image_wrapper = profile(process_image)
        profile.add_function(get_spectrum)
        profile.add_function(get_summation_matrix)

        n_iterations = 5000

        start_time = time()

        for _ in range(n_iterations):
            process_image_wrapper(image, "image", roi, min_threshold, max_threshold, rotation)

        end_time = time()

        time_difference = end_time - start_time
        rate = n_iterations / time_difference

        print("Processing rate: ", rate)

        profile.print_stats()


if __name__ == '__main__':
    unittest.main()
