from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from decimal import Context
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import threading
import time
from typing import Optional

import boto3
import boto3.dynamodb.types

boto3.dynamodb.types.DYNAMODB_CONTEXT = Context(prec=100)


NPM_SECURITY_VERSION = "0.0.1-security"

# Number of packages to download (and zip) concurrently. Each download spawns an
# `aws s3 sync` subprocess, so the work is I/O-bound and benefits from parallelism.
# Overridable via the SYNC_DOWNLOAD_CONCURRENCY environment variable.
DOWNLOAD_CONCURRENCY = int(os.environ.get("SYNC_DOWNLOAD_CONCURRENCY", "16"))

# Number of DynamoDB parallel-scan segments. A value <= 1 falls back to a single sequential
# scan. Overridable via the SYNC_SCAN_SEGMENTS environment variable.
SCAN_TOTAL_SEGMENTS = int(os.environ.get("SYNC_SCAN_SEGMENTS", "16"))

# Samples whose generated archive exceeds this size (in MB) are excluded from the dataset.
# GitHub hard-rejects pushes containing blobs larger than 100 MB, so a single oversized
# sample would fail the entire PR push. Overridable via the SYNC_MAX_SAMPLE_MB environment
# variable or the --max-sample-mb flag.
MAX_SAMPLE_MB = int(os.environ.get("SYNC_MAX_SAMPLE_MB", "100"))


class SampleTooLarge(Exception):
  """Raised when a generated sample archive exceeds the configured size cap."""


# Tombstone file, committed to the repository alongside the samples, listing samples
# excluded because their archive exceeded the size cap. Persisting the exclusions means
# later runs skip them immediately instead of re-downloading them every day. Its content
# never changes for a given sample (the S3 payload is immutable), so entries accumulate.
OVERSIZED_SAMPLES_FILE = "oversized-samples.txt"

_oversized_lock = threading.Lock()


def load_oversized_samples() -> set:
  """Return the set of sample paths recorded in the oversized-samples tombstone."""
  entries = set()
  path = Path(OVERSIZED_SAMPLES_FILE)
  if path.is_file():
    for line in path.read_text().splitlines():
      line = line.strip()
      if line and not line.startswith("#"):
        entries.add(line.split("\t")[0])
  return entries


def record_oversized_sample(sample_path, sample_size) -> None:
  """Append a sample to the oversized-samples tombstone (thread-safe)."""
  with _oversized_lock:
    path = Path(OVERSIZED_SAMPLES_FILE)
    if not path.is_file():
      path.write_text(
        "# Samples excluded from the GitHub repository because their archive exceeded the\n"
        "# size cap (MAX_SAMPLE_MB). They remain available in S3 and listed in the manifest.\n"
        "# Format: <sample path>\t<archive size in bytes>\n"
      )
    with path.open("a") as f:
      f.write(f"{sample_path.as_posix()}\t{sample_size}\n")


def parse_arguments():
    parser = ArgumentParser(description='Download malicious samples from S3')
    parser.add_argument('--ecosystem', help='npm or pypi', default='pypi')
    parser.add_argument('--since', help='Date in YYYY-MM-DD format', required=True)
    parser.add_argument('--destination', help='Where to store the resulting ZIP', required=True)
    parser.add_argument('--s3-bucket', help='S3 bucket containing the samples')
    parser.add_argument('--scan-table', help='DynamoDB table containing the scan results')
    parser.add_argument('--triage-table', help='DynamoDB table containing the triage results')
    parser.add_argument('--max-sample-mb', type=int, default=MAX_SAMPLE_MB,
                        help='Skip samples whose archive exceeds this size, in MB '
                             f'(default: {MAX_SAMPLE_MB}, the GitHub blob size limit)')
    args = parser.parse_args()
    return args


