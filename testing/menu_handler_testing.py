import json
import pytest

from src.handlers.admin.menu_handler import button_handler
from src import constants
from src.texts import _


from unittest.mock import patch

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from telegram.constants import ParseMode

from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_update(mocker):
    # Mock the callback_query
    callback_query = AsyncMock()
    callback_query.data = json.dumps({"action": constants.Actions.start_select_chat})
    callback_query.message.chat_id = 12345
    callback_query.message.message_id = 67890
    callback_query.from_user = AsyncMock()
    callback_query.from_user.id = 111

    message_mock = AsyncMock()
    message_mock.reply_text = AsyncMock()

    update = AsyncMock()
    update.callback_query = callback_query
    update.message = message_mock
    return update


@pytest.fixture
def mock_context(mocker):
    context = AsyncMock()
    context.bot.edit_message_text = AsyncMock()
    return context


@pytest.fixture(autouse=True)
def mock_create_async_engine():
    with patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=MagicMock()):
        yield


@pytest.fixture(autouse=True)
def mock_model_module():
    with patch("src.model.Chat", autospec=True), patch(
        "src.model.User", autospec=True
    ), patch("src.model.session_scope", autospec=True) as mock_session_scope, patch(
        "src.model.engine", autospec=True
    ), patch(
        "src.model.AsyncSessionLocal", autospec=True
    ), patch(
        "src.model.orm_to_dict", side_effect=lambda x: x._asdict()
    ):

        async def session_context():
            mock_session = AsyncMock()
            mock_session.commit = AsyncMock()
            mock_session.rollback = AsyncMock()
            mock_session.close = AsyncMock()
            yield mock_session

        mock_session_scope.side_effect = session_context

        yield  # This yields control back to the test function


@pytest.mark.asyncio
async def test_button_handler_no_chats(mock_update, mock_context, mocker):
    with patch("src.handlers.admin.menu_handler.get_chats_list", return_value=[]):
        await button_handler(mock_update, mock_context)

    # Assert that the expected message was sent
    mock_update.message.reply_text.assert_awaited_once_with(
        _("msg__no_chats_available")
    )


@pytest.mark.asyncio
async def test_button_handler_basic_start(mock_update, mock_context, mocker):
    # Mock the 'get_chats_list' to return a non-empty list
    mock_chats = [
        {"title": "Chat 1", "id": 1},
        {"title": "Chat 2", "id": 2},
    ]

    with patch(
        "src.handlers.admin.menu_handler.get_chats_list",
        AsyncMock(return_value=mock_chats),
    ):
        await button_handler(mock_update, mock_context)

    mock_context.bot.edit_message_text.assert_awaited_once_with(
        _("msg__start_command"),
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Chat 1",
                        callback_data=json.dumps(
                            {"chat_id": 1, "action": constants.Actions.select_chat}
                        ),
                    )
                ],
                [
                    InlineKeyboardButton(
                        "Chat 2",
                        callback_data=json.dumps(
                            {"chat_id": 2, "action": constants.Actions.select_chat}
                        ),
                    )
                ],
            ]
        ),
        chat_id=mock_update.callback_query.message.chat_id,
        message_id=mock_update.callback_query.message.message_id,
    )


@pytest.mark.asyncio
async def test_select_chat_action(mock_update, mock_context, mocker):
    # Set the data for the select_chat action
    action = constants.Actions.select_chat
    selected_chat_id = 1
    chat_name = "Test Chat"

    # Mock the data being received from the callback_query
    mock_update.callback_query.data = json.dumps(
        {"action": action, "chat_id": selected_chat_id}
    )
    chat_mock = AsyncMock()
    chat_mock.title = chat_name
    mocker.patch("handlers.admin.menu_handler.get_chat_name", return_value=chat_mock)

    expected_keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text=_("btn__intro"),
                    callback_data=json.dumps(
                        {
                            "chat_id": selected_chat_id,
                            "action": constants.Actions.set_intro_settings,
                        }
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text=_("btn__kicks"),
                    callback_data=json.dumps(
                        {
                            "chat_id": selected_chat_id,
                            "action": constants.Actions.set_kick_bans_settings,
                        }
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text=_("btn__back_to_chats"),
                    callback_data=json.dumps(
                        {
                            "chat_id": selected_chat_id,
                            "action": constants.Actions.back_to_chats,
                        }
                    ),
                )
            ],
        ]
    )

    await button_handler(mock_update, mock_context)
    actual_call = mock_context.bot.edit_message_text.call_args[
        1
    ]  # This gets the kwargs of the last call
    assert actual_call["reply_markup"] == expected_keyboard


