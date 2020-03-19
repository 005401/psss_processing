import math
import numba
import numpy
import scipy.optimize


@numba.njit(parallel=True)
def get_spectrum(image, background):
    y = image.shape[0]
    x = image.shape[1]

    profile = numpy.zeros(x, dtype=numpy.uint32)

    for i in numba.prange(y):
        for j in range(x):
            v = image[i,j]
            b = background[i,j]
            if v > b:
                v -= b
            else:
                v = 0

            profile[j] += v

    return profile


def _gauss_function(x, offset, amplitude, center, standard_deviation):
    return offset + amplitude * numpy.exp(-(x - center) ** 2 / (2 * standard_deviation ** 2))


def _gauss_deriv(x, offset, amplitude, center, standard_deviation):
    fac = numpy.exp(-(x - center) ** 2 / (2 * standard_deviation ** 2))

    result = numpy.empty((4, x.size), dtype=x.dtype)
    result[0, :] = 1.0
    result[1, :] = fac
    result[2, :] = amplitude * fac * (x - center) / (standard_deviation**2)
    result[3, :] = amplitude * fac * ((x-center)**2) / (standard_deviation**3)

    return result


def gauss_fit(profile, axis, **kwargs):
    if axis.shape[0] != profile.shape[0]:
        raise RuntimeError("Invalid axis passed %d %d" % (axis.shape[0], profile.shape[0]))

    offset = kwargs.get('offset', profile.min())  # Minimum is good estimation of offset
    amplitude = kwargs.get('amplitude', profile.max() - offset)  # Max value is a good estimation of amplitude
    center = kwargs.get('center', numpy.dot(axis, profile) / profile.sum()) # Center of mass is a good estimation of center (mu)
    # Consider gaussian integral is amplitude * sigma * sqrt(2*pi)
    standard_deviation = kwargs.get('standard_deviation', numpy.trapz((profile - offset), x=axis) / (amplitude * numpy.sqrt(2 * numpy.pi)))
    maxfev = kwargs.get('maxfev', 20) # the default is 100 * (N + 1), which is over killing

    # If user requests fitting to be skipped, return the estimated parameters.
    if kwargs.get('skip', False):
        return offset, amplitude, center, abs(standard_deviation)

    try:
        optimal_parameter, _ = scipy.optimize.curve_fit(
                _gauss_function, axis, profile.astype("float64"),
                p0=[offset, amplitude, center, standard_deviation],
                jac=_gauss_deriv,
                col_deriv=1,
                maxfev=maxfev)
        offset, amplitude, center, standard_deviation = optimal_parameter
    except BaseException as e:
        pass

    return offset, amplitude, center, abs(standard_deviation)
