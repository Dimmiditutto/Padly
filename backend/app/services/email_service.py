from __future__ import annotations

import logging
import smtplib
from datetime import UTC, datetime
from email.message import EmailMessage

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Booking, EmailNotificationLog

logger = logging.getLogger(__name__)


class EmailService:
    def _deliver(self, to_email: str, subject: str, html: str) -> tuple[str, str | None]:
        if not settings.smtp_host or not settings.smtp_username or not settings.smtp_password:
            logger.info('SMTP non configurato: email simulata a %s con oggetto %s', to_email, subject)
            return 'SKIPPED', 'SMTP non configurato'

        message = EmailMessage()
        message['From'] = settings.smtp_from
        message['To'] = to_email
        message['Subject'] = subject
        message.set_content('Apri questa email in formato HTML per visualizzare il riepilogo.')
        message.add_alternative(html, subtype='html')

        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
                smtp.starttls()
                smtp.login(settings.smtp_username, settings.smtp_password)
                smtp.send_message(message)
            return 'SENT', None
        except Exception as exc:  # pragma: no cover
            logger.exception('Invio email fallito')
            return 'FAILED', str(exc)

    def send(self, db: Session, *, booking: Booking | None, to_email: str, template: str, subject: str, html: str) -> None:
        status_value, error = self._deliver(to_email, subject, html)
        db.add(
            EmailNotificationLog(
                booking_id=booking.id if booking else None,
                recipient=to_email,
                template=template,
                status=status_value,
                error=error,
                sent_at=datetime.now(UTC) if status_value == 'SENT' else None,
            )
        )

    def booking_confirmation(self, db: Session, booking: Booking) -> None:
        customer = booking.customer
        if not customer:
            return
        html = f"""
        <div style='font-family:Arial,sans-serif;max-width:640px;margin:auto;padding:24px;color:#0f172a'>
          <h2 style='margin-bottom:8px'>Prenotazione confermata ✅</h2>
          <p>Ciao {customer.first_name}, la tua prenotazione è confermata.</p>
          <p><strong>Codice:</strong> {booking.public_reference}<br/>
             <strong>Data:</strong> {booking.booking_date_local}<br/>
             <strong>Durata:</strong> {booking.duration_minutes} minuti<br/>
             <strong>Caparra ricevuta:</strong> €{booking.deposit_amount}</p>
          <p>Il saldo residuo verrà pagato direttamente al campo.</p>
        </div>
        """
        self.send(db, booking=booking, to_email=customer.email, template='booking_confirmation', subject='Prenotazione confermata', html=html)

    def booking_cancelled(self, db: Session, booking: Booking) -> None:
        customer = booking.customer
        if not customer:
            return
        html = f"<div style='font-family:Arial,sans-serif;padding:24px'><h2>Prenotazione annullata</h2><p>La prenotazione {booking.public_reference} è stata annullata.</p></div>"
        self.send(db, booking=booking, to_email=customer.email, template='booking_cancelled', subject='Prenotazione annullata', html=html)

    def booking_expired(self, db: Session, booking: Booking) -> None:
        customer = booking.customer
        if not customer:
            return
        html = f"<div style='font-family:Arial,sans-serif;padding:24px'><h2>Pagamento non completato</h2><p>La tua richiesta {booking.public_reference} è scaduta. Puoi effettuare una nuova prenotazione quando vuoi.</p></div>"
        self.send(db, booking=booking, to_email=customer.email, template='booking_expired', subject='Prenotazione scaduta', html=html)

    def reminder(self, db: Session, booking: Booking) -> None:
        customer = booking.customer
        if not customer:
            return
        html = f"<div style='font-family:Arial,sans-serif;padding:24px'><h2>Promemoria prenotazione</h2><p>Ti aspettiamo presto per la prenotazione {booking.public_reference}.</p></div>"
        self.send(db, booking=booking, to_email=customer.email, template='booking_reminder', subject='Promemoria prenotazione', html=html)

    def admin_notification(self, db: Session, booking: Booking) -> None:
        html = f"<div style='font-family:Arial,sans-serif;padding:24px'><h2>Nuova prenotazione</h2><p>Ricevuta prenotazione {booking.public_reference}.</p></div>"
        self.send(db, booking=booking, to_email=str(settings.admin_email), template='admin_new_booking', subject='Nuova prenotazione ricevuta', html=html)


email_service = EmailService()
