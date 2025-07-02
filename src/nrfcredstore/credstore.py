import base64
import io
from enum import Enum
from typing import List

FUN_MODE_OFFLINE = 4

class CredType(Enum):
    ANY = -1
    ROOT_CA_CERT = 0
    CLIENT_CERT = 1
    CLIENT_KEY = 2
    PSK = 3
    PSK_ID = 4
    PUB_KEY = 5
    DEV_ID_PUB_KEY = 6
    RESERVED = 7
    ENDORSEMENT_KEY = 8
    OWNERSHIP_KEY = 9
    NORDIC_ID_ROOT_CA = 10
    NORDIC_PUB_KEY = 11

class Credential:
    def __init__(self, tag: int, type: int, sha: str):
        self.tag = tag
        self.type = CredType(type)
        self.sha = sha

class CredStore:
    def __init__(self, command_interface):
        self.command_interface = command_interface

    def func_mode(self, mode):
        """Set modem functioning mode

        See AT Command Reference Guide for valid modes.
        """

        return self.command_interface.at_command(f'AT+CFUN={mode}', wait_for_result=True)

    def list(self, tag = None, type: CredType = CredType.ANY) -> List[Credential]:
        """List stored credentials

        tag and type is optional, but specifying type requires tag.
        """

        cmd = 'AT%CMNG=1'

        if tag is None and type != CredType.ANY:
            raise RuntimeError('Cannot list with type without a tag')

        # Optional secure tag
        if tag is not None:
            cmd = f'{cmd},{tag}'

            # Optional key type
            if type != CredType.ANY:
                cmd = f'{cmd},{CredType(type).value}'

        self.command_interface.at_command(cmd, wait_for_result=False)
        result, response = self.command_interface.comms.expect_response("OK", "ERROR", "%CMNG: ")
        if not result:
            raise RuntimeError("Failed to list credentials")
        response_lines = response.splitlines()
        response_lines = [line.strip() for line in response_lines if line.strip()]

        columns = map(lambda line: line.replace('%CMNG: ', '').replace('"', '').split(','), response_lines)
        cred_map = map(lambda columns:
                Credential(int(columns[0]), int(columns[1]), columns[2].strip()),
                columns
            )

        return list(cred_map)

    def write(self, tag: int, type: CredType, file: io.TextIOBase):
        """Write a credential file to the modem

        type can not be ANY.
        """

        if type == CredType.ANY:
            raise ValueError
        cert = file.read().rstrip()
        if not self.command_interface.at_command(f'AT%CMNG=0,{tag},{type.value},"{cert}"', wait_for_result=True):
            raise RuntimeError("Failed to write credential")

    def delete(self, tag: int, type: CredType):
        """Delete a credential from the modem

        type can not be ANY.
        """

        if type == CredType.ANY:
            raise ValueError
        if not self.command_interface.at_command(f'AT%CMNG=3,{tag},{type.value}', wait_for_result=True):
            raise RuntimeError("Failed to delete credential")

    def keygen(self, tag: int, file: io.BufferedIOBase, attributes: str = ''):
        """Generate a new private key and return a certificate signing request in DER format"""

        keygen_output = self.command_interface.get_csr(sectag=tag, attributes=attributes)

        if not keygen_output:
            raise RuntimeError("Failed to generate key")

        csr_der_b64 = keygen_output.split('.')[0]
        csr_der_bytes = base64.urlsafe_b64decode(csr_der_b64 + '===')

        file.write(csr_der_bytes)
        file.close()
