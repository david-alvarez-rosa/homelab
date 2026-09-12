import logging

logger = logging.getLogger(__name__)

DOUBLE_PUPPET = "fi.mau.double_puppet_source"
EDIT_KEYS = ("m.relates_to", "m.new_content", "com.beeper.dont_render_edited")
EDIT_PREFIX = "* "
EDITED_MARK = "✏️ "
DELETED_MARK = "🗑️ Deleted"
MARKABLE_TYPES = ("m.room.message", "m.sticker")


class KeepWhatsAppMessages:
    def __init__(self, config, api):
        self._api = api
        self._marked = set()
        api.register_third_party_rules_callbacks(
            check_event_allowed=self.check_event_allowed,
        )

    @staticmethod
    def parse_config(config):
        return config

    async def check_event_allowed(self, event, state_events):
        try:
            if event.type == "m.room.redaction" and event.sender.startswith("@whatsapp"):
                logger.info(
                    "keep_whatsapp: blocking redaction %s of %s from %s in %s",
                    event.event_id, event.redacts, event.sender, event.room_id,
                )
                self._api.run_as_background_process(
                    "keep_whatsapp_mark_deleted",
                    self._mark_deleted,
                    event.room_id, event.sender, event.redacts,
                )
                return False, None
            if event.type == "m.room.message":
                unrolled = await self._unroll_edit(event)
                if unrolled is not None:
                    return True, unrolled
        except Exception:
            logger.exception("keep_whatsapp: error while checking event, allowing")
        return True, None

    async def _mark_deleted(self, room_id, sender, target_id):
        try:
            if not isinstance(target_id, str) or target_id in self._marked:
                return
            target = await self._api._store.get_event(target_id, allow_none=True)
            if target is None or target.type not in MARKABLE_TYPES:
                return
            self._marked.add(target_id)
            await self._api.create_and_send_event_into_room({
                "type": "m.room.message",
                "room_id": room_id,
                "sender": sender,
                "content": {
                    "msgtype": "m.notice",
                    "body": DELETED_MARK,
                    "m.relates_to": {"m.in_reply_to": {"event_id": target_id}},
                },
            })
            logger.info("keep_whatsapp: marked %s as deleted in %s", target_id, room_id)
        except Exception:
            logger.exception("keep_whatsapp: failed to mark %s as deleted", target_id)

    async def _unroll_edit(self, event):
        relates_to = event.content.get("m.relates_to")
        if not isinstance(relates_to, dict):
            return None
        if relates_to.get("rel_type") != "m.replace":
            return None
        if not self._from_whatsapp(event):
            return None
        target_id = relates_to.get("event_id")
        if not isinstance(target_id, str) or not target_id:
            return None
        target = await self._api._store.get_event(target_id, allow_none=True)
        if target is None:
            return None
        if target.content.get("msgtype") == "m.notice":
            return None
        new_content = {k: v for k, v in event.content.items() if k not in EDIT_KEYS}
        for key in ("body", "formatted_body"):
            value = new_content.get(key)
            if isinstance(value, str) and value.startswith(EDIT_PREFIX):
                new_content[key] = EDITED_MARK + value[len(EDIT_PREFIX):]
        new_content["m.relates_to"] = {"m.in_reply_to": {"event_id": target_id}}
        new_event = event.get_dict()
        new_event["content"] = new_content
        logger.info(
            "keep_whatsapp: unrolled edit of %s from %s in %s",
            target_id, event.sender, event.room_id,
        )
        return new_event

    @staticmethod
    def _from_whatsapp(event):
        return (
            event.sender.startswith("@whatsapp")
            or event.content.get(DOUBLE_PUPPET) == "mautrix-whatsapp"
        )
