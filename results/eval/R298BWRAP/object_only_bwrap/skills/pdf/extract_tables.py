from __future__ import annotations
import argparse
import hashlib
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--input', required=True)
parser.add_argument('--output', required=True)
args = parser.parse_args()
data = Path(args.input).read_bytes()
Path(args.output).parent.mkdir(parents=True, exist_ok=True)
Path(args.output).write_text('xlsx:' + hashlib.sha256(data).hexdigest() + '\n')
