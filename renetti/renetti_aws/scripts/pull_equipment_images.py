import os

import boto3


def list_and_download_s3_files(bucket_name, local_directory):
    # Initialize the S3 client
    s3_client = boto3.client("s3")

    # Ensure the local directory exists
    if not os.path.exists(local_directory):
        os.makedirs(local_directory)

    try:
        # Paginate through the list of objects in the bucket
        paginator = s3_client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket_name)

        print(f"Downloading files from bucket '{bucket_name}' to '{local_directory}':")

        for page in pages:
            if "Contents" in page:
                for obj in page["Contents"]:
                    file_key = obj["Key"]
                    local_file_path = os.path.join(local_directory, file_key)

                    # Ensure subdirectories exist
                    if "/" in file_key:
                        subdir = os.path.dirname(local_file_path)
                        if not os.path.exists(subdir):
                            os.makedirs(subdir)

                    # Download the file
                    print(f"Downloading {file_key}...")
                    s3_client.download_file(bucket_name, file_key, local_file_path)

        print("Download completed!")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    # Replace 'your-bucket-name' with the name of your bucket
    bucket_name = "equipment-model-data"

    # Replace 'your-local-directory' with your desired local directory
    local_directory = "/Users/dan/Work/dev/projects/renetti/files/model_data"

    list_and_download_s3_files(bucket_name, local_directory)