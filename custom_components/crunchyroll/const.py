from __future__ import annotations

from typing import Final

DOMAIN: Final = "crunchyroll"

CONF_EMAIL: Final = "email"
CONF_PASSWORD: Final = "password"
CONF_LOCALE: Final = "locale"
CONF_AUDIO_LOCALE: Final = "preferred_audio_language"
CONF_SCAN_INTERVAL: Final = "scan_interval"

DEFAULT_SCAN_INTERVAL: Final = 86400  # 24 hours
MIN_SCAN_INTERVAL: Final = 3600  # 1 hour
DEFAULT_LOCALE: Final = "en-US"
DEFAULT_AUDIO_LOCALE: Final = "ja-JP"

ATTR_ACCOUNT_ID: Final = "account_id"
ATTR_PROFILE_NAME: Final = "profile_name"
ATTR_EMAIL: Final = "email"
ATTR_EMAIL_VERIFIED: Final = "email_verified"
ATTR_IS_PREMIUM: Final = "is_premium"
ATTR_SUBSCRIPTION_TIER: Final = "subscription_tier"
ATTR_PRODUCTS: Final = "products"
ATTR_MATURITY_RATING: Final = "maturity_rating"
ATTR_WATCHLIST_COUNT: Final = "watchlist_count"
ATTR_WATCHLIST: Final = "watchlist"
ATTR_HISTORY_COUNT: Final = "history_count"
ATTR_LAST_WATCHED: Final = "last_watched"
ATTR_RECOMMENDATIONS: Final = "recommendations"
ATTR_ITEMS: Final = "items"
ATTR_COMPLETED_ANIMES: Final = "completed_animes"
ATTR_IN_PROGRESS_ANIMES: Final = "in_progress_animes"
ATTR_NEW_ANIMES: Final = "new_animes"
ATTR_POPULAR_ANIMES: Final = "popular_animes"
ATTR_SIMULCASTS: Final = "simulcasts"
ATTR_MOVIES: Final = "movies"
ATTR_CUSTOM_LISTS: Final = "custom_lists"
ATTR_CATEGORIES: Final = "categories"
ATTR_NEW_EPISODES: Final = "new_episodes"
ATTR_NEW_EPISODES_FOR_WATCHED: Final = "new_episodes_for_watched"

EVENT_CRUNCHYROLL_WATCHLIST_UPDATED: Final = "crunchyroll_watchlist_updated"
EVENT_CRUNCHYROLL_NEW_EPISODE_AVAILABLE: Final = "crunchyroll_new_episode_available"
