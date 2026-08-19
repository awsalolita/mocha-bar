MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="BOUNDARY"

--BOUNDARY
Content-Type: text/x-shellscript; charset="us-ascii"

#!/bin/bash
set -ex
/etc/eks/bootstrap.sh unicorn-cluster \
  --use-max-pods false \
  --kubelet-extra-args '--max-pods=110'

--BOUNDARY--