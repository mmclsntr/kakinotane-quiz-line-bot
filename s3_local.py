import boto3

s3 = boto3.resource('s3')


def put_object(bucket_name: str, file_name: str, output_file_name: str):
    data = open(file_name, 'rb')
    s3.Bucket(bucket_name).put_object(Key=output_file_name, Body=data)


def get_public_url(bucket_name: str, file_name: str):
    return "https://{}.s3.amazonaws.com/{}".format(
        bucket_name,
        file_name)
