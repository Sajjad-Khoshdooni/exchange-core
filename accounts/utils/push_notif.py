from oauth2client.service_account import ServiceAccountCredentials

def _get_access_token():
    """Retrieve a valid access token that can be used to authorize requests.

  :return: Access token.
  """

    SCOPES = ['https://www.googleapis.com/auth/firebase.messaging']

    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        'glassy-ripsaw-271116-bbd810287776 .json', SCOPES)
    access_token_info = credentials.get_access_token()

    return access_token_info.access_token
import requests


def send_push_notif(token: str, title: str, message: str):

    resp = requests.post(
        url=' https://fcm.googleapis.com/v1/projects/glassy-ripsaw-271116/messages:send',
        headers={
            'Authorization': 'Bearer ' + _get_access_token(),
            'Content-Type': 'application/json; UTF-8',
        },
        json={
            "message": {
                "token": token,
                "notification": {
                    "body": message,
                    "title": title
                }
            }
        }

    )
    return resp
