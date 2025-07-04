import pytest

from unittest.mock import Mock, ANY, patch
from serial import SerialException
from nrfcredstore.cli import main, parse_args, run, FUN_MODE_OFFLINE

from nrfcredstore.credstore import CredType
from nrfcredstore.exceptions import NoATClientException, ATCommandError

# pylint: disable=no-self-use
class TestCli():

    @pytest.fixture
    def command_interface(self):
        command_interface = Mock()
        return command_interface

    @pytest.fixture
    def credstore(self, command_interface):
        credstore = Mock()
        credstore.command_interface = command_interface
        return credstore

    @pytest.fixture
    def empty_cred_list(self, credstore):
        credstore.list.return_value = []

    @pytest.fixture
    def cred_list_minimal(self, credstore):
        credstore.list.return_value = [
            Mock(tag=4294967292, type=CredType.NORDIC_PUB_KEY, sha='672E2F05962B4EFBFA8801255D87E0E0418F2DDF4DDAEFC59E9B4162F512CB63'),
            Mock(tag=4294967293, type=CredType.NORDIC_ID_ROOT_CA, sha='2C43952EE9E000FF2ACC4E2ED0897C0A72AD5FA72C3D934E81741CBD54F05BD1'),
            Mock(tag=4294967294, type=CredType.DEV_ID_PUB_KEY, sha='A0C145630DB69B4ED933DDE9F3E77BCD5540A869461DBC82D6F554EA64B6AC9E'),
        ]

    # non-responsive device
    def test_non_responsive_device(self, credstore, command_interface):
        command_interface.detect_shell_mode.side_effect = TimeoutError()
        with pytest.raises(TimeoutError) as e:
            main(parse_args(['fakedev', 'list']), credstore)
        assert e.type == TimeoutError

    def test_non_responsive_device(self, credstore, command_interface, empty_cred_list):
        command_interface.detect_shell_mode.enable_error_codes.return_value = False
        main(parse_args(['fakedev', 'list']), credstore)

    def test_list_default_empty(self, credstore, empty_cred_list):
        main(parse_args(['fakedev', 'list']), credstore)
        credstore.func_mode.assert_called_with(FUN_MODE_OFFLINE)
        credstore.list.assert_called_with(None, CredType.ANY)

    def test_list_default(self, credstore, cred_list_minimal):
        main(parse_args(['fakedev', 'list']), credstore)
        credstore.func_mode.assert_called_with(FUN_MODE_OFFLINE)
        credstore.list.assert_called_with(None, CredType.ANY)

    def test_list_with_tag(self, credstore, empty_cred_list):
        main(parse_args(['fakedev', 'list', '--tag', '123']), credstore)
        credstore.func_mode.assert_called_with(FUN_MODE_OFFLINE)
        credstore.list.assert_called_with(123, ANY)

    def test_list_with_type(self, credstore, empty_cred_list):
        main(parse_args(['fakedev', 'list', '--tag', '123', '--type', 'CLIENT_KEY']), credstore)
        credstore.func_mode.assert_called_with(FUN_MODE_OFFLINE)
        credstore.list.assert_called_with(ANY, CredType.CLIENT_KEY)

    def test_write_tag_and_type(self, credstore):
        credstore.write.return_value = True
        main(parse_args(['fakedev', 'write', '123', 'ROOT_CA_CERT', 'tests/fixtures/root-ca.pem']), credstore)
        credstore.func_mode.assert_called_with(FUN_MODE_OFFLINE)
        credstore.write.assert_called_with(123, CredType.ROOT_CA_CERT, ANY)

    @patch('builtins.open')
    def test_write_file(self, mock_file, credstore):
        credstore.write.return_value = True
        main(parse_args(['fakedev', 'write', '123', 'ROOT_CA_CERT', 'foo.pem']), credstore)
        credstore.func_mode.assert_called_with(FUN_MODE_OFFLINE)
        mock_file.assert_called_with('foo.pem', 'r', ANY, ANY, ANY)

    @patch('builtins.open')
    def test_write_psk_file(self, mock_file, credstore):
        credstore.write.return_value = True
        main(parse_args(['fakedev', 'write', '123', 'PSK', 'foo.psk']), credstore)
        credstore.func_mode.assert_called_with(FUN_MODE_OFFLINE)
        mock_file.assert_called_with('foo.psk', 'r', ANY, ANY, ANY)

    def test_delete(self, credstore):
        credstore.delete.return_value = True
        main(parse_args(['fakedev', 'delete', '123', 'CLIENT_KEY']), credstore)
        credstore.func_mode.assert_called_with(FUN_MODE_OFFLINE)
        credstore.delete.assert_called_with(123, CredType.CLIENT_KEY)

    def test_delete_any_should_fail(self, credstore):
        with pytest.raises(SystemExit):
            main(parse_args(['fakedev', 'delete', '123', 'ANY']), credstore)

    def test_deleteall(self, credstore, cred_list_minimal):
        credstore.deleteall.return_value = True
        main(parse_args(['fakedev', 'deleteall']), credstore)
        credstore.func_mode.assert_called_with(FUN_MODE_OFFLINE)
        credstore.list.assert_called_with(None, CredType.ANY)

    @patch('builtins.open')
    def test_generate_tag(self, mock_file, credstore):
        credstore.keygen.return_value = True
        main(parse_args(['fakedev', 'generate', '123', 'foo.der']), credstore)
        credstore.func_mode.assert_called_with(FUN_MODE_OFFLINE)
        credstore.keygen.assert_called_with(123, ANY, ANY)

    @patch('builtins.open')
    def test_generate_file(self, mock_file, credstore):
        credstore.keygen.return_value = True
        main(parse_args(['fakedev', 'generate', '123', 'foo.der']), credstore)
        credstore.func_mode.assert_called_with(FUN_MODE_OFFLINE)
        mock_file.assert_called_with('foo.der', 'wb', ANY, ANY, ANY)

    @patch('builtins.open')
    def test_generate_with_attributes(self, credstore):
        credstore.keygen.return_value = True
        main(parse_args(['fakedev', 'generate', '123', 'foo.der', '--attributes', 'CN=foo']), credstore)
        credstore.func_mode.assert_called_with(FUN_MODE_OFFLINE)
        credstore.keygen.assert_called_with(123, ANY, 'CN=foo')

    def test_imei(self, credstore):
        credstore.command_interface.get_imei.return_value = '123456789012345'
        args = parse_args(['fakedev', 'imei'])
        main(args, credstore)
        credstore.command_interface.get_imei.assert_called_once()

    def test_attestation_token(self, credstore):
        credstore.command_interface.get_attestation_token.return_value = '2dn3hQFQUDYxVDkxRPCAIhIbZAFifQNQGv86y_GmR2SiY0wmRsHGVFDT791_BPH8YOWFiyCHND1q.0oRDoQEmoQRBIfZYQGuXwJliinHc6xDPruiyjsaXyXZbZVpUuOhHG9YS8L05VuglCcJhMN4EUhWVGpaHgNnHHno6ahi-d5tOeZmAcNY'
        args = parse_args(['fakedev', 'attoken'])
        main(args, credstore)
        credstore.command_interface.get_attestation_token.assert_called_once()

    def test_at_command_error_exit_code(self, credstore):
        credstore.func_mode.side_effect = RuntimeError("Failed to set modem to offline mode.")
        with pytest.raises(RuntimeError) as e:
            main(parse_args(['fakedev', 'list']), credstore)
        assert e.type == RuntimeError

    def test_cannot_find_device(self):
        with patch("nrfcredstore.comms.__init__", return_value=Mock()) as mock_comms:
            mock_comms.side_effect = Exception("No device found")
            with pytest.raises(Exception) as e:
                run(['nrfcredstore', 'fakedev', 'list'])
        assert e.type == Exception
