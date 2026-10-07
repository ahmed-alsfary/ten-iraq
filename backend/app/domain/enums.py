import enum


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    DATA_MANAGER = "data_manager"
    AI_REVIEWER = "ai_reviewer"
    SUPPORT = "support"
    COMPANY_OWNER = "company_owner"
    COMPANY_MANAGER = "company_manager"
    COMPANY_USER = "company_user"
    CUSTOMER = "customer"


class TenderStatus(str, enum.Enum):
    DRAFT = "draft"
    DISCOVERED = "discovered"
    PROCESSING = "processing"
    PUBLISHED = "published"
    CLOSING_SOON = "closing_soon"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class SourceType(str, enum.Enum):
    WEBSITE = "website"
    TENDER_PORTAL = "tender_portal"
    PDF_REPOSITORY = "pdf_repository"
    RSS = "rss"
    API = "api"
    SOCIAL_MEDIA = "social_media"


class CrawlerType(str, enum.Enum):
    GENERIC_HTML = "generic_html"
    PDF_DISCOVERY = "pdf_discovery"
    SITEMAP = "sitemap"
    RSS = "rss"
    API = "api"
    CUSTOM_ADAPTER = "custom_adapter"
    ITP_IQ = "itp_iq"
    MOHESR = "mohesr"
    BAGHDAD = "baghdad"
    SRC = "src"
    MINISTRY_CMS = "ministry_cms"
    SOMO = "somo"
    KIMADIA = "kimadia"
