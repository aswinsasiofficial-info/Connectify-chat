from django.core.management.base import BaseCommand
from chat.models import Status
from django.utils import timezone

class Command(BaseCommand):
    help = 'Deletes expired statuses from the database'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        expired_statuses = Status.objects.filter(expires_at__lte=now)
        count = expired_statuses.count()
        expired_statuses.delete()
        
        self.stdout.write(self.style.SUCCESS(f'Successfully deleted {count} expired statuses.'))
