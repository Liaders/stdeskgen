"""Create a signing seed outside the repository; print only its public key."""
import argparse
import os
from pathlib import Path

from nacl.signing import SigningKey


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--private-file', type=Path, required=True)
    args = parser.parse_args()
    key = SigningKey.generate()
    descriptor = os.open(args.private_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        stream.write(key.encode().hex() + '\n')
    print(key.verify_key.encode().hex())
