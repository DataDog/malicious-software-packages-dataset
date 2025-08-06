from argparse import ArgumentParser
from datetime import datetime
from decimal import Context
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import time
from typing import Optional

import boto3
import boto3.dynamodb.types

boto3.dynamodb.types.DYNAMODB_CONTEXT = Context(prec=100)


NPM_SECURITY_VERSION = "0.0.1-security"


def parse_arguments():
    parser = ArgumentParser(description='Download malicious samples from S3')
    parser.add_argument('--ecosystem', help='npm or pypi', default='pypi')
    parser.add_argument('--since', help='Date in YYYY-MM-DD format', required=True)
    parser.add_argument('--destination', help='Where to store the resulting ZIP', required=True)
    parser.add_argument('--s3-bucket', help='S3 bucket containing the samples')
    parser.add_argument('--scan-table', help='DynamoDB table containing the scan results')
    parser.add_argument('--triage-table', help='DynamoDB table containing the triage results')
    args = parser.parse_args()
    return args


def query_and_download_items(ecosystem, cutoff_date, dest, scan_table, triage_table, s3_bucket):
  os.chdir(dest)

  since = datetime.strptime(cutoff_date + " 00:00:00", '%Y-%m-%d %H:%M:%S')
  since_timestamp = round(time.mktime(since.timetuple()))

  scan_query = "ecosystem = :ecosystem AND triage_state = :state AND scan_timestamp >= :cutoff_timestamp"
  scan_values = {
    ":ecosystem": ecosystem,
    ":state": "malicious",
    ":cutoff_timestamp": since_timestamp
  }
  scan_results = perform_table_scan(scan_table, scan_query, scan_values)
  
  print(f"Syncing samples of {len(scan_results)} packages")
  for item in scan_results:
    package_name = item["package_name"].removeprefix("npm|")
    package_version = item["package_version"]
    if package_name != item["package_name"] and package_version.startswith(NPM_SECURITY_VERSION):
      continue

    # Determine whether this package is a compromised lib and classify the sample accordingly
    triage_query_key = "package = :package"
    triage_query_filter = "compromised_lib = :true"
    triage_query_values = {
      ":package": f"{package_name}|{ecosystem}",
      ":true": True,
    }
    triage_results = perform_table_query(triage_table, triage_query_key, triage_query_filter, triage_query_values)

    sample_kind = "compromised_lib" if triage_results else "malicious_intent"

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

    print(f"Downloading files for {package_name}-v{package_version}")
    with TemporaryDirectory() as tempdir:
      try:
        # Download the folder from S3
        s3_url = f"s3://{s3_bucket}/{ecosystem}/{scan_datetime}/{package_name}/{package_version}/"
        subprocess.run(['aws', 's3', 'sync', s3_url, tempdir], check=True, capture_output=True)
      except subprocess.CalledProcessError as e:
        print("Unable to download: " + str(e))
        print("Command: " + " ".join(command))
        print(e.stderr)
        exit(1)

      Path(sample_directory).mkdir(parents=True, exist_ok=True)

      # We spawn zip because no way to encrypt with the standard ZipFile library...
      command = ["zip", "--encrypt", "-r", "-P", "infected", sample_path, tempdir]
      try:
        subprocess.run(command, check=True, capture_output=True, cwd=dest)
      except subprocess.CalledProcessError as e:
        print("Unable to ZIP: " + str(e))
        print(e.stderr)
        exit(1)
      print(f"Wrote new ZIP file {sample_path}")


def perform_table_scan(table_name: str, filter_expr: str, expr_attr_values: Optional[dict]) -> list:
  table = boto3.resource("dynamodb").Table(table_name)

  scan_args = {
    "FilterExpression": filter_expr,
  }
  if expr_attr_values:
      scan_args["ExpressionAttributeValues"] = expr_attr_values

  return _perform_table_operation(table.scan, scan_args)


def perform_table_query(
  table_name: str,
  key_condition_expr: str,
  filter_expr: Optional[str],
  expr_attr_values: Optional[dict]
) -> list:
  table = boto3.resource("dynamodb").Table(table_name)

  query_args = {
    "KeyConditionExpression": key_condition_expr,
  }
  if filter_expr:
      query_args["FilterExpression"] = filter_expr
  if expr_attr_values:
      query_args["ExpressionAttributeValues"] = expr_attr_values

  return _perform_table_operation(table.query, query_args)

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
    query_and_download_items(
      args.ecosystem,
      args.since,
      args.destination,
      args.scan_table,
      args.triage_table,
      args.s3_bucket
    )
