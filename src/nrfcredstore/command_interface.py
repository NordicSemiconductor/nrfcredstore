#!/usr/bin/env python3
#
# Copyright (c) 2025 Nordic Semiconductor ASA
#
# SPDX-License-Identifier: BSD-3-Clause

from enum import Enum
from abc import ABC, abstractmethod
import math
import time
from nrfcredstore.comms import Comms
import base64
import hashlib
import coloredlogs, logging
import re
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

IMEI_LEN = 15

class CredentialCommandInterface(ABC):
    def __init__(self, comms: Comms):
        """Initialize a Credentials Command Interface

        Args:
            comms: Comms object to use for serial communication.
        """
        self.comms = comms

    def write_raw(self, command: str):
        """Write a raw line directly to the serial interface."""
        self.comms.write_line(command)

    @abstractmethod
    def write_credential(self, sectag: int, cred_type: int, cred_text: str) -> bool:
        """Write a credential string to the command interface"""
        return False

    @abstractmethod
    def delete_credential(self, sectag: int, cred_type: int) -> bool:
        """Delete a credential using command interface"""
        return False

    @abstractmethod
    def check_credential_exists(self, sectag: int, cred_type: int, get_hash=True) -> tuple[bool, Optional[str]]:
        """Verify that a credential is installed. If check_hash is true, retrieve the SHA hash."""
        return False, None

    @abstractmethod
    def calculate_expected_hash(self, cred_text: str) -> str:
        """Returns the expected digest/hash for a given credential as a string"""
        return ""

    @abstractmethod
    def get_csr(self, sectag: int, attributes: str) -> Optional[str]:
        """Generate a private/public keypair and a corresponding Certificate Signing Request.

        Returns:
            CSR blob in modem specific body.cose format.
        """
        return

    @abstractmethod
    def go_offline(self) -> bool:
        """Tell the device to go offline so that credentials can be modified"""
        return False

    @abstractmethod
    def get_imei(self) -> Optional[str]:
        """Get device IMEI, if applicable"""
        return

    @abstractmethod
    def get_mfw_version(self) -> Optional[str]:
        """Get modem firmware version, if applicable"""
        return

class ATCommandInterface(CredentialCommandInterface):
    shell = False

    def _parse_sha(self, cmng_result_str: str):
        # Example AT%CMNG response:
        #   %CMNG: 123,0,"2C43952EE9E000FF2ACC4E2ED0897C0A72AD5FA72C3D934E81741CBD54F05BD1"
        # The first item in " is the SHA.
        try:
            return cmng_result_str.split('"')[1]
        except (ValueError, IndexError):
            logger.error(f'Could not parse credential hash: {cmng_result_str}')
            return None

    def set_shell_mode(self, shell: bool):
        self.shell = shell

    def detect_shell_mode(self):
        """Detect if the device is in shell mode or not."""
        for cmd, shell_mode in [("at AT+CGSN", True), ("AT+CGSN", False)]:
            for _ in range(3):
                self.write_raw(cmd)
                result, output = self.comms.expect_response("OK", "ERROR", "", suppress_errors=True, timeout=2)
                if result and len(re.findall("[0-9]{15}", output)) > 0:
                    self.set_shell_mode(shell_mode)
                    return
        raise TimeoutError("Failed to detect shell mode. Device does not respond to AT commands.")

    def enable_error_codes(self):
        """Enable error codes in the AT client"""
        if not self.at_command('AT+CMEE=1', wait_for_result=True):
            logger.error("Failed to enable error codes.")

    def at_command(self, at_command: str, wait_for_result=False, suppress_errors=False):
        """Write an AT command to the command interface. Optionally wait for OK"""

        self.comms.reset_input_buffer()

        if self.shell:
            # Transform line endings to match shell expectations
            at_command = at_command.replace("\r", "")
            at_command = at_command.replace("\n", "\\n")
            self.write_raw("at '" + at_command + "'")
        else:
            self.write_raw(at_command)

        if wait_for_result:
            result, _ = self.comms.expect_response("OK", "ERROR", suppress_errors=suppress_errors)
            return result
        else:
            return True

    def write_credential(self, sectag: int, cred_type: int, cred_text: str):
        return self.at_command(f'AT%CMNG=0,{sectag},{cred_type},"{cred_text}"', wait_for_result=True)

    def delete_credential(self, sectag: int, cred_type: int):
        return self.at_command(f'AT%CMNG=3,{sectag},{cred_type}', wait_for_result=True)

    def check_credential_exists(self, sectag: int, cred_type: int, get_hash=True):
        self.at_command(f'AT%CMNG=1,{sectag},{cred_type}')
        retval, output = self.comms.expect_response("OK", "ERROR", "%CMNG: ")
        # get the last line of the response
        output = [x.strip() for x in output.split("\n") if x.strip()][-1]
        if retval and output:
            if not get_hash:
                return True, None
            else:
                return True, self._parse_sha(output)

        return False, None

    def calculate_expected_hash(self, cred_text: str):
        # AT Command host returns hex of SHA256 hash of credential plaintext
        return hashlib.sha256(cred_text.encode('utf-8')).hexdigest().upper()

    def go_offline(self):
        return self.at_command('AT+CFUN=4', wait_for_result=True)

    def get_imei(self):
        self.at_command('AT+CGSN')
        retval, output = self.comms.expect_response("OK", "ERROR", "")
        # get the last line of the response
        output = [x.strip() for x in output.split("\n") if x.strip()][-1]
        if not retval:
            return None
        return output[:IMEI_LEN]

    def get_model_id(self):
        self.at_command('AT+CGMM')
        retval, output = self.comms.expect_response("OK", "ERROR", "")
        # get the last line of the response
        output = [x.strip() for x in output.split("\n") if x.strip()][-1]
        if not retval:
            return None
        return output

    def get_mfw_version(self):
        self.at_command('AT+CGMR')
        retval, output = self.comms.expect_response("OK", "ERROR", "")
        # get the last line of the response
        output = [x.strip() for x in output.split("\n") if x.strip()][-1]
        if not retval:
            return None
        return output

    def get_attestation_token(self):
        self.at_command('AT%ATTESTTOKEN')
        retval, output = self.comms.expect_response("OK", "ERROR", "%ATTESTTOKEN:")
        if not retval:
            return None
        attest_tok = output.split('"')[1]
        return attest_tok

    def get_csr(self, sectag=0, attributes=""):
        if attributes:
            self.at_command(f'AT%KEYGEN={sectag},2,0,"{attributes}"')
        else:
            self.at_command(f'AT%KEYGEN={sectag},2,0')

        retval, output = self.comms.expect_response("OK", "ERROR", "%KEYGEN:")

        if not retval:
            return None

        # Convert the encoded blob to an actual cert
        csr_blob = str(output).split('"')[1]
        logger.debug('CSR blob: {}'.format(csr_blob))

        # Format is "body.cose"
        # body is base64 encoded DER
        # cose is base64 encoded COSE header (CBOR)

        return csr_blob

