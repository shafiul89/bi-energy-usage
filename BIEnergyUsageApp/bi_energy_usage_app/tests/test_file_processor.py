import gzip
import os
import pytest
import bi_energy_usage_app.elt.file_processor as file_processor


@pytest.fixture
def input_gas_file_path():
    path = os.path.dirname(__file__)
    path = os.path.join(path, 'GasInput.csv.gz')
    if not os.path.exists(path):
        raise FileNotFoundError('Test file not found: ' + path)
    return path


@pytest.fixture
def expected_output_gas_file_path():
    path = os.path.dirname(__file__)
    path = os.path.join(path, 'GasExpectedOutput.csv.gz')
    if not os.path.exists(path):
        raise FileNotFoundError('Test file not found: ' + path)
    return path


@pytest.fixture
def test_output_gas_file_path():
    path = os.path.dirname(__file__)
    path = os.path.join(path, 'GasTestOutput.csv.gz')
    return path


@pytest.fixture
def input_electricity_file_path():
    path = os.path.dirname(__file__)
    path = os.path.join(path, 'ElectricityInput.csv.gz')
    if not os.path.exists(path):
        raise FileNotFoundError('Test file not found: ' + path)
    return path


@pytest.fixture
def expected_output_electricity_file_path():
    path = os.path.dirname(__file__)
    path = os.path.join(path, 'ElectricityExpectedOutput.csv.gz')
    if not os.path.exists(path):
        raise FileNotFoundError('Test file not found: ' + path)
    return path


@pytest.fixture
def test_output_electricity_file_path():
    path = os.path.dirname(__file__)
    path = os.path.join(path, 'ElectricityTestOutput.csv.gz')
    return path


def test_file_processor_gas(input_gas_file_path,
                            expected_output_gas_file_path, test_output_gas_file_path):
    # produce test file
    file_processor.try_process_file(energy_type='gas', year=2020, raw_file_path=input_gas_file_path,
                                    processed_file_path=test_output_gas_file_path, extra_log_info={})
    # read expected results
    with gzip.open(expected_output_gas_file_path, mode='rt', encoding='utf-8-sig') as f:
        expected_output = f.read()
    # read actual results
    with gzip.open(test_output_gas_file_path, mode='rt', encoding='utf-8-sig') as f:
        test_output = f.read()
    # compare
    assert expected_output == test_output
    # delete test file
    os.remove(test_output_gas_file_path)


def test_file_processor_electricity(input_electricity_file_path,
                                    expected_output_electricity_file_path, test_output_electricity_file_path):
    # produce test file
    file_processor.try_process_file(energy_type='electricity', year=2020, raw_file_path=input_electricity_file_path,
                                    processed_file_path=test_output_electricity_file_path, extra_log_info={})
    # read expected results
    with gzip.open(expected_output_electricity_file_path, mode='rt', encoding='utf-8-sig') as f:
        expected_output = f.read()
    # read actual results
    with gzip.open(test_output_electricity_file_path, mode='rt', encoding='utf-8-sig') as f:
        test_output = f.read()
    # compare
    assert expected_output == test_output
    # delete test file
    os.remove(test_output_electricity_file_path)
