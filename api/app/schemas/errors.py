"""Error response schemas."""

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str = Field(..., examples=["INVALID_ADDRESS"])
    message: str = Field(..., examples=["指定された住所を解析できませんでした"])
    field: str | None = Field(None, examples=["address"])


class ErrorResponse(BaseModel):
    error: ErrorDetail


# ---------- Known error codes ----------

INVALID_REQUEST = ErrorDetail(code="INVALID_REQUEST", message="リクエストの形式が不正です")
INVALID_ADDRESS = ErrorDetail(code="INVALID_ADDRESS", message="指定された住所を解析できませんでした")
INVALID_COORDINATES = ErrorDetail(
    code="INVALID_COORDINATES",
    message="緯度経度が日本国内の範囲にありません",
)
MISSING_LOCATION = ErrorDetail(
    code="MISSING_LOCATION",
    message="address または lat/lng のいずれかを指定してください",
)
UNAUTHORIZED = ErrorDetail(code="UNAUTHORIZED", message="API Key が無効です")
FORBIDDEN = ErrorDetail(code="FORBIDDEN", message="このリソースへのアクセス権がありません")
NOT_FOUND = ErrorDetail(code="NOT_FOUND", message="指定された住所のデータが見つかりません")
RATE_LIMITED = ErrorDetail(code="RATE_LIMITED", message="レートリミットを超過しました")
QUOTA_EXCEEDED = ErrorDetail(code="QUOTA_EXCEEDED", message="月間リクエスト上限を超過しました")
INTERNAL_ERROR = ErrorDetail(code="INTERNAL_ERROR", message="サーバー内部エラーが発生しました")
SERVICE_UNAVAILABLE = ErrorDetail(
    code="SERVICE_UNAVAILABLE", message="サービスが一時的に利用できません"
)
