from __future__ import annotations

from app.models.social_capture import SocialCapture
from app.repositories.base import Repository

social_capture_repository = Repository(SocialCapture)

