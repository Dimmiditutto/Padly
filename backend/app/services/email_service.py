from __future__ import annotations

import logging
import smtplib
from datetime import UTC, datetime
from decimal import Decimal
from email.message import EmailMessage
from html import escape
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Admin, Booking, BookingSource, Club, EmailNotificationLog, PaymentProvider, PaymentStatus, PlayAccessPurpose
from app.services.settings_service import get_booking_rules
from app.services.tenant_service import build_club_app_url, get_default_club_id

logger = logging.getLogger(__name__)
OPTIONAL_EMAIL_ENVS = {'development', 'test'}


class EmailService:
    def _resolve_timezone(self, booking: Booking | None = None) -> ZoneInfo:
        timezone_name = settings.timezone
        if booking and booking.club and booking.club.timezone:
            timezone_name = booking.club.timezone
        return ZoneInfo(timezone_name)

    def _localize(self, value: datetime, booking: Booking | None = None) -> datetime:
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(self._resolve_timezone(booking))

    def _format_currency(self, value: Decimal | int | float) -> str:
        return f"{Decimal(value):.2f}".replace('.', ',')

    def _provider_label(self, booking: Booking) -> str:
        labels = {
            'STRIPE': 'Stripe',
            'PAYPAL': 'PayPal',
            'NONE': 'Nessuno',
        }
        return labels.get(booking.payment_provider.value, booking.payment_provider.value)

    def _base_booking_details(self, booking: Booking) -> list[tuple[str, str]]:
        start_local = self._localize(booking.start_at, booking)
        end_local = self._localize(booking.end_at, booking)
        return [
            ('Codice prenotazione', booking.public_reference),
            ('Data', start_local.strftime('%d/%m/%Y')),
            ('Orario', f"{start_local.strftime('%H:%M')} - {end_local.strftime('%H:%M')}"),
            ('Durata', f'{booking.duration_minutes} minuti'),
        ]

    def _payment_booking_details(self, booking: Booking) -> list[tuple[str, str]]:
        return [
            ('Caparra', f"EUR {self._format_currency(booking.deposit_amount)}"),
            ('Saldo residuo', 'Da saldare al campo'),
            ('Provider caparra', self._provider_label(booking)),
        ]

    def _booking_details(self, booking: Booking, *, include_payment_details: bool = True) -> list[tuple[str, str]]:
        details = self._base_booking_details(booking)
        if include_payment_details:
            details += self._payment_booking_details(booking)
        return details

    def _has_online_payment_context(self, booking: Booking) -> bool:
        return (
            booking.source == BookingSource.PUBLIC
            and booking.payment_provider in {PaymentProvider.STRIPE, PaymentProvider.PAYPAL}
            and booking.payment_status == PaymentStatus.PAID
        )

    def _public_cancellation_url(self, booking: Booking) -> str | None:
        if not booking.cancel_token:
            return None
        return build_club_app_url(booking.club, '/booking/cancel', query_params={'token': booking.cancel_token})

    def _refund_notes(self, booking: Booking, *, cancellation_window_hours: int) -> list[str]:
        if not self._has_online_payment_context(booking):
            return []

        latest_payment = max(booking.payments, key=lambda payment: payment.created_at, default=None)
        if not latest_payment or not latest_payment.refund_status:
            return ['Il circolo verificherà separatamente l\'eventuale rimborso della caparra online.']
        if latest_payment.refund_status == 'NOT_REQUIRED':
            return [f'La caparra online non è rimborsabile per annullamenti effettuati nelle ultime {cancellation_window_hours} ore.']
        if latest_payment.refund_status == 'SUCCEEDED':
            return ['La caparra online è stata rimborsata automaticamente.']
        if latest_payment.refund_status == 'PENDING':
            return ['Il rimborso automatico della caparra è stato avviato e verrà finalizzato dal provider.']
        if latest_payment.refund_status == 'FAILED':
            return ['Il rimborso automatico non è andato a buon fine: il circolo verificherà manualmente la situazione.']
        return []

    def _render_email(
        self,
        *,
        title: str,
        intro: str,
        booking: Booking,
        details: list[tuple[str, str]] | None = None,
        notes: list[str] | None = None,
        accent: str = '#0f766e',
    ) -> str:
        detail_rows = ''.join(
            f"""
            <tr>
              <td style='padding:10px 0;border-bottom:1px solid #e5e7eb;color:#475569;font-size:14px'>{escape(label)}</td>
              <td style='padding:10px 0;border-bottom:1px solid #e5e7eb;color:#0f172a;font-size:14px;text-align:right;font-weight:600'>{escape(value)}</td>
            </tr>
            """
            for label, value in (details or self._booking_details(booking))
        )
        note_rows = ''.join(
            f"<li style='margin-bottom:8px;color:#334155;line-height:1.6'>{escape(note)}</li>"
            for note in (notes or [])
        )
        notes_block = (
            f"<ul style='margin:0;padding-left:18px'>{note_rows}</ul>"
            if note_rows
            else "<p style='margin:0;color:#334155;line-height:1.6'>Per qualsiasi necessità puoi rispondere a questa email o contattare direttamente il circolo.</p>"
        )
        return f"""
        <div style='background:#f8fafc;padding:32px 16px;font-family:Arial,sans-serif;color:#0f172a'>
          <div style='max-width:640px;margin:0 auto;background:#ffffff;border:1px solid #e2e8f0;border-radius:18px;overflow:hidden'>
            <div style='padding:28px 28px 22px;background:{accent}'>
              <p style='margin:0 0 8px 0;color:#ccfbf1;font-size:12px;letter-spacing:0.08em;text-transform:uppercase'>PadelBooking</p>
              <h1 style='margin:0;color:#ffffff;font-size:28px;line-height:1.2'>{escape(title)}</h1>
            </div>
            <div style='padding:28px'>
              <p style='margin:0 0 20px 0;color:#334155;font-size:16px;line-height:1.7'>{escape(intro)}</p>
              <div style='padding:20px;border:1px solid #e2e8f0;border-radius:14px;background:#f8fafc'>
                <table style='width:100%;border-collapse:collapse'>
                  {detail_rows}
                </table>
              </div>
              <div style='margin-top:20px;padding:20px;border-radius:14px;background:#f8fafc;border:1px solid #e2e8f0'>
                {notes_block}
              </div>
            </div>
          </div>
        </div>
        """

    def _deliver(self, to_email: str, subject: str, html: str) -> tuple[str, str | None]:
        if not settings.smtp_host or not settings.smtp_username or not settings.smtp_password:
            if settings.app_env.lower() in OPTIONAL_EMAIL_ENVS:
                logger.info('SMTP non configurato in %s: email simulata a %s con oggetto %s', settings.app_env, to_email, subject)
                return 'SKIPPED', 'SMTP non configurato'
            logger.error('SMTP non configurato in %s: invio email impossibile verso %s con oggetto %s', settings.app_env, to_email, subject)
            return 'FAILED', 'SMTP non configurato'

        message = EmailMessage()
        message['From'] = settings.smtp_from
        message['To'] = to_email
        message['Subject'] = subject
        message.set_content('Apri questa email in formato HTML per visualizzare il riepilogo.')
        message.add_alternative(html, subtype='html')

        use_ssl = settings.smtp_use_ssl or settings.smtp_port == 465

        try:
            smtp_client_factory = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
            with smtp_client_factory(settings.smtp_host, settings.smtp_port) as smtp:
                if not use_ssl:
                    smtp.starttls()
                smtp.login(settings.smtp_username, settings.smtp_password)
                smtp.send_message(message)
            return 'SENT', None
        except Exception as exc:  # pragma: no cover
            logger.exception('Invio email fallito')
            return 'FAILED', str(exc)

    def send(
        self,
        db: Session,
        *,
        booking: Booking | None,
        to_email: str,
        template: str,
        subject: str,
        html: str,
        club_id: str | None = None,
    ) -> str:
        status_value, error = self._deliver(to_email, subject, html)
        db.add(
            EmailNotificationLog(
                club_id=booking.club_id if booking else (club_id or get_default_club_id(db)),
                booking_id=booking.id if booking else None,
                recipient=to_email,
                template=template,
                status=status_value,
                error=error,
                sent_at=datetime.now(UTC) if status_value == 'SENT' else None,
            )
        )
        return status_value

    def booking_confirmation(self, db: Session, booking: Booking) -> str:
        customer = booking.customer
        if not customer:
            return 'SKIPPED'
        booking_rules = get_booking_rules(db, club_id=booking.club_id)
        cancellation_window_hours = booking_rules['cancellation_window_hours']
        cancellation_url = self._public_cancellation_url(booking)
        notes = [
            "Presentati al campo con qualche minuto di anticipo rispetto all'orario prenotato.",
            'Il saldo residuo verrà gestito direttamente al campo secondo il listino del circolo.',
            'Conserva il codice prenotazione per eventuali richieste di assistenza.',
        ]
        if cancellation_url:
            notes.append(f'Per annullare in autonomia usa questo link: {cancellation_url}')
            notes.append(
                f'Se hai già pagato la caparra online, il rimborso viene avviato automaticamente solo se la cancellazione avviene prima delle ultime {cancellation_window_hours} ore dell\'orario prenotato.'
            )
        html = self._render_email(
            title='Prenotazione confermata e caparra ricevuta',
            intro=f"Ciao {customer.first_name}, la tua prenotazione è confermata e la caparra è stata registrata con successo.",
            booking=booking,
            notes=notes,
            accent='#0f766e',
        )
        return self.send(
            db,
            booking=booking,
            to_email=customer.email,
            template='booking_confirmation',
            subject='Prenotazione confermata e caparra ricevuta',
            html=html,
        )

    def booking_cancelled(self, db: Session, booking: Booking) -> str:
        customer = booking.customer
        if not customer:
            return 'SKIPPED'
        booking_rules = get_booking_rules(db, club_id=booking.club_id)
        notes = [
            'Lo slot torna disponibile per nuove prenotazioni.',
            "Se l'annullamento non era previsto, contatta il circolo indicando il codice prenotazione.",
        ]
        notes.extend(self._refund_notes(booking, cancellation_window_hours=booking_rules['cancellation_window_hours']))
        html = self._render_email(
            title='Prenotazione annullata',
            intro=f"Ciao {customer.first_name}, la prenotazione {booking.public_reference} è stata annullata.",
            booking=booking,
            notes=notes,
            accent='#b45309',
        )
        return self.send(
            db,
            booking=booking,
            to_email=customer.email,
            template='booking_cancelled',
            subject='Prenotazione annullata',
            html=html,
        )

    def booking_expired(self, db: Session, booking: Booking) -> str:
        customer = booking.customer
        if not customer:
            return 'SKIPPED'
        html = self._render_email(
            title='Prenotazione scaduta',
            intro=f"Ciao {customer.first_name}, il pagamento della caparra per la prenotazione {booking.public_reference} non è stato completato nei tempi previsti.",
            booking=booking,
            notes=[
                'Lo slot e tornato disponibile automaticamente.',
                'Se vuoi ancora giocare, puoi creare una nuova prenotazione dal sito.',
            ],
            accent='#b91c1c',
        )
        return self.send(
            db,
            booking=booking,
            to_email=customer.email,
            template='booking_expired',
            subject='Prenotazione scaduta',
            html=html,
        )

    def reminder(self, db: Session, booking: Booking) -> str:
        customer = booking.customer
        if not customer:
            return 'SKIPPED'
        has_online_payment = self._has_online_payment_context(booking)
        reminder_intro = f"Ciao {customer.first_name}, ti ricordiamo la tua prenotazione imminente {booking.public_reference}."
        reminder_notes = [
            'Controlla con anticipo di avere tutto il necessario per il gioco.',
        ]
        if has_online_payment:
            reminder_notes.append('Il saldo residuo viene gestito direttamente al campo.')
        else:
            reminder_intro = f"Ciao {customer.first_name}, ti ricordiamo la tua prenotazione confermata {booking.public_reference}, registrata dal circolo o dal sistema interno."
            reminder_notes.append('Questa comunicazione non implica una caparra online già incassata.')
        html = self._render_email(
            title='Promemoria prenotazione',
            intro=reminder_intro,
            booking=booking,
            details=self._booking_details(booking, include_payment_details=has_online_payment),
            notes=reminder_notes,
            accent='#1d4ed8',
        )
        return self.send(
            db,
            booking=booking,
            to_email=customer.email,
            template='booking_reminder',
            subject='Promemoria prenotazione',
            html=html,
        )

    def admin_notification(self, db: Session, booking: Booking) -> str:
        customer_name = booking.customer_name or 'Cliente non associato'
        customer_email = booking.customer_email or 'Non disponibile'
        customer_phone = booking.customer_phone or 'Non disponibile'
        recipient = settings.admin_email
        if booking.club and booking.club.notification_email:
            recipient = booking.club.notification_email
        html = self._render_email(
            title='Nuova prenotazione ricevuta',
            intro='Una prenotazione è stata confermata con caparra registrata. Di seguito il riepilogo operativo.',
            booking=booking,
            details=self._booking_details(booking)
            + [
                ('Cliente', customer_name),
                ('Email cliente', customer_email),
                ('Telefono cliente', customer_phone),
            ],
            notes=[
                'Verifica eventuali note lasciate dal cliente direttamente nell area admin.',
                'Il saldo residuo resta da riscuotere al campo.',
            ],
            accent='#111827',
        )
        return self.send(
            db,
            booking=booking,
            to_email=str(recipient),
            template='admin_new_booking',
            subject='Nuova prenotazione ricevuta',
            html=html,
        )

    def admin_password_reset(self, db: Session, admin: Admin, reset_url: str) -> str:
        html = f"""
        <div style='background:#f8fafc;padding:32px 16px;font-family:Arial,sans-serif;color:#0f172a'>
            <div style='max-width:640px;margin:0 auto;background:#ffffff;border:1px solid #e2e8f0;border-radius:18px;overflow:hidden'>
                <div style='padding:28px 28px 22px;background:#111827'>
                    <p style='margin:0 0 8px 0;color:#bfdbfe;font-size:12px;letter-spacing:0.08em;text-transform:uppercase'>PadelBooking</p>
                    <h1 style='margin:0;color:#ffffff;font-size:28px;line-height:1.2'>Reset password admin</h1>
                </div>
                <div style='padding:28px'>
                    <p style='margin:0 0 20px 0;color:#334155;font-size:16px;line-height:1.7'>Ciao {escape(admin.full_name)}, abbiamo ricevuto una richiesta di reimpostazione password per l'area admin.</p>
                    <p style='margin:0 0 20px 0;color:#334155;font-size:16px;line-height:1.7'>Questo link è valido per 30 minuti e diventa inutilizzabile dopo un cambio password.</p>
                    <div style='margin:24px 0'>
                        <a href='{escape(reset_url, quote=True)}' style='display:inline-block;padding:14px 20px;border-radius:14px;background:#0f172a;color:#ffffff;text-decoration:none;font-weight:600'>Reimposta password</a>
                    </div>
                    <p style='margin:0;color:#475569;font-size:14px;line-height:1.7'>Se non hai richiesto tu il reset, puoi ignorare questa email.</p>
                </div>
            </div>
        </div>
        """
        return self.send(
            db,
            booking=None,
            to_email=admin.email,
            template='admin_password_reset',
            subject='Reset password area admin',
            html=html,
            club_id=admin.club_id,
        )

    def play_access_otp(
        self,
        db: Session,
        *,
        club: Club,
        to_email: str,
        otp_code: str,
        expires_at: datetime,
        purpose: PlayAccessPurpose,
    ) -> str:
        localized_expiry = self._localize(expires_at)
        purpose_labels = {
            PlayAccessPurpose.INVITE: 'Completare il tuo invito community',
            PlayAccessPurpose.GROUP: 'Entrare nella community dal link condiviso',
            PlayAccessPurpose.DIRECT: 'Entrare o rientrare nella community',
            PlayAccessPurpose.RECOVERY: 'Recuperare il tuo accesso community',
        }
        intro = purpose_labels.get(purpose, 'Entrare o rientrare nella community')
        html = f"""
        <div style='background:#f8fafc;padding:32px 16px;font-family:Arial,sans-serif;color:#0f172a'>
            <div style='max-width:640px;margin:0 auto;background:#ffffff;border:1px solid #e2e8f0;border-radius:18px;overflow:hidden'>
                <div style='padding:28px 28px 22px;background:#0f172a'>
                    <p style='margin:0 0 8px 0;color:#bfdbfe;font-size:12px;letter-spacing:0.08em;text-transform:uppercase'>{escape(club.public_name)}</p>
                    <h1 style='margin:0;color:#ffffff;font-size:28px;line-height:1.2'>Codice di accesso community</h1>
                </div>
                <div style='padding:28px'>
                    <p style='margin:0 0 16px 0;color:#334155;font-size:16px;line-height:1.7'>{escape(intro)} su {escape(club.public_name)}.</p>
                    <p style='margin:0 0 24px 0;color:#334155;font-size:16px;line-height:1.7'>Inserisci questo codice nella schermata di accesso. Il codice resta valido fino alle {escape(localized_expiry.strftime('%H:%M'))}.</p>
                    <div style='margin:24px 0;padding:20px;border-radius:16px;background:#f8fafc;border:1px solid #e2e8f0;text-align:center'>
                        <p style='margin:0 0 10px 0;color:#64748b;font-size:13px;letter-spacing:0.08em;text-transform:uppercase'>Codice OTP</p>
                        <p style='margin:0;color:#0f172a;font-size:36px;font-weight:700;letter-spacing:0.24em'>{escape(otp_code)}</p>
                    </div>
                    <p style='margin:0;color:#475569;font-size:14px;line-height:1.7'>Se non hai richiesto tu questo accesso, puoi ignorare questa email.</p>
                </div>
            </div>
        </div>
        """
        return self.send(
            db,
            booking=None,
            to_email=to_email,
            template='play_access_otp',
            subject=f'Codice accesso community {club.public_name}',
            html=html,
            club_id=club.id,
        )


email_service = EmailService()
