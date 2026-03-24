from django.core.management.base import BaseCommand
from django.utils import timezone
from appointments.models import Appointment

class Command(BaseCommand):
    help = 'Automatically cancels pending appointments that have passed their scheduled date without doctor response.'

    def handle(self, *args, **options):
        # Find all pending appointments that are older than today's date
        # (meaning the scheduled date has already passed)
        now = timezone.now()
        
        # We target pending appointments where the date_time is in the past
        # The user's request: "if a patient books an appointment 2026-03-22 and doctor cannot response these date 
        # and the another day appointment should be cancelled automatically"
        # This implies that on 2026-03-23, the appointment for 2026-03-22 should be cancelled.
        
        expired_appointments = Appointment.objects.filter(
            status='pending',
            date_time__lt=now
        )
        
        count = expired_appointments.count()
        
        for appointment in expired_appointments:
            appointment.status = 'cancelled'
            cancellation_note = f"Automatically cancelled on {now.strftime('%Y-%m-%d')} because the doctor did not respond by the scheduled date ({appointment.date_time.strftime('%Y-%m-%d')})."
            
            if appointment.notes:
                appointment.notes = f"{cancellation_note}\n\n{appointment.notes}"
            else:
                appointment.notes = cancellation_note
            
            appointment.save()
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully cancelled appointment {appointment.id} for patient {appointment.patient.get_full_name()}')
            )

        if count == 0:
            self.stdout.write(self.style.NOTICE('No expired pending appointments found.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Successfully cancelled {count} expired pending appointments.'))
