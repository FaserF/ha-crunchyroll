from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CrunchyrollProfile:
    """Crunchyroll user profile."""

    account_id: str = ""
    profile_name: str = ""
    username: str = ""
    email: str = ""
    email_verified: bool = False
    maturity_rating: str = ""
    avatar: str = ""
    preferred_communication_language: str = ""
    preferred_content_subtitle_language: str = ""

    @classmethod
    def from_dict(
        cls, data: dict[str, Any], account_id: str = ""
    ) -> CrunchyrollProfile:
        return cls(
            account_id=account_id or data.get("account_id", ""),
            profile_name=data.get("profile_name", ""),
            username=data.get("username", ""),
            email=data.get("email", ""),
            email_verified=bool(
                data.get("crleg_email_verified") or data.get("email_verified", False)
            ),
            maturity_rating=data.get("maturity_rating", ""),
            avatar=data.get("avatar", ""),
            preferred_communication_language=data.get(
                "preferred_communication_language", ""
            ),
            preferred_content_subtitle_language=data.get(
                "preferred_content_subtitle_language", ""
            ),
        )


@dataclass
class CrunchyrollSubscription:
    """Crunchyroll subscription status."""

    is_premium: bool = False
    tier: str = "free"
    products: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CrunchyrollSubscription:
        items = data.get("items", [])
        if not items and isinstance(data, list):
            items = data
        prods = []
        is_prem = False
        for it in items:
            pid = it.get("product_id", it.get("id", ""))
            prods.append(pid)
            if "premium" in pid.lower() or "fan" in pid.lower():
                is_prem = True
        tier_name = prods[0] if prods else ("mega_fan" if is_prem else "free")
        return cls(is_premium=is_prem, tier=tier_name, products=prods)


@dataclass
class CrunchyrollItem:
    """A single anime series, episode, or movie."""

    id: str
    title: str
    description: str = ""
    type: str = "series"  # series, episode, movie
    image_url: str = ""
    series_id: str | None = None
    series_title: str | None = None
    episode_number: str | None = None
    season_number: int | None = None
    season_title: str | None = None
    last_playhead_secs: int = 0
    duration_ms: int = 0
    is_completed: bool = False
    date_played: str | None = None
    release_date: str | None = None

    @classmethod
    def from_panel_dict(cls, data: dict[str, Any]) -> CrunchyrollItem:
        panel = data.get("panel", data)
        id_ = data.get("id", panel.get("id", ""))
        type_ = data.get("type", panel.get("type", "series"))
        title = panel.get("title", "")
        desc = panel.get("description", "")

        # image parsing
        img_url = ""
        images = panel.get("images", {})
        if "poster_tall" in images:
            posters = images["poster_tall"]
            if posters and isinstance(posters, list):
                last_elem = posters[-1]
                if isinstance(last_elem, list) and last_elem:
                    img_url = last_elem[-1].get("source", "")
                elif isinstance(last_elem, dict):
                    img_url = last_elem.get("source", "")
        if not img_url and "thumbnail" in images:
            thumbs = images["thumbnail"]
            if thumbs and isinstance(thumbs, list):
                last_elem = thumbs[-1]
                if isinstance(last_elem, list) and last_elem:
                    img_url = last_elem[-1].get("source", "")
                elif isinstance(last_elem, dict):
                    img_url = last_elem.get("source", "")

        ep_meta = panel.get("episode_metadata", {})
        series_id = ep_meta.get("series_id") or data.get("parent_id")
        series_title = ep_meta.get("series_title")
        ep_num = ep_meta.get("episode_number") if ep_meta else None
        season_num = ep_meta.get("season_number") if ep_meta else None
        season_t = ep_meta.get("season_title") if ep_meta else None

        playhead = data.get("playhead", 0)
        duration = ep_meta.get("duration_ms") or data.get("duration_ms", 0)
        is_compl = bool(data.get("fully_watched", False))
        date_played = data.get("date_played")
        rel_date = (
            ep_meta.get("availability_starts")
            or ep_meta.get("episode_air_date")
            or ep_meta.get("upload_date")
            or data.get("last_public")
        )

        return cls(
            id=id_,
            title=title,
            description=desc,
            type=type_,
            image_url=img_url,
            series_id=series_id,
            series_title=series_title,
            episode_number=str(ep_num) if ep_num is not None else None,
            season_number=season_num,
            season_title=season_t,
            last_playhead_secs=playhead,
            duration_ms=duration,
            is_completed=is_compl,
            date_played=date_played,
            release_date=rel_date,
        )

    @property
    def display_title(self) -> str:
        if self.episode_number:
            prefix = f"{self.series_title} - " if self.series_title else ""
            return f"{prefix}{self.title} (Episode {self.episode_number})"
        return self.title

    @property
    def crunchyroll_url(self) -> str:
        target_id = self.series_id or self.id
        target_type = "series" if self.type == "series" or self.series_id else "watch"
        return f"https://www.crunchyroll.com/{target_type}/{target_id}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "display_title": self.display_title,
            "type": self.type,
            "series_id": self.series_id,
            "series_title": self.series_title,
            "episode_number": self.episode_number,
            "season_number": self.season_number,
            "season_title": self.season_title,
            "image_url": self.image_url,
            "description": self.description,
            "last_playhead_secs": self.last_playhead_secs,
            "duration_ms": self.duration_ms,
            "is_completed": self.is_completed,
            "date_played": self.date_played,
            "release_date": self.release_date,
            "url": self.crunchyroll_url,
        }