def query_and_download_items(ecosystem, cutoff_date, dest, scan_table, triage_table, s3_bucket, max_sample_bytes):
  os.chdir(dest)

  # Samples excluded by previous runs because they were oversized. Loaded from the
  # tombstone committed to the repository (relative to --destination, i.e. samples/<eco>).
  oversized_samples = load_oversized_samples()
  skipped_tombstoned = 0

  since = datetime.strptime(cutoff_date + " 00:00:00", '%Y-%m-%d %H:%M:%S')
  since_timestamp = round(time.mktime(since.timetuple()))

  scan_query = "ecosystem = :ecosystem AND triage_state = :state AND scan_timestamp >= :cutoff_timestamp"
  scan_values = {
    ":ecosystem": ecosystem,
    ":state": "malicious",
    ":cutoff_timestamp": since_timestamp
  }
  scan_results = perform_table_scan(scan_table, scan_query, scan_values)

  # Fetch every compromised-lib package once, instead of querying the triage table per
  # package (which adds a DynamoDB round-trip for each of potentially thousands of items).
  compromised_libs = fetch_compromised_libs(triage_table, ecosystem)

  print(f"Syncing samples of {len(scan_results)} packages")

  pending = []
  seen_sample_paths = set()
  for item in scan_results:
    package_name = item["package_name"].removeprefix("npm|")
    package_version = item["package_version"]
    if package_name != item["package_name"] and package_version.startswith(NPM_SECURITY_VERSION):
      continue

    sample_kind = "compromised_lib" if f"{package_name}|{ecosystem}" in compromised_libs else "malicious_intent"

    # `@` is used in place of `/` in forming directory names because it is unambiguously
    # as a replacement character (used for manifest computation) and is already used in
    # npm package names, thus safe to use
    package_name_directory = package_name.replace('/', '@')
    package_version_directory = package_version.replace('/', '@')
    sample_directory = Path(sample_kind) / package_name_directory / package_version_directory

    scan_datetime = datetime.strptime(item['scan_datetime'], '%Y-%m-%d %H:%M:%S.%f').strftime('%Y-%m-%d')

    package_name_file = package_name.replace('/', '_')
    package_version_file = package_version.replace('/', '_')
    sample_file = f"{scan_datetime}-{package_name_file}-v{package_version_file}.zip"

    sample_path = sample_directory / sample_file
    if sample_path.is_file():
      continue

    # Skip samples excluded by a previous run: their S3 content is immutable, so
    # re-downloading and re-zipping them would be wasted work.
    if sample_path.as_posix() in oversized_samples:
      skipped_tombstoned += 1
      continue

    # Guard against duplicate scan rows for the same sample, so two threads never race
    # to write the same archive.
    if sample_path in seen_sample_paths:
      continue
    seen_sample_paths.add(sample_path)

    s3_url = f"s3://{s3_bucket}/{ecosystem}/{scan_datetime}/{package_name}/{package_version}/"
    pending.append((package_name, package_version, sample_directory, sample_path, s3_url))

  failures = 0
  oversized = 0
  with ThreadPoolExecutor(max_workers=DOWNLOAD_CONCURRENCY) as executor:
    futures = {
      executor.submit(download_and_zip_sample, dest, *work, max_sample_bytes): work
      for work in pending
    }
    for future in as_completed(futures):
      package_name, package_version, *_ = futures[future]
      try:
        future.result()
      except SampleTooLarge as e:
        # Samples above the size cap are deliberately excluded from the GitHub repository
        # (GitHub rejects blobs larger than 100 MB, which would fail the entire PR push).
        # They still exist in S3 and in the manifest as usual — this is not a failure.
        oversized += 1
        print(f"Not syncing sample to GitHub (oversized, kept in S3/manifest): {e}")
      except Exception as e:
        # A single package failing to download (e.g. a transient S3 error or a missing
        # prefix) should not abort the whole sync. Log it and keep going, but report the
        # failure count to the caller so CI can surface it.
        failures += 1
        print(f"Skipping {package_name}-v{package_version}: {e}")

  if oversized:
    print(f"{oversized} sample(s) above {max_sample_bytes // (1024 * 1024)} MB were not synced to GitHub "
          f"(still available in S3 and listed in the manifest)")
  if skipped_tombstoned:
    print(f"Skipped {skipped_tombstoned} sample(s) excluded as oversized by a previous run")
  if failures:
    print(f"Finished with {failures} package(s) that could not be synced")

  return failures


