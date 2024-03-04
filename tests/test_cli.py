import pytest

from unittest.mock import Mock, ANY, patch
from serial import SerialException
from nrfcredstore.cli import main

from nrfcredstore.credstore import CredType
from nrfcredstore.exceptions import NoATClientException, ATCommandError

# pylint: disable=no-self-use
class TestCli():

    @pytest.fixture
    def at_client(self):
        at_client = Mock()
        return at_client

    @pytest.fixture
    def credstore(self, at_client):
        credstore = Mock()
        credstore.at_client = at_client
        return credstore

    @pytest.fixture
    def offline(self, credstore):
        credstore.funk_mode.return_value = True

    @pytest.fixture
    def empty_cred_list(self, credstore):
        credstore.list.return_value = []

    def test_device_passed_to_connect(self, credstore, at_client, offline, empty_cred_list):
        main(['/dev/tty.usb', 'list'], credstore)
        at_client.connect.assert_called_with('/dev/tty.usb', ANY, ANY)

    def test_baudrate_passed_to_connect(self, credstore, at_client, offline, empty_cred_list):
        main(['fakedev', '--baudrate', '9600', 'list'], credstore)
        at_client.connect.assert_called_with(ANY, 9600, ANY)

    def test_timeout_passed_to_connect(self, credstore, at_client, offline, empty_cred_list):
        main(['fakedev', '--timeout', '3', 'list'], credstore)
        at_client.connect.assert_called_with(ANY, ANY, 3)

    def test_at_client_verify(self, credstore, at_client, offline, empty_cred_list):
        main(['fakedev', 'list'], credstore)
        at_client.verify.assert_called()

    @patch('builtins.print')
    def test_at_client_verify_fail(self, mock_print, credstore, at_client):
        at_client.verify.side_effect = NoATClientException()
        with pytest.raises(SystemExit) as e:
            main(['fakedev', 'list'], credstore)
        assert 'does not respond to AT commands' in mock_print.call_args[0][0]

    def test_at_client_enable_error_codes(self, credstore, at_client, offline, empty_cred_list):
        main(['fakedev', 'list'], credstore)
        at_client.enable_error_codes.assert_called()

    def test_list_default(self, credstore, offline, empty_cred_list):
        main(['fakedev', 'list'], credstore)
        credstore.list.assert_called_with(None, CredType.ANY)

    def test_list_with_tag(self, credstore, offline, empty_cred_list):
        main(['fakedev', 'list', '--tag', '123'], credstore)
        credstore.list.assert_called_with(123, ANY)

    def test_list_with_type(self, credstore, offline, empty_cred_list):
        main(['fakedev', 'list', '--tag', '123', '--type', 'CLIENT_KEY'], credstore)
        credstore.list.assert_called_with(ANY, CredType.CLIENT_KEY)

    def test_write_tag_and_type(self, credstore, offline):
        credstore.write.return_value = True
        main(['fakedev', 'write', '123', 'ROOT_CA_CERT', 'tests/fixtures/root-ca.pem'], credstore)
        credstore.write.assert_called_with(123, CredType.ROOT_CA_CERT, ANY)

    @patch('builtins.open')
    def test_write_file(self, mock_file, credstore, offline):
        credstore.write.return_value = True
        main(['fakedev', 'write', '123', 'ROOT_CA_CERT', 'foo.pem'], credstore)
        mock_file.assert_called_with('foo.pem', 'r', ANY, ANY, ANY)

    @patch('builtins.open')
    def test_write_psk_file(self, mock_file, credstore, offline):
        credstore.write.return_value = True
        main(['fakedev', 'write', '123', 'PSK', 'foo.psk'], credstore)
        mock_file.assert_called_with('foo.psk', 'r', ANY, ANY, ANY)

    def test_delete(self, credstore, offline):
        credstore.delete.return_value = True
        main(['fakedev', 'delete', '123', 'CLIENT_KEY'], credstore)
        credstore.delete.assert_called_with(123, CredType.CLIENT_KEY)

    def test_delete_any_should_fail(self, credstore, offline):
        with pytest.raises(SystemExit):
            main(['fakedev', 'delete', '123', 'ANY'], credstore)

    @patch('builtins.open')
    def test_generate_tag(self, mock_file, credstore, offline):
        credstore.keygen.return_value = True
        main(['fakedev', 'generate', '123', 'foo.der'], credstore)
        credstore.keygen.assert_called_with(123, ANY)

    @patch('builtins.open')
    def test_generate_file(self, mock_file, credstore, offline):
        credstore.keygen.return_value = True
        main(['fakedev', 'generate', '123', 'foo.der'], credstore)
        mock_file.assert_called_with('foo.der', 'wb', ANY, ANY, ANY)

    def test_no_at_client_exit_code(self, credstore, at_client):
        at_client.verify.side_effect = NoATClientException()
        with pytest.raises(SystemExit) as e:
            main(['fakedev', 'list'], credstore)
        assert e.type == SystemExit
        assert e.value.code == 10

    def test_at_command_error_exit_code(self, credstore, at_client):
        at_client.verify.side_effect = ATCommandError()
        with pytest.raises(SystemExit) as e:
            main(['fakedev', 'list'], credstore)
        assert e.type == SystemExit
        assert e.value.code == 11

    def test_timeout_error_exit_code(self, credstore, at_client):
        at_client.verify.side_effect = TimeoutError()
        with pytest.raises(SystemExit) as e:
            main(['fakedev', 'list'], credstore)
        assert e.type == SystemExit
        assert e.value.code == 12

    def test_serial_exception_exit_code(self, credstore, at_client):
        at_client.connect.side_effect = SerialException()
        with pytest.raises(SystemExit) as e:
            main(['fakedev', 'list'], credstore)
        assert e.type == SystemExit
        assert e.value.code == 13

    def test_unhandled_exception_exit_code(self, credstore, at_client):
        at_client.verify.side_effect = Exception()
        with pytest.raises(SystemExit) as e:
            main(['fakedev', 'list'], credstore)
        assert e.type == SystemExit
        assert e.value.code == 1
