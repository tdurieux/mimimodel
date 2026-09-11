#!/usr/bin/env python3
"""Download pinned parity assets without installing the reference wheel."""
import hashlib
import io
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

BASE = 'https://huggingface.co/Cactus-Compute/needle2/resolve/32e9e3a93b205f786929697446ae669cf0a84579/'
OUT = Path(__file__).resolve().parent.parent / '.optimization/assets'

def fetch(remote, digest):
    with urlopen(BASE + remote) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError('Hash mismatch: ' + remote)
    return data

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    assets = [
        ('needle2.cact', 'b43aabfcaf1a6db6acf488076eab71d823c08697c7af4521fc1d174b60ede5ba'),
        ('LICENSE', 'cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30'),
    ]
    for name, digest in assets:
        target = OUT / name
        if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            target.write_bytes(fetch(name, digest))
    target = OUT / 'libneedle.so'
    digest = '9fa5386d3e3a8ee17914fb23643bc5f5c906b683fa33561e79c5445dd78bc389'
    if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest() != digest:
        wheel = fetch('python/cactus_needle-2.0.4-py3-none-manylinux2014_x86_64.whl',
                      '13a84e6c73095fd175b11d46a30a984b62123d94421b769c107074aff7f65c2b')
        data = ZipFile(io.BytesIO(wheel)).read('needle/libneedle.so')
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError('Hash mismatch: libneedle.so')
        target.write_bytes(data)
    print('Pinned parity assets ready in', OUT)

if __name__ == '__main__':
    main()
