from common.constants import (
    MODERATION_STATUS_APPROVED, MODERATION_STATUS_FLAGGED, MODERATION_STATUS_BLOCKED,
    MODALITY_TEXT, MODALITY_IMAGE, MODALITY_VIDEO, MODALITY_MULTIMODAL,
    SEVERITY_LOW, SEVERITY_MEDIUM, SEVERITY_HIGH, SEVERITY_CRITICAL,
)

MODERATION_STATUS_CHOICES = [
    (MODERATION_STATUS_APPROVED, 'Approved'),
    (MODERATION_STATUS_FLAGGED,  'Flagged'),
    (MODERATION_STATUS_BLOCKED,  'Blocked'),
]

MODALITY_CHOICES = [
    (MODALITY_TEXT,       'Text'),
    (MODALITY_IMAGE,      'Image'),
    (MODALITY_VIDEO,      'Video'),
    ('audio',             'Audio'),
    (MODALITY_MULTIMODAL, 'Multimodal'),
]

SEVERITY_CHOICES = [
    (SEVERITY_LOW,      'Low'),
    (SEVERITY_MEDIUM,   'Medium'),
    (SEVERITY_HIGH,     'High'),
    (SEVERITY_CRITICAL, 'Critical'),
]

REPORT_STATUS_CHOICES = [
    ('PENDING',   'Pending'),
    ('REVIEWED',  'Reviewed'),
    ('RESOLVED',  'Resolved'),
    ('DISMISSED', 'Dismissed'),
]

CONTENT_TYPE_CHOICES = [
    ('post',    'Post'),
    ('comment', 'Comment'),
    ('profile', 'Profile'),
]
