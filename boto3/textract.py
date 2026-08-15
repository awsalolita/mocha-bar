"""
Amazon Textract unit functions — CLIENT only (no resource API).

client = boto3.client("textract")

Covers: synchronous detect/analyze (single-page images/PDFs), asynchronous
jobs for multi-page S3 documents (start/get), plus small helpers to pull the
plain text lines out of the block soup Textract returns.

Sync APIs accept bytes (Document={"Bytes": ...}) or S3
(Document={"S3Object": {...}}). Async APIs are S3-only.
"""
import time
import boto3


def get_client(region=None):
    return boto3.client("textract", region_name=region)


def _document(doc_bytes=None, bucket=None, key=None):
    if doc_bytes is not None:
        return {"Bytes": doc_bytes}
    return {"S3Object": {"Bucket": bucket, "Name": key}}


# ---- Synchronous (single page image / PDF) ----
def txtc_detect_text(client, doc_bytes=None, bucket=None, key=None):
    """Raw OCR: returns all Block objects (LINE/WORD/PAGE)."""
    return client.detect_document_text(
        Document=_document(doc_bytes, bucket, key)).get("Blocks", [])


def txtc_analyze_document(client, features=("FORMS", "TABLES"),
                          doc_bytes=None, bucket=None, key=None):
    """Structured analysis. features subset of FORMS|TABLES|SIGNATURES|LAYOUT."""
    return client.analyze_document(
        Document=_document(doc_bytes, bucket, key),
        FeatureTypes=list(features)).get("Blocks", [])


def txtc_analyze_expense(client, doc_bytes=None, bucket=None, key=None):
    """Receipts/invoices -> line items + summary fields."""
    return client.analyze_expense(
        Document=_document(doc_bytes, bucket, key)).get("ExpenseDocuments", [])


def txtc_analyze_id(client, doc_bytes=None, bucket=None, key=None):
    """ID documents (passport/driver license) -> identity fields."""
    return client.analyze_id(
        DocumentPages=[_document(doc_bytes, bucket, key)]).get("IdentityDocuments", [])


# ---- Asynchronous (multi-page docs in S3) ----
def txtc_start_text_detection(client, bucket, key, sns_topic_arn=None, role_arn=None):
    """Kick off async OCR. Returns JobId. Optionally publish completion to SNS."""
    kwargs = {"DocumentLocation": {"S3Object": {"Bucket": bucket, "Name": key}}}
    if sns_topic_arn and role_arn:
        kwargs["NotificationChannel"] = {"SNSTopicArn": sns_topic_arn,
                                         "RoleArn": role_arn}
    return client.start_document_text_detection(**kwargs)["JobId"]


def txtc_start_analysis(client, bucket, key, features=("FORMS", "TABLES")):
    """Kick off async analyze_document. Returns JobId."""
    return client.start_document_analysis(
        DocumentLocation={"S3Object": {"Bucket": bucket, "Name": key}},
        FeatureTypes=list(features))["JobId"]


def txtc_get_text_detection(client, job_id, next_token=None):
    kwargs = {"JobId": job_id}
    if next_token:
        kwargs["NextToken"] = next_token
    return client.get_document_text_detection(**kwargs)


def txtc_get_analysis(client, job_id, next_token=None):
    kwargs = {"JobId": job_id}
    if next_token:
        kwargs["NextToken"] = next_token
    return client.get_document_analysis(**kwargs)


def txtc_wait_text_detection(client, job_id, poll=5, timeout=300):
    """Poll until an async text-detection job finishes; returns all Blocks."""
    waited = 0
    while waited < timeout:
        resp = client.get_document_text_detection(JobId=job_id)
        status = resp["JobStatus"]
        if status in ("SUCCEEDED", "FAILED"):
            break
        time.sleep(poll)
        waited += poll
    if resp["JobStatus"] != "SUCCEEDED":
        return []
    blocks = resp.get("Blocks", [])
    token = resp.get("NextToken")
    while token:
        resp = client.get_document_text_detection(JobId=job_id, NextToken=token)
        blocks.extend(resp.get("Blocks", []))
        token = resp.get("NextToken")
    return blocks


# ---- Helpers to make the block soup usable ----
def txtc_lines(blocks):
    """Extract plain text lines (in reading order) from a list of Blocks."""
    return [b["Text"] for b in blocks if b.get("BlockType") == "LINE"]


def txtc_full_text(blocks):
    """Join all detected lines into a single string."""
    return "\n".join(txtc_lines(blocks))
