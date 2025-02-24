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
    parser.add_argument('--dynamodb-table', help='DynamoDB table containing the scan results')
    args = parser.parse_args()
    return args


def query_and_download_items(ecosystem, cutoff_date, dest, dynamodb_table, s3_bucket):
  table = boto3.resource('dynamodb').Table(dynamodb_table)

  # Convert the date to a timestamp
  since = datetime.strptime(cutoff_date + " 00:00:00", '%Y-%m-%d %H:%M:%S')
  since_ts = round(time.mktime(since.timetuple()))

  # Scan the DynamoDB table
  results = []
  response = {}
  query = "ecosystem = :ecosystem AND triage_state = :state AND scan_timestamp >= :cutoff_timestamp"
  values = {
    ":ecosystem": ecosystem,
    ":state": "malicious",
    ":cutoff_timestamp": since_ts
  }
  first_query = True
  while 'LastEvaluatedKey' in response or first_query:
    if first_query:
      response = table.scan(FilterExpression=query, ExpressionAttributeValues=values)
      first_query = False
    else:
      response = table.scan(FilterExpression=query, ExpressionAttributeValues=values, ExclusiveStartKey=response['LastEvaluatedKey'])
    
    results.extend(response['Items'])
  
  print("Syncing samples of " + str(len(results)) + " packages")
  os.chdir(dest)
  for item in results:
    # Convert scan_datetime to the desired format
    scan_datetime = datetime.strptime(item['scan_datetime'], '%Y-%m-%d %H:%M:%S.%f')
    formatted_date = scan_datetime.strftime('%Y-%m-%d')

    package_name = item["package_name"].removeprefix("npm|")
    package_version = item["package_version"]
    if package_name != item["package_name"] and package_version.startswith(NPM_SECURITY_VERSION):
      continue

    # Sanitize the package name and version for use in a file or directory name
    # `@` is used in place of `/` for the directory versions because it is:
    #   1) unambiguously identifiable as a replacement character (used by the manifest generator on that basis)
    #   2) already used in certain of the npm package names
    package_name_directory = package_name.replace('/', '@')
    package_version_directory = package_version.replace('/', '@')
    package_name_file = package_name.replace('/', '_')
    package_version_file = package_version.replace('/', '_')

    sample_identifier = f"{formatted_date}-{package_name_file}-v{package_version_file}"
    sample_directory = os.path.join(package_name_directory, package_version_directory)
    sample_filename = os.path.join(sample_directory, f"{sample_identifier}.zip")

    if os.path.isfile(sample_filename):
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
      command = ["zip", "--encrypt", "-r", "-P", "infected", sample_filename, tempdir]
      try:
        subprocess.run(command, check=True, capture_output=True, cwd=dest)
      except subprocess.CalledProcessError as e:
        print("Unable to ZIP: " + str(e))
        print(e.stderr)
        exit(1)
      print("Wrote new ZIP file " + sample_filename)


if __name__ == "__main__":
    args = parse_arguments()
    query_and_download_items(args.ecosystem, args.since, args.destination, args.dynamodb_table, args.s3_bucket)
