import boto3

if __name__ == '__main__':
    s3_client = boto3.client('s3')
    get_last_modified = lambda obj: int(obj['LastModified'].strftime('%s'))

    result = s3_client.list_objects_v2(Bucket='update-helper')
    count = result['KeyCount']
    latest = None

    while count != 0:
        objects = result['Contents']
        sorted_objects = [obj for obj in sorted(objects, key=get_last_modified)]
        if latest is None:
            latest = sorted_objects[-1]
        else:
            latest = sorted_objects[-1] if sorted_objects[-1]['LastModified'] > latest['LastModified'] else latest

        last = objects[-1]
        key = last['Key']
        result = s3_client.list_objects_v2(Bucket='update-helper', StartAfter=key)
        count = result['KeyCount']

    print(latest)
