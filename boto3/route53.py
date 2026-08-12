"""
Route 53 unit functions — CLIENT only.

client = boto3.client("route53")   # Route 53 is global

Covers: hosted zones + record sets (UPSERT/DELETE) + alias records.
"""
import time
import boto3


def get_client(region=None):
    return boto3.client("route53", region_name=region)


# ---- Hosted zones ----
def r53_create_hosted_zone(client, name, private=False, vpc_id=None, region=None):
    """name e.g. 'example.com.' (trailing dot optional)."""
    kwargs = {"Name": name, "CallerReference": str(time.time())}
    if private:
        kwargs["HostedZoneConfig"] = {"PrivateZone": True}
        kwargs["VPC"] = {"VPCRegion": region, "VPCId": vpc_id}
    return client.create_hosted_zone(**kwargs)


def r53_list_hosted_zones(client):
    return client.list_hosted_zones()["HostedZones"]


def r53_delete_hosted_zone(client, zone_id):
    return client.delete_hosted_zone(Id=zone_id)


def r53_get_zone_id_by_name(client, name):
    if not name.endswith("."):
        name += "."
    for z in client.list_hosted_zones()["HostedZones"]:
        if z["Name"] == name:
            return z["Id"].split("/")[-1]
    return None


# ---- Record sets ----
def r53_upsert_record(client, zone_id, name, rtype, value, ttl=300):
    """Create or update a simple record. value: single str or list of str.
    rtype: 'A' | 'AAAA' | 'CNAME' | 'TXT' | 'MX' | ..."""
    values = value if isinstance(value, list) else [value]
    return client.change_resource_record_sets(
        HostedZoneId=zone_id,
        ChangeBatch={"Changes": [{
            "Action": "UPSERT",
            "ResourceRecordSet": {
                "Name": name, "Type": rtype, "TTL": ttl,
                "ResourceRecords": [{"Value": v} for v in values]}}]})


def r53_delete_record(client, zone_id, name, rtype, value, ttl=300):
    values = value if isinstance(value, list) else [value]
    return client.change_resource_record_sets(
        HostedZoneId=zone_id,
        ChangeBatch={"Changes": [{
            "Action": "DELETE",
            "ResourceRecordSet": {
                "Name": name, "Type": rtype, "TTL": ttl,
                "ResourceRecords": [{"Value": v} for v in values]}}]})


def r53_upsert_alias(client, zone_id, name, target_dns, target_zone_id,
                     rtype="A", eval_health=False):
    """Alias record (e.g. to an ALB/CloudFront). target_zone_id is the
    canonical hosted zone ID of the AWS resource."""
    return client.change_resource_record_sets(
        HostedZoneId=zone_id,
        ChangeBatch={"Changes": [{
            "Action": "UPSERT",
            "ResourceRecordSet": {
                "Name": name, "Type": rtype,
                "AliasTarget": {
                    "HostedZoneId": target_zone_id,
                    "DNSName": target_dns,
                    "EvaluateTargetHealth": eval_health}}}]})


def r53_list_records(client, zone_id):
    return client.list_resource_record_sets(
        HostedZoneId=zone_id)["ResourceRecordSets"]
