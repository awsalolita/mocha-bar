"""
Amazon Translate unit functions — CLIENT only (no resource API).

client = boto3.client("translate")

Covers: real-time text translation (single + convenience batch loop),
async document-batch jobs over S3, and terminology management.

Language codes are ISO like 'en', 'fr', 'es'. Use 'auto' as source to
auto-detect the input language.
"""
import boto3


def get_client(region=None):
    return boto3.client("translate", region_name=region)


# ---- Real-time text ----
def trnc_translate_text(client, text, source="auto", target="en", terminology=None):
    """Translate a single string. Returns the translated text."""
    kwargs = {"Text": text, "SourceLanguageCode": source, "TargetLanguageCode": target}
    if terminology:
        kwargs["TerminologyNames"] = [terminology]
    return client.translate_text(**kwargs)["TranslatedText"]


def trnc_translate_full(client, text, source="auto", target="en"):
    """Same as above but returns the full response (incl. detected source lang)."""
    return client.translate_text(
        Text=text, SourceLanguageCode=source, TargetLanguageCode=target)


def trnc_translate_many(client, texts, source="auto", target="en"):
    """Convenience: translate a list of strings one-by-one. Returns list of strings."""
    return [trnc_translate_text(client, t, source, target) for t in texts]


# ---- Async document batch (S3 in/out) ----
def trnc_start_batch_job(client, job_name, input_s3_uri, output_s3_uri, role_arn,
                         source="auto", targets=("en",), content_type="text/plain"):
    """Start async batch translation over documents in S3. Returns JobId."""
    return client.start_text_translation_job(
        JobName=job_name,
        InputDataConfig={"S3Uri": input_s3_uri, "ContentType": content_type},
        OutputDataConfig={"S3Uri": output_s3_uri},
        DataAccessRoleArn=role_arn,
        SourceLanguageCode=source,
        TargetLanguageCodes=list(targets))["JobId"]


def trnc_describe_batch_job(client, job_id):
    return client.describe_text_translation_job(
        JobId=job_id)["TextTranslationJobProperties"]


def trnc_stop_batch_job(client, job_id):
    return client.stop_text_translation_job(JobId=job_id)


# ---- Custom terminology ----
def trnc_import_terminology(client, name, csv_bytes):
    """Upload a CSV terminology file (bytes). MergeStrategy only supports OVERWRITE."""
    return client.import_terminology(
        Name=name,
        MergeStrategy="OVERWRITE",
        TerminologyData={"File": csv_bytes, "Format": "CSV"})


def trnc_list_terminologies(client):
    return client.list_terminologies().get("TerminologyPropertiesList", [])


def trnc_delete_terminology(client, name):
    return client.delete_terminology(Name=name)
