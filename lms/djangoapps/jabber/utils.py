"""
Various utilities for working with Jabber chat. Includes helper
functions to parse the settings, create and retrieve chat-specific
passwords for users, etc.
"""
import base64

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .models import JabberUser

# The default length of the Jabber passwords we create. We set a
# really long default since we're storing these passwords in
# plaintext (ejabberd implementation detail).
DEFAULT_PASSWORD_LENGTH = 256

def get_bosh_url():
    """
    Build a "Bidirectional-streams Over Synchronous HTTP" (BOSH) URL
    for connecting to a Jabber server. It has the following format:

        <protocol>://<host>:<port>/<path>

    The Candy.js widget connects to ejabberd at this endpoint.

    By default, the BOSH URL uses HTTP, not HTTPS. The port and the
    path are optional; only the host is required.
    """
    __validate_settings()

    protocol = "http"
    use_ssl = settings.JABBER.get("USE_SSL", False)
    if use_ssl:
        protocol = "https"

    host = settings.JABBER.get("HOST")
    bosh_url = "%s://%s" % (protocol, host)

    # The port is an optional setting
    port = settings.JABBER.get("PORT")
    if port is not None:
        # Convert port to a string in case it's specified as a number
        bosh_url += ":%s" % str(port)

    # Also optional is the "path", which could possibly use a better
    # name...help @jrbl?
    path = settings.JABBER.get("PATH")
    if path is not None:
        bosh_url += "/%s" % path

    return bosh_url


def get_password_for_user(username):
    """
    Retrieve the password for the user with the given username. If
    a password doesn't exist, then we'll create one by generating a
    random string.
    """
    try:
        jabber_user = JabberUser.objects.get(username=username)
    except JabberUser.DoesNotExist:
        password = __generate_random_string(DEFAULT_PASSWORD_LENGTH)
        jabber_user = JabberUser(username=username,
                                 password=password)
        jabber_user.save()

    return jabber_user.password


def get_room_name_for_course(course_id):
    """
    Build a Jabber chat room name given a course ID with format:

        <room>@<domain>

    The room name will just be the course name (parsed from the
    course_id), and the domain will be the Jabber host with the
    optional multi-user chat (MUC) subdomain.
    """
    __validate_settings()
    host = settings.JABBER.get("HOST")

    # The "multi-user chat" subdomain is a convention in Jabber to
    # keep chatroom traffic from blowing up your one-to-one traffic.
    # This is an optional setting.
    muc_subdomain = settings.JABBER.get("MUC_SUBDOMAIN")
    if muc_subdomain is not None:
        host = "%s.%s" % (muc_subdomain, host)

    # Rather than using the whole course ID, which is rather ugly for
    # display, we'll just grab the name portion.
    # TODO: is there a better way to just grab the name out?
    org, num, name = course_id.split('/')

    return "%s_class@%s" % (name, host)


def __generate_random_string(length):
    """
    Generate a Base64-encoded random string of the specified length,
    suitable for a password that can be stored in a database.
    """
    # Base64 encoding gives us 4 chars for every 3 bytes we give it,
    # so figure out how many random bytes we need to get a string of
    # just the right length
    num_bytes = length / 4 * 3
    with open("/dev/random", "rb") as random:
        return base64.b64encode(random.read(num_bytes))


def __validate_settings():
    """
    Ensure that the Jabber settings are properly configured. This
    is intended for internal use only to prevent code duplication.
    """
    if getattr(settings, "JABBER") is None:
        raise ImproperlyConfigured("Missing Jabber dict in settings")

    host = settings.JABBER.get("HOST")
    if host is None or host == "":
        raise ImproperlyConfigured("Missing Jabber HOST in settings")
