from unittest.mock import patch, Mock
from collections import namedtuple
import pytest

from nrfcredstore.comms import (
    get_connected_nordic_boards,
    select_jlink,
    select_device_by_serial,
    select_device,
    Comms,
)

Port = namedtuple("Port", ["hwid", "device"])

list_ports_mac = [
    Port("n/a", "/dev/cu.debug-console"),
    Port("n/a", "/dev/cu.Bluetooth-Incoming-Port"),
    Port(
        "USB VID:PID=1366:1069 SER=001051202135 LOCATION=1-1.4.4",
        "/dev/cu.usbmodem0010512021353",
    ),
    Port(
        "USB VID:PID=1366:1069 SER=001051202135 LOCATION=1-1.4.4",
        "/dev/cu.usbmodem0010512021351",
    ),
]

list_ports_windows = [
    Port("ACPI\\PNP0501\\1", "COM1"),
    Port("USB VID:PID=1915:910A SER=THINGY91X_F39CC1B120C LOCATION=1-21:x.1", "COM35"),
    Port("USB VID:PID=1915:910A SER=THINGY91X_F39CC1B120C LOCATION=1-21:x.4", "COM36"),
]

list_ports_linux_one = [
    Port("n/a", "/dev/ttyS0"),
    Port("n/a", "/dev/ttyS1"),
    Port(
        "USB VID:PID=1915:910A SER=THINGY91X_F39CC1B120C LOCATION=3-12.1.3.2.1.4:1.1",
        "/dev/ttyACM0",
    ),
    Port(
        "USB VID:PID=1915:910A SER=THINGY91X_F39CC1B120C LOCATION=3-12.1.3.2.1.4:1.4",
        "/dev/ttyACM1",
    ),
]

list_ports_linux_multi = [
    Port("n/a", "/dev/ttyS0"),
    Port("n/a", "/dev/ttyS1"),
    Port(
        "USB VID:PID=1915:910A SER=THINGY91X_F39CC1B120C LOCATION=3-12.1.3.2.1.4:1.1",
        "/dev/ttyACM0",
    ),
    Port(
        "USB VID:PID=1915:910A SER=THINGY91X_F39CC1B120C LOCATION=3-12.1.3.2.1.4:1.4",
        "/dev/ttyACM1",
    ),
    Port(
        "USB VID:PID=1366:1069 SER=001051202135 LOCATION=3-12.1.3.2.4:1.0",
        "/dev/ttyACM2",
    ),
    Port(
        "USB VID:PID=1366:1069 SER=001051202135 LOCATION=3-12.1.3.2.4:1.2",
        "/dev/ttyACM3",
    ),
    Port(
        "USB VID:PID=1366:1051 SER=001050760093 LOCATION=3-12.1.3.2.4:1.0",
        "/dev/ttyACM4",
    ),
    Port(
        "USB VID:PID=1366:1051 SER=001050760093 LOCATION=3-12.1.3.2.4:1.2",
        "/dev/ttyACM5",
    ),
]

list_ports_linux_jlink = [
    Port("n/a", "/dev/ttyS0"),
    Port("n/a", "/dev/ttyS1"),
    Port(
        "USB VID:PID=1366:0105 SER=000821001234 LOCATION=3-12.1.3.2.4:1.0",
        "/dev/ttyACM0",
    ),
]

list_ports_linux_mixed = [
    Port("n/a", "/dev/ttyS0"),
    Port("n/a", "/dev/ttyS1"),
    Port(
        "USB VID:PID=1366:0105 SER=000821001234 LOCATION=3-12.1.3.2.4:1.0",
        "/dev/ttyACM0",
    ),
    Port(
        "USB VID:PID=1366:1051 SER=001050760093 LOCATION=3-12.1.3.2.4:1.0",
        "/dev/ttyACM1",
    ),
    Port(
        "USB VID:PID=1366:1051 SER=001050760093 LOCATION=3-12.1.3.2.4:1.2",
        "/dev/ttyACM2",
    ),
]

list_ports_linux_jlink_multi_com = [
    Port("n/a", "/dev/ttyS0"),
    Port("n/a", "/dev/ttyS1"),
    Port(
        "USB VID:PID=1366:0105 SER=000821001234 LOCATION=3-12.1.3.2.4:1.0",
        "/dev/ttyACM0",
    ),
    Port(
        "USB VID:PID=1366:0105 SER=000821001234 LOCATION=3-12.1.3.2.4:1.2",
        "/dev/ttyACM1",
    ),
    Port(
        "USB VID:PID=1366:0105 SER=000821001234 LOCATION=3-12.1.3.2.4:1.4",
        "/dev/ttyACM2",
    ),
]

