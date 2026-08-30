import argparse
import gzip
import hashlib
import json
import os
import tempfile
from pathlib import Path


def safe_path(root, relative):
    supplied = Path(relative)
    if supplied.is_absolute() or '..' in supplied.parts or '.git' in supplied.parts or not supplied.parts:
        raise ValueError('Unsafe manifest path: ' + str(relative))
    destination = root / supplied
    resolved = destination.resolve()
    if not resolved.is_relative_to(root) or '.git' in resolved.relative_to(root).parts:
        raise ValueError('Manifest path escapes the repository: ' + str(relative))
    return destination


def file_hash(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def unpack(root, record, output=None):
    with tempfile.TemporaryFile() as compressed:
        for part in record['parts']:
            path = safe_path(root, part['path'])
            digest = hashlib.sha256()
            size = 0
            with path.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(chunk)
                    size += len(chunk)
                    compressed.write(chunk)
            if size != part['bytes'] or digest.hexdigest() != part['sha256']:
                raise ValueError('Corrupt packaged part: ' + part['path'])
        compressed.seek(0)
        digest = hashlib.sha256()
        size = 0
        with gzip.GzipFile(fileobj=compressed, mode='rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                size += len(chunk)
                if size > record['bytes']:
                    raise ValueError('Payload exceeds declared size: ' + record['path'])
                digest.update(chunk)
                if output is not None:
                    output.write(chunk)
        if size != record['bytes'] or digest.hexdigest() != record['sha256']:
            raise ValueError('Restored payload checksum mismatch: ' + record['path'])


def restore(root, record):
    destination = safe_path(root, record['path'])
    if destination.is_symlink():
        raise ValueError('Refusing to replace a symlink: ' + record['path'])
    if destination.exists():
        if destination.is_file() and file_hash(destination) == record['sha256']:
            return 'already_present'
        raise ValueError('Refusing to overwrite a different existing file: ' + record['path'])
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix='.restore-', delete=False) as output:
            temporary_path = Path(output.name)
            unpack(root, record, output)
        temporary_path.chmod(record.get('mode', 0o644) & 0o777)
        os.link(temporary_path, destination)
        return 'restored'
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description='Verify or restore losslessly packaged tasks_v3 data.')
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--only', default='', help='Select original paths with this prefix.')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--list', action='store_true')
    mode.add_argument('--verify', action='store_true')
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    manifest = json.loads((root / 'PUBLICATION_MANIFEST_V4.json').read_text())
    records = [record for record in manifest['files'] if record['storage'] == 'gzip_chunks'
               and record['path'].startswith(arguments.only)]
    if not records:
        raise ValueError('No packaged artifacts match the requested selection.')
    if arguments.list:
        print(json.dumps([{'path': record['path'], 'bytes': record['bytes']} for record in records], indent=2))
        return
    verified = set()
    for record in records:
        if arguments.verify:
            identity = (record['sha256'], record['bytes'], tuple(part['sha256'] for part in record['parts']))
            if identity not in verified:
                unpack(root, record)
                verified.add(identity)
            result = 'verified'
        else:
            result = restore(root, record)
        print(json.dumps({'path': record['path'], 'result': result}), flush=True)


if __name__ == '__main__':
    main()
