""" Python interface for the Average Magnetic field and Polar current System (AMPS) model

This module can be used to 
1) Calculate and plot average magnetic field and current parameters 
   on a grid. This is done through the AMPS class. The parameters 
   that are available for calculation/plotting are:
    - field aligned current (scalar)
    - equivalent current function (scalar)
    - divergence-free part of horizontal current (vector)
    - curl-free part of horizontal current (vector)
    - total horizontal current (vector)
    - eastward or northward ground perturbation 
      corresponding to equivalent current (scalars)
||||||||  2) Calculate the model magnetic field in space, along a trajetory, 
||todo||     provided a time series of external parameters. This is done through
||||||||     the get_magnetic_field(...) function. The magnetic field will be provided in geographic coordinates
||||||||  3) Calculate the model magnetic field in space, along a trajetory, 
||todo||     provided a time series of external parameters. This is done through
||||||||     the get_ground_perturbation(...) function. 



MIT License

Copyright (c) 2017 Karl M. Laundal

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from __future__ import division
import numpy as np
import matplotlib.pyplot as plt
from plot_utils import equalAreaGrid, Polarsubplot
from sh_utils import get_legendre, SHkeys
from model_utils import get_model_vectors
from matplotlib import rc


rc('font', **{'family': 'serif', 'serif': ['Computer Modern']})
rc('text', usetex=True)

MU0   = 4*np.pi*1e-7 # Permeability constant
REFRE = 6371.2 # Reference radius used in geomagnetic modeling

DEFAULT = object()


class AMPS(object):
    """
    Calculate and plot maps of the model Average Magnetic field and Polar current System (AMPS)

    Parameters
    ---------
    v : float
        solar wind velocity in km/s
    By : float
        IMF GSM y component in nT
    Bz : float
        IMF GSM z component in nT
    tilt : float
        dipole tilt angle in degrees
    F107 : float
        F10.7 index in s.f.u.
    minlat : float, optional
        low latitude boundary of grids  (default 60)
    maxlat : float, optional
        low latitude boundary of grids  (default 89.99)
    height : float, optional
        altitude of the ionospheric currents (default 110 km)
    dr : int, optional
        latitudinal spacing between equal area grid points (default 2 degrees)
    M0 : int, optional
        number of grid points in the most poleward circle of equal area grid points (default 4)
    resolution: int, optional
        resolution in both directions of the scalar field grids (default 100)


    Examples
    --------
    >>> # initialize by supplying a set of external conditions:
    >>> m = AMPS(solar_wind_velocity_in_km_per_s, 
                 IMF_By_in_nT, IMF_Bz_in_nT, 
                 dipole_tilt_in_deg, 
                 F107_index)
    
    >>> # make summary plot:
    >>> m.plot_currents()
        
    >>> # extract map of field-aligned currents in north and south:
    >>> Jun, Jus = m.get_upward_current()

    >>> # Jus.flatten() will be evaluated at the following coords:
    >>> mlat = np.split(m.scalargrid[0], 2)[1]
    >>> mlt  = np.split(m.scalargrid[1], 2)[1]

    >>> # get map of total height-integrated horizontal currents:
    >>> je_n, je_s, jn_n, jn_s = m.get_total_current()

    >>> # je_n, the eastward current in northern hemisphere, will
    >>> # be evaluated at the following coords:
    >>> mlat = np.split(m.vectorgrid[0], 2)[0]
    >>> mlt  = np.split(m.vectorgrid[1], 2)[0]

    >>> # update model vectors (tor_c, tor_s, etc.) without 
    >>> # recalculating the other matrices:
    >>> m.update_model(new_v, new_By, new_Bz, new_tilt, new_F107)

    Attributes
    ----------
    tor_c : np.array
        vector of cos term coefficents in the toroidal field expansion
    tor_s : np.array
        vector of sin term coefficents in the toroidal field expansion
    pol_c : np.array
        vector of cos term coefficents in the poloidal field expansion
    pol_s : np.array
        vector of sin term coefficents in the poloidal field expansion
    keys_P : list
        list of spherical harmonic wave number pairs (n,m) corresponding to elements of pol_c and pol_s 
    keys_T : list
        list of spherical harmonic wave number pairs (n,m) corresponding to elements of tor_c and tor_s 
    vectorgrid : tuple
        grid used to calculate and plot vector fields
    scalargrid : tuple
        grid used to calculate and plot scalar fields
                   
        The grid formats are as follows (see also example below):
        (np.hstack((mlat_north, mlat_south)), np.hstack((mlt_north, mlt_south)))
        
        The grids can be changed directly, but member function calculate_matrices() 
        must then be called for the change to take effect. Also the grid format
        described above should be used.

    """



    def __init__(self, v, By, Bz, tilt, F107, minlat = 60, maxlat = 89.99, height = 110., dr = 2, M0 = 4, resolution = 100):
        """ __init__ function for class AMPS
        """

        self.tor_c, self.tor_s, self.pol_c, self.pol_s, self.pol_keys, self.tor_keys = get_model_vectors(v, By, Bz, tilt, F107)

        self.height = height

        self.dr = dr
        self.M0 = M0


        assert (len(self.pol_s) == len(self.pol_c)) and (len(self.pol_s) == len(self.pol_c))

        self.minlat = minlat
        self.maxlat = maxlat

        self.keys_P = [c for c in self.pol_keys]
        self.keys_T = [c for c in self.tor_keys]
        self.m_P = np.array(self.keys_P).T[1][np.newaxis, :]
        self.m_T = np.array(self.keys_T).T[1][np.newaxis, :]
        self.n_P = np.array(self.keys_P).T[0][np.newaxis, :]
        self.n_T = np.array(self.keys_T).T[0][np.newaxis, :]


        # find highest degree and order:
        self.N, self.M = np.max( np.hstack((np.array([c for c in self.tor_keys]).T, np.array([c for c in self.tor_keys]).T)), axis = 1)

        self.vectorgrid = self._get_vectorgrid()
        self.scalargrid = self._get_scalargrid(resolution = resolution)
        self.calculate_matrices()

    def update_model(self, v, By, Bz, tilt, F107):
        """
        Update the model vectors without updating all the other matrices. This leads to better
        performance than just making a new AMPS object.

        Parameters
        ----------
        v : float
            solar wind velocity in km/s
        By : float
            IMF GSM y component in nT
        Bz : float
            IMF GSM z component in nT
        tilt : float
            dipole tilt angle in degrees
        F107 : float
            F10.7 index in s.f.u.

        Examples
        --------
        If model currents shall be calculated on the same grid for a range of 
        external conditions, it is faster to do this:
        
        >>> m1 = AMPS(solar_wind_velocity_in_km_per_s, IMF_By_in_nT, IMF_Bz_in_nT, dipole_tilt_in_deg, F107_index)
        >>> # ... current calculations ...
        >>> m1.update_model(new_v, new_By, new_Bz, new_tilt, new_F107)
        >>> # ... new current calcuations ...
        
        than to make a new object:
        
        >>> m2 = AMPS(new_v, new_By, new_Bz, new_tilt, new_F107)
        >>> # ... new current calculations ...
        
        Also note that the inputs are scalars in both cases. It is possible to optimize the calculations significantly
        by allowing the inputs to be arrays. That is not yet implemented.

        """
        
        self.tor_c, self.tor_s, self.pol_c, self.pol_s, self.pol_keys, self.tor_keys = get_model_vectors(v, By, Bz, tilt, F107)



    def _get_vectorgrid(self, **kwargs):
        """ 
        Make grid for plotting vectors

        kwargs are passed to equalAreaGrid(...)
        """

        grid = equalAreaGrid(dr = self.dr, M0 = self.M0, **kwargs)
        mlt  = grid[1] + grid[2]/2. # shift to the center points of the bins
        mlat = grid[0] + (grid[0][1] - grid[0][0])/2  # shift to the center points of the bins

        mlt  = mlt[ (mlat >= self.minlat) & (mlat <= self.maxlat)]# & (mlat <=60 )]
        mlat = mlat[(mlat >= self.minlat) & (mlat <= self.maxlat)]# & (mlat <= 60)]

        mlat = np.hstack((mlat, -mlat)) # add southern hemisphere points
        mlt  = np.hstack((mlt ,  mlt)) # add southern hemisphere points


        return mlat[:, np.newaxis], mlt[:, np.newaxis] # reshape to column vectors and return


    def _get_scalargrid(self, resolution = 100):
        """ 
        Make grid for calculations of scalar fields 

        Parameters
        ----------
        resolution : int, optional
            resolution in both directions of the scalar field grids (default 100)
        """

        mlat, mlt = map(np.ravel, np.meshgrid(np.linspace(self.minlat , self.maxlat, resolution), np.linspace(-179.9, 179.9, resolution)))
        mlat = np.hstack((mlat, -mlat)) # add southern hemisphere points
        mlt  = np.hstack((mlt ,   mlt)) * 12/180 # add points for southern hemisphere and scale to mlt
        self.scalar_resolution = resolution

        return mlat[:, np.newaxis], mlt[:, np.newaxis] + 12 # reshape to column vectors and return

    def calculate_matrices(self):
        """ 
        Calculate the matrices that are needed to calculate currents and potentials 

        Call this function if and only if the grid has been changed manually
        """

        mlt2r = np.pi/12

        # cos(m * phi) and sin(m * phi):
        self.pol_cosmphi_vector = np.cos(self.m_P * self.vectorgrid[1] * mlt2r)
        self.pol_cosmphi_scalar = np.cos(self.m_P * self.scalargrid[1] * mlt2r)
        self.pol_sinmphi_vector = np.sin(self.m_P * self.vectorgrid[1] * mlt2r)
        self.pol_sinmphi_scalar = np.sin(self.m_P * self.scalargrid[1] * mlt2r)
        self.tor_cosmphi_vector = np.cos(self.m_T * self.vectorgrid[1] * mlt2r)
        self.tor_cosmphi_scalar = np.cos(self.m_T * self.scalargrid[1] * mlt2r)
        self.tor_sinmphi_vector = np.sin(self.m_T * self.vectorgrid[1] * mlt2r)
        self.tor_sinmphi_scalar = np.sin(self.m_T * self.scalargrid[1] * mlt2r)

        self.coslambda_vector = np.cos(self.vectorgrid[0] * np.pi/180)

        # P and dP ( shape  NEQ, NED):
        vector_P, vector_dP = get_legendre(self.N, self.M, 90 - self.vectorgrid[0])
        scalar_P, scalar_dP = get_legendre(self.N, self.M, 90 - self.scalargrid[0])

        self.pol_P_vector  =  np.array([vector_P[ key] for key in self.keys_P ]).squeeze().T
        self.pol_dP_vector = -np.array([vector_dP[key] for key in self.keys_P ]).squeeze().T # change sign since we use lat - not colat
        self.pol_P_scalar  =  np.array([scalar_P[ key] for key in self.keys_P ]).squeeze().T
        self.pol_dP_scalar = -np.array([scalar_dP[key] for key in self.keys_P ]).squeeze().T
        self.tor_P_vector  =  np.array([vector_P[ key] for key in self.keys_T ]).squeeze().T
        self.tor_dP_vector = -np.array([vector_dP[key] for key in self.keys_T ]).squeeze().T
        self.tor_P_scalar  =  np.array([scalar_P[ key] for key in self.keys_T ]).squeeze().T
        self.tor_dP_scalar = -np.array([scalar_dP[key] for key in self.keys_T ]).squeeze().T



    def get_toroidal_scalar(self):
        """ 
        Calculate the toroidal scalar values (unit is nT). 

        Returns
        -------
        T_n : numpy.array
            Toroidal scalar in the northern hemisphere.
            Shape: (self.resolution, self.resolution)
        T_s : numpy.array
            Toroidal scalar in the southern hemisphere.
            Shape: (self.resolution, self.resolution)
        """

        T = (  np.dot(self.tor_P_scalar * self.tor_cosmphi_scalar, self.tor_c)
             + np.dot(self.tor_P_scalar * self.tor_sinmphi_scalar, self.tor_s) ) 

        _reshape = lambda x: np.reshape(x, (self.scalar_resolution, self.scalar_resolution))
        return map( _reshape, np.split(T, 2)) # north, south 


    def get_poloidal_scalar(self):
        """ 
        Calculate the poloidal scalar potential values (unit is microTm).

        Returns
        -------
        V_n : numpy.array
            Poloidal scalar potential in the northern hemisphere.
            Shape: (self.resolution, self.resolution)
        V_s : numpy.array
            Poloidal scalar potential in the southern hemisphere.
            Shape: (self.resolution, self.resolution)
        """

        rtor = (REFRE / (REFRE + self.height)) ** (self.n_P + 1)
        P = REFRE * (  np.dot(rtor * self.pol_P_scalar * self.pol_cosmphi_scalar, self.pol_c ) 
                     + np.dot(rtor * self.pol_P_scalar * self.pol_sinmphi_scalar, self.pol_s ) )

        _reshape = lambda x: np.reshape(x, (self.scalar_resolution, self.scalar_resolution))
        return map( _reshape, np.split(P, 2)) # north, south 


    def get_equivalent_current_function(self):
        """
        Calculate the equivalent current function (unit is kA). Isocontours of the
        equivalent current function indicates the alignment of the divergence-free
        part of the horizontal current. Its direction is given by the cross product between
        a vertical vector and the gradient of the equivalent current function. 
        A fixed amount of current flows between isocontours. The calculations refer to 
        the height chosen upon initialization of the AMPS object (default 110 km).

        Note
        ----
        Normally, the term `equivalent current` signifies a horizontal current in space which is 
        equivalent with observed ground magnetic field perturbations. The present `equivalent current` 
        is derived from measurements above the ionosphere, and thus it contains signal both from 
        ionospheric currents below low Earth orbit, and from subsurface induced currents. 
        See Laundal et al. (2016) [1]_ where this current is called
        `Psi` for more detail.


        Returns
        -------
        Psi_n : numpy.array
            Equivalent current function in the northern hemisphere.
            Shape: (self.resolution, self.resolution)
        Psi_s : numpy.array
            Equivalent current function in the southern hemisphere.
            Shape: (self.resolution, self.resolution)

        References
        ----------
        .. [1] K. M. Laundal, C. C. Finlay, and N. Olsen, "Sunlight effects on the 3D polar current 
           system determined from low Earth orbit measurements" Earth, Planets and Space, 2016,
           https://doi.org/10.1186/s40623-016-0518-x
        """

        rtor = (REFRE / (REFRE + self.height)) ** (self.n_P + 1.) * (2.*self.n_P + 1.)/self.n_P
        Psi = - REFRE / MU0 * (  np.dot(rtor * self.pol_P_scalar * self.pol_cosmphi_scalar, self.pol_c ) 
                               + np.dot(rtor * self.pol_P_scalar * self.pol_sinmphi_scalar, self.pol_s ) ) * 1e-9  # kA
        
        _reshape = lambda x: np.reshape(x, (self.scalar_resolution, self.scalar_resolution))
        return map( _reshape, np.split(Psi, 2)) # north, south 

    def get_equivalent_current_laplacian(self):
        """ 
        Calculate the Laplacian of the equivalent current function. In some circumstances, this
        quantity is similar to the upward current.

        Returns
        -------
        d2P_n : numpy.array
            Laplacian of the equivalent current function in the northern hemisphere.
            Shape: (self.resolution, self.resolution)
        d2P_s : numpy.array
            Laplacian of the equivalent current function in the southern hemisphere.
            Shape: (self.resolution, self.resolution)
        """
        
        rtor = (REFRE/(REFRE + self.height))**(self.n_P + 2)
        Ju = 1e-6/(MU0 * (REFRE + self.height) ) * (   np.dot((self.n_P + 1)* (2*self.n_P + 1) * rtor * self.pol_P_scalar * self.pol_cosmphi_scalar, self.pol_c) 
                                                     + np.dot((self.n_P + 1)* (2*self.n_P + 1) * rtor * self.pol_P_scalar * self.pol_sinmphi_scalar, self.pol_s) )

        _reshape = lambda x: np.reshape(x, (self.scalar_resolution, self.scalar_resolution))
        return map( _reshape, np.split(Ju, 2)) # north, south 

    def get_upward_current(self):
        """
        Calculate the upward current (unit is microAmps per square meter). The 
        calculations refer to the height chosen upon initialization of the 
        AMPS object (default 110 km).


        Returns
        -------
        Ju_n : numpy.array
            Upward current in the northern hemisphere.
            Shape: (self.resolution, self.resolution)
        Ju_s : numpy.array
            Upward current in the southern hemisphere.
            Shape: (self.resolution, self.resolution)
        """
        
        Ju = -1e-6/(MU0 * (REFRE + self.height) ) * (   np.dot(self.n_T * (self.n_T + 1) * self.tor_P_scalar * self.tor_cosmphi_scalar, self.tor_c) 
                                                      + np.dot(self.n_T * (self.n_T + 1) * self.tor_P_scalar * self.tor_sinmphi_scalar, self.tor_s) )

        _reshape = lambda x: np.reshape(x, (self.scalar_resolution, self.scalar_resolution))
        return map( _reshape, np.split(Ju, 2)) # north, south 


    def get_curl_free_current_potential(self):
        """ 
        Calculate the curl-free current potential (unit is kA). The curl-free
        current potential is a scalar alpha which relates to the curl-free part
        of the horizontal current by J_{cf} = grad(alpha). The calculations 
        refer to the height chosen upon initialization of the AMPS object (default 
        110 km). 

        Returns
        -------
        alpha_n : numpy.array
            Curl-free current potential in the northern hemisphere.
            Shape: (self.resolution, self.resolution)
        alpha_s : numpy.array
            Curl-free current potential in the southern hemisphere.
            Shape: (self.resolution, self.resolution)

        """
        alpha = -(REFRE + self.height) / MU0 * (   np.dot(self.tor_P_scalar * self.tor_cosmphi_scalar, self.tor_c) 
                                                 + np.dot(self.tor_P_scalar * self.tor_sinmphi_scalar, self.tor_s) ) * 1e-9

        _reshape = lambda x: np.reshape(x, (self.scalar_resolution, self.scalar_resolution))
        return map( _reshape, np.split(alpha, 2)) # north, south 



    def get_divergence_free_current(self, mlat = DEFAULT, mlt = DEFAULT):
        """ 
        Calculate the divergence-free part of the horizontal current, in units of mA/m.
        The calculations refer to the height chosen upon initialization of the AMPS 
        object (default 110 km).

        Parameters
        ----------
        mlat : numpy.array, optional
            array of mlats at which to calculate the current. Will be ignored if mlt is not also specified. If 
            not specified, the calculations will be done using the coords of the `vectorgrid` attribute.
        mlt : numpy.array, optional
            array of mlts at which to calculate the current. Will be ignored if mlat is not also specified. If 
            not specified, the calculations will be done using the coords of the `vectorgrid` attribute.


        Return
        ------
        jdf_eastward : numpy.array, float
            eastward component of the divergence-free current evalulated at the coordinates given by the `vectorgrid` attribute
        jdf_northward : numpy.array, float
            northward component of the divergence-free current evalulated at the coordinates given by the `vectorgrid` attribute

        See Also
        --------
        get_curl_free_current : Calculate curl-free part of the current
        get_total_current : Calculate total horizontal current

        """
        
        rtor = (REFRE / (REFRE + self.height)) ** (self.n_P + 2.) * (2.*self.n_P + 1.)/self.n_P /MU0 * 1e-6

        if mlat is DEFAULT or mlt is DEFAULT:
            east  =    (  np.dot(rtor * self.pol_dP_vector * self.pol_cosmphi_vector, self.pol_c) 
                        + np.dot(rtor * self.pol_dP_vector * self.pol_sinmphi_vector, self.pol_s) )
    
            north =  - (  np.dot(rtor * self.pol_P_vector * self.m_P * self.pol_cosmphi_vector, self.pol_s)
                        - np.dot(rtor * self.pol_P_vector * self.m_P * self.pol_sinmphi_vector, self.pol_c) ) / self.coslambda_vector


        else: # calculate at custom mlat, mlt
            mlat = mlat.flatten()[:, np.newaxis]
            mlt  = mlt.flatten()[:, np.newaxis]

            P, dP = get_legendre(self.N, self.M, 90 - mlat)
            P  =  np.array([ P[ key] for key in self.keys_P]).T.squeeze()
            dP = -np.array([dP[ key] for key in self.keys_P]).T.squeeze()
            cosmphi   = np.cos(self.m_P *  mlt * np.pi/12 )
            sinmphi   = np.sin(self.m_P *  mlt * np.pi/12 )
            coslambda = np.cos(           mlat * np.pi/180)

            east  = (  np.dot(rtor * dP            * cosmphi, self.pol_c) \
                     + np.dot(rtor * dP            * sinmphi, self.pol_s) )
            north = (- np.dot(rtor *  P * self.m_P * cosmphi, self.pol_s) \
                     + np.dot(rtor *  P * self.m_P * sinmphi, self.pol_c) ) / coslambda

        return east.flatten(), north.flatten()



    def get_curl_free_current(self, mlat = DEFAULT, mlt = DEFAULT):
        """ 
        Calculate the curl-free part of the horizontal current, in units of mA/m.
        The calculations refer to the height chosen upon initialization of the AMPS 
        object (default 110 km).


        Parameters
        ----------
        mlat : numpy.array, optional
            array of mlats at which to calculate the current. Will be ignored if mlt is not also specified. If 
            not specified, the calculations will be done using the coords of the `vectorgrid` attribute.
        mlt : numpy.array, optional
            array of mlts at which to calculate the current. Will be ignored if mlat is not also specified. If 
            not specified, the calculations will be done using the coords of the `vectorgrid` attribute.


        Return
        ------
        jcf_eastward : numpy.array, float
            eastward component of the curl-free current evalulated at the coordinates given by the `vectorgrid` attribute
        jcf_northward : numpy.array, float
            northward component of the curl-free current evalulated at the coordinates given by the `vectorgrid` attribute

        See Also
        --------
        get_divergence_free_current : Calculate divergence-free part of the horizontal current
        get_total_current : Calculate total horizontal current
        """

        rtor = -1.e-6/MU0

        if mlat is DEFAULT or mlt is DEFAULT:
            east = rtor * (    np.dot(self.tor_P_vector * self.m_T * self.tor_cosmphi_vector, self.tor_s )
                             - np.dot(self.tor_P_vector * self.m_T * self.tor_sinmphi_vector, self.tor_c )) / self.coslambda_vector
    
            north = rtor * (   np.dot(self.tor_dP_vector * self.tor_cosmphi_vector, self.tor_c)
                             + np.dot(self.tor_dP_vector * self.tor_sinmphi_vector, self.tor_s))

        else: # calculate at custom mlat, mlt
            mlat = mlat.flatten()[:, np.newaxis]
            mlt  = mlt.flatten()[ :, np.newaxis]

            P, dP = get_legendre(self.N, self.M, 90 - mlat)
            P  =  np.array([ P[ key] for key in self.keys_T]).T.squeeze()
            dP = -np.array([dP[ key] for key in self.keys_T]).T.squeeze()
            cosmphi   = np.cos(self.m_T *  mlt * np.pi/12 )
            sinmphi   = np.sin(self.m_T *  mlt * np.pi/12 )
            coslambda = np.cos(           mlat * np.pi/180)

            east  = (  np.dot(rtor *  P * self.m_T * cosmphi, self.tor_s) \
                     - np.dot(rtor *  P * self.m_T * sinmphi, self.tor_c) ) / coslambda
            north = (  np.dot(rtor * dP            * cosmphi, self.tor_c) \
                     + np.dot(rtor * dP            * sinmphi, self.tor_s) ) 


        return east.flatten(), north.flatten()


    def get_total_current(self, mlat = DEFAULT, mlt = DEFAULT):
        """ 
        Calculate the total horizontal current, in units of mA/m. This is calculated as 
        the sum of the curl-free and divergence-free parts. The calculations refer to 
        the height chosen upon initialization of the AMPS object (default 110 km).

        Parameters
        ----------
        mlat : numpy.array, optional
            array of mlats at which to calculate the current. Will be ignored if mlt is not also specified. If 
            not specified, the calculations will be done using the coords of the `vectorgrid` attribute.
        mlt : numpy.array, optional
            array of mlts at which to calculate the current. Will be ignored if mlat is not also specified. If 
            not specified, the calculations will be done using the coords of the `vectorgrid` attribute.


        Return
        ------
        j_eastward : numpy.array, float
            eastward component of the horizontal current evalulated at the coordinates given by the `vectorgrid` attribute
        j_northward : numpy.array, float
            northward component of the horizontal current evalulated at the coordinates given by the `vectorgrid` attribute


        See Also
        --------
        get_divergence_free_current : Calculate divergence-free part of the horizontal current
        get_curl_free_current : Calculate curl-free part of the horizontal current
        """
        
        return [x + y for x, y in zip(self.get_curl_free_current(      mlat = mlat, mlt = mlt), 
                                      self.get_divergence_free_current(mlat = mlat, mlt = mlt))]


    def get_integrated_upward_current(self):
        """ 
        Calculate the integrated upward and downward current, poleward of `minlat`,
        in units of MA.

        Return
        ------
        J_up_n : float
            Total upward current in the northern hemisphere
        J_down_n : float
            Total downward current in the northern hemisphere
        J_up_s : float
            Total upward current in the southern hemisphere
        J_down_s : float
            Total downward current in the southern hemisphere
        """

        jun, jus = self.get_upward_current()
        jun, jus = jun * 1e-6, jus * 1e-6 # convert to A/m^2

        # get surface area element in each cell:
        mlat, mlt = np.split(self.scalargrid[0], 2)[0], np.split(self.scalargrid[1], 2)[0]
        mlat, mlt = mlat.reshape((self.scalar_resolution, self.scalar_resolution)), mlt.reshape((self.scalar_resolution, self.scalar_resolution))
        mltres  = (mlt[1] - mlt[0])[0] * np.pi/12
        mlatres = (mlat[:, 1] - mlat[:, 0])[0] * np.pi/180
        R = (REFRE + self.height) * 1e3  # radius in meters
        dS = R**2 * np.cos(mlat * np.pi/180) * mlatres * mltres


        J_n = dS * jun * 1e-6 # convert to MA
        J_s = dS * jus * 1e-6 # 

        #      J_up_north            J_down_north          J_up_south            J_down_south
        return np.sum(J_n[J_n > 0]), np.sum(J_n[J_n < 0]), np.sum(J_s[J_s > 0]), np.sum(J_s[J_s < 0])


    def get_ground_perturbation(self, mlat, mlt):
        """ 
        Calculate magnetic field perturbations on ground, in units of nT, that corresponds 
        to the equivalent current function.

        Parameters
        ----------
        mlat : np.array, float
            magnetic latitude of the output. The array shape will not be preserved, and 
            the results will be returned as a 1-dimensional array
        mlt : np.array, float
            magnetic local time of the output. The array shape will not be preserved, and 
            the results will be returned as a 1-dimensional array

        Note
        ----
        These calculations are made by assuming that the equivalent current function calculated
        with the AMPS model correspond to the equivalent current function of an external 
        magnetic potential, as described by Chapman & Bartels 1940 [2]_. Induced components are 
        thus ignored. The height of the current function also becomes important when propagating
        the model values to the ground. 

        Also note that the output parameters will be QD components, and that they can be converted
        to geographic by use of QD base vectors [3]_

        This function is not optimized for calculating long time series of model ground
        magnetic field perturbations, although it is possible to use for that.


        Return
        ------
        dB_east : np.array
            Eastward component of the magnetic field disturbance on ground
        dB_north : np.array
            Northward component of the magnetic field disurubance on ground

        References
        ----------
        .. [2] S. Chapman & J. Bartels "Geomagnetism Vol 2" Oxford University Press 1940
        
        .. [3] A. D. Richmond, "Ionospheric Electrodynamics Using Magnetic Apex Coordinates", 
           Journal of geomagnetism and geoelectricity Vol. 47, 1995, http://doi.org/10.5636/jgg.47.191

        """

        mlt  = mlt. flatten()[:, np.newaxis]
        mlat = mlat.flatten()[:, np.newaxis]
        rr   = REFRE / (REFRE + self.height) # ratio of current radius to earth radius

        m = self.m_P
        n = self.n_P


        P, dP = get_legendre(self.N, self.M, 90 - mlat)
        P  = np.array([ P[ key] for key in self.keys_P]).T.squeeze()
        dP = np.array([dP[ key] for key in self.keys_P]).T.squeeze()
        cosmphi = np.cos(m * mlt * np.pi/12)
        sinmphi = np.sin(m * mlt * np.pi/12)

        # G matrix for north component
        G_cn   =  - rr ** (2 * n + 1) * (n + 1.)/n * dP
        Gn     =  np.hstack(( G_cn * cosmphi, G_cn * sinmphi))
        
        # G matrix for east component
        G_ce   =  rr ** (2 * n + 1) * (n + 1.)/n * P * m / np.cos(mlat * np.pi / 180)
        Ge     =  np.hstack((-G_ce * sinmphi, G_ce * cosmphi))

        model = np.vstack((self.pol_c, self.pol_s))

        return Ge.dot(model), Gn.dot(model)


    def get_AE_indices(self):
        """ 
        Calculate model synthetic auroral electrojet (AE) indices: AL and AU. The unit is nT

        Note
        ----
        Here, AL and AU are defined as the lower/upper envelope curves for the northward component
        of the ground magnetic field perturbation that is equivalent with the equivalent current,
        evaluated on `scalargrid`. Thus all the caveats for the `get_ground_perturbation()` function
        applies to these calculations as well. An additional caveat is that we have in principle
        perfect coverage with the model, while the true AE indices are derived using a small set of
        magnetometers in the auroral zone. The model values are also based on QD northward component,
        instead of the "H component", which is used in the official measured AL index. It is possible
        to calculate model AE indices that are more directly comparable to the measured indices.

        Returns
        -------
        AL_n : float
            Model AL index in the northerm hemisphere
        AL_s : float
            Model AL index in the southern hemisphere
        AU_n : float
            Model AU index in the northerm hemisphere
        AU_s : float
            Model AU index in the southern hemisphere
        """

        rr   = REFRE / (REFRE + self.height) # ratio of current radius to earth radius
        m = self.m_P
        n = self.n_P

        dP = self.pol_dP_scalar

        G_cn   =  rr ** (2 * n + 1) * (n + 1.)/n * dP
        Gn     =  np.hstack(( G_cn * self.pol_cosmphi_scalar, G_cn * self.pol_sinmphi_scalar))

        Bn     = Gn.dot(np.vstack((self.pol_c, self.pol_s)))
        Bn_n, Bn_s = np.split(Bn, 2)

        return Bn_n.min(), Bn_s.min(), Bn_n.max(), Bn_s.max()



    def plot_currents(self, vector_scale = 200):
        """ 
        Create a summary plot of the current fields

        Parameters
        ----------
        vector_scale : optional
            Current vector lengths will be shown relative to a template. This parameter determines
            the magnitude of that template, in mA/m. Default is 200 mA/m

        Examples
        --------
        >>> # initialize by supplying a set of external conditions:
        >>> m = AMPS(300, # solar wind velocity in km/s 
                     -4, # IMF By in nT
                     -3, # IMF Bz in nT
                     20, # dipole tilt angle in degrees
                     150) # F10.7 index in s.f.u.
        >>> # make summary plot:
        >>> m.plot_currents()

        """

        # get the grids:
        mlats = np.split(self.scalargrid[0], 2)[0].reshape((self.scalar_resolution, self.scalar_resolution))
        mlts  = np.split(self.scalargrid[1], 2)[0].reshape((self.scalar_resolution, self.scalar_resolution))
        mlatv = np.split(self.vectorgrid[0], 2)[0]
        mltv  = np.split(self.vectorgrid[1], 2)[0]

        # set up figure and polar coordinate plots:
        fig = plt.figure(figsize = (15, 7))
        pax_n = Polarsubplot(plt.subplot2grid((1, 15), (0,  0), colspan = 7), minlat = self.minlat, linestyle = ':', linewidth = .3, color = 'lightgrey')
        pax_s = Polarsubplot(plt.subplot2grid((1, 15), (0,  7), colspan = 7), minlat = self.minlat, linestyle = ':', linewidth = .3, color = 'lightgrey')
        pax_c = plt.subplot2grid((1, 150), (0, 149), colspan = 1)
        
        # labels
        pax_n.writeMLTlabels(mlat = self.minlat, size = 16)
        pax_s.writeMLTlabels(mlat = self.minlat, size = 16)
        pax_n.write(self.minlat, 3,    str(self.minlat) + r'$^\circ$' , ha = 'left', va = 'top', size = 18)
        pax_s.write(self.minlat, 3,    r'$-$' + str(self.minlat) + '$^\circ$', ha = 'left', va = 'top', size = 18)
        pax_n.write(self.minlat-5, 12, r'North' , ha = 'center', va = 'center', size = 18)
        pax_s.write(self.minlat-5, 12, r'South' , ha = 'center', va = 'center', size = 18)

        # calculate and plot FAC
        Jun, Jus = self.get_upward_current()
        faclevels = np.r_[-.925:.926:.05]
        pax_n.contourf(mlats, mlts, Jun, levels = faclevels, cmap = plt.cm.bwr, extend = 'both')
        pax_s.contourf(mlats, mlts, Jus, levels = faclevels, cmap = plt.cm.bwr, extend = 'both')

        # Total horizontal
        j_e, j_n = self.get_total_current()
        nn, ns = np.split(j_n, 2)
        en, es = np.split(j_e, 2)
        pax_n.featherplot(mlatv, mltv, nn , en, SCALE = vector_scale, markersize = 10, unit = 'mA/m', linewidth = '.5', color = 'gray', markercolor = 'grey')
        pax_s.featherplot(mlatv, mltv, -ns, es, SCALE = vector_scale, markersize = 10, unit = None  , linewidth = '.5', color = 'gray', markercolor = 'grey')


        # colorbar
        pax_c.contourf(np.vstack((np.zeros_like(faclevels), np.ones_like(faclevels))), 
                       np.vstack((faclevels, faclevels)), 
                       np.vstack((faclevels, faclevels)), 
                       levels = faclevels, cmap = plt.cm.bwr)
        pax_c.set_xticks([])
        pax_c.set_ylabel('downward    $\hspace{3cm}\mu$A/m$^2\hspace{3cm}$      upward', size = 18)
        pax_c.yaxis.set_label_position("right")
        pax_c.yaxis.tick_right()

        # print AL index values and integrated up/down currents
        AL_n, AL_s, AU_n, AU_s = self.get_AE_indices()
        ju_n, jd_n, ju_s, jd_s = self.get_integrated_upward_current()
        pax_n.ax.text(pax_n.ax.get_xlim()[0], pax_n.ax.get_ylim()[0], 
                      'AL: \t${AL_n:+}$ nT\nAU: \t${AU_n:+}$ nT\n $\int j_\uparrow$:\t ${jn_up:+.1f}$ MA\n $\int j_\downarrow$:\t ${jn_down:+.1f}$ MA'.format(AL_n = int(np.round(AL_n)), AU_n = int(np.round(AU_n)), jn_up = ju_n, jn_down = jd_n), ha = 'left', va = 'bottom', size = 14)
        pax_s.ax.text(pax_s.ax.get_xlim()[0], pax_s.ax.get_ylim()[0], 
                      'AL: \t${AL_s:+}$ nT\nAU: \t${AU_s:+}$ nT\n $\int j_\uparrow$:\t ${js_up:+.1f}$ MA\n $\int j_\downarrow$:\t ${js_down:+.1f}$ MA'.format(AL_s = int(np.round(AL_s)), AU_s = int(np.round(AU_s)), js_up = ju_s, js_down = jd_s), ha = 'left', va = 'bottom', size = 14)


        plt.subplots_adjust(hspace = 0, wspace = 0, left = .05, right = .95, bottom = .05, top = .95)
        plt.show()