@pytest.fixture
def mock_os_realpath():
    with patch("nrfcredstore.comms.os.path.realpath", autospec=True) as m:
        m.side_effect = lambda x: x  # identity function
        yield m

@pytest.fixture
def platform_darwin():
    with patch("nrfcredstore.comms.platform.system", autospec=True) as m:
        m.return_value = "Darwin"
        yield m


@pytest.fixture
def platform_linux():
    with patch("nrfcredstore.comms.platform.system", autospec=True) as m:
        m.return_value = "Linux"
        yield m


@pytest.fixture
def platform_windows():
    with patch("nrfcredstore.comms.platform.system", autospec=True) as m:
        m.return_value = "Windows"
        yield m


@pytest.fixture
def ports_mac():
    with patch("nrfcredstore.comms.list_ports", autospec=True) as m:
        m.comports.return_value = list_ports_mac
        yield m


@pytest.fixture
def ports_windows():
    with patch("nrfcredstore.comms.list_ports", autospec=True) as m:
        m.comports.return_value = list_ports_windows
        yield m


@pytest.fixture
def ports_linux_one():
    with patch("nrfcredstore.comms.list_ports", autospec=True) as m:
        m.comports.return_value = list_ports_linux_one
        yield m


@pytest.fixture
def ports_linux_multi():
    with patch("nrfcredstore.comms.list_ports", autospec=True) as m:
        m.comports.return_value = list_ports_linux_multi
        yield m


@pytest.fixture
def ports_linux_jlink():
    with patch("nrfcredstore.comms.list_ports", autospec=True) as m:
        m.comports.return_value = list_ports_linux_jlink
        yield m


@pytest.fixture
def ports_linux_mixed():
    with patch("nrfcredstore.comms.list_ports", autospec=True) as m:
        m.comports.return_value = list_ports_linux_mixed
        yield m


@pytest.fixture
def ports_empty():
    with patch("nrfcredstore.comms.list_ports", autospec=True) as m:
        m.comports.return_value = []
        yield m


@pytest.fixture
def ports_linux_jlink_multi_com():
    with patch("nrfcredstore.comms.list_ports", autospec=True) as m:
        m.comports.return_value = list_ports_linux_jlink_multi_com
        yield m

@pytest.fixture
def mock_serial():
    """Mock the serial.Serial class."""
    with patch("nrfcredstore.comms.serial.Serial", autospec=True) as mock_serial:
        yield mock_serial

# Tests for get_connected_nordic_boards


def test_mac(platform_darwin, ports_mac):
    boards = get_connected_nordic_boards()
    assert len(boards) == 1
    name, serial, port = boards[0]
    assert port.device == "/dev/cu.usbmodem0010512021351"
    assert serial == 1051202135
    assert name == "nRF9151-DK"


def test_windows(platform_windows, ports_windows):
    boards = get_connected_nordic_boards()
    assert len(boards) == 1
    name, serial, port = boards[0]
    assert port.device == "COM35"
    assert serial == "THINGY91X_F39CC1B120C"
    assert name == "Thingy:91 X"


def test_linux_one(platform_linux, ports_linux_one):
    boards = get_connected_nordic_boards()
    assert len(boards) == 1
    name, serial, port = boards[0]
    assert port.device == "/dev/ttyACM0"
    assert serial == "THINGY91X_F39CC1B120C"
    assert name == "Thingy:91 X"


def test_linux_multi(platform_linux, ports_linux_multi):
    boards = get_connected_nordic_boards()
    assert len(boards) == 3
    assert "Thingy:91 X" in [name for name, _, _ in boards]
    assert "nRF9151-DK" in [name for name, _, _ in boards]
    assert "nRF7002-DK" in [name for name, _, _ in boards]

    for name, serial, port in boards:
        if name == "Thingy:91 X":
            assert port.device == "/dev/ttyACM0"
            assert serial == "THINGY91X_F39CC1B120C"
        elif name == "nRF9151-DK":
            assert port.device == "/dev/ttyACM2"
            assert serial == 1051202135
        elif name == "nRF7002-DK":
            assert port.device == "/dev/ttyACM5"
            assert serial == 1050760093


def test_linux_jlink(platform_linux, ports_linux_jlink):
    boards = get_connected_nordic_boards()
    assert len(boards) == 0


# Tests for select_jlink


