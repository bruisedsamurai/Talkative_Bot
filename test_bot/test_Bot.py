from unittest import mock


def side_effect_text(user_id, message, notification_type='REGULAR', quick_replies=None):
    assert len(message) <= 640
    assert isinstance(message, str)
    assert isinstance(notification_type, str)
    assert notification_type in {"REGULAR", "SILENT_PUSH", "NO_PUSH"}
    if quick_replies is not None:
        assert len(quick_replies) < 11
        assert isinstance(quick_replies, list)


idx = '12123123132'


@mock.patch.object('Facebook.send.Send', 'send_text', side_effect_text)
def mock_send_text(mockery):
    mockery.method().assert_called_with(idx)


message_dict = {}
