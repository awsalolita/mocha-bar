sudo yum update
sudo yum install -y nfs-utils

EFS_ID="fs-xxxxxx"
MOUNT_POINT="/mnt/efs"

sudo mkdir -p $MOUNT_POINT

sudo mount -t nfs -o nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport $EFS_ID:/ $MOUNT_POINT
sudo mount -t nfs -o nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport $EFS_ID:/ $MOUNT_POINT