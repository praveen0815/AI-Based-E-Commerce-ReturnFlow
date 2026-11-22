"""Knowledge document types and processing lifecycle."""

from enum import Enum


class KnowledgeDocumentType(str, Enum):
    RETURN_POLICY = "RETURN_POLICY"
    REFUND_POLICY = "REFUND_POLICY"
    SHIPPING_POLICY = "SHIPPING_POLICY"
    WARRANTY = "WARRANTY"
    PRODUCT_CONDITIONS = "PRODUCT_CONDITIONS"
    STORE_SOP = "STORE_SOP"
    CUSTOM = "CUSTOM"


class KnowledgeProcessingStatus(str, Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"