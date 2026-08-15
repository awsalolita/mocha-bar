"""
Amazon Rekognition unit functions — CLIENT only (no resource API).

client = boto3.client("rekognition")

Covers: label/text/face detection, moderation, celebrity recognition,
face comparison, and face collections (index/search).

Image input is either bytes (Image={"Bytes": ...}) or an S3 object
(Image={"S3Object": {"Bucket": ..., "Name": ...}}). Helpers below accept
either `image_bytes=` or (`bucket=`, `key=`).
"""
import boto3


def get_client(region=None):
    return boto3.client("rekognition", region_name=region)


def _image(image_bytes=None, bucket=None, key=None):
    """Build the Image= argument from raw bytes OR an S3 object."""
    if image_bytes is not None:
        return {"Bytes": image_bytes}
    return {"S3Object": {"Bucket": bucket, "Name": key}}


# ---- Detection ----
def rekc_detect_labels(client, image_bytes=None, bucket=None, key=None,
                       max_labels=10, min_confidence=70.0):
    """Detect objects/scenes/concepts. Returns list of label dicts."""
    return client.detect_labels(
        Image=_image(image_bytes, bucket, key),
        MaxLabels=max_labels,
        MinConfidence=min_confidence).get("Labels", [])


def rekc_detect_text(client, image_bytes=None, bucket=None, key=None):
    """OCR-lite: detect text (words/lines) in an image."""
    return client.detect_text(
        Image=_image(image_bytes, bucket, key)).get("TextDetections", [])


def rekc_detect_faces(client, image_bytes=None, bucket=None, key=None,
                      attributes="ALL"):
    """Detect faces + attributes (age, emotions, etc). attributes: 'DEFAULT'|'ALL'."""
    return client.detect_faces(
        Image=_image(image_bytes, bucket, key),
        Attributes=[attributes]).get("FaceDetails", [])


def rekc_detect_moderation_labels(client, image_bytes=None, bucket=None, key=None,
                                  min_confidence=60.0):
    """Detect unsafe/explicit content."""
    return client.detect_moderation_labels(
        Image=_image(image_bytes, bucket, key),
        MinConfidence=min_confidence).get("ModerationLabels", [])


def rekc_recognize_celebrities(client, image_bytes=None, bucket=None, key=None):
    return client.recognize_celebrities(
        Image=_image(image_bytes, bucket, key)).get("CelebrityFaces", [])


# ---- Face comparison ----
def rekc_compare_faces(client, source_bytes=None, target_bytes=None,
                       source_bucket=None, source_key=None,
                       target_bucket=None, target_key=None, similarity=80.0):
    """Compare a face in the source image against faces in the target image."""
    return client.compare_faces(
        SourceImage=_image(source_bytes, source_bucket, source_key),
        TargetImage=_image(target_bytes, target_bucket, target_key),
        SimilarityThreshold=similarity).get("FaceMatches", [])


# ---- Face collections (server-side face index for search) ----
def rekc_create_collection(client, collection_id):
    return client.create_collection(CollectionId=collection_id)


def rekc_delete_collection(client, collection_id):
    return client.delete_collection(CollectionId=collection_id)


def rekc_list_collections(client):
    return client.list_collections().get("CollectionIds", [])


def rekc_index_faces(client, collection_id, image_bytes=None, bucket=None, key=None,
                     external_id=None, max_faces=1):
    """Add faces from an image into a collection (for later search)."""
    kwargs = {
        "CollectionId": collection_id,
        "Image": _image(image_bytes, bucket, key),
        "MaxFaces": max_faces,
        "DetectionAttributes": ["DEFAULT"],
    }
    if external_id:
        kwargs["ExternalImageId"] = external_id
    return client.index_faces(**kwargs).get("FaceRecords", [])


def rekc_search_faces_by_image(client, collection_id, image_bytes=None,
                               bucket=None, key=None, threshold=80.0, max_faces=5):
    """Search a collection for faces matching the face in the given image."""
    return client.search_faces_by_image(
        CollectionId=collection_id,
        Image=_image(image_bytes, bucket, key),
        FaceMatchThreshold=threshold,
        MaxFaces=max_faces).get("FaceMatches", [])


def rekc_list_faces(client, collection_id):
    return client.list_faces(CollectionId=collection_id).get("Faces", [])


def rekc_delete_faces(client, collection_id, face_ids):
    return client.delete_faces(CollectionId=collection_id, FaceIds=face_ids)
