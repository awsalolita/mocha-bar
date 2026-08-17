#!/bin/bash
set -euo pipefail
chown -R www-data:www-data /var/www/<APP> || chown -R ec2-user:ec2-user /var/www/<APP>
