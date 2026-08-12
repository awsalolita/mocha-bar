"""
CloudWatch unit functions.

- CloudWatch metrics/alarms: client = boto3.client("cloudwatch")
                             resource = boto3.resource("cloudwatch")
- CloudWatch Logs:           logs_client = boto3.client("logs")   (CLIENT ONLY)
- EventBridge (CW Events):   events_client = boto3.client("events")  (CLIENT ONLY)
"""
import time
import boto3


def get_client(region=None):
    return boto3.client("cloudwatch", region_name=region)


def get_resource(region=None):
    return boto3.resource("cloudwatch", region_name=region)


def get_logs_client(region=None):
    return boto3.client("logs", region_name=region)


def get_events_client(region=None):
    return boto3.client("events", region_name=region)


# ============================================================
# ------------- CLOUDWATCH METRICS / ALARMS (CLIENT) ---------
# ============================================================

def cwc_put_metric(client, namespace, name, value, unit="None", dimensions=None):
    metric = {"MetricName": name, "Value": value, "Unit": unit}
    if dimensions:
        metric["Dimensions"] = [{"Name": k, "Value": v}
                                for k, v in dimensions.items()]
    return client.put_metric_data(Namespace=namespace, MetricData=[metric])


def cwc_get_metric_statistics(client, namespace, name, start, end, period=300,
                              stats=("Average",), dimensions=None):
    kwargs = {"Namespace": namespace, "MetricName": name,
              "StartTime": start, "EndTime": end,
              "Period": period, "Statistics": list(stats)}
    if dimensions:
        kwargs["Dimensions"] = [{"Name": k, "Value": v}
                                for k, v in dimensions.items()]
    return client.get_metric_statistics(**kwargs)


def cwc_list_metrics(client, namespace=None):
    kwargs = {"Namespace": namespace} if namespace else {}
    return client.list_metrics(**kwargs).get("Metrics", [])


def cwc_put_alarm(client, name, namespace, metric_name, threshold,
                  comparison="GreaterThanThreshold", period=300,
                  eval_periods=1, stat="Average", dimensions=None,
                  alarm_actions=None):
    """comparison: GreaterThanThreshold | LessThanThreshold |
       GreaterThanOrEqualToThreshold | LessThanOrEqualToThreshold.
       alarm_actions: list of SNS topic ARNs to notify."""
    kwargs = {
        "AlarmName": name, "Namespace": namespace, "MetricName": metric_name,
        "Threshold": threshold, "ComparisonOperator": comparison,
        "Period": period, "EvaluationPeriods": eval_periods, "Statistic": stat}
    if dimensions:
        kwargs["Dimensions"] = [{"Name": k, "Value": v}
                                for k, v in dimensions.items()]
    if alarm_actions:
        kwargs["AlarmActions"] = alarm_actions
    return client.put_metric_alarm(**kwargs)


def cwc_delete_alarms(client, names):
    return client.delete_alarms(AlarmNames=names)


def cwc_describe_alarms(client):
    return client.describe_alarms().get("MetricAlarms", [])


# ---- Resource variant (metrics/alarms) ----
def cwr_get_metric(resource, namespace, name):
    return resource.Metric(namespace, name)


def cwr_put_metric_data(resource, namespace, name, value, unit="None"):
    return resource.Metric(namespace, name).put_data(
        Namespace=namespace,
        MetricData=[{"MetricName": name, "Value": value, "Unit": unit}])


def cwr_list_alarms(resource):
    return list(resource.alarms.all())


# ============================================================
# ---------------- CLOUDWATCH LOGS (CLIENT ONLY) -------------
# ============================================================

def logs_create_group(logs_client, group):
    return logs_client.create_log_group(logGroupName=group)


def logs_delete_group(logs_client, group):
    return logs_client.delete_log_group(logGroupName=group)


def logs_set_retention(logs_client, group, days=14):
    return logs_client.put_retention_policy(
        logGroupName=group, retentionInDays=days)


def logs_create_stream(logs_client, group, stream):
    return logs_client.create_log_stream(
        logGroupName=group, logStreamName=stream)


def logs_put_events(logs_client, group, stream, messages):
    """messages: list of strings. Timestamps set to now (ms)."""
    ts = int(time.time() * 1000)
    events = [{"timestamp": ts, "message": m} for m in messages]
    return logs_client.put_log_events(
        logGroupName=group, logStreamName=stream, logEvents=events)


def logs_filter_events(logs_client, group, pattern="", start=None, end=None):
    kwargs = {"logGroupName": group, "filterPattern": pattern}
    if start:
        kwargs["startTime"] = start
    if end:
        kwargs["endTime"] = end
    return logs_client.filter_log_events(**kwargs).get("events", [])


def logs_tail(logs_client, group, stream, limit=100):
    return logs_client.get_log_events(
        logGroupName=group, logStreamName=stream,
        limit=limit, startFromHead=False).get("events", [])


# ============================================================
# -------------- EVENTBRIDGE / CW EVENTS (CLIENT) -----------
# ============================================================

def events_put_rule_schedule(events_client, name, schedule_expr):
    """schedule_expr e.g. 'rate(5 minutes)' or 'cron(0 12 * * ? *)'."""
    return events_client.put_rule(
        Name=name, ScheduleExpression=schedule_expr, State="ENABLED")


def events_put_target(events_client, rule_name, target_id, target_arn):
    return events_client.put_targets(
        Rule=rule_name,
        Targets=[{"Id": target_id, "Arn": target_arn}])
