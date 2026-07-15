import logging

logger = logging.getLogger(__name__)


class KeepWhatsAppMessages:
    def __init__(self, config, api):
        self._api = api
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
                    "keep_whatsapp: blocking redaction %s from %s in %s",
                    event.event_id, event.sender, event.room_id,
                )
                return False, None
        except Exception:
            logger.exception("keep_whatsapp: error while checking event, allowing")
        return True, None
