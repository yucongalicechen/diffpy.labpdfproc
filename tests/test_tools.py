import os
import re
from pathlib import Path

import pytest

from diffpy.labpdfproc.labpdfprocapp import get_args
from diffpy.labpdfproc.tools import (
    known_sources,
    load_metadata,
    load_package_info,
    load_user_info,
    load_user_metadata,
    preprocessing_args,
    set_input_lists,
    set_mud,
    set_output_directory,
    set_wavelength,
    set_xtype,
)
from diffpy.utils.diffraction_objects import XQUANTITIES


@pytest.mark.parametrize(
    "inputs, expected",
    [
        # Use cases can be found here: https://github.com/diffpy/diffpy.labpdfproc/issues/48
        # This test covers existing single input file, directory, a file list, and multiple files
        # We store absolute path into input_directory and file names into input_file
        (  # C1: single good file in the current directory, expect to return the absolute Path of the file
            ["good_data.chi"],
            ["good_data.chi"],
        ),
        (  # C2: single good file in an input directory, expect to return the absolute Path of the file
            ["input_dir/good_data.chi"],
            ["input_dir/good_data.chi"],
        ),
        (  # C3: glob current directory, expect to return all files in the current directory
            ["."],
            ["good_data.chi", "good_data.xy", "good_data.txt", "unreadable_file.txt", "binary.pkl"],
        ),
        (  # C4: glob input directory, expect to return all files in that directory
            ["./input_dir"],
            [
                "input_dir/good_data.chi",
                "input_dir/good_data.xy",
                "input_dir/good_data.txt",
                "input_dir/unreadable_file.txt",
                "input_dir/binary.pkl",
            ],
        ),
        (  # C5: glob list of input directories, expect to return all files in the directories
            [".", "./input_dir"],
            [
                "./good_data.chi",
                "./good_data.xy",
                "./good_data.txt",
                "./unreadable_file.txt",
                "./binary.pkl",
                "input_dir/good_data.chi",
                "input_dir/good_data.xy",
                "input_dir/good_data.txt",
                "input_dir/unreadable_file.txt",
                "input_dir/binary.pkl",
            ],
        ),
        (  # C6: file_list_example2.txt list of files provided in different directories with wildcard,
            # expect to return all files listed on the file_list file
            ["input_dir/file_list_example2.txt"],
            [
                "input_dir/good_data.chi",
                "good_data.xy",
                "input_dir/good_data.txt",
                "input_dir/unreadable_file.txt",
            ],
        ),
        (  # C7: wildcard pattern, expect to match files with .chi extension in the same directory
            ["./*.chi"],
            ["good_data.chi"],
        ),
        (  # C8: wildcard pattern, expect to match files with .chi extension in the input directory
            ["input_dir/*.chi"],
            ["input_dir/good_data.chi"],
        ),
        (  # C9: wildcard pattern, expect to match files starting with good_data
            ["good_data*"],
            ["good_data.chi", "good_data.xy", "good_data.txt"],
        ),
    ],
)
def test_set_input_lists(inputs, expected, user_filesystem):
    base_dir = Path(user_filesystem)
    os.chdir(base_dir)
    expected_paths = [base_dir.resolve() / expected_path for expected_path in expected]

    cli_inputs = ["2.5"] + inputs
    actual_args = get_args(cli_inputs)
    actual_args = set_input_lists(actual_args)
    assert sorted(actual_args.input_paths) == sorted(expected_paths)


