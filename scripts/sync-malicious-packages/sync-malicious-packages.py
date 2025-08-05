import argparse
from datetime import datetime
import os
from pathlib import Path
import tempfile
import time
import subprocess
import boto3.dynamodb.types
import decimal

import boto3

boto3.dynamodb.types.DYNAMODB_CONTEXT = decimal.Context(prec=100)


NPM_SECURITY_VERSION = "0.0.1-security"


def parse_arguments():
    parser = argparse.ArgumentParser(description='Download malicious samples from S3')
    parser.add_argument('--ecosystem', help='npm or pypi', default='pypi')
    parser.add_argument('--since', help='Date in YYYY-MM-DD format', required=True)
    parser.add_argument('--destination', help='Where to store the resulting ZIP', required=True)
    parser.add_argument('--s3-bucket', help='S3 bucket containing the samples')
    parser.add_argument('--scan-table', help='DynamoDB table containing the scan results')
    parser.add_argument('--triage-table', help='DynamoDB table containing the triage results')
    args = parser.parse_args()
    return args


def query_and_download_items(ecosystem, cutoff_date, dest, scan_table, triage_table, s3_bucket):
  # Convert the date to a timestamp
  since = datetime.strptime(cutoff_date + " 00:00:00", '%Y-%m-%d %H:%M:%S')
  since_ts = round(time.mktime(since.timetuple()))

  scan_query = "ecosystem = :ecosystem AND triage_state = :state AND scan_timestamp >= :cutoff_timestamp"
  scan_values = {
    ":ecosystem": ecosystem,
    ":state": "malicious",
    ":cutoff_timestamp": since_ts
  }
  scan_results = perform_table_scan(scan_table, scan_query, scan_values)
  
  print("Syncing samples of " + str(len(scan_results)) + " packages")
  os.chdir(dest)
  for item in scan_results:
    # Convert scan_datetime to the desired format
    scan_datetime = datetime.strptime(item['scan_datetime'], '%Y-%m-%d %H:%M:%S.%f')
    formatted_date = scan_datetime.strftime('%Y-%m-%d')

    package_name = item["package_name"].removeprefix("npm|")
    package_version = item["package_version"]
    if package_name != item["package_name"] and package_version.startswith(NPM_SECURITY_VERSION):
      continue

    # TODO(ikretz): Replace this with a query and filters
    triage_query = "package = :package"
    triage_values = { ":package": f"{package_name}|{ecosystem}" }
    triage_results = perform_table_scan(triage_table, triage_query, triage_values)

    directory_prefix = Path("malicious_intent")
    if any(
      map(
        lambda r: r.get("compromised_lib", False) and package_version in r.get("malicious_versions", []),
        triage_results
      )
    ):
      directory_prefix = Path("compromised_lib")

    # `@` is used in place of `/` for directories because it is:
    #   1) unambiguously identifiable as a replacement character (used to generate manifests)
    #   2) already used in npm package names, thus safe to use
    package_name_directory = package_name.replace('/', '@')
    package_version_directory = package_version.replace('/', '@')
    sample_directory = directory_prefix / package_name_directory / package_version_directory

    package_name_file = package_name.replace('/', '_')
    package_version_file = package_version.replace('/', '_')
    sample_file = f"{formatted_date}-{package_name_file}-v{package_version_file}.zip"

    sample_path = sample_directory / sample_file
    if sample_path.is_file():
      continue

    print(f"Downloading files for {package_name}-v{package_version}")
    s3_prefix = f'{ecosystem}/{formatted_date}/{package_name}/{package_version}/'
    s3_url = f"s3://{s3_bucket}/{s3_prefix}"
    with tempfile.TemporaryDirectory() as tempdir:
      # Download the folder from S3
      command = ['aws', 's3', 'sync', s3_url, tempdir]
      try:
        subprocess.run(command, check=True, capture_output=True)
      except subprocess.CalledProcessError as e:
        print("Unable to download: " + str(e))
        print("Command: " + " ".join(command))
        print(e.stderr)
        exit(1)

      # Make the directory for the sample zip file
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


def perform_table_scan(table_name: str, filter_expr: str, expr_attr_values: dict) -> list:
  results = []

  response, first_query = {}, True
  table = boto3.resource('dynamodb').Table(table_name)

  while first_query or "LastEvaluatedKey" in response:
    args = {
      "FilterExpression": filter_expr,
      "ExpressionAttributeValues": expr_attr_values,
    }

    if first_query:
      first_query = False
    else:
      args["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    response = table.scan(**args)
    results.extend(response['Items'])

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
