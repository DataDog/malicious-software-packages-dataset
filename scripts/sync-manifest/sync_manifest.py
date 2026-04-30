"""
Provides the sync_manifest script's main routine, CLI, core logic.
"""

from argparse import ArgumentParser
from datetime import datetime
import json
import logging
import pathlib
import sys
from typing import Optional, TypeAlias

from packaging.version import parse as parse_version

from model import ECOSYSTEM, TriagedResultsModel

log = logging.getLogger(__name__)

LOG_LEVELS = list(
    map(
        logging.getLevelName,
        [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR]
    )
)
DEFAULT_LOG_LEVEL = logging.getLevelName(logging.WARNING)

Manifest: TypeAlias = dict[str, Optional[list[str]]]
"""
A malicious packages dataset manifest mapping package names to affected versions.
"""


def sync_manifest(input_manifest: Manifest, ecosystem: ECOSYSTEM, since: datetime) -> Manifest:
    """
    Synchronize an input manifest with the latest triage content.

    Args:
        `input_manifest`: The input `Manifest` to be synchronized.
        `ecosystem`: The package `ECOSYSTEM` to sync against.
        `since`: A `datetime` specifying the lookback cutoff for synchronization.

    Returns:
        A `Manifest` containing the content of `input_manifest` plus new and updated content
        derived from synchronizing with the backend.
    """
    output_manifest = {package: versions for package, versions in input_manifest.items()}

    triage_records = TriagedResultsModel.scan_latest_records(ecosystem, since)

    for triage_record in triage_records:
        _, package = triage_record.get_ecosystem_package()

        if triage_record.compromised_lib:
            if not triage_record.malicious_versions:
                log.warning(
                    f"Triage record for compromised lib {ecosystem}|{package} contains no affected versions"
                )

            try:
                triage_record.malicious_versions.sort(key=parse_version)
            except Exception as e:
                log.warning(f"Failed to semantically sort affected versions of package {package}: {e}")
                triage_record.malicious_versions.sort()

            output_manifest[package] = triage_record.malicious_versions

        else:
            output_manifest[package] = None

    return {package: output_manifest[package] for package in sorted(output_manifest)}


def cli() -> ArgumentParser:
    """
    Defines the `sync_manifest` script's command-line interface.

    Returns:
        An `ArgumentParser` for the script's command-line interface.
    """
    parser = ArgumentParser(
        prog="sync_manifest",
        description="A script for updating dataset manifests with the latest OSV advisory content",
    )

    parser.add_argument(
        "--ecosystem",
        type=ECOSYSTEM.from_str,
        required=True,
        help="The package ecosystem to synchronize against (options: npm, pypi)",
    )

    parser.add_argument(
        "--since",
        type=lambda t: datetime.strptime(t, "%Y-%m-%d %H:%M:%S"),
        required=True,
        help="The lookback cutoff time to synchronize against (%%Y-%%m-%%d %%H:%%M:%%S)",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        choices=LOG_LEVELS,
        default=DEFAULT_LOG_LEVEL,
        metavar="LEVEL",
        help="Desired logging level (default: %(default)s, options: %(choices)s)"
    )

    parser.add_argument(
        "--input-file",
        type=pathlib.Path,
        metavar="PATH",
        help="Input manifest file to use as a starting point when synchronizing",
    )

    parser.add_argument(
        "--output-file",
        type=pathlib.Path,
        metavar="PATH",
        help="Output file where the synchronized manifest should be written (default: stdout)",
    )

    return parser


def main() -> int:
    """
    The `sync_manifest` script's main routine.

    Returns:
        An `int` return code, 0 or 1.
    """
    try:
        args = cli().parse_args()
        logging.basicConfig(level=args.log_level)

        input_manifest = {}
        if args.input_file and args.input_file.is_file():
            with open(args.input_file) as f:
                input_manifest = json.load(f)

        output_manifest = sync_manifest(input_manifest, args.ecosystem, args.since)

        if args.output_file:
            with open(args.output_file, 'w') as f:
                json.dump(output_manifest, f, indent=4)
        else:
            print(json.dumps(output_manifest, indent=4))

        return 0

    except Exception as e:
        log.error(e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