@pytest.mark.parametrize(
    "inputs, expected_error_msg",
    [
        # This test covers non-existing single input file or directory, in this case we raise an error with message
        (  # C1: non-existing single file
            ["non_existing_file.xy"],
            "Cannot find non_existing_file.xy. Please specify valid input file(s) or directories.",
        ),
        (  # C2: non-existing single file with directory
            ["./input_dir/non_existing_file.xy"],
            "Cannot find ./input_dir/non_existing_file.xy. Please specify valid input file(s) or directories.",
        ),
        (  # C3: non-existing single directory
            ["./non_existing_dir"],
            "Cannot find ./non_existing_dir. Please specify valid input file(s) or directories.",
        ),
        (  # C4: list of files provided (with missing files)
            ["good_data.chi", "good_data.xy", "unreadable_file.txt", "missing_file.txt"],
            "Cannot find missing_file.txt. Please specify valid input file(s) or directories.",
        ),
        (  # C5: file_list.txt list of files provided (with missing files)
            ["input_dir/file_list.txt"],
            "Cannot find missing_file.txt. Please specify valid input file(s) or directories.",
        ),
    ],
)
def test_set_input_files_bad(inputs, expected_error_msg, user_filesystem):
    base_dir = Path(user_filesystem)
    os.chdir(base_dir)
    cli_inputs = ["2.5"] + inputs
    actual_args = get_args(cli_inputs)
    with pytest.raises(FileNotFoundError, match=re.escape(expected_error_msg)):
        actual_args = set_input_lists(actual_args)


@pytest.mark.parametrize(
    "inputs, expected",
    [
        ([], ["."]),
        (["--output-directory", "."], ["."]),
        (["--output-directory", "new_dir"], ["new_dir"]),
        (["--output-directory", "input_dir"], ["input_dir"]),
    ],
)
def test_set_output_directory(inputs, expected, user_filesystem):
    os.chdir(user_filesystem)
    expected_output_directory = Path(user_filesystem) / expected[0]
    cli_inputs = ["2.5", "data.xy"] + inputs
    actual_args = get_args(cli_inputs)
    actual_args = set_output_directory(actual_args)
    assert actual_args.output_directory == expected_output_directory
    assert Path(actual_args.output_directory).exists()
    assert Path(actual_args.output_directory).is_dir()


def test_set_output_directory_bad(user_filesystem):
    os.chdir(user_filesystem)
    cli_inputs = ["2.5", "data.xy", "--output-directory", "good_data.chi"]
    actual_args = get_args(cli_inputs)
    with pytest.raises(FileExistsError):
        actual_args = set_output_directory(actual_args)
        assert Path(actual_args.output_directory).exists()
        assert not Path(actual_args.output_directory).is_dir()


@pytest.mark.parametrize(
    "inputs, expected",
    [
        ([], {"wavelength": 0.71073, "anode_type": "Mo"}),
        (["--anode-type", "Ag"], {"wavelength": 0.59, "anode_type": "Ag"}),
        (["--wavelength", "0.25"], {"wavelength": 0.25, "anode_type": None}),
        (["--wavelength", "0.25", "--anode-type", "Ag"], {"wavelength": 0.25, "anode_type": None}),
    ],
)
def test_set_wavelength(inputs, expected):
    cli_inputs = ["2.5", "data.xy"] + inputs
    actual_args = get_args(cli_inputs)
    actual_args = set_wavelength(actual_args)
    assert actual_args.wavelength == expected["wavelength"]
    assert getattr(actual_args, "anode_type", None) == expected["anode_type"]


@pytest.mark.parametrize(
    "inputs, expected_error_msg",
    [
        (
            ["--anode-type", "invalid"],
            f"Anode type not recognized. Please rerun specifying an anode_type from {*known_sources, }.",
        ),
        (
            ["--wavelength", "0"],
            "No valid wavelength. Please rerun specifying a known anode_type or a positive wavelength.",
        ),
        (
            ["--wavelength", "-1", "--anode-type", "Mo"],
            "No valid wavelength. Please rerun specifying a known anode_type or a positive wavelength.",
        ),
    ],
)
def test_set_wavelength_bad(inputs, expected_error_msg):
    cli_inputs = ["2.5", "data.xy"] + inputs
    actual_args = get_args(cli_inputs)
    with pytest.raises(ValueError, match=re.escape(expected_error_msg)):
        actual_args = set_wavelength(actual_args)


