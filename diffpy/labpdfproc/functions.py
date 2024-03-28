from diffpy.utils.scattering_objects.diffraction_objects import Diffraction_object
import numpy as np
import math

RADIUS_MM = 1
N_POINTS_ON_DIAMETER = 249
TTH_GRID = np.arange(1, 141, 1)

wavelengths = {"Mo": 0.7107, "Ag": 0.59} # dont need to be capitalized because it's a function

class Gridded_circle():
    def __init__(self,radius,n_points_on_diameter,mu=None):
        self.radius = radius
        self.npoints = n_points_on_diameter
        self.mu = mu
        self.distances = []
        self.muls = []
        self.get_grid_points()

    def get_grid_points(self):
        '''
        given a radius and a grid size, return a grid of points to uniformly sample that circle

        Parameters
        ----------
        radius float
          the radius of the circle
        grid_size int
          the number of points to put along a diameter of the circle.  Odd numbers are preferred.

        Returns
        -------
        the list of tuples that are the coordinates of the grid points

        '''
        xs = np.linspace(-self.radius, self.radius, self.npoints)
        ys = np.linspace(-self.radius, self.radius, self.npoints)
        self.grid = [(x, y) for x in xs for y in ys if x ** 2 + y ** 2 <= self.radius ** 2]
        self.total_points_in_grid = len(self.grid)


    def get_coordinate_index(self,coordinate): # I think we probably dont need this function?
        count = 0
        for i, target in enumerate(self.grid):
            if coordinate == target:
                return i
            else:
                count += 1
        if count >= len(self.grid):
            raise IndexError(f"WARNING: no coordinate {coordinate} found in coordinates list")

    def set_distances_at_angle(self, angle):
        # newly added docstring
        '''
        given an angle, set the distances from the grid points to the entry and exit coordinates

        Parameters
        ----------
        angle float
          the angle in degrees

        Returns
        -------
        the list of distances containing total distance, primary distance and secondary distance

        '''
        self.primary_distances, self.secondary_distances, self.distances = [], [], []
        for coord in self.grid:
            distance, primary, secondary = get_path_length(coord, angle, self.radius)
            self.distances.append(distance)
            self.primary_distances.append(primary)
            self.secondary_distances.append(secondary)

    def set_muls_at_angle(self, angle):
        # newly added docstring
        '''
        compute muls = exp(-mu*distance) for a given angle

        Parameters
        ----------
        angle float
          the angle in degrees

        Returns
        -------
        an array of floats containing the muls corresponding to each angle

        '''
        mu = self.mu
        self.muls = []
        if len(self.distances) == 0:
            self.set_distances_at_angle(angle)
        for distance in self.distances:
            self.muls.append(np.exp(-mu*distance))



def get_entry_exit_coordinates(coordinate, angle, radius):
    '''
    get the coordinates where the beam enters and leaves the circle for a given angle and grid point

    Parameters
    ----------
    grid_point tuple of floats
      the coordinates of the grid point

    angle float
      the angle in degrees

    radius float
      the radius of the circle in units of inverse mu

    it is calculated in the following way:
    For the entry coordinate, the y-component will be the y of the grid point and the x-component will be minus
    the value of x on the circle at the height of this y.

    For the exit coordinate:
    Find the line y = ax + b that passes through grid_point at angle angle
    The circle is x^2 + y^2 = r^2
    The exit point is where these are simultaneous equations
    x^2 + y^2 = r^2 & y = ax + b
    x^2 + (ax+b)^2 = r^2
    => x^2 + a^2x^2 + 2abx + b^2 - r^2 = 0
    => (1+a^2) x^2 + 2abx + (b^2 - r^2) = 0
    to find x_exit we find the roots of these equations and pick the root that is above y-grid
    then we get y_exit from y_exit = a*x_exit + b

    Returns
    -------
    (1) the coordinate of the entry point and (2) of the exit point of a beam entering horizontally
    impinging on a coordinate point that lies in the circle and then exiting at some angle, angle.

    '''
    epsilon = 1e-7   # precision close to 90
    angle = math.radians(angle)
    xgrid = coordinate[0]
    ygrid = coordinate[1]

    entry_point = (-math.sqrt(radius ** 2 - ygrid ** 2), ygrid)

    if not math.isclose(angle, math.pi / 2, abs_tol=epsilon):
        b = ygrid - xgrid * math.tan(angle)
        a = math.tan(angle)
        xexit_root1, xexit_root2 = np.roots((1 + a ** 2, 2 * a * b, b ** 2 - radius ** 2))
        yexit_root1 = a * xexit_root1 + b
        yexit_root2 = a * xexit_root2 + b
        if (yexit_root2 >= ygrid):  # We pick the point above
            exit_point = (xexit_root2, yexit_root2)
        else:
            exit_point = (xexit_root1, yexit_root1)
    else:
        exit_point = (xgrid, math.sqrt(radius**2 - xgrid**2))

    return entry_point, exit_point

