import streamlit as st
import streamlit.components.v1 as components
import boto3
import pandas as pd
import plotly.express as px

from datetime import datetime
from zoneinfo import ZoneInfo
from botocore.exceptions import ClientError

st.set_page_config(
    page_title="Backup Monitoring System",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

REGION = "us-east-1"
TABLE_NAME = "BackupHistory"

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #100D1C, #171329, #20183A);
    color: #F5F3FF;
}
.block-container { padding-top: 2rem; max-width: 1450px; }
h1, h2, h3 { color: #F5F3FF !important; }
p, label { color: #C4B5FD; }
[data-testid="stSidebar"] {
    background: #151226;
    border-right: 1px solid #342B52;
}
[data-testid="stMetric"] {
    background: linear-gradient(145deg, #292344, #211C38);
    border: 1px solid #55417D;
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 5px 18px rgba(0,0,0,0.25);
}
[data-testid="stMetricLabel"] { color: #C4B5FD !important; }
[data-testid="stMetricValue"] { color: #FFFFFF !important; }
.stButton > button {
    background: linear-gradient(90deg, #6D28D9, #9333EA);
    color: white;
    border: 1px solid #A78BFA;
    border-radius: 10px;
    font-weight: 600;
}
.stButton > button:hover { background: #7C3AED; color: white; }
.stDownloadButton > button {
    background: #292344;
    color: #DDD6FE;
    border: 1px solid #7C3AED;
    border-radius: 10px;
}
[data-testid="stDataFrame"] {
    border: 1px solid #55417D;
    border-radius: 12px;
}
hr { border-color: #44365F; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<h1>🛡️ Backup Monitoring System</h1>
<p style="font-size:19px;color:#C4B5FD;font-weight:600;">
Backup Success / Failure Alert Dashboard
</p>
<p style="font-size:14px;color:#A79BC7;">
AWS Cloud Backup Monitoring and Status Analytics
</p>
""", unsafe_allow_html=True)

st.divider()

@st.cache_data(ttl=30)
def load_backup_data():
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table = dynamodb.Table(TABLE_NAME)
    response = table.scan()
    items = response.get("Items", [])

    while "LastEvaluatedKey" in response:
        response = table.scan(
            ExclusiveStartKey=response["LastEvaluatedKey"]
        )
        items.extend(response.get("Items", []))

    return items

with st.sidebar:
    st.markdown("## ⚙️ Dashboard Controls")
    st.caption("Cloud Backup Monitoring")

    if st.button("🔄 Refresh Dashboard"):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.markdown("### ☁️ AWS Configuration")
    st.write("**Region:**", REGION)
    st.write("**Database:**", TABLE_NAME)
    st.write("**Service:** Amazon DynamoDB")

    st.divider()
    st.markdown("### 📌 Status Information")
    st.markdown("🟢 Successful")
    st.markdown("🔴 Failed")
    st.markdown("🟠 In Progress")

if "acknowledged_failures" not in st.session_state:
    st.session_state.acknowledged_failures = set()

try:
    records = load_backup_data()
    df = pd.DataFrame(records)

    if not df.empty:
        if "overall_status" in df.columns:
            df["display_status"] = (
                df["overall_status"].fillna("UNKNOWN")
                .astype(str).str.upper()
            )
        elif "status" in df.columns:
            status_mapping = {
                "COMPLETED": "SUCCESS",
                "ERROR": "FAILED",
                "PENDING": "IN_PROGRESS"
            }
            df["display_status"] = (
                df["status"].fillna("UNKNOWN")
                .astype(str).str.upper()
                .replace(status_mapping)
            )
        else:
            df["display_status"] = "UNKNOWN"
    else:
        df = pd.DataFrame(columns=[
            "snapshot_id", "volume_id", "status", "overall_status",
            "progress", "start_time", "description", "checked_at",
            "display_status"
        ])

    total = len(df)
    successful = int((df["display_status"] == "SUCCESS").sum())
    failed = int((df["display_status"] == "FAILED").sum())
    progress_count = int((df["display_status"] == "IN_PROGRESS").sum())
    other = total - successful - failed - progress_count

    st.subheader("❤️ Overall Backup Health")
    if failed > 0:
        st.error(f"⚠️ {failed} failed backup record(s) detected.")
    elif progress_count > 0:
        st.warning(f"⏳ {progress_count} backup(s) in progress.")
    elif total > 0 and other == 0:
        st.success("✅ All recorded backups are successful.")
    elif total == 0:
        st.info("No backup records are available.")
    else:
        st.warning("Some backup records have unknown status.")

    st.divider()
    st.subheader("🚨 Backup Failure Alerts")

    failed_backups = [
        item for item in records
        if str(item.get(
            "overall_status", item.get("status", "")
        )).upper() in ["FAILED", "ERROR"]
    ]

    current_failed_ids = {
        str(item.get("snapshot_id", "Unknown"))
        for item in failed_backups
    }
    st.session_state.acknowledged_failures.intersection_update(
        current_failed_ids
    )

    unacknowledged_failures = [
        item for item in failed_backups
        if str(item.get("snapshot_id", "Unknown"))
        not in st.session_state.acknowledged_failures
    ]

    if failed_backups:
        st.error(f"⚠️ {len(failed_backups)} backup failure(s) detected!")

        for item in failed_backups:
            snapshot_id = str(item.get("snapshot_id", "Unknown"))
            with st.container(border=True):
                st.markdown(f"**Snapshot ID:** {snapshot_id}")
                st.markdown(
                    f"**Volume ID:** {item.get('volume_id', 'Unknown')}"
                )
                st.write(
                    f"Description: {item.get('description', 'No description')}"
                )

                if snapshot_id in st.session_state.acknowledged_failures:
                    st.success("Alert acknowledged.")
                elif st.button(
                    "🔕 Acknowledge / Stop Buzzer",
                    key=f"ack_{snapshot_id}"
                ):
                    st.session_state.acknowledged_failures.add(snapshot_id)
                    st.rerun()

        if unacknowledged_failures:
            st.warning(
                "🔊 Buzzer active: Please check the failed backup."
            )

            buzzer_html = """
            <script>
            let audioContext;

            function playBuzzer() {
                try {
                    const AudioContext =
                        window.AudioContext || window.webkitAudioContext;

                    if (!audioContext) audioContext = new AudioContext();

                    if (audioContext.state === "suspended") {
                        audioContext.resume();
                    }

                    const oscillator = audioContext.createOscillator();
                    const gain = audioContext.createGain();

                    oscillator.type = "square";
                    oscillator.frequency.value = 850;
                    gain.gain.value = 0.12;

                    oscillator.connect(gain);
                    gain.connect(audioContext.destination);
                    oscillator.start();

                    setTimeout(() => oscillator.stop(), 350);
                } catch (error) {
                    console.log("Buzzer could not play:", error);
                }
            }

            playBuzzer();
            const buzzerTimer = setInterval(playBuzzer, 1200);

            window.addEventListener("pagehide", () => {
                clearInterval(buzzerTimer);
            });
            </script>
            """
            components.html(buzzer_html, height=1, scrolling=False)
    else:
        st.success("✅ No backup failures detected.")

    st.divider()
    st.subheader("📊 Backup Overview")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Backups", total)
    col2.metric("Successful", successful)
    col3.metric("Failed", failed)
    col4.metric("In Progress", progress_count)

    if other:
        st.caption(f"Other or unknown records: {other}")

    st.divider()
    st.subheader("📈 Backup Analytics")

    if not df.empty:
        status_counts = (
            df["display_status"].value_counts()
            .rename_axis("Status").reset_index(name="Count")
        )

        status_colors = {
            "SUCCESS": "#22C55E",
            "FAILED": "#F87171",
            "IN_PROGRESS": "#FBBF24",
            "UNKNOWN": "#A78BFA"
        }

        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            pie = px.pie(
                status_counts, names="Status", values="Count",
                hole=0.58, title="Backup Status Distribution",
                color="Status", color_discrete_map=status_colors
            )
            pie.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#F5F3FF"
            )
            st.plotly_chart(pie, use_container_width=True)

        with chart_col2:
            bar = px.bar(
                status_counts, x="Status", y="Count",
                color="Status", text="Count",
                title="Backup Status Count",
                color_discrete_map=status_colors
            )
            bar.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#F5F3FF",
                xaxis_title="Backup Status",
                yaxis_title="Number of Backups",
                showlegend=False
            )
            st.plotly_chart(bar, use_container_width=True)
    else:
        st.info("Charts will appear when records are available.")

    st.divider()
    st.subheader("📁 Backup History")

    if not df.empty:
        available_statuses = sorted(df["display_status"].unique().tolist())
        selected_statuses = st.multiselect(
            "Filter by Backup Status",
            options=available_statuses,
            default=available_statuses,
            key="backup_status_filter"
        )

        filtered_df = df[
            df["display_status"].isin(selected_statuses)
        ].copy()

        search_text = st.text_input("🔎 Search Snapshot ID or Volume ID")

        if search_text:
            search_columns = [
                col for col in ["snapshot_id", "volume_id"]
                if col in filtered_df.columns
            ]
            if search_columns:
                mask = pd.Series(False, index=filtered_df.index)
                for column in search_columns:
                    mask |= filtered_df[column].astype(str).str.contains(
                        search_text, case=False, na=False
                    )
                filtered_df = filtered_df[mask]

        display_columns = [
            col for col in [
                "snapshot_id", "volume_id", "status", "overall_status",
                "progress", "start_time", "description", "checked_at",
                "source"
            ] if col in filtered_df.columns
        ]

        if filtered_df.empty:
            st.info("No matching backup records.")
        else:
            st.dataframe(
                filtered_df[display_columns],
                use_container_width=True,
                hide_index=True
            )

        st.caption(f"Showing {len(filtered_df)} of {total} records.")

        csv_data = filtered_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download Backup History (CSV)",
            data=csv_data,
            file_name="backup_history.csv",
            mime="text/csv"
        )
    else:
        st.info("No backup history is available yet.")

    st.divider()
    st.subheader("➕ Add Manual Backup")
    st.caption(
        "Add sample records for testing. "
        "Manual entries do not create actual EBS snapshots."
    )

    with st.form("manual_backup_form"):
        snapshot_id = st.text_input(
            "Snapshot ID", placeholder="Example: MANUAL-001"
        )
        volume_id = st.text_input(
            "Volume ID", placeholder="Example: vol-manual-001"
        )
        backup_status = st.selectbox(
            "Backup Status", ["SUCCESS", "FAILED", "IN_PROGRESS"]
        )
        manual_progress = st.slider("Backup Progress (%)", 0, 100, 100)
        description = st.text_area("Description")
        submitted = st.form_submit_button("Add Backup")

        if submitted:
            if not snapshot_id.strip() or not volume_id.strip():
                st.error("Please enter both Snapshot ID and Volume ID.")
            else:
                try:
                    manual_table = boto3.resource(
                        "dynamodb", region_name=REGION
                    ).Table(TABLE_NAME)

                    current_time = datetime.now(
                        ZoneInfo("Asia/Kolkata")
                    ).isoformat()

                    status_mapping = {
                        "SUCCESS": "completed",
                        "FAILED": "error",
                        "IN_PROGRESS": "pending"
                    }

                    manual_table.put_item(
                        Item={
                            "snapshot_id": snapshot_id.strip(),
                            "volume_id": volume_id.strip(),
                            "status": status_mapping[backup_status],
                            "overall_status": backup_status,
                            "progress": f"{manual_progress}%",
                            "description": description,
                            "start_time": current_time,
                            "checked_at": current_time,
                            "source": "MANUAL"
                        },
                        ConditionExpression="attribute_not_exists(snapshot_id)"
                    )

                    st.success("Manual backup record added successfully!")
                    st.cache_data.clear()
                    st.rerun()

                except ClientError as error:
                    code = error.response.get("Error", {}).get("Code", "")
                    if code == "ConditionalCheckFailedException":
                        st.error("This Snapshot ID already exists.")
                    else:
                        st.error(f"Unable to add backup: {error}")

                except Exception as error:
                    st.error(f"Unable to add backup: {error}")

    st.divider()

    current_time = datetime.now(
        ZoneInfo("Asia/Kolkata")
    ).strftime("%d-%m-%Y %I:%M:%S %p")

    st.markdown(
        f"""
        <div style="text-align:center; padding:18px;">
            <p style="color:#C4B5FD; font-size:16px; font-weight:600;">
                AWS Cloud Backup Monitoring System
            </p>
            <p style="color:#A79BC7; font-size:12px;">
                Powered by Amazon EC2 | AWS Lambda |
                Amazon EventBridge | Amazon DynamoDB
            </p>
            <p style="color:#8B80A8; font-size:12px;">
                Dashboard viewed: {current_time} IST
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

except ClientError as error:
    st.error("Unable to access DynamoDB backup history.")
    st.code(str(error))
    st.info(
        "Check the EC2 instance profile permissions for DynamoDB."
    )

except Exception as error:
    st.error("An unexpected dashboard error occurred.")
    st.exception(error)