@pytest.mark.parametrize(
    "inputs, expected_xtype",
    [
        ([], "tth"),
        (["--xtype", "2theta"], "tth"),
        (["--xtype", "d"], "d"),
        (["--xtype", "q"], "q"),
    ],
)
def test_set_xtype(inputs, expected_xtype):
    cli_inputs = ["2.5", "data.xy"] + inputs
    actual_args = get_args(cli_inputs)
    actual_args = set_xtype(actual_args)
    assert actual_args.xtype == expected_xtype


def test_set_xtype_bad():
    cli_inputs = ["2.5", "data.xy", "--xtype", "invalid"]
    actual_args = get_args(cli_inputs)
    with pytest.raises(
        ValueError, match=re.escape(f"Unknown xtype: invalid. Allowed xtypes are {*XQUANTITIES, }.")
    ):
        actual_args = set_xtype(actual_args)


def test_set_mud(user_filesystem):
    cli_inputs = ["2.5", "data.xy"]
    actual_args = get_args(cli_inputs)
    actual_args = set_mud(actual_args)
    assert actual_args.mud == pytest.approx(2.5, rel=1e-4, abs=0.1)
    assert actual_args.z_scan_file is None

    cwd = Path(user_filesystem)
    test_dir = cwd / "test_dir"
    os.chdir(cwd)
    inputs = ["--z-scan-file", "test_dir/testfile.xy"]
    expected = [3, str(test_dir / "testfile.xy")]
    cli_inputs = ["2.5", "data.xy"] + inputs
    actual_args = get_args(cli_inputs)
    actual_args = set_mud(actual_args)
    assert actual_args.mud == pytest.approx(expected[0], rel=1e-4, abs=0.1)
    assert actual_args.z_scan_file == expected[1]


def test_set_mud_bad():
    cli_inputs = ["2.5", "data.xy", "--z-scan-file", "invalid file"]
    actual_args = get_args(cli_inputs)
    with pytest.raises(FileNotFoundError, match="Cannot find invalid file. Please specify a valid file path."):
        actual_args = set_mud(actual_args)


@pytest.mark.parametrize(
    "inputs, expected",
    [
        ([], []),
        (
            ["--user-metadata", "facility=NSLS II", "beamline=28ID-2", "favorite color=blue"],
            [["facility", "NSLS II"], ["beamline", "28ID-2"], ["favorite color", "blue"]],
        ),
        (["--user-metadata", "x=y=z"], [["x", "y=z"]]),
    ],
)
def test_load_user_metadata(inputs, expected):
    expected_args = get_args(["2.5", "data.xy"])
    for expected_pair in expected:
        setattr(expected_args, expected_pair[0], expected_pair[1])
    delattr(expected_args, "user_metadata")

    cli_inputs = ["2.5", "data.xy"] + inputs
    actual_args = get_args(cli_inputs)
    actual_args = load_user_metadata(actual_args)
    assert actual_args == expected_args


@pytest.mark.parametrize(
    "inputs, expected_error_msg",
    [
        (
            ["--user-metadata", "facility=", "NSLS II"],
            "Please provide key-value pairs in the format key=value. "
            "For more information, use `labpdfproc --help.`",
        ),
        (
            ["--user-metadata", "favorite", "color=blue"],
            "Please provide key-value pairs in the format key=value. "
            "For more information, use `labpdfproc --help.`",
        ),
        (
            ["--user-metadata", "beamline", "=", "28ID-2"],
            "Please provide key-value pairs in the format key=value. "
            "For more information, use `labpdfproc --help.`",
        ),
        (
            ["--user-metadata", "facility=NSLS II", "facility=NSLS III"],
            "Please do not specify repeated keys: facility.",
        ),
        (
            ["--user-metadata", "wavelength=2"],
            "wavelength is a reserved name. Please rerun using a different key name.",
        ),
    ],
)
def test_load_user_metadata_bad(inputs, expected_error_msg):
    cli_inputs = ["2.5", "data.xy"] + inputs
    actual_args = get_args(cli_inputs)
    with pytest.raises(ValueError, match=re.escape(expected_error_msg)):
        actual_args = load_user_metadata(actual_args)


