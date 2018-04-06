# -*- coding:utf-8 -*-
import logging
import smtplib
import threading
import time
from Queue import Queue, Empty

LOGGER = logging.getLogger(__name__)


class Emailer(object):
    """
    An instance that sits in its own thread and sends emails when they
    are available in the queue.
    """
    def __init__(self, notification_config, password):
        self._from = notification_config["email_address"]
        self._recipients = notification_config["recipients"]
        self._username = notification_config["username"]
        self._password = password

        self._emailer_thread = None
        self._running = False
        self._queue = Queue()
        self._queue_lock = threading.Lock()

    def _send_email(self, summary, content):
        from_address = self._from
        to_address = self._recipients
        subject = "VPA Anomaly Detected: {}".format(summary)
        body = content

        # Prepare actual message
        message = """From: %s\nTo: %s\nSubject: %s\n\n%s
        """ % (from_address, ", ".join(to_address), subject, body)
        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.ehlo()
            server.starttls()
            server.login(self._username, self._password)
            server.sendmail(from_address, to_address, message)
            server.close()
            LOGGER.info('Successfully sent the mail to: %s', to_address)
        except Exception as exc:
            LOGGER.error("Failed to send mail. Exception: %r", exc)

    def start(self):
        self._running = True
        self._emailer_thread = threading.Thread(target=self._run)
        self._emailer_thread.start()

    def stop(self):
        if self._emailer_thread is not None:
            self._running = False
            self._emailer_thread.join()

    def _run(self):
        while self._running:
            try:
                with self._queue_lock:
                    new_email = self._queue.get_nowait()
                summary, content = new_email
                self._send_email(summary, content)
            except Empty:
                pass
            time.sleep(1)

    def add_email_to_queue(self, summary, content):
        LOGGER.info("Added email to queue: %s", summary)
        with self._queue_lock:
            self._queue.put((summary, content))