def test_select_jlink_no_jlinks():
    with pytest.raises(Exception, match="No J-Link device found"):
        select_jlink(jlinks=[], list_all=True)


def test_select_jlink_one_jlink():
    selected = select_jlink(jlinks=[1051202135], list_all=True)
    assert selected == 1051202135


def test_select_jlink_multiple_jlinks():
    jlinks = [1051202135, 1050760093]
    with patch(
        "nrfcredstore.comms.inquirer.prompt", return_value={"serial": 1051202135}
    ):
        selected = select_jlink(jlinks=jlinks, list_all=True)
        assert selected == 1051202135


# note: is it important to align the mocked ports and the jlink list?
def test_select_jlink_multiple_non_nordic_jlinks(platform_linux, ports_linux_jlink):
    with pytest.raises(Exception, match="No J-Link device found"):
        select_jlink(jlinks=[821001234, 821001235], list_all=False)


def test_select_jlink_mixed_jlinks(platform_linux, ports_linux_mixed):
    selected = select_jlink(jlinks=[821001234, 1050760093], list_all=False)
    assert selected == 1050760093


# Tests for select_device_by_serial


def test_select_device_by_serial_no_devices(ports_empty):
    with pytest.raises(Exception, match="No device found with serial 821001234"):
        select_device_by_serial(serial_number=821001234, list_all=False)


def test_select_device_by_serial_no_matching_device(platform_linux, ports_linux_one):
    with pytest.raises(Exception, match="No device found with serial 999999999"):
        select_device_by_serial(serial_number=999999999, list_all=False)


def test_select_device_by_serial_one_matching_device(platform_linux, ports_linux_one):
    serial_number_requested = "THINGY91X_F39CC1B120C"
    selected_port, serial_number = select_device_by_serial(
        serial_number="THINGY91X_F39CC1B120C", list_all=False
    )
    assert selected_port.device == "/dev/ttyACM0"
    assert serial_number == serial_number_requested


def test_select_device_by_serial_multiple_matching_ports(
    platform_linux, ports_linux_jlink_multi_com
):
    serial_number_requested = 821001234
    port_to_select = list_ports_linux_jlink_multi_com[2]
    with patch(
        "nrfcredstore.comms.inquirer.prompt",
        return_value={"port": port_to_select},
    ):
        selected_port, serial_number = select_device_by_serial(
            serial_number=serial_number_requested, list_all=True
        )
    assert selected_port.device == port_to_select.device
    assert serial_number == serial_number_requested

# Tests for select_device

# rtt true, no serial number
def test_select_device_rtt_true_no_serial_number(platform_linux, ports_linux_multi):
    with patch("nrfcredstore.comms.get_connected_jlinks", return_value=[1051202135, 1050760093]):
        with patch("nrfcredstore.comms.inquirer.prompt", return_value={"serial": 1051202135}):
            _, serial_number = select_device(
                rtt=True, serial_number=None, port=None, list_all=True
            )
    assert serial_number == 1051202135

# rtt true, serial number, device found
def test_select_device_rtt_true_serial_number_found(platform_linux, ports_linux_multi):
    with patch("nrfcredstore.comms.get_connected_jlinks", return_value=[1051202135, 1050760093]):
        _, serial_number = select_device(
            rtt=True, serial_number=1050760093, port=None, list_all=False
        )
    assert serial_number == 1050760093

# rtt true, serial number, device not found
def test_select_device_rtt_true_serial_number_not_found(platform_linux, ports_linux_multi):
    with patch("nrfcredstore.comms.get_connected_jlinks", return_value=[1051202135, 1050760093]):
        with pytest.raises(Exception, match="No device found with serial 999999999"):
            _, serial_number = select_device(
                rtt=True, serial_number=999999999, port=None, list_all=False
            )

# port given
def test_select_device_port_given(platform_linux, ports_linux_multi, mock_os_realpath):
    port, serial_number = select_device(
        rtt=False, serial_number=None, port="/dev/ttyACM0", list_all=False
    )
    assert port.device == "/dev/ttyACM0"
    assert serial_number == "THINGY91X_F39CC1B120C"


# serial number given
def test_select_device_serial_number_given(platform_linux, ports_linux_multi):
    port, serial_number = select_device(
        rtt=False, serial_number="THINGY91X_F39CC1B120C", port=None, list_all=False
    )
    assert port.device == "/dev/ttyACM0"
    assert serial_number == "THINGY91X_F39CC1B120C"