@pytest.mark.parametrize(
    "inputs, expected",
    [  # Test that when cli inputs are present, they override home config, otherwise we take home config
        (
            {"username": None, "email": None, "orcid": None},
            {"username": "home_username", "email": "home@email.com", "orcid": "home_orcid"},
        ),
        (
            {"username": "cli_username", "email": None, "orcid": None},
            {"username": "cli_username", "email": "home@email.com", "orcid": "home_orcid"},
        ),
        (
            {"username": None, "email": "cli@email.com", "orcid": None},
            {"username": "home_username", "email": "cli@email.com", "orcid": "home_orcid"},
        ),
        (
            {"username": None, "email": None, "orcid": "cli_orcid"},
            {"username": "home_username", "email": "home@email.com", "orcid": "cli_orcid"},
        ),
        (
            {"username": "cli_username", "email": "cli@email.com", "orcid": "cli_orcid"},
            {"username": "cli_username", "email": "cli@email.com", "orcid": "cli_orcid"},
        ),
    ],
)
def test_load_user_info(monkeypatch, inputs, expected, user_filesystem):
    cwd = Path(user_filesystem)
    home_dir = cwd / "home_dir"
    monkeypatch.setattr("pathlib.Path.home", lambda _: home_dir)
    os.chdir(cwd)

    cli_inputs = [
        "2.5",
        "data.xy",
        "--username",
        inputs["username"],
        "--email",
        inputs["email"],
        "--orcid",
        inputs["orcid"],
    ]
    actual_args = get_args(cli_inputs)
    actual_args = load_user_info(actual_args)
    assert actual_args.username == expected["username"]
    assert actual_args.email == expected["email"]
    assert actual_args.orcid == expected["orcid"]


def test_load_package_info(mocker):
    mocker.patch(
        "importlib.metadata.version",
        side_effect=lambda package_name: "3.3.0" if package_name == "diffpy.utils" else "1.2.3",
    )
    cli_inputs = ["2.5", "data.xy"]
    actual_args = get_args(cli_inputs)
    actual_args = load_package_info(actual_args)
    assert actual_args.package_info == {"diffpy.labpdfproc": "1.2.3", "diffpy.utils": "3.3.0"}


def test_load_metadata(mocker, user_filesystem):
    cwd = Path(user_filesystem)
    home_dir = cwd / "home_dir"
    mocker.patch("pathlib.Path.home", lambda _: home_dir)
    os.chdir(cwd)
    mocker.patch(
        "importlib.metadata.version",
        side_effect=lambda package_name: "3.3.0" if package_name == "diffpy.utils" else "1.2.3",
    )
    cli_inputs = [
        "2.5",
        ".",
        "--user-metadata",
        "key=value",
        "--username",
        "cli_username",
        "--email",
        "cli@email.com",
        "--orcid",
        "cli_orcid",
    ]
    actual_args = get_args(cli_inputs)
    actual_args = preprocessing_args(actual_args)
    for filepath in actual_args.input_paths:
        actual_metadata = load_metadata(actual_args, filepath)
        expected_metadata = {
            "mud": 2.5,
            "input_directory": str(filepath),
            "anode_type": "Mo",
            "output_directory": str(Path.cwd().resolve()),
            "xtype": "tth",
            "method": "polynomial_interpolation",
            "key": "value",
            "username": "cli_username",
            "email": "cli@email.com",
            "orcid": "cli_orcid",
            "package_info": {"diffpy.labpdfproc": "1.2.3", "diffpy.utils": "3.3.0"},
            "z_scan_file": None,
        }
        assert actual_metadata == expected_metadata
