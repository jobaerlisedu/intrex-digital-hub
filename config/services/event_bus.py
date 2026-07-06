import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class EventBus:
    _subscribers = {}

    def subscribe(self, event_type, handler):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)
            logger.debug(f"Subscribed {handler.__name__} to {event_type}")

    def unsubscribe(self, event_type, handler):
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                h for h in self._subscribers[event_type] if h != handler
            ]

    def publish(self, event_type, data=None, source=None):
        if data is None:
            data = {}
        event = {
            'type': event_type,
            'data': data,
            'source': source,
            'timestamp': datetime.now().isoformat(),
        }
        logger.info(f"Event: {event_type} from {source}")
        for handler in self._subscribers.get(event_type, []):
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Handler {handler.__name__} failed on {event_type}: {e}")
        for wildcard_handler in self._subscribers.get('*', []):
            try:
                wildcard_handler(event)
            except Exception as e:
                logger.error(f"Wildcard handler {wildcard_handler.__name__} failed: {e}")


event_bus = EventBus()
