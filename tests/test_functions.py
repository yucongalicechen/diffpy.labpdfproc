import re

import numpy as np
import pytest

from diffpy.labpdfproc.functions import (
    CVE_METHODS,
    Gridded_circle,
    apply_corr,
    compute_cve,
)
from diffpy.utils.diffraction_objects import DiffractionObject


@pytest.mark.parametrize(
    "inputs, expected_grid",
    [
        (
            {"radius": 0.5, "n_points_on_diameter": 3, "mu": 1},
            {(0.0, -0.5), (0.0, 0.0), (0.5, 0.0), (-0.5, 0.0), (0.0, 0.5)},
        ),
        (
            {"radius": 1, "n_points_on_diameter": 4, "mu": 1},
            {
                (-0.333333, -0.333333),
                (0.333333, -0.333333),
                (-0.333333, 0.333333),
                (0.333333, 0.333333),
            },
        ),
    ],
)
def test_get_grid_points(inputs, expected_grid):
    actual_gs = Gridded_circle(
        radius=inputs["radius"],
        n_points_on_diameter=inputs["n_points_on_diameter"],
        mu=inputs["mu"],
    )
    actual_grid_sorted = sorted(actual_gs.grid)
    expected_grid_sorted = sorted(expected_grid)
    for actual_pt, expected_pt in zip(
        actual_grid_sorted, expected_grid_sorted
    ):
        assert actual_pt == pytest.approx(expected_pt, rel=1e-4, abs=1e-6)


@pytest.mark.parametrize(
    "inputs, expected_distances",
    [
        (
            {"radius": 1, "n_points_on_diameter": 3, "mu": 1, "angle": 45},
            [0, 1.4142135, 1.4142135, 2, 2],
        ),
        (
            {"radius": 1, "n_points_on_diameter": 3, "mu": 1, "angle": 90},
            [0, 0, 2, 2, 2],
        ),
        (
            {"radius": 1, "n_points_on_diameter": 3, "mu": 1, "angle": 120},
            [0, 0, 2, 3, 1.73205],
        ),
        (
            {"radius": 1, "n_points_on_diameter": 4, "mu": 1, "angle": 30},
            [2.057347, 2.044451, 1.621801, 1.813330],
        ),
        (
            {"radius": 1, "n_points_on_diameter": 4, "mu": 1, "angle": 90},
            [1.885618, 1.885618, 2.552285, 1.218951],
        ),
        (
            {"radius": 1, "n_points_on_diameter": 4, "mu": 1, "angle": 140},
            [1.139021, 2.200102, 2.744909, 1.451264],
        ),
    ],
)
def test_set_distances_at_angle(inputs, expected_distances):
    actual_gs = Gridded_circle(
        radius=inputs["radius"],
        n_points_on_diameter=inputs["n_points_on_diameter"],
        mu=inputs["mu"],
    )
    actual_gs.set_distances_at_angle(inputs["angle"])
    actual_distances_sorted = sorted(actual_gs.distances)
    expected_distances_sorted = sorted(expected_distances)
    assert actual_distances_sorted == pytest.approx(
        expected_distances_sorted, rel=1e-4, abs=1e-6
    )


@pytest.mark.parametrize(
    "input_mu, expected_muls",
    [
        (1, [1, 1, 0.135335, 0.049787, 0.176921]),
        (2, [1, 1, 0.018316, 0.002479, 0.031301]),
    ],
)
def test_set_muls_at_angle(input_mu, expected_muls):
    actual_gs = Gridded_circle(radius=1, n_points_on_diameter=3, mu=input_mu)
    actual_gs.set_muls_at_angle(120)
    actual_muls_sorted = sorted(actual_gs.muls)
    expected_muls_sorted = sorted(expected_muls)
    assert actual_muls_sorted == pytest.approx(
        expected_muls_sorted, rel=1e-4, abs=1e-6
    )


