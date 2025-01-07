from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from datetime import timedelta
import icalendar
import pytz
import uuid

class CalendarService:
    @staticmethod
    def create_calendar_event(translation):
        """Create an iCalendar event from translation data"""
        cal = icalendar.Calendar()
        cal.add('prodid', '-//Translation Platform//Calendar Events//EN')
        cal.add('version', '2.0')
        cal.add('method', 'REQUEST')  # This makes it an invitation

        event = icalendar.Event()
        
        # Required unique identifier for the event
        event.add('uid', str(uuid.uuid4()))
        
        # Basic event information
        event.add('summary', translation.title)
        event.add('description', translation.description)
        
        # Start and end times
        if translation.start_date:
            event.add('dtstart', translation.start_date.replace(tzinfo=pytz.UTC))
            
            # Calculate end time based on duration or default to 1 hour
            if translation.duration_minutes:
                end_time = translation.start_date + timedelta(minutes=translation.duration_minutes)
            else:
                end_time = translation.start_date + timedelta(hours=1)
            
            event.add('dtend', end_time.replace(tzinfo=pytz.UTC))
        
        # Add location based on translation type
        if translation.translation_type == 'LIVE_ON_SITE':
            event.add('location', translation.address)
        elif translation.translation_type == 'REMOTE_MEETING':
            event.add('location', translation.meeting_link)
            # Add online meeting details
            event.add('x-alt-desc;fmttype=text/html', 
                     f'Meeting Link: {translation.meeting_link}')
        
        # Add reminders
        alarm = icalendar.Alarm()
        alarm.add('action', 'DISPLAY')
        alarm.add('description', 'Reminder')
        alarm.add('trigger', timedelta(minutes=-30))  # 30 minutes before
        event.add_component(alarm)
        
        # Add the event to the calendar
        cal.add_component(event)
        
        return cal

    @staticmethod
    def send_calendar_invitation(translation, recipients=None):
        """Send calendar invitation for a translation session"""
        if recipients is None:
            recipients = [translation.translator.email]
            if translation.client:
                recipients.append(translation.client.email)

        # Create the calendar event
        cal = CalendarService.create_calendar_event(translation)

        # Create email with calendar attachment
        subject = f'Calendar Invitation: {translation.title}'
        
        # Different email body based on translation type
        if translation.translation_type == 'LIVE_ON_SITE':
            body = f"""
            You have been invited to an on-site interpretation session.
            
            Location: {translation.address}
            Date: {translation.start_date.strftime('%B %d, %Y')}
            Time: {translation.start_date.strftime('%I:%M %p')}
            
            Please arrive 15 minutes early.
            """
        elif translation.translation_type == 'REMOTE_MEETING':
            body = f"""
            You have been invited to a remote interpretation session.
            
            Meeting Link: {translation.meeting_link}
            Date: {translation.start_date.strftime('%B %d, %Y')}
            Time: {translation.start_date.strftime('%I:%M %p')}
            
            Please test your connection 10 minutes before the session.
            """
        elif translation.translation_type == 'REMOTE_PHONE':
            body = f"""
            You have been invited to a phone interpretation session.
            
            Phone Number: {translation.phone_number}
            Date: {translation.start_date.strftime('%B %d, %Y')}
            Time: {translation.start_date.strftime('%I:%M %p')}
            
            Please ensure you have good phone reception.
            """
        else:
            body = f"""
            Calendar invitation for translation project: {translation.title}
            Date: {translation.start_date.strftime('%B %d, %Y')}
            Time: {translation.start_date.strftime('%I:%M %p')}
            """

        email = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=translation.client.email,
            to=recipients
        )

        # Attach the calendar event
        email.attach('invitation.ics', 
                    cal.to_ical(), 
                    'text/calendar; method=REQUEST; charset=UTF-8')

        return email.send()

    @staticmethod
    def update_calendar_event(translation):
        """Send calendar update for a modified session"""
        cal = CalendarService.create_calendar_event(translation)
        cal.add('method', 'UPDATE')  # This makes it an update

        email = EmailMultiAlternatives(
            subject=f'Updated Calendar Event: {translation.title}',
            body=f'The details for {translation.title} have been updated.',
            from_email=translation.client.email,
            to=[translation.translator.email]
        )

        email.attach('event_update.ics', 
                    cal.to_ical(), 
                    'text/calendar; method=UPDATE; charset=UTF-8')

        return email.send()

    @staticmethod
    def cancel_calendar_event(translation):
        """Send calendar cancellation"""
        cal = CalendarService.create_calendar_event(translation)
        cal.add('method', 'CANCEL')  # This makes it a cancellation

        email = EmailMultiAlternatives(
            subject=f'Cancelled: {translation.title}',
            body=f'The session {translation.title} has been cancelled.',
            from_email=translation.client.email,
            to=[translation.translator.email]
        )

        email.attach('event_cancellation.ics', 
                    cal.to_ical(), 
                    'text/calendar; method=CANCEL; charset=UTF-8')