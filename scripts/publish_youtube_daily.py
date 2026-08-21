"""Publish the daily AstroPratidin set to YouTube and verify processing.

Uploads exactly 13 videos per successful render: 1 combined 12-Rashi video
plus 12 individual Rashi videos. All uploads are submitted before processing
verification so YouTube can process them in parallel.
"""
from pathlib import Path
import datetime as dt
import json
import os
import time

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

OUT = Path("output")
UPLOADS = OUT / "youtube_uploads"
RASHIS = [
    (1, "मेष", "मेष राशि"), (2, "वृषभ", "वृषभ राशि"),
    (3, "मिथुन", "मिथुन राशि"), (4, "कर्क", "कर्क राशि"),
    (5, "सिंह", "सिंह राशि"), (6, "कन्या", "कन्या राशि"),
    (7, "तुला", "तुला राशि"), (8, "वृश्चिक", "वृश्चिक राशि"),
    (9, "धनु", "धनु राशि"), (10, "मकर", "मकर राशि"),
    (11, "कुंभ", "कुंभ राशि"), (12, "मीन", "मीन राशि"),
]


def upload(youtube, path, title, description, tags):
    body = {
        "snippet": {"title": title[:100], "description": description[:4900], "categoryId": "22", "tags": tags},
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(str(path), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"YouTube upload {path.name}: {int(status.progress() * 100)}%")
    return response["id"]


def verify_processing(youtube, video_id, timeout_seconds=900):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        item = youtube.videos().list(part="status,processingDetails", id=video_id).execute().get("items", [])
        if not item:
            raise RuntimeError(f"YouTube video disappeared after upload: {video_id}")
        video = item[0]
        status = video.get("status", {})
        processing = video.get("processingDetails", {})
        upload_status = status.get("uploadStatus")
        processing_status = processing.get("processingStatus")
        print(f"VERIFY {video_id}: uploadStatus={upload_status} processingStatus={processing_status} privacy={status.get('privacyStatus')}")
        if upload_status in {"failed", "rejected"}:
            raise RuntimeError(f"YouTube upload failed for {video_id}: {status.get('failureReason') or status.get('rejectionReason')}")
        if processing_status == "failed":
            raise RuntimeError(f"YouTube processing failed for {video_id}: {processing.get('processingFailureReason')}")
        if upload_status == "processed" and processing_status == "succeeded":
            if status.get("privacyStatus") != "public":
                raise RuntimeError(f"YouTube privacy status is {status.get('privacyStatus')} for {video_id}, expected public")
            return
        time.sleep(15)
    raise RuntimeError(f"YouTube processing verification timed out for {video_id}")


def main():
    raw = os.environ.get("YOUTUBE_TOKEN_JSON", "")
    if not raw:
        raise SystemExit("Missing ASTROPRATIDIN_YOUTUBE_TOKEN_JSON repository secret")
    token = json.loads(raw)
    creds = Credentials.from_authorized_user_info(token, scopes=["https://www.googleapis.com/auth/youtube.upload"])
    youtube = build("youtube", "v3", credentials=creds)
    today = dt.date.today().isoformat()
    script = (OUT / "daily_script.md").read_text(encoding="utf-8")
    base_description = "AstroPratidin — आपका दैनिक ज्योतिष साथी।\n\n"
    jobs = []

    combined = OUT / "daily_video.mp4"
    if not combined.exists():
        raise SystemExit("Combined daily video missing")
    jobs.append(("combined", None, combined,
                 f"आज का राशिफल | AstroPratidin | {today}",
                 base_description + script + "\n\n#AstroPratidin #दैनिकराशिफल #ज्योतिष #राशिफल",
                 ["AstroPratidin", "दैनिक राशिफल", "राशिफल", "ज्योतिष", "आज का राशिफल"]))

    for index, key, label in RASHIS:
        path = UPLOADS / f"{index:02d}_{key}.mp4"
        if not path.exists():
            raise SystemExit(f"Individual Rashi video missing: {path}")
        description = (
            f"AstroPratidin — {label} के लिए आज का दैनिक राशिफल।\n\n"
            f"{key} राशि के ग्रह गोचर, संकेत और आज के महत्वपूर्ण ज्योतिषीय मार्गदर्शन के लिए यह दैनिक वीडियो देखें।\n\n"
            f"#AstroPratidin #{key}राशि #दैनिकराशिफल #ज्योतिष #राशिफल"
        )
        jobs.append(("rashi", key, path, f"आज का {label} राशिफल | AstroPratidin | {today}", description,
                     ["AstroPratidin", label, f"{key} राशि", "दैनिक राशिफल", "ज्योतिष"]))

    results = []
    print("YOUTUBE UPLOAD PLAN: 1 combined + 12 Rashi videos = 13 total")
    for kind, rashi, path, title, description, tags in jobs:
        vid = upload(youtube, path, title, description, tags)
        print(f"UPLOADED {kind} {rashi or 'combined'}: {vid}")
        results.append({"type": kind, "rashi": rashi, "video_id": vid, "url": f"https://www.youtube.com/watch?v={vid}"})

    print("ALL 13 UPLOADS ACCEPTED — VERIFYING YOUTUBE PROCESSING")
    for result in results:
        verify_processing(youtube, result["video_id"])

    manifest = OUT / "youtube_publish_manifest.json"
    manifest.write_text(json.dumps({"date": today, "videos": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("YOUTUBE DAILY PUBLISH: PASS — 1 combined + 12 Rashi videos")
    for result in results:
        print(f"PUBLISHED_{result['type'].upper()}={result['video_id']}")
