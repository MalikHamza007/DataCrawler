from app.models.collection_job import CollectionJob, CollectionLog
from app.repositories.base import Repository

collection_job_repository = Repository(CollectionJob)
collection_log_repository = Repository(CollectionLog)