def get_path_length(grid_point, angle, radius):
    '''
    return the path length of a horizontal line entering the circle to the grid point then exiting at angle angle

    Parameters
    ----------
    grid_point double of floats
      the coordinate inside the circle

    angle float
      the angle of the output beam

    radius
      the radius of the circle

    Returns
    -------
    floats total distance, primary distance and secondary distance

    '''

    # move angle a tad above zero if it is zero to avoid it having the wrong sign due to some rounding error
    angle_delta = 0.000001
    if angle == float(0):
        angle = angle + angle_delta
    entry_exit = get_entry_exit_coordinates(grid_point, angle, radius)
    primary_distance = math.dist(grid_point, entry_exit[0])
    secondary_distance = math.dist(grid_point, entry_exit[1])
    total_distance = primary_distance + secondary_distance
    return total_distance, primary_distance, secondary_distance





def compute_cve(diffraction_data, mud, wavelength):
    # newly added docstring
    '''
    compute the cve for given diffraction data, mud and wavelength

    Parameters
    ----------
    diffraction_data diffraction object
      the diffraction object to which the cve will be applied
    mud float
      the mu*D of the diffraction object, where D is the diameter of the circle
    wavelength float
      the wavelength of the diffraction object

    Returns
    -------
    the diffraction object with cve curves

    it is computed as follows:
    We first resample data and absorption correction to a more reasonable grid,
    then calculate corresponding cve for the given mud in the resample grid
    (since the same mu*D yields the same cve, we can assume that D/2=1, so mu=mud/2),
    and finally interpolate cve to the original grid in diffraction_data.
    '''

    mu_sample_invmm = mud/2
    abs_correction = Gridded_circle(RADIUS_MM, N_POINTS_ON_DIAMETER, mu=mu_sample_invmm)
    distances, muls = [], []
    for angle in TTH_GRID:
        abs_correction.set_distances_at_angle(angle)
        abs_correction.set_muls_at_angle(angle)
        distances.append(sum(abs_correction.distances))
        muls.append(sum(abs_correction.muls))
    distances = np.array(distances) / abs_correction.total_points_in_grid
    muls = np.array(muls) / abs_correction.total_points_in_grid
    cve = 1/muls

    orig_grid = diffraction_data.on_tth[0]
    newcve = np.interp(orig_grid, TTH_GRID, cve)
    abdo = Diffraction_object(wavelength=wavelength)
    abdo.insert_scattering_quantity(orig_grid, newcve, "tth")

    return abdo


def apply_corr(modo, abdo):
    # newly added docstring
    '''
    Apply correction to the given diffraction object modo with the correction diffraction object abdo

    Parameters
    ----------
    modo diffraction object
      the input diffraction object to which the cve will be applied
    abdo diffraction object
      the diffraction object that contains the cve to be applied

    Returns
    -------
    a corrected diffraction object with the correction applied through multiplication

    '''

    abscormodo = modo * abdo
    print(modo.on_tth[0])
    print(modo.on_tth[1])
    print(abdo.on_tth[0])
    print(abdo.on_tth[1])
    print(abscormodo.on_tth[0])
    print(abscormodo.on_tth[1])
    return abscormodo


# to be added in diffpy.utils
#def dump(base_name, do):
#    data_to_save = np.column_stack((do.on_tth[0], do.on_tth[1]))
#    np.savetxt(f'{base_name}_proc.chi', data_to_save)