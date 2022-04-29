import os.path

import click.exceptions
import pytest
import rich
from openff.qcsubmit.results import TorsionDriveResultCollection
from openff.utilities import get_data_file_path

from openff.bespokefit.cli.cache import (
    _connect_to_qcfractal,
    _results_from_file,
    _update_from_qcsubmit_result,
    update_cli,
)
from openff.bespokefit.tests import does_not_raise


@pytest.mark.parametrize(
    "filename, expected_raises, output",
    [
        pytest.param(
            "torsion_collection.json",
            does_not_raise(),
            "torsion_collection.json loaded as a `TorsionDriveResultCollection`.",
            id="torsiondrive",
        ),
        pytest.param(
            "optimization_collection.json",
            does_not_raise(),
            "optimization_collection.json loaded as a `OptimizationResultCollection`",
            id="optimization",
        ),
        pytest.param(
            "hessian_collection.json",
            pytest.raises(click.exceptions.Exit),
            "[ERROR] The result file",
            id="hessian",
        ),
    ],
)
def test_results_from_file(filename, expected_raises, output):
    """
    Test loading qcsubmit results files.
    """

    console = rich.get_console()

    with console.capture() as capture:
        file_path = get_data_file_path(
            os.path.join("test", "schemas", filename), package_name="openff.bespokefit"
        )

        with expected_raises:
            _ = _results_from_file(console=console, input_file_path=file_path)

    assert output in capture.get().replace("\n", "")


@pytest.mark.parametrize(
    "address, expected_raises, expected_output",
    [
        pytest.param(
            "api.qcarchive.molssi.org:443",
            does_not_raise(),
            "[✓] connected to QCFractal",
            id="QCArchive",
        ),
        pytest.param(
            "api.qcarchive.molssi.com:1",
            pytest.raises(click.exceptions.Exit),
            "[ERROR] Unable to connect to QCFractal due to the following error.",
            id="Error",
        ),
    ],
)
def test_connecting_to_fractal_address(address, expected_raises, expected_output):
    """
    Test connecting to fractal from using an address.
    """
    console = rich.get_console()

    with console.capture() as capture:
        with expected_raises:
            _ = _connect_to_qcfractal(
                console=console, qcf_address=address, qcf_config=None
            )
    assert expected_output in capture.get().replace("\n", "")


def test_connecting_to_fractal_file():
    """
    Try to connect to the QCArchive using an config file.
    """

    console = rich.get_console()

    with console.capture() as capture:
        _ = _connect_to_qcfractal(
            console=console,
            qcf_address="",
            qcf_config=get_data_file_path(
                os.path.join("test", "miscellaneous", "qcfractal.yaml"),
                package_name="openff.bespokefit",
            ),
        )
    assert "[✓] connected to QCFractal" in capture.get()


def test_update_from_qcsubmit(redis_connection):
    """
    Test adding a mocked result to a local redis instance.
    """

    console = rich.get_console()
    qcsubmit_result = TorsionDriveResultCollection.parse_file(
        get_data_file_path(
            os.path.join("test", "schemas", "torsion_collection.json"),
            package_name="openff.bespokefit",
        )
    )

    with console.capture() as capture:
        _update_from_qcsubmit_result(
            console=console,
            qcsubmit_results=qcsubmit_result,
            redis_connection=redis_connection,
        )
    assert "[✓] local results built" in capture.get()
    assert "1/1 results cached" in capture.get()

    # find the result in redis
    task_id = redis_connection.hget(
        name="qcgenerator:task-ids",
        key="21212802afd507cae91fa9b8af76d7fa76174cc1ba4ab04b7c251aa5263598fbb79d9d85a7d0654257afe684312db399bbdbeb174366425a981ab20a31eb6938",
    ).decode()
    assert redis_connection.hget("qcgenerator:types", task_id).decode() == "torsion1d"


def test_cache_cli_fractal(runner, tmpdir):
    """Test running the cache update cli."""

    output = runner.invoke(
        update_cli,
        args=[
            "--qcf-dataset",
            "OpenFF Gen 2 Torsion Set 6 supplemental 2",
            "--qcf-datatype",
            "torsion",
        ],
    )
    assert output.exit_code == 0, print(output.output)
    assert "4. saving local cache" in output.output
