import boto3
import json
from datetime import datetime, timezone

ec2 = boto3.client("ec2")
dynamodb = boto3.resource("dynamodb")

table = dynamodb.Table("BackupHistory")

def lambda_handler(event, context):
    try:
        response = ec2.describe_snapshots(
            OwnerIds=["self"],
            Filters=[
                {
                    "Name": "tag:Name",
                    "Values": ["BackupDashboard-Snapshot"]
                }
            ]
        )

        snapshots = response.get("Snapshots", [])
        snapshots.sort(key=lambda x: x["StartTime"], reverse=True)

        if not snapshots:
            overall_status = "NO_BACKUP"
        elif any(s["State"] == "error" for s in snapshots):
            overall_status = "FAILED"
        elif any(s["State"] == "pending" for s in snapshots):
            overall_status = "IN_PROGRESS"
        elif all(s["State"] == "completed" for s in snapshots):
            overall_status = "SUCCESS"
        else:
            overall_status = "UNKNOWN"

        backup_records = []

        for snapshot in snapshots:
            record = {
                "snapshot_id": snapshot["SnapshotId"],
                "volume_id": snapshot.get("VolumeId", ""),
                "status": snapshot["State"],
                "progress": snapshot.get("Progress", "N/A"),
                "start_time": snapshot["StartTime"].isoformat(),
                "description": snapshot.get("Description", ""),
                "overall_status": overall_status,
                "checked_at": datetime.now(timezone.utc).isoformat()
            }

            table.put_item(Item=record)
            backup_records.append(record)

        result = {
            "project": "Backup Success/Failure Alert",
            "overall_status": overall_status,
            "total_snapshots": len(snapshots),
            "snapshots": backup_records,
            "database": "BackupHistory"
        }

        return {
            "statusCode": 200,
            "body": json.dumps(result)
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({
                "overall_status": "ERROR",
                "message": str(e)
            })
        }