def download_and_zip_sample(dest, package_name, package_version, sample_directory, sample_path, s3_url, max_sample_bytes):
  print(f"Downloading files for {package_name}-v{package_version}")
  with TemporaryDirectory() as tempdir:
    try:
      subprocess.run(['aws', 's3', 'sync', s3_url, tempdir], check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
      raise RuntimeError(f"unable to download {s3_url}: {e.stderr.decode(errors='replace')}") from e

    Path(sample_directory).mkdir(parents=True, exist_ok=True)

    # We spawn zip because no way to encrypt with the standard ZipFile library...
    command = ["zip", "--encrypt", "-r", "-P", "infected", str(sample_path), tempdir]
    try:
      subprocess.run(command, check=True, capture_output=True, cwd=dest)
    except subprocess.CalledProcessError as e:
      raise RuntimeError(f"unable to zip {sample_path}: {e.stderr.decode(errors='replace')}") from e

    sample_size = sample_path.stat().st_size
    if sample_size > max_sample_bytes:
      sample_path.unlink()
      record_oversized_sample(sample_path, sample_size)
      raise SampleTooLarge(
        f"{sample_path} is {sample_size / (1024 * 1024):.1f} MB "
        f"(cap: {max_sample_bytes // (1024 * 1024)} MB)"
      )

    print(f"Wrote new ZIP file {sample_path}")


def fetch_compromised_libs(triage_table: str, ecosystem: str) -> set:
  """Return the set of `package|ecosystem` keys flagged as compromised libraries.

  This is a single scan of the triage table, replacing a per-package query that
  otherwise runs once for every malicious package in the scan results.
  """
  results = perform_table_scan(
    triage_table,
    "compromised_lib = :true",
    {":true": True},
  )
  return {item["package"] for item in results if item["package"].endswith(f"|{ecosystem}")}


def perform_table_scan(table_name: str, filter_expr: str, expr_attr_values: Optional[dict]) -> list:
  scan_args = {
    "FilterExpression": filter_expr,
  }
  if expr_attr_values:
      scan_args["ExpressionAttributeValues"] = expr_attr_values

  if SCAN_TOTAL_SEGMENTS <= 1:
    table = boto3.resource("dynamodb").Table(table_name)
    return _perform_table_operation(table.scan, scan_args)

  # DynamoDB parallel scan: split the table into independent segments scanned concurrently.
  # A full-table scan with a FilterExpression reads every item server-side, so without this it
  # is the slowest part of the sync. boto3 resources are not thread-safe, so each worker builds
  # its own session.
  results = []
  with ThreadPoolExecutor(max_workers=SCAN_TOTAL_SEGMENTS) as executor:
    futures = [
      executor.submit(_scan_segment, table_name, scan_args, segment, SCAN_TOTAL_SEGMENTS)
      for segment in range(SCAN_TOTAL_SEGMENTS)
    ]
    for future in futures:
      results.extend(future.result())
  return results


def _scan_segment(table_name: str, scan_args: dict, segment: int, total_segments: int) -> list:
  table = boto3.Session().resource("dynamodb").Table(table_name)
  segment_args = {**scan_args, "Segment": segment, "TotalSegments": total_segments}
  return _perform_table_operation(table.scan, segment_args)


def _perform_table_operation(operation, args: dict) -> list:
  results = []
  response, first_query = {}, True

  while first_query or "LastEvaluatedKey" in response:
    query_args = {k: v for k, v in args.items()}

    if first_query:
      first_query = False
    else:
      query_args["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    response = operation(**query_args)
    results.extend(response["Items"])

  return results


if __name__ == "__main__":
    args = parse_arguments()
    failures = query_and_download_items(
      args.ecosystem,
      args.since,
      args.destination,
      args.scan_table,
      args.triage_table,
      args.s3_bucket,
      args.max_sample_mb * 1024 * 1024
    )
    # Exit non-zero so CI surfaces partial failures, while still having attempted every package.
    if failures:
      exit(1)