@pytest.mark.parametrize(
    "input_xtype, expected",
    [
        (
            "tth",
            {
                "xarray": np.array([90, 90.1, 90.2]),
                "yarray": np.array([0.5, 0.5, 0.5]),
                "xtype": "tth",
            },
        ),
        (
            "q",
            {
                "xarray": np.array([5.76998, 5.77501, 5.78004]),
                "yarray": np.array([0.5, 0.5, 0.5]),
                "xtype": "q",
            },
        ),
    ],
)
def test_compute_cve(input_xtype, expected, mocker):
    xarray, yarray = np.array([90, 90.1, 90.2]), np.array([2, 2, 2])
    expected_cve = np.array([0.5, 0.5, 0.5])
    mocker.patch("numpy.interp", return_value=expected_cve)
    input_pattern = DiffractionObject(
        xarray=xarray,
        yarray=yarray,
        xtype="tth",
        wavelength=1.54,
        scat_quantity="x-ray",
        name="test",
        metadata={"thing1": 1, "thing2": "thing2"},
    )
    actual_cve_do = compute_cve(
        input_pattern,
        mud=1,
        method="polynomial_interpolation",
        xtype=input_xtype,
    )
    expected_cve_do = DiffractionObject(
        xarray=expected["xarray"],
        yarray=expected["yarray"],
        xtype=expected["xtype"],
        wavelength=1.54,
        scat_quantity="cve",
        name="absorption correction, cve, for test",
        metadata={"thing1": 1, "thing2": "thing2"},
    )
    assert actual_cve_do == expected_cve_do


@pytest.mark.parametrize(
    "inputs, msg",
    [
        (
            {"mud": 10, "method": "polynomial_interpolation"},
            f"mu*D = 10 is out of the acceptable range (0.5 to 7) "
            f"for polynomial interpolation. "
            f"Please rerun with a value within this range "
            f"or specifying another method from {*CVE_METHODS, }.",
        ),
        (
            {"mud": 1, "method": "invalid_method"},
            f"Unknown method: invalid_method. "
            f"Allowed methods are {*CVE_METHODS, }.",
        ),
        (
            {"mud": 7, "method": "invalid_method"},
            f"Unknown method: invalid_method. "
            f"Allowed methods are {*CVE_METHODS, }.",
        ),
    ],
)
def test_compute_cve_bad(mocker, inputs, msg):
    xarray, yarray = np.array([90, 90.1, 90.2]), np.array([2, 2, 2])
    expected_cve = np.array([0.5, 0.5, 0.5])
    mocker.patch("diffpy.labpdfproc.functions.TTH_GRID", xarray)
    mocker.patch("numpy.interp", return_value=expected_cve)
    input_pattern = DiffractionObject(
        xarray=xarray,
        yarray=yarray,
        xtype="tth",
        wavelength=1.54,
        scat_quantity="x-ray",
        name="test",
        metadata={"thing1": 1, "thing2": "thing2"},
    )
    with pytest.raises(ValueError, match=re.escape(msg)):
        compute_cve(input_pattern, mud=inputs["mud"], method=inputs["method"])


def test_apply_corr(mocker):
    xarray, yarray = np.array([90, 90.1, 90.2]), np.array([2, 2, 2])
    expected_cve = np.array([0.5, 0.5, 0.5])
    mocker.patch("diffpy.labpdfproc.functions.TTH_GRID", xarray)
    mocker.patch("numpy.interp", return_value=expected_cve)
    input_pattern = DiffractionObject(
        xarray=xarray,
        yarray=yarray,
        xtype="tth",
        wavelength=1.54,
        scat_quantity="x-ray",
        name="test",
        metadata={"thing1": 1, "thing2": "thing2"},
    )
    absorption_correction = DiffractionObject(
        xarray=xarray,
        yarray=expected_cve,
        xtype="tth",
        wavelength=1.54,
        scat_quantity="cve",
        name="absorption correction, cve, for test",
        metadata={"thing1": 1, "thing2": "thing2"},
    )
    actual_corr = apply_corr(input_pattern, absorption_correction)
    expected_corr = DiffractionObject(
        xarray=xarray,
        yarray=np.array([1, 1, 1]),
        xtype="tth",
        wavelength=1.54,
        scat_quantity="x-ray",
        name="test",
        metadata={"thing1": 1, "thing2": "thing2"},
    )
    assert actual_corr == expected_corr
