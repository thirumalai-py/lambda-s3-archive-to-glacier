import boto3
from datetime import datetime, timezone, timedelta

# Configuration
BUCKET_NAME = 'thiru-auto-archive-bucket'
ARCHIVE_AFTER_MINUTES = 5  # Change to 1 for quick test

# AWS Client
s3 = boto3.client('s3')

def lambda_handler(event, context):
    now = datetime.now(timezone.utc)
    archived_files = []

    print(f"[{now.isoformat()}] Starting archival process...")

    response = s3.list_objects_v2(Bucket=BUCKET_NAME)
    if 'Contents' not in response:
        print("No objects found.")
        return {"status": "No files in bucket."}

    for obj in response['Contents']:
        key = obj['Key']

        # ✅ Skip files inside archive-log folder
        if key.startswith('archive-log/'):
            continue

        last_modified = obj['LastModified']
        storage_class = obj.get('StorageClass', 'STANDARD')
        age_minutes = (now - last_modified).total_seconds() / 60

        if age_minutes >= ARCHIVE_AFTER_MINUTES and storage_class == 'STANDARD':
            print(f"📦 Archiving: {key} | Age: {age_minutes:.1f} minutes")

            s3.copy_object(
                Bucket=BUCKET_NAME,
                Key=key,
                CopySource={'Bucket': BUCKET_NAME, 'Key': key},
                StorageClass='GLACIER',
                MetadataDirective='COPY'
            )
            archived_files.append(f"{key} (LastModified: {last_modified})")

    if archived_files:
        log_summary = f"✅ Archived {len(archived_files)} file(s):\n" + "\n".join(archived_files)
        print(log_summary)

        # Write log to S3
        log_key = f"archive-log/log_{now.strftime('%Y%m%d_%H%M%S')}.txt"
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=log_key,
            Body=log_summary.encode('utf-8')
        )
    else:
        print("No eligible files found for archival")

    return {
        "archived_count": len(archived_files),
        "archived_files": archived_files
    }
