import io
import pytest

from unittest.mock import Mock, patch
from nrfcredstore.credstore import *
from nrfcredstore.exceptions import ATCommandError

# pylint: disable=no-self-use
class TestCredStore:
    """Test suite for CredStore

    Most of the tests depend on a fixture that defines the at_client response instead of defining
    the response in each test.
    """

    @pytest.fixture
    def cred_store(self):
        self.command_interface = Mock()
        return CredStore(self.command_interface)

    @pytest.fixture
    def list_all_resp(self, cred_store):
        cred_store.command_interface.comms.expect_response.return_value = (
            True,
            "\r\f".join([
                '%CMNG: 12345678, 0, "978C...02C4"',
                '%CMNG: 567890, 1, "C485...CF09"'
            ])
        )

    @pytest.fixture
    def list_all_resp_blank_lines(self, cred_store):
        cred_store.command_interface.comms.expect_response.return_value = (
            True,
            "\r\f".join([
                '',
                '%CMNG: 12345678, 0, "978C...02C4"',
                '%CMNG: 567890, 1, "C485...CF09"',
                ''
            ])
        )

    @pytest.fixture
    def ok_resp(self, cred_store):
        cred_store.command_interface.at_command.return_value = True

    @pytest.fixture
    def csr_resp(self, cred_store):
        # KEYGEN value is base64-encoded 'foo' and base64-encoded 'bar' joined by '.'
        cred_store.command_interface.get_csr.return_value = "Zm9v.YmFy"

    @pytest.fixture
    def at_error(self, cred_store):
        cred_store.command_interface.at_command.return_value = False

    @pytest.fixture
    def at_error_in_expect_response(self, cred_store):
        cred_store.command_interface.comms.expect_response.return_value = (False, "")

    def test_exposes_command_interface(self, cred_store):
        assert cred_store.command_interface is self.command_interface

    def test_func_mode_offline(self, cred_store):
        cred_store.func_mode(4)
        self.command_interface.at_command.assert_called_with('AT+CFUN=4', wait_for_result=True)

    def test_func_mode_min(self, cred_store):
        cred_store.func_mode(0)
        self.command_interface.at_command.assert_called_with('AT+CFUN=0', wait_for_result=True)

    def test_list_sends_cmng_command(self, cred_store, list_all_resp):
        cred_store.list()
        self.command_interface.at_command.assert_called_with('AT%CMNG=1', wait_for_result=False)
        self.command_interface.comms.expect_response.assert_called_with("OK", "ERROR", "%CMNG: ")

    def test_list_with_tag_part_of_cmng(self, cred_store, list_all_resp):
        cred_store.list(12345678)
        self.command_interface.at_command.assert_called_with('AT%CMNG=1,12345678', wait_for_result=False)

    def test_list_with_tag_and_type_part_of_cmng(self, cred_store, list_all_resp):
        cred_store.list(12345678, CredType(0))
        self.command_interface.at_command.assert_called_with('AT%CMNG=1,12345678,0', wait_for_result=False)

    def test_list_credentials_contains_tag(self, cred_store, list_all_resp):
        first = cred_store.list()[0]
        assert first.tag == 12345678

    def test_list_credentials_contains_type(self, cred_store, list_all_resp):
        first = cred_store.list()[0]
        assert first.type == CredType(0)

    def test_list_credentials_contains_sha(self, cred_store, list_all_resp):
        first = cred_store.list()[0]
        assert first.sha == '978C...02C4'

    def test_list_all_credentials_returns_multiple_credentials(self, cred_store, list_all_resp):
        result = cred_store.list()
        assert len(result) == 2
        assert result[0].sha == '978C...02C4'
        assert result[1].sha == 'C485...CF09'

    def test_list_all_with_blank_lines_in_resp(self, cred_store, list_all_resp_blank_lines):
        result = cred_store.list()
        assert len(result) == 2
        assert result[0].sha == '978C...02C4'
        assert result[1].sha == 'C485...CF09'

    def test_list_type_without_tag(self, cred_store):
        with pytest.raises(RuntimeError):
            cred_store.list(None, CredType(0))

    def test_list_fail(self, cred_store, at_error_in_expect_response):
        with pytest.raises(RuntimeError):
            cred_store.list()

    def test_delete_success(self, cred_store, ok_resp):
        cred_store.delete(567890, CredType(1))
        self.command_interface.at_command.assert_called_with('AT%CMNG=3,567890,1', wait_for_result=True)

    def test_delete_fail(self, cred_store, at_error):
        with pytest.raises(RuntimeError):
            cred_store.delete(123, CredType(1))

    def test_delete_any_type_fail(self, cred_store):
        with pytest.raises(ValueError):
            cred_store.delete(567890, CredType.ANY)

    def test_write_success(self, cred_store, ok_resp):
        cert_text = '''-----BEGIN CERTIFICATE-----
dGVzdA==
-----END CERTIFICATE-----'''
        fake_file = io.StringIO(cert_text)
        cred_store.write(567890, CredType.CLIENT_KEY, fake_file)
        self.command_interface.at_command.assert_called_with(f'AT%CMNG=0,567890,2,"{cert_text}"', wait_for_result=True)

    def test_write_fail(self, cred_store, at_error):
        with pytest.raises(RuntimeError):
            cred_store.write(567890, CredType.CLIENT_KEY, io.StringIO())

    def test_write_any_type_fail(self, cred_store):
        with pytest.raises(ValueError):
            cred_store.write(567890, CredType.ANY, io.StringIO())

    def test_generate_sends_keygen_cmd(self, cred_store, csr_resp):
        fake_binary_file = Mock()
        cred_store.keygen(12345678, fake_binary_file)
        self.command_interface.get_csr.assert_called_with(sectag=12345678, attributes='')

    def test_generate_with_attributes(self, cred_store, csr_resp):
        cred_store.keygen(12345678, Mock(), 'O=Nordic Semiconductor,L=Trondheim,C=no,CN=mydevice')
        self.command_interface.get_csr.assert_called_with(
            sectag=12345678,
            attributes="O=Nordic Semiconductor,L=Trondheim,C=no,CN=mydevice"
        )

    def test_generate_writes_csr_to_stream(self, cred_store, csr_resp):
        fake_binary_file = Mock()
        cred_store.keygen(12345678, fake_binary_file)
        fake_binary_file.write.assert_called_with(b'foo')

    def test_generate_fail(self, cred_store):
        with patch.object(cred_store.command_interface, 'get_csr', return_value=None):
            with pytest.raises(RuntimeError):
                cred_store.keygen(12345678, Mock())
