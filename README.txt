# Backup Success/Failure Alert System

## Project files
- `app.py` — Streamlit dashboard, DynamoDB history, charts, filters, CSV export, failure alert and browser buzzer.
- `lambda_function.py` — AWS Lambda code that checks EBS snapshots and writes results to DynamoDB.
- `requirements.txt` — Python dependencies.

## AWS configuration used in this project
- Region: `us-east-1`
- DynamoDB table: `BackupHistory`
- Lambda function: `BackupMonitorFunction`
- EventBridge schedule: `BackupMonitorDaily`
- EBS snapshot Name tag filter: `BackupDashboard-Snapshot`

## Run the dashboard on EC2
Install dependencies:
```bash
python3 -m pip install --user -r requirements.txt
```

Run:
```bash
python3 -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

Open:
`http://YOUR-EC2-PUBLIC-IP:8501`

## AWS permissions
The EC2 instance role needs permission to scan the `BackupHistory` DynamoDB table.
The Lambda execution role needs permission to describe EBS snapshots and put items into `BackupHistory`.

## Important notes
- The dashboard's manual entry form is for demonstration/testing only. It does not create an EBS snapshot.
- The browser buzzer may require a user interaction before the browser allows audio playback.
- EventBridge is configured for 9:00 PM Asia/Kolkata, but an actual scheduled invocation should be verified in Lambda monitoring/CloudWatch after the scheduled time.
- This package contains the application and Lambda source code. It does not contain AWS credentials, deployed AWS resources, or the EC2 systemd service configuration.
