import os
import base64
import json
import time
import hmac
import hashlib
from datetime import datetime
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import APIRouter, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse
import oss2

load_dotenv()

router = APIRouter(prefix="/oss", tags=["OSS"])

OSS_ACCESS_KEY_ID = os.getenv("OSS_ACCESS_KEY_ID")
OSS_ACCESS_KEY_SECRET = os.getenv("OSS_ACCESS_KEY_SECRET")
OSS_ENDPOINT = os.getenv("OSS_ENDPOINT", "oss-cn-hangzhou.aliyuncs.com")
OSS_BUCKET_NAME = os.getenv("OSS_BUCKET_NAME")
OSS_EXPIRE_SECONDS = 3600

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_extension(filename: str) -> str:
    return filename.rsplit(".", 1)[1].lower() if "." in filename else ""

def get_oss_client():
    if not OSS_ACCESS_KEY_ID or not OSS_ACCESS_KEY_SECRET or not OSS_BUCKET_NAME:
        raise HTTPException(status_code=500, detail="OSS 配置未完成")
    auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
    return oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)

@router.post("/signature", summary="获取上传签名（前端直传）")
async def get_upload_signature(
    dir: str = Query(default="images/", description="存储目录"),
    expire: int = Query(default=3600, description="过期时间（秒）")
):
    if not OSS_ACCESS_KEY_ID or not OSS_ACCESS_KEY_SECRET or not OSS_BUCKET_NAME:
        raise HTTPException(status_code=500, detail="OSS 配置未完成")
    
    now = int(time.time())
    expire_time = now + expire
    
    expiration = datetime.utcfromtimestamp(expire_time).strftime('%Y-%m-%dT%H:%M:%S.000Z')
    
    conditions = [
        ["content-length-range", 0, 10 * 1024 * 1024],
        ["starts-with", "$key", dir]
    ]
    
    policy_dict = {
        "expiration": expiration,
        "conditions": conditions
    }
    
    policy = json.dumps(policy_dict).strip()
    policy_base64 = base64.b64encode(policy.encode("utf-8")).decode("utf-8")
    
    signature = base64.b64encode(
        hmac.new(
            OSS_ACCESS_KEY_SECRET.encode("utf-8"),
            policy_base64.encode("utf-8"),
            hashlib.sha1
        ).digest()
    ).decode("utf-8")
    
    host = f"https://{OSS_BUCKET_NAME}.{OSS_ENDPOINT}"
    
    return JSONResponse(content={
        "success": True,
        "access_key_id": OSS_ACCESS_KEY_ID,
        "policy": policy_base64,
        "signature": signature,
        "host": host,
        "dir": dir,
        "expire": expire_time
    })

@router.get("/presign", summary="获取预签名上传URL")
async def get_presign_url(filename: str):
    content_type_map = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp"
    }
    ext = filename.split(".")[-1].lower() if "." in filename else "jpg"
    content_type = content_type_map.get(ext, "application/octet-stream")
    
    try:
        bucket = get_oss_client()
        url = bucket.sign_url('PUT', filename, OSS_EXPIRE_SECONDS, headers={'Content-Type': content_type})
        
        return {
            "success": True,
            "uploadUrl": url,
            "contentType": content_type,
            "accessUrl": f"https://{OSS_BUCKET_NAME}.{OSS_ENDPOINT}/{filename}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成预签名URL失败: {str(e)}")

@router.post("/upload/image", summary="上传图片到阿里云 OSS")
async def upload_image(file: UploadFile = File(...)):
    if not allowed_file(file.filename):
        raise HTTPException(status_code=400, detail=f"不支持的文件类型，仅支持: {', '.join(ALLOWED_EXTENSIONS)}")
    
    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件大小超过限制（最大10MB）")
    
    try:
        bucket = get_oss_client()
        
        ext = get_file_extension(file.filename)
        date_str = datetime.now().strftime("%Y/%m/%d")
        file_name = f"{date_str}/{uuid4().hex}.{ext}"
        
        bucket.put_object(file_name, file_content)
        
        url = f"https://{OSS_BUCKET_NAME}.{OSS_ENDPOINT}/{file_name}"
        
        return JSONResponse(content={
            "success": True,
            "message": "上传成功",
            "url": url,
            "filename": file_name
        })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")

@router.delete("/delete", summary="删除 OSS 文件")
async def delete_file(file_path: str):
    try:
        bucket = get_oss_client()
        bucket.delete_object(file_path)
        
        return JSONResponse(content={
            "success": True,
            "message": "删除成功"
        })
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

@router.get("/url", summary="获取 OSS 文件访问 URL")
async def get_file_url(file_path: str):
    if not OSS_ACCESS_KEY_ID or not OSS_ACCESS_KEY_SECRET or not OSS_BUCKET_NAME:
        raise HTTPException(status_code=500, detail="OSS 配置未完成")
    
    url = f"https://{OSS_BUCKET_NAME}.{OSS_ENDPOINT}/{file_path}"
    
    return JSONResponse(content={
        "success": True,
        "url": url,
        "file_path": file_path
    })

@router.get("/info", summary="获取 OSS 文件信息")
async def get_file_info(file_path: str):
    try:
        bucket = get_oss_client()
        file_info = bucket.get_object_meta(file_path)
        
        return JSONResponse(content={
            "success": True,
            "file_path": file_path,
            "content_length": file_info.content_length,
            "last_modified": file_info.last_modified,
            "content_type": file_info.content_type
        })
    
    except oss2.exceptions.NoSuchKey:
        raise HTTPException(status_code=404, detail="文件不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文件信息失败: {str(e)}")
