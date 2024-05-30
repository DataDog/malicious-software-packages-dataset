import argparse
import boto3
from datetime import datetime
import os
from pathlib import Path
import time
import subprocess
import shutil

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
    
    # Download the folder from S3
    s3_prefix = f'{ecosystem}/{formatted_date}/{item["package_name"]}/{item["package_version"]}/'
    package_name = item["package_name"]
    package_name = package_name.replace("/", "_")
    package_name = package_name.replace("npm|", "")
    package_identifier = f'{package_name}-v{item["package_version"]}'
    local_folder = f'{formatted_date}-{package_identifier}'
    Path(local_folder).mkdir(parents=True, exist_ok=True)
    zip_file = f'{local_folder}.zip'
    
    if os.path.isfile(zip_file):
      continue

    s3_url = f"s3://{s3_bucket}/{s3_prefix}"
    print(f"Downloading files for {package_identifier}")
    command = ['aws', 's3', 'sync', s3_url, local_folder]
    try:
      subprocess.run(command, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
      print("Unable to download: " + str(e))
      print("Command: " + " ".join(command))
      print(e.stderr)
      exit(1)

    # Zip and encrypt the folder
    # We spawn zip because no way to encrypt with the standard ZipFile library...
    command = ["zip", "--encrypt", "-r", "-P", "infected", zip_file, local_folder]
    try:
      subprocess.run(command, check=True, capture_output=True, cwd=dest)
    except subprocess.CalledProcessError as e:
      print("Unable to ZIP: " + str(e))
      print(e.stderr)
      exit(1)
    print("Wrote new ZIP file " + zip_file)
    shutil.rmtree(local_folder, ignore_errors=True)
  
if __name__ == "__main__":
    args = parse_arguments()
    query_and_download_items(args.ecosystem, args.since, args.destination, args.dynamodb_table, args.s3_bucket)