@pytest.mark.asyncio
async def test_set_kick_bans_settings(mock_update, mock_context, mocker):
    action = constants.Actions.set_kick_bans_settings
    selected_chat_id = 1
    mock_update.callback_query.data = json.dumps(
        {"action": action, "chat_id": selected_chat_id}
    )
    await button_handler(mock_update, mock_context)

    expected_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=_("btn__current_settings"),
                    callback_data=json.dumps(
                        {
                            "chat_id": selected_chat_id,
                            "action": constants.Actions.get_current_kick_settings,
                        }
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text=_("btn__change_kick_timeout"),
                    callback_data=json.dumps(
                        {
                            "chat_id": selected_chat_id,
                            "action": constants.Actions.set_kick_timeout,
                        }
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text=_("btn__change_kick_message"),
                    callback_data=json.dumps(
                        {
                            "chat_id": selected_chat_id,
                            "action": constants.Actions.set_on_kick_message,
                        }
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text=_("btn__back"),
                    callback_data=json.dumps(
                        {
                            "chat_id": selected_chat_id,
                            "action": constants.Actions.select_chat,
                        }
                    ),
                )
            ],
        ]
    )

    mock_context.bot.edit_message_reply_markup.assert_awaited_once_with(
        reply_markup=expected_keyboard,
        chat_id=mock_update.callback_query.message.chat_id,
        message_id=mock_update.callback_query.message.message_id,
    )


@pytest.mark.asyncio
async def test_back_to_chats(mock_update, mock_context, mocker):
    mock_chats = [
        {"title": "Chat 1", "id": 1},
        {"title": "Chat 2", "id": 2},
    ]

    with patch(
        "src.handlers.admin.menu_handler.get_chats_list",
        AsyncMock(return_value=mock_chats),
    ):
        await button_handler(mock_update, mock_context)
    mock_context.bot.edit_message_text.assert_awaited_once_with(
        _("msg__start_command"),
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Chat 1",
                        callback_data=json.dumps(
                            {"chat_id": 1, "action": constants.Actions.select_chat}
                        ),
                    )
                ],
                [
                    InlineKeyboardButton(
                        "Chat 2",
                        callback_data=json.dumps(
                            {"chat_id": 2, "action": constants.Actions.select_chat}
                        ),
                    )
                ],
            ]
        ),
        chat_id=mock_update.callback_query.message.chat_id,
        message_id=mock_update.callback_query.message.message_id,
    )


@pytest.mark.asyncio
async def test_set_on_new_chat_member_message_response(
    mock_update, mock_context, mocker
):
    action = constants.Actions.set_on_new_chat_member_message_response
    selected_chat_id = 1
    mock_update.callback_query.data = json.dumps(
        {"action": action, "chat_id": selected_chat_id}
    )

    await button_handler(mock_update, mock_context)

    mock_context.bot.edit_message_text.assert_awaited_once_with(
        text=_("msg__set_new_welcome_message"),
        chat_id=mock_update.callback_query.message.chat_id,
        message_id=mock_update.callback_query.message.message_id,
        parse_mode=ParseMode.MARKDOWN,
    )


@pytest.mark.asyncio
async def test_set_kick_timeout(mock_update, mock_context, mocker):
    action = constants.Actions.set_kick_timeout
    selected_chat_id = 1
    mock_update.callback_query.data = json.dumps(
        {"action": action, "chat_id": selected_chat_id}
    )

    await button_handler(mock_update, mock_context)

    mock_context.bot.edit_message_text.assert_awaited_once_with(
        text=_("msg__set_new_kick_timout"),
        chat_id=mock_update.callback_query.message.chat_id,
        message_id=mock_update.callback_query.message.message_id,
    )


@pytest.mark.asyncio
async def test_set_on_known_new_chat_member_message_response(
    mock_update, mock_context, mocker
):
    action = constants.Actions.set_on_known_new_chat_member_message_response
    selected_chat_id = 1
    mock_update.callback_query.data = json.dumps(
        {"action": action, "chat_id": selected_chat_id}
    )

    await button_handler(mock_update, mock_context)

    mock_context.bot.edit_message_text.assert_awaited_once_with(
        text=_("msg__set_new_rewelcome_message"),
        chat_id=mock_update.callback_query.message.chat_id,
        message_id=mock_update.callback_query.message.message_id,
        parse_mode=ParseMode.MARKDOWN,
    )


