import argparse
import sys
import serial

from nrfcredstore.exceptions import ATCommandError, NoATClientException
from nrfcredstore.at_client import ATClient
from nrfcredstore.credstore import CredStore, CredType

FUN_MODE_OFFLINE = 4
KEY_TYPES_OR_ANY = list(map(lambda type: type.name, CredType))
KEY_TYPES = KEY_TYPES_OR_ANY.copy()
KEY_TYPES.remove('ANY')

ERR_UNKNOWN = 1
ERR_NO_AT_CLIENT = 10
ERR_AT_COMMAND = 11
ERR_TIMEOUT = 12
ERR_SERIAL = 13

def parse_args(in_args):
    parser = argparse.ArgumentParser(description='Manage certificates stored in a cellular modem.')
    parser.add_argument('dev', help='Serial device used to communicate with the modem.')
    parser.add_argument('--baudrate', type=int, default=115200, help='Serial baudrate')
    parser.add_argument('--timeout', type=int, default=3,
        help='Serial communication timeout in seconds')

    subparsers = parser.add_subparsers(
        title='subcommands', dest='subcommand', help='Certificate related commands'
    )

    # add list command
    list_parser = subparsers.add_parser('list', help='List all keys stored in the modem')
    list_parser.add_argument('--tag', type=int,
        help='Only list keys in secure tag')
    list_parser.add_argument('--type', choices=KEY_TYPES_OR_ANY, default='ANY',
        help='Only list key with given type')

    # add write command
    write_parser = subparsers.add_parser('write', help='Write key/cert to a secure tag')
    write_parser.add_argument('tag', type=int,
        help='Secure tag to write key to')
    write_parser.add_argument('type',
        choices=['ROOT_CA_CERT','CLIENT_CERT','CLIENT_KEY', 'PSK'],
        help='Key type to write')
    write_parser.add_argument('file',
        type=argparse.FileType('r', encoding='UTF-8'),
        help='PEM file to read from')

    # add delete command
    delete_parser = subparsers.add_parser('delete', help='Delete value from a secure tag')
    delete_parser.add_argument('tag', type=int,
        help='Secure tag to delete key')
    delete_parser.add_argument('type', choices=KEY_TYPES,
        help='Key type to delete')

    deleteall_parser = subparsers.add_parser('deleteall', help='Delete all keys in a secure tag')

    # add generate command and args
    generate_parser = subparsers.add_parser('generate', help='Generate private key')
    generate_parser.add_argument('tag', type=int,
        help='Secure tag to store generated key')
    generate_parser.add_argument('file', type=argparse.FileType('wb'),
        help='File to store CSR in DER format')
    generate_parser.add_argument('--attributes', type=str, default='',
        help='Comma-separated list of attribute ID and value pairs for the CSR response')

    return parser.parse_args(in_args)

def exec_cmd(args, credstore):
    if args.subcommand:
        credstore.func_mode(FUN_MODE_OFFLINE)

    if args.subcommand == 'list':
        ct = CredType[args.type]
        if ct != CredType.ANY and args.tag is None:
            raise RuntimeError("Cannot use --type without a --tag.")
        creds = credstore.list(args.tag, ct)
        table_format = "{:<12} {:<18} {:<64}"
        print(table_format.format('Secure tag','Key type','SHA'))
        for c in creds:
            columns = [
                c.tag,
                c.type.name,
                c.sha
            ]
            print(table_format.format(*columns))
    elif args.subcommand=='write':
        ct = CredType[args.type]
        credstore.write(args.tag, ct, args.file)
    elif args.subcommand=='delete':
        ct = CredType[args.type]
        if credstore.delete(args.tag, ct):
            print(f'{ct.name} in secure tag {args.tag} deleted')
    elif args.subcommand=='deleteall':
        creds = credstore.list(None, CredType.ANY)
        if not creds:
            raise RuntimeError(f'No keys found in secure tag {args.tag}')
        for c in creds:
            if c.tag in [4294967292, 4294967293, 4294967294]:
                continue  # Skip reserved tags
            credstore.delete(c.tag, c.type)
        print(f'All credentials deleted.')
    elif args.subcommand=='generate':
        credstore.keygen(args.tag, args.file, args.attributes)
        print(f'New private key generated in secure tag {args.tag}')
        print(f'Wrote CSR in DER format to {args.file.name}')

def exit_with_msg(exitcode, msg):
    print(msg)
    exit(exitcode)

def main(in_args, credstore):
    at_client = credstore.at_client
    try:
        args = parse_args(in_args)
        if args.dev:
            at_client.connect(args.dev, args.baudrate, args.timeout)
            at_client.verify()
            at_client.enable_error_codes()
        exec_cmd(args, credstore)
    except NoATClientException:
        exit_with_msg(ERR_NO_AT_CLIENT, 'The device does not respond to AT commands. Please flash at_client sample.')
    except ATCommandError as err:
        exit_with_msg(ERR_AT_COMMAND, err)
    except TimeoutError as err:
        exit_with_msg(ERR_TIMEOUT, 'The device did not respond in time. Please try again.')
    except serial.SerialException as err:
        exit_with_msg(ERR_SERIAL, f'Serial error: {err}')
    except Exception as err:
        exit_with_msg(ERR_UNKNOWN, f'Unhandled Error: {err}')

def run():
    main(sys.argv[1:], CredStore(ATClient(serial.Serial())))
