import os
import uuid

from dotenv import load_dotenv
from fastapi import APIRouter
import boto3

load_dotenv()

router = APIRouter()

# R2配置
account_id = os.getenv("R2_ACCOUNT_ID")

access_key = os.getenv("R2_ACCESS_KEY_ID")
secret_key = os.getenv("R2_SECRET_ACCESS_KEY")

bucket = os.getenv("R2_BUCKET")
public_domain = os.getenv("R2_PUBLIC_DOMAIN")

# 创建S3客户端
s3_client = boto3.client(
    "s3",
    endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    region_name="auto",
)

@router.get("/file/presign")
def get_presigned_url(filename: str):
    """
    获取预签名上传地址
    """

    # 获取后缀
    ext = filename.split(".")[-1].lower() if "." in filename else "jpg"

    # 新文件名
    uid = str(uuid.uuid4())
    new_filename = f"{uid}.{ext}"

    # 生成PUT预签名URL
    upload_url = s3_client.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": bucket,
            "Key": new_filename,
        },
        ExpiresIn=120,
    )

    # 文件访问地址
    access_url = f"{public_domain}/{new_filename}"

    return {
        "uploadUrl": upload_url,
        "accessUrl": access_url,
        "filename": new_filename,
    }