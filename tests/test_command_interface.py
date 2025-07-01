from unittest.mock import patch, Mock
from collections import namedtuple
import pytest

from nrfcredstore.command_interface import CredentialCommandInterface, ATCommandInterface, TLSCredShellInterface
from nrfcredstore.credstore import CredType

@pytest.fixture
def comms():
    """Mock comms object"""
    comms = Mock()
    return comms

@pytest.fixture
def at_command_interface(comms):
    """Mock command interface"""
    interface = ATCommandInterface(comms)
    return interface

@pytest.fixture
def tls_cred_shell_interface(comms):
    """Mock TLSCredShellInterface"""
    interface = TLSCredShellInterface(comms)
    return interface

def test_write_raw_at(at_command_interface):
    """Test writing raw AT commands"""
    at_command_interface.comms.write_line = Mock()
    at_command_interface.write_raw('AT+TEST=1')
    at_command_interface.comms.write_line.assert_called_once_with('AT+TEST=1')

def test_write_raw_tls(tls_cred_shell_interface):
    """Test writing raw TLS commands"""
    tls_cred_shell_interface.comms.write_line = Mock()
    tls_cred_shell_interface.write_raw('AT+TEST=1')
    tls_cred_shell_interface.comms.write_line.assert_called_once_with('AT+TEST=1')

def test_write_credential_at(at_command_interface):
    """Test writing a credential using ATCommandInterface"""
    at_command_interface.comms.write_line = Mock()
    at_command_interface.comms.expect_response.return_value = (True, "")
    at_command_interface.write_credential(sectag=42, cred_type=CredType.CLIENT_CERT.value, cred_text='test_value')
    at_command_interface.comms.write_line.assert_called_once_with('AT%CMNG=0,42,1,"test_value"')

def test_delete_credential_at(at_command_interface):
    """Test deleting a credential using ATCommandInterface"""
    at_command_interface.comms.write_line = Mock()
    at_command_interface.comms.expect_response.return_value = (True, "")
    at_command_interface.delete_credential(sectag=42, cred_type=CredType.CLIENT_CERT.value)
    at_command_interface.comms.write_line.assert_called_once_with('AT%CMNG=3,42,1')

def test_check_credential_exists_at(at_command_interface):
    """Test checking if a credential exists using ATCommandInterface"""
    at_command_interface.comms.write_line = Mock()
    at_command_interface.comms.expect_response.return_value = (True, '%CMNG: 42,1,"8CEA57609B0F95C0D0F80383A7A21ECD1C6E102FDCC3CDCEB1948B0EA828601D"')
    exists, sha = at_command_interface.check_credential_exists(sectag=42, cred_type=CredType.CLIENT_CERT.value)
    assert exists is True
    assert sha == '8CEA57609B0F95C0D0F80383A7A21ECD1C6E102FDCC3CDCEB1948B0EA828601D'

def test_get_csr_at(at_command_interface):
    """Test getting a CSR using ATCommandInterface"""
    at_command_interface.comms.write_line = Mock()
    at_command_interface.comms.expect_response.return_value = (True, '%KEYGEN: "foo.bar"')
    csr = at_command_interface.get_csr(sectag=42, attributes='O=Test,CN=Device')
    assert csr == 'foo.bar'
    at_command_interface.comms.write_line.assert_called_once_with('AT%KEYGEN=42,2,0,"O=Test,CN=Device"')

def test_get_csr_no_attributes(at_command_interface):
    """Test getting a CSR without attributes using ATCommandInterface"""
    at_command_interface.comms.write_line = Mock()
    at_command_interface.comms.expect_response.return_value = (True, '%KEYGEN: "foo.bar"')
    csr = at_command_interface.get_csr(sectag=42)
    assert csr == 'foo.bar'
    at_command_interface.comms.write_line.assert_called_once_with('AT%KEYGEN=42,2,0')

def test_get_imei(at_command_interface):
    """Test getting IMEI using ATCommandInterface"""
    at_command_interface.comms.write_line = Mock()
    at_command_interface.comms.expect_response.return_value = (True, '123456789012345')
    imei = at_command_interface.get_imei()
    assert imei == '123456789012345'
    at_command_interface.comms.write_line.assert_called_once_with('AT+CGSN')

def test_go_offline(at_command_interface):
    """Test going offline using ATCommandInterface"""
    at_command_interface.comms.write_line = Mock()
    at_command_interface.comms.expect_response.return_value = (True, '')
    at_command_interface.go_offline()
    at_command_interface.comms.write_line.assert_called_once_with('AT+CFUN=4')

def test_get_model_id(at_command_interface):
    """Test getting model ID using ATCommandInterface"""
    at_command_interface.comms.write_line = Mock()
    at_command_interface.comms.expect_response.return_value = (True, 'nRF9151-LACA')
    model_id = at_command_interface.get_model_id()
    assert model_id == 'nRF9151-LACA'
    at_command_interface.comms.write_line.assert_called_once_with('AT+CGMM')

def test_get_mfw_version(at_command_interface):
    """Test getting MFW version using ATCommandInterface"""
    at_command_interface.comms.write_line = Mock()
    at_command_interface.comms.expect_response.return_value = (True, 'mfw_nrf91x1_2.0.2')
    mfw_version = at_command_interface.get_mfw_version()
    assert mfw_version == 'mfw_nrf91x1_2.0.2'
    at_command_interface.comms.write_line.assert_called_once_with('AT+CGMR')

def test_get_attestation_token(at_command_interface):
    """Test getting attestation token using ATCommandInterface"""
    at_command_interface.comms.write_line = Mock()
    at_command_interface.comms.expect_response.return_value = (True, '%ATTESTTOKEN: "foo.bar"')
    attestation_token = at_command_interface.get_attestation_token()
    assert attestation_token == 'foo.bar'
    at_command_interface.comms.write_line.assert_called_once_with('AT%ATTESTTOKEN')

def test_enable_error_codes(at_command_interface):
    """Test enabling error codes using ATCommandInterface"""
    at_command_interface.comms.write_line = Mock()
    at_command_interface.comms.expect_response.return_value = (True, '')
    at_command_interface.enable_error_codes()
    at_command_interface.comms.write_line.assert_called_once_with('AT+CMEE=1')

class MockCommsAT:
    """Mock comms for ATCommandInterface"""
    def write_line(self, line):
        self.last_written = line

    def expect_response(self, ok_str=None, error_str=None, store_str=None, timeout=15, suppress_errors=False):
        if self.last_written == 'AT+CGSN':
            return True, '123456789012345'
        else:
            return False, ''

def test_detect_shell_mode_at(at_command_interface):
    """Test detecting shell mode using ATCommandInterface (AT Host)"""
    at_command_interface.comms = MockCommsAT()
    at_command_interface.detect_shell_mode()
    assert at_command_interface.shell == False

class MockCommsATShell:
    """Mock comms for TLSCredShellInterface"""
    def write_line(self, line):
        self.last_written = line

    def expect_response(self, ok_str=None, error_str=None, store_str=None, timeout=15, suppress_errors=False):
        if self.last_written == 'at AT+CGSN':
            return True, '123456789012345'
        else:
            return False, ''

def test_detect_shell_mode_shell(at_command_interface):
    """Test detecting shell mode using ATCommandInterface (AT Shell)"""
    at_command_interface.comms = MockCommsATShell()
    at_command_interface.detect_shell_mode()
    assert at_command_interface.shell == True