# list all
def test_select_device_list_all(platform_linux, ports_linux_multi):
    port_to_select = list_ports_linux_jlink_multi_com[2]
    with patch("nrfcredstore.comms.inquirer.prompt", return_value={"port": port_to_select}):
        port, serial_number = select_device(
            rtt=False, serial_number=None, port=None, list_all=True
        )
    assert port.device == "/dev/ttyACM0"
    assert serial_number == 821001234

# no list-all, no devices
def test_select_device_no_list_all_no_devices(platform_linux, ports_empty):
    with pytest.raises(Exception, match="No device found"):
        select_device(
            rtt=False, serial_number=None, port=None, list_all=False
        )

# no list-all, one device
def test_select_device_no_list_all_one_device(platform_linux, ports_linux_one):
    port, serial_number = select_device(
        rtt=False, serial_number=None, port=None, list_all=False
    )
    assert port.device == "/dev/ttyACM0"
    assert serial_number == "THINGY91X_F39CC1B120C"

# no list-all, more devices
def test_select_device_no_list_all_more_devices(
    platform_linux, ports_linux_multi
):
    port_to_select = list_ports_linux_multi[2]
    with patch("nrfcredstore.comms.inquirer.prompt", return_value={"port": port_to_select}):
        port, serial_number = select_device(
            rtt=False, serial_number=None, port=None, list_all=False
        )
    assert port.device == port_to_select.device
    assert serial_number == "THINGY91X_F39CC1B120C"

# tests for expect_response

def test_expect_response_ok(mock_serial):
    with patch("nrfcredstore.comms.select_device", return_value=(Mock(), "123456789")) as mock_select:
        comms = Comms()
        comms.read_line = Mock(return_value="OK")
        result, output = comms.expect_response("OK", "ERROR")
        mock_select.assert_called_once()
        assert result is True
        assert output == ''

def test_expect_response_error(mock_serial):
    with patch("nrfcredstore.comms.select_device", return_value=(Mock(), "123456789")) as mock_select:
        comms = Comms()
        comms.read_line = Mock(return_value="ERROR")
        result, output = comms.expect_response("OK", "ERROR")
        mock_select.assert_called_once()
        assert result is False
        assert output == ''

def test_expect_response_error_not_allowed(mock_serial):
    with patch("nrfcredstore.comms.select_device", return_value=(Mock(), "123456789")) as mock_select:
        with patch("nrfcredstore.comms.logging.error") as mock_error:
            comms = Comms()
            comms.read_line = Mock(return_value="+CME ERROR: 514")
            result, output = comms.expect_response("OK", "ERROR")
            mock_select.assert_called_once()
            assert result is False
            assert output == ''
            mock_error.assert_called_once_with("AT command error: Not allowed")

def test_expect_response_timeout(mock_serial):
    with patch("nrfcredstore.comms.select_device", return_value=(Mock(), "123456789")) as mock_select:
        comms = Comms()
        comms.read_line = Mock(return_value="")
        result, output = comms.expect_response("OK", "ERROR", timeout=1)
        mock_select.assert_called_once()
        assert result is False
        assert output == ''

def test_expect_response_store(mock_serial):
    with patch("nrfcredstore.comms.select_device", return_value=(Mock(), "123456789")) as mock_select:
        comms = Comms()
        comms.read_line = Mock(side_effect=['%ATTESTTOKEN: "foo.bar"', "OK"])
        result, output = comms.expect_response("OK", "ERROR", "%ATTESTTOKEN: ")
        mock_select.assert_called_once()
        assert result is True
        assert output.strip() == '%ATTESTTOKEN: "foo.bar"'

def test_expect_response_pattern(mock_serial):
    with patch("nrfcredstore.comms.select_device", return_value=(Mock(), "123456789")) as mock_select:
        comms = Comms()
        comms.read_line = Mock(side_effect=[
            "Stored 48 bytes.",
            "16842753,CA,qLqL2kIyuj7FF9aFXQuhmc8kbMOHNYsM451gElqNyVQ=,0",
            "1 credentials found.",
            "0 credentials found."
        ])
        assert comms.expect_response(ok_pattern="Stored") == (True, '')
        assert comms.expect_response(
            ok_pattern="1 credentials found.",
            error_pattern="0 credentials found.",
            store_str="16842753,CA") == (True, "16842753,CA,qLqL2kIyuj7FF9aFXQuhmc8kbMOHNYsM451gElqNyVQ=,0\r\n")
        assert comms.expect_response(
            ok_pattern="1 credentials found.",
            error_pattern="0 credentials found.",
            store_str="16842753,CA") == (False, '')
