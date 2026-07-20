from app.models.worker_lease import WorkerLease
from app.repositories.base import Repository

worker_lease_repository = Repository(WorkerLease)