@pytest.mark.asyncio
async def test_set_new_notify_message(mock_update, mock_context, mocker):
    action = constants.Actions.set_notify_message
    selected_chat_id = 1
    mock_update.callback_query.data = json.dumps(
        {"action": action, "chat_id": selected_chat_id}
    )

    await button_handler(mock_update, mock_context)

    mock_context.bot.edit_message_text.assert_awaited_once_with(
        text=_("msg__set_new_notify_message"),
        chat_id=mock_update.callback_query.message.chat_id,
        message_id=mock_update.callback_query.message.message_id,
        parse_mode=ParseMode.MARKDOWN,
    )


@pytest.mark.asyncio
async def test_set_on_new_chat_member_message_response(
    mock_update, mock_context, mocker
):
    action = constants.Actions.set_on_new_chat_member_message_response
    selected_chat_id = 1
    mock_update.callback_query.data = json.dumps(
        {"action": action, "chat_id": selected_chat_id}
    )

    await button_handler(mock_update, mock_context)

    mock_context.bot.edit_message_text.assert_awaited_once_with(
        text=_("msg__set_new_welcome_message"),
        chat_id=mock_update.callback_query.message.chat_id,
        message_id=mock_update.callback_query.message.message_id,
        parse_mode=ParseMode.MARKDOWN,
    )


@pytest.mark.asyncio
async def test_set_on_successful_introducion_response(
    mock_update, mock_context, mocker
):
    action = constants.Actions.set_on_successful_introducion_response
    selected_chat_id = 1
    mock_update.callback_query.data = json.dumps(
        {"action": action, "chat_id": selected_chat_id}
    )

    await button_handler(mock_update, mock_context)

    mock_context.bot.edit_message_text.assert_awaited_once_with(
        text=_("msg__set_new_sucess_message"),
        chat_id=mock_update.callback_query.message.chat_id,
        message_id=mock_update.callback_query.message.message_id,
        parse_mode=ParseMode.MARKDOWN,
    )


@pytest.mark.asyncio
async def test_set_whois_length(mock_update, mock_context, mocker):
    action = constants.Actions.set_whois_length
    selected_chat_id = 1
    mock_update.callback_query.data = json.dumps(
        {"action": action, "chat_id": selected_chat_id}
    )

    await button_handler(mock_update, mock_context)

    mock_context.bot.edit_message_text.assert_awaited_once_with(
        text=_("msg__set_new_whois_length"),
        chat_id=mock_update.callback_query.message.chat_id,
        message_id=mock_update.callback_query.message.message_id,
    )


@pytest.mark.asyncio
async def test_set_on_kick_message(mock_update, mock_context, mocker):
    action = constants.Actions.set_on_kick_message
    selected_chat_id = 1
    mock_update.callback_query.data = json.dumps(
        {"action": action, "chat_id": selected_chat_id}
    )

    await button_handler(mock_update, mock_context)

    mock_context.bot.edit_message_text.assert_awaited_once_with(
        text=_("msg__set_new_kick_message"),
        chat_id=mock_update.callback_query.message.chat_id,
        message_id=mock_update.callback_query.message.message_id,
        parse_mode=ParseMode.MARKDOWN,
    )


@pytest.mark.asyncio
async def test_set_notify_timeout(mock_update, mock_context, mocker):
    action = constants.Actions.set_notify_timeout
    selected_chat_id = 1
    mock_update.callback_query.data = json.dumps(
        {"action": action, "chat_id": selected_chat_id}
    )

    await button_handler(mock_update, mock_context)

    mock_context.bot.edit_message_text.assert_awaited_once_with(
        text=_("msg__set_new_notify_timeout"),
        chat_id=mock_update.callback_query.message.chat_id,
        message_id=mock_update.callback_query.message.message_id,
    )


@pytest.mark.asyncio
async def test_set_on_introduce_message_update(mock_update, mock_context, mocker):
    action = constants.Actions.set_on_introduce_message_update
    selected_chat_id = 1
    mock_update.callback_query.data = json.dumps(
        {"action": action, "chat_id": selected_chat_id}
    )

    await button_handler(mock_update, mock_context)

    mock_context.bot.edit_message_text.assert_awaited_once_with(
        text=_("msg__set_new_whois_message"),
        chat_id=mock_update.callback_query.message.chat_id,
        message_id=mock_update.callback_query.message.message_id,
        parse_mode=ParseMode.MARKDOWN,
    )
