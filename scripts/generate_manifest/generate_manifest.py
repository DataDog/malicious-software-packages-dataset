#!/usr/bin/env python3

from argparse import ArgumentParser
import json
import os
import sys

from packaging.version import parse as version_parse


def generate_manifest(directory: str) -> dict[str, list[str]]:
    def restore_original_name(package_name: str) -> str:
        return package_name[0] + package_name[1:].replace('@', '/')

    def restore_original_version(package_version: str) -> str:
        return package_version.replace('@', '/')

    manifest = {}

    package_dirs = filter(lambda d: d.is_dir(), os.scandir(directory))
    for package_dir in package_dirs:
        package_name = restore_original_name(package_dir.name)
        manifest[package_name] = []

        version_dirs = filter(lambda d: d.is_dir(), os.scandir(package_dir))
        for version_dir in version_dirs:
            package_version = restore_original_version(version_dir.name)
            manifest[package_name].append(package_version)
            manifest[package_name].sort(key=version_parse)

    return {package: manifest[package] for package in sorted(manifest)}


def cli() -> ArgumentParser:
    parser = ArgumentParser(
        prog="generate_manifest",
        description="Generate a JSON manifest file for an ecosystem's malicious package samples"
    )

    parser.add_argument(
        "directory",
        type=str,
        metavar="PATH",
        help="The path to the top-level directory containing the samples"
    )

    parser.add_argument(
        "--output-file",
        type=str,
        default=None,
        metavar="FILE",
        help="A file where the manifest should be written (stdout otherwise)"
    )

    return parser


def main() -> int:
    try:
        args = cli().parse_args()

        manifest = generate_manifest(args.directory)
        manifest_json = json.dumps(manifest, indent=4)

        if args.output_file:
            with open(args.output_file, 'w') as f:
                f.write(manifest_json)
        else:
            print(manifest_json)

        return 0
    except Exception as e:
        sys.stderr.write(f"Error: {e}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
