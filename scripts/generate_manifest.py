#!/usr/bin/env python

from argparse import ArgumentParser
import json
import os
import sys


def _parse_sample_filename(file: str) -> tuple[str, str]:  
    # `generate_manifest()` ensures `file` ends in `.zip`
    file, _ = os.path.splitext(file)
    components = file.split(':')
    if len(components) != 3:
        raise Exception(f"Malformed sample file name: {file + '.zip'}")
    _, package, version = components

    return package.replace(',', '/'), version


def generate_manifest(sample_dir: str) -> dict[str, list[str]]:
    manifest = {}

    for _, _, files in os.walk(sample_dir):
        for file in files:
            if not file.endswith(".zip"):
                continue
            package, version = _parse_sample_filename(file)
            if package not in manifest:
                manifest[package] = [version] if version else []
            elif version and version not in manifest[package]:
                manifest[package].append(version)
                manifest[package].sort()

    return manifest


def cli() -> ArgumentParser:
    parser = ArgumentParser(
        prog="generate_manifest",
        description="Generate JSON manifest files for the current set of samples"
    )

    parser.add_argument(
        "sample_dir",
        type=str,
        help="The path to the directory containing the sample ZIP files"
    )

    parser.add_argument(
        "--output-file",
        type=str,
        default=None,
        metavar="FILE",
        help="Output the manifest to the given file (stdout if not given)"
    )

    return parser


def main() -> int:
    try:
        args = cli().parse_args()

        manifest = generate_manifest(args.sample_dir)

        if args.output_file:
            with open(args.output_file, 'w') as f:
                f.write(json.dumps(manifest))
        else:
            print(json.dumps(manifest))

        return 0
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