TLS_CRED_TYPES = ["CA", "SERV", "PK"]
# This chunk size can be any multiple of 4, as long as it is small enough to fit within the
# Zephyr shell buffer.
TLS_CRED_CHUNK_SIZE = 48

class TLSCredShellInterface(CredentialCommandInterface):
    def write_credential(self, sectag, cred_type, cred_text):
        # Because the Zephyr shell does not support multi-line commands,
        # we must base-64 encode our PEM strings and install them as if they were binary.
        # Yes, this does mean we are base-64 encoding a string which is already mostly base-64.
        # We could alternatively strip the ===== BEGIN/END XXXX ===== header/footer, and then pass
        # everything else directly as a binary payload (using BIN mode instead of BINT, since
        # MBedTLS uses the NULL terminator to determine if the credential is raw DER, or is a
        # PEM string). But this will fail for multi-CA installs, such as CoAP.

        # text -> bytes -> base64 bytes -> base64 text
        encoded = base64.b64encode(cred_text.encode()).decode()

        # Clear credential buffer -- If it is already clear, there may not be text feedback
        self.write_raw("cred buf clear")

        # Write the encoded credential in chunks
        chunks = math.ceil(len(encoded)/TLS_CRED_CHUNK_SIZE)
        for c in range(chunks):
            chunk = encoded[c*TLS_CRED_CHUNK_SIZE:(c+1)*TLS_CRED_CHUNK_SIZE]
            self.write_raw(f"cred buf {chunk}")
            self.comms.expect_response(ok_pattern="Stored")

        # Store the buffered credential
        self.write_raw(f"cred add {sectag} {TLS_CRED_TYPES[cred_type]} DEFAULT bint")
        result, _ = self.comms.expect_response(ok_pattern="Added TLS credential")
        return result

    def delete_credential(self, sectag: int, cred_type: int):
        self.write_raw(f'cred del {sectag} {TLS_CRED_TYPES[cred_type]}')
        result, _ = self.comms.expect_response(ok_pattern="Deleted TLS credential", error_pattern="There is no TLS credential")
        return result

    def check_credential_exists(self, sectag: int, cred_type: int, get_hash=True):
        self.write_raw(f'cred list {sectag} {TLS_CRED_TYPES[cred_type]}')

        # This will capture the list dump for the credential if it exists.
        result, output = self.comms.expect_response(ok_pattern="1 credentials found.",
                                                    error_pattern="0 credentials found.",
                                                    store_str=f"{sectag},{TLS_CRED_TYPES[cred_type]}")

        if not result:
            return False, None

        if not get_hash:
            return True, None

        # Output is a comma separated list of positional items
        data = output.split(",")
        hash = data[2].strip()
        status_code = data[3].strip()

        if (status_code != "0"):
            logger.error(f"Error retrieving credential hash: {output.strip()}.")
            logger.error("Device might not support credential digests.")
            return True, None

        return True, hash

    def calculate_expected_hash(self, cred_text: str):
        # TLS Credentials shell returns base-64 of SHA256 hash of full credential, including NULL
        # termination.
        hash = hashlib.sha256(cred_text.encode('utf-8') + b'\x00')
        return base64.b64encode(hash.digest()).decode()

    def get_csr(self, sectag=0, attributes=""):
        raise RuntimeError("The TLS Credentials Shell does not support CSR generation")

    def go_offline(self):
        # TLS credentials shell has no concept of online/offline. Just no-op.
        return True

    def get_imei(self):
        raise RuntimeError("The TLS Credentials Shell does not support IMEI extraction")

    def get_mfw_version(self):
        raise RuntimeError("The TLS Credentials Shell does not support MFW version extraction")
