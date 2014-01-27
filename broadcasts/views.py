import re
import json
from django.http import HttpResponse
from .models import BroadcastMessage


def decode_excluded(exclude_string):
    if exclude_string:
        excluded = map(int, exclude_string.split(","))
        return set(excluded)
    else:
        return set()


def encode_excluded(exclude_set):
    if exclude_set:
        excluded = ",".join(map(str, list(exclude_set)))
        return excluded
    else:
        return ""


def get_messages(request):
    """
    Get messages for the user
    """
    if request.user.is_authenticated():
        msgs = BroadcastMessage.objects.current().for_auth_users()
    else:
        msgs = BroadcastMessage.objects.current().for_unauth_users()

    # exclude by those seen
    excluded_session = decode_excluded(request.session.get("excluded_broadcasts", ""))
    excluded_cookie = decode_excluded(request.COOKIES.get("excluded_broadcasts", ""))
    excluded = excluded_session | excluded_cookie
    msgs = msgs.exclude(pk__in=list(excluded))

    # filter them by the HTTP_REFERER
    host = "https://" if request.is_secure() else "http://"
    host += request.get_host()
    path = request.META.get('HTTP_REFERER', '/').replace(host, "")
    valid_messages = [msg for msg in msgs if re.match(msg.url_target, path)]
    msg_list = []
    for msg in valid_messages:
        msg_list.append(msg.msg_info())
        if msg.show_frequency == BroadcastMessage.SHOW_ONCE:
            excluded_cookie.add(msg.pk)
        elif msg.show_frequency == BroadcastMessage.SHOW_ONCE_SESSION:
            excluded_session.add(msg.pk)
    request.session['excluded_broadcasts'] = encode_excluded(excluded_session)
    response = HttpResponse(json.dumps(msg_list),
                            content_type="application/json")
    response.set_cookie('excluded_broadcasts', encode_excluded(excluded_cookie))
    return response


def reset_messages(request):
    """
    reset the excluded messages
    """
    request.session['excluded_broadcasts'] = ""
    response = HttpResponse("[]",
                            content_type="application/json")
    response.set_cookie('excluded_broadcasts', "")
    return response