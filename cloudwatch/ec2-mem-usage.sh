sudo yum install amazon-cloudwatch-agent
sudo systemctl enable amazon-cloudwatch-agent.service


sudo cat /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.d/file_config.json <<'EOF'
{
  "agent": {
    "metrics_collection_interval": 60,
    "debug": false,
    "run_as_user": "cwagent"
  },
  "metrics": {
    "append_dimensions": {
      "InstanceId": "${aws:InstanceId}"
    },
    "aggregation_dimensions": [
      [
        "InstanceId"
      ]
    ],
    "metrics_collected": {
      "mem": {
        "measurement": [
          "mem_used_percent"
        ]
      },
      "disk": {
        "measurement": [
          "disk_used_percent"
        ],
        "resources": [
          "/"
        ],
        "ignore_file_system_types": [
          "sysfs",
          "devtmpfs",
          "tmpfs"
        ]
      }
    }
  }
}

EOF

sudo systemctl daemon-reload
sudo systemctl restart amazon-cloudwatch-agent.service