@dataclass
class AnimeProgress:
    """Consolidated anime series watch progress."""

    series_id: str
    series_title: str
    episode_id: str
    episode_title: str
    episode_number: str | None = None
    season_number: int | None = None
    season_title: str | None = None
    playhead_seconds: int = 0
    duration_ms: int = 0
    is_completed: bool = False
    date_played: str | None = None
    image_url: str = ""
    description: str = ""
    total_episodes_watched: int = 1

    @property
    def progress_percent(self) -> int:
        if self.duration_ms and self.duration_ms > 0:
            duration_s = self.duration_ms / 1000.0
            return min(100, max(0, int((self.playhead_seconds / duration_s) * 100)))
        return 100 if self.is_completed else 0

    @property
    def crunchyroll_url(self) -> str:
        return f"https://www.crunchyroll.com/series/{self.series_id}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "series_id": self.series_id,
            "series_title": self.series_title,
            "episode_id": self.episode_id,
            "episode_title": self.episode_title,
            "episode_number": self.episode_number,
            "season_number": self.season_number,
            "season_title": self.season_title,
            "playhead_seconds": self.playhead_seconds,
            "duration_ms": self.duration_ms,
            "progress_percent": self.progress_percent,
            "is_completed": self.is_completed,
            "date_played": self.date_played,
            "image_url": self.image_url,
            "description": self.description,
            "total_episodes_watched": self.total_episodes_watched,
            "url": f"https://www.crunchyroll.com/series/{self.series_id}",
        }


@dataclass
class CustomList:
    """A user custom anime list / crunchylist."""

    list_id: str
    title: str
    total: int = 0
    is_public: bool = False
    modified_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "list_id": self.list_id,
            "title": self.title,
            "total": self.total,
            "is_public": self.is_public,
            "modified_at": self.modified_at,
        }


@dataclass
class Category:
    """Crunchyroll anime category/genre."""

    id: str
    localization: str = ""

    @property
    def name(self) -> str:
        return self.localization or self.id.title()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
        }


@dataclass
class CrunchyrollData:
    """Consolidated data object for Coordinator."""

    profile: CrunchyrollProfile
    subscription: CrunchyrollSubscription
    watchlist: list[CrunchyrollItem] = field(default_factory=list)
    history: list[CrunchyrollItem] = field(default_factory=list)
    recommendations: list[CrunchyrollItem] = field(default_factory=list)
    completed_animes: list[AnimeProgress] = field(default_factory=list)
    in_progress_animes: list[AnimeProgress] = field(default_factory=list)
    new_animes: list[CrunchyrollItem] = field(default_factory=list)
    popular_animes: list[CrunchyrollItem] = field(default_factory=list)
    simulcasts: list[CrunchyrollItem] = field(default_factory=list)
    movies: list[CrunchyrollItem] = field(default_factory=list)
    custom_lists: list[CustomList] = field(default_factory=list)
    categories: list[Category] = field(default_factory=list)
    new_episodes: list[CrunchyrollItem] = field(default_factory=list)
    new_episodes_for_watched: list[CrunchyrollItem] = field(default_factory=list)
