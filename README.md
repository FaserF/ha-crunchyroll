# Crunchyroll (for Home Assistant)

[![GitHub Release](https://img.shields.io/github/release/FaserF/ha-crunchyroll.svg?style=flat-square)](https://github.com/FaserF/ha-crunchyroll/releases)
[![Downloads (Current release)](https://img.shields.io/github/downloads/FaserF/ha-crunchyroll/latest/crunchyroll.zip?label=Downloads%20(Current%20release)&style=flat-square)](https://github.com/FaserF/ha-crunchyroll/releases)
[![License](https://img.shields.io/github/license/FaserF/ha-crunchyroll.svg?style=flat-square)](LICENSE)
[![hacs](https://img.shields.io/badge/HACS-custom-orange.svg?style=flat-square)](https://hacs.xyz)
[![Add to Home Assistant](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=crunchyroll)
[![CI Orchestrator](https://github.com/FaserF/ha-crunchyroll/actions/workflows/ci-orchestrator.yml/badge.svg)](https://github.com/FaserF/ha-crunchyroll/actions/workflows/ci-orchestrator.yml)

A clean, production-ready Home Assistant custom integration for **Crunchyroll**. Seamlessly monitor your personal anime watchlist, continue watching series, completed shows, watch history, premium subscription status, and recommendations directly inside your Smart Home dashboard and automations.

## 🧭 Quick Links

| | | | |
| :--- | :--- | :--- | :--- |
| [✨ Features](#-features) | [❤️ Support](#️-support-this-project) | [📦 Installation](#-installation) | [⚙️ Configuration](#️-configuration) |
| [📊 Entities & Attributes](#-entities--attributes) | [🛠️ Options](#️-options-flow) | [🧱 Services](#-services) | [📖 Automations](#-automation-examples) |
| [🛡️ Security](#-security--privacy) | [❓ FAQ](#-troubleshooting--faq) | [🧑‍💻 Development](#-development) | [📄 License](#-license) |

### Why use this integration?
Unlike fragile web scraping solutions or browser automation scripts, this integration connects natively to Crunchyroll's official OAuth2 and mobile REST APIs. It communicates over secure HTTPS, handles automatic token refreshes, accurately calculates playback percentages, aggregates completed versus in-progress series, and provides full service endpoints to manage watchlists and browse the catalog directly from Home Assistant.

---

## ✨ Features

- **🔐 Native OAuth2 Authentication**:
  - Secure credential authentication with automatic refresh token rotation.
  - Device session registration matching official mobile clients.
  - Automatic re-authentication handling without requiring restarts.
- **📺 Comprehensive Sensor Suite**:
  - **Account Sensor** (`sensor.crunchyroll_<user>_account`):
    - State indicates subscription tier (`free`, `fan`, `mega_fan`).
    - Attributes: Username, profile name, account ID, email, verification state, maturity rating, avatar URL, content locale, last watched item, top recommendations, custom lists overview, and genres.
  - **Watchlist Sensor** (`sensor.crunchyroll_<user>_watchlist`):
    - State represents total count of bookmarked anime in watchlist.
    - Attributes: Full list of items with series ID, title, description, high-resolution poster images, and direct Crunchyroll web URLs.
  - **In-Progress Animes Sensor** (`sensor.crunchyroll_<user>_in_progress_animes`):
    - Direct integration with Crunchyroll's native *Continue Watching* engine (`/content/v2/discover/{account_id}/history`).
    - Exact playback progress tracking: playhead position in seconds, total episode duration, and calculated progress percent (0–100%).
    - Attributes: Latest active series, episode title, season number, episode number, thumbnail, and cumulative count of episodes logged.
  - **Completed Animes Sensor** (`sensor.crunchyroll_<user>_completed_animes`):
    - Aggregated list of series watched through to completion (distinguished from active continue-watching queues).
    - Accurately tracks long-running anime across hundreds of logged episodes.
    - Attributes: Total completed count, latest finished title and episode, finish timestamp, and full series breakdown with episode counts.
  - **New Animes Sensor** (`sensor.crunchyroll_<user>_new_animes`):
    - Tracks recent releases and simulcast updates from Crunchyroll's catalog feed.
    - Attributes: Release date, title, episode metadata, artwork, and direct episode URLs.
  - **Popular Animes Sensor** (`sensor.crunchyroll_<user>_popular_animes`):
    - Displays trending and top-ranked series in your region.
  - **Custom Lists Sensor** (`sensor.crunchyroll_<user>_custom_lists`):
    - Tracks personal user-created Crunchylists with counts and list IDs.
  - **Premium Status Binary Sensor** (`binary_sensor.crunchyroll_<user>_premium`):
    - Dedicated binary sensor for fast automation triggers (`on` when active premium subscription exists).
- **⚡ Full Suite of Actionable Services**:
  - `crunchyroll.search`: Search anime series, movies, and episodes on demand.
  - `crunchyroll.add_to_watchlist`: Add any series or anime directly to your watchlist via ID.
  - `crunchyroll.remove_from_watchlist`: Remove items from your watchlist.
  - `crunchyroll.mark_as_watched`: Mark episodes or content items as completely watched.
  - `crunchyroll.get_watchlist`: Query watchlist items with custom limit.
  - `crunchyroll.get_history`: Query watch history with episode and playhead metadata.
  - `crunchyroll.get_popular`: Query currently trending/popular anime.
  - `crunchyroll.get_similar`: Find similar anime series based on a given series ID.
  - `crunchyroll.get_seasons`: Fetch all seasons for a series.
  - `crunchyroll.get_episodes`: Fetch all episodes in a season.
  - `crunchyroll.get_custom_list_items`: Fetch items in a specific custom Crunchylist.
- **🔔 Real-Time Automation Events**:
  - `crunchyroll_watchlist_updated`: Dispatched automatically when anime is added or modified in the user's watchlist.
- **🛡️ Privacy & Diagnostics**:
  - Built-in Home Assistant diagnostics with automated redaction of sensitive credentials, tokens, and email addresses.
- **🎨 Official Brand Assets**:
  - Bundled brand logos and icons formatted to Home Assistant specification standards for high-DPI displays.
- **🌐 Native Experience & Localization**:
  - Complete English (`en`) and German (`de`) translations for config flow, sensors, binary sensors, and service descriptions.

---

## ❤️ Support This Project

> I maintain this integration in my **free time alongside my regular job** — bug hunting, testing with live accounts, reverse-engineering official endpoints, and building new features.
>
> **This project is and will always remain 100% free.** There are no paywalls, hidden tiers, or telemetry.
>
> Donations are completely voluntary — every contribution helps me stay motivated and dedicate more time to open-source Home Assistant integrations! 💪

<div align="center">

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor%20on-GitHub-%23EA4AAA?style=for-the-badge&logo=github-sponsors&logoColor=white)](https://github.com/sponsors/FaserF)&nbsp;&nbsp;
[![PayPal](https://img.shields.io/badge/Donate%20via-PayPal-%2300457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/FaserF)

</div>

---

## 📦 Installation

### Option 1: HACS (Recommended)

This integration is fully compatible with [HACS](https://hacs.xyz/).

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?repository=FaserF/ha-crunchyroll&category=integration)

1. Open **HACS** in your Home Assistant instance.
2. Click the top-right menu (three dots) and select **Custom repositories**.
3. Add `FaserF/ha-crunchyroll` with category **Integration**.
4. Search for **Crunchyroll** and click **Download**.
5. Restart Home Assistant.

### Option 2: Manual Installation

1. Download the latest release asset `crunchyroll.zip` from the [Releases](https://github.com/FaserF/ha-crunchyroll/releases) page.
2. Extract the `crunchyroll` directory into `<homeassistant-config>/custom_components/`.
3. Verify the folder structure is:
   ```text
   config/custom_components/crunchyroll/__init__.py
   config/custom_components/crunchyroll/manifest.json
   ```
4. Restart Home Assistant.

---

## ⚙️ Configuration

Adding your Crunchyroll account is done entirely through the Home Assistant UI. **No YAML configuration is required.**

[![Add to Home Assistant](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=crunchyroll)

1. Navigate to **Settings > Devices & Services** in Home Assistant.
2. Click **Add Integration** and search for **Crunchyroll**.
3. Fill in your credentials:
   - **Email / Username**: Your Crunchyroll account login email.
   - **Password**: Your Crunchyroll account password.
   - **Locale** *(Optional)*: Content localization language (e.g. `en-US`, `de-DE`, `fr-FR`). Default: `en-US`.
   - **Preferred Audio Language** *(Optional)*: Desired dubbing track (e.g. `ja-JP`, `de-DE`, `en-US`). Default: `ja-JP`.
4. Click **Submit**. The integration validates your credentials against the OAuth2 endpoint and configures all entities immediately.

---

## 🛠️ Options Flow

After setup, click **Configure** on the integration page to customize settings at any time without re-authenticating:

| Option | Description | Default |
|:---|:---|:---:|
| **Scan Interval (seconds)** | How frequently to poll profile, watch history, and recommendations. | `300` (5 min) |
| **Locale** | Content localization language code for titles and descriptions (`en-US`, `de-DE`, etc.). | `en-US` |
| **Preferred Audio Language** | Preferred audio dub language filter for catalog and recommendations (`ja-JP`, `de-DE`, etc.). | `ja-JP` |

---

## 📊 Entities & Attributes

| Entity ID | Type | Default | State | Key Attributes |
|:---|:---:|:---:|:---|:---|
| `sensor.crunchyroll_<user>_account` | Sensor | **Enabled** | Subscription Tier (`free`, `fan`, `mega_fan`) | `account_id`, `profile_name`, `username`, `email`, `email_verified`, `is_premium`, `subscription_tier`, `products`, `maturity_rating`, `avatar`, `last_watched`, `recommendations`, `custom_lists`, `categories` |
| `sensor.crunchyroll_<user>_watchlist` | Sensor | **Enabled** | Watchlist Item Count (e.g. `16`) | `watchlist_count`, `latest_added_title`, `latest_added_id`, `latest_added_image`, `latest_added_url`, `items` (with full series & episode metadata) |
| `sensor.crunchyroll_<user>_in_progress_animes` | Sensor | **Enabled** | In-Progress Series Count (e.g. `53`) | `latest_series`, `latest_episode`, `latest_episode_number`, `latest_playhead_seconds`, `latest_progress_percent`, `latest_image`, `latest_url`, `in_progress_animes` |
| `sensor.crunchyroll_<user>_completed_animes` | Sensor | **Enabled** | Finished Series Count (e.g. `12`) | `latest_completed_series`, `latest_completed_episode`, `latest_completed_episode_number`, `latest_completed_date`, `latest_completed_url`, `completed_animes` (with `total_episodes_watched`) |
| `sensor.crunchyroll_<user>_new_episodes_for_watched` | Sensor | **Enabled** | New Episodes Count for Watched Shows | `latest_episode_title`, `latest_series_title`, `latest_episode_number`, `latest_release_date`, `latest_image_url`, `new_episodes_for_watched` |
| `sensor.crunchyroll_<user>_simulcasts` | Sensor | **Enabled** | Current Season Simulcasts Count | `latest_simulcast_title`, `latest_simulcast_id`, `latest_simulcast_image`, `latest_simulcast_url`, `simulcasts` |
| `calendar.crunchyroll_<user>_releases` | Calendar | **Enabled** | Calendar Entity | Real-time release schedules, episode titles, durations, stream URLs, and start/end times |
| `sensor.crunchyroll_<user>_new_animes` | Sensor | *Disabled* | New Catalog Releases Count | `latest_release_title`, `latest_release_id`, `latest_release_image`, `latest_release_url`, `new_animes` |
| `sensor.crunchyroll_<user>_popular_animes` | Sensor | *Disabled* | Trending Series Count | `top_popular_title`, `top_popular_id`, `top_popular_image`, `top_popular_url`, `popular_animes` |
| `sensor.crunchyroll_<user>_movies` | Sensor | *Disabled* | Anime Movies Catalog Count | `latest_movie_title`, `latest_movie_id`, `latest_movie_image`, `latest_movie_url`, `movies` |
| `sensor.crunchyroll_<user>_new_episodes` | Sensor | *Disabled* | All Newly Added Episodes Count | `latest_episode_title`, `latest_series_title`, `latest_episode_number`, `latest_release_date`, `latest_image_url`, `new_episodes` |
| `sensor.crunchyroll_<user>_custom_lists` | Sensor | *Disabled* | Custom Crunchylists Count | `custom_lists` (list of user lists with `list_id`, `title`, `total`, `is_public`, `modified_at`) |

### Attribute Details

#### `in_progress_animes`
Contains an array of objects for every anime currently in progress with exact playhead timestamps and percentage:
```json
{
  "series_id": "GY5P48XEY",
  "series_title": "Seirei Gensouki: Spirit Chronicles",
  "episode_id": "GZ7UV88P7",
  "episode_title": "Clash",
  "episode_number": "11",
  "season_number": 2,
  "season_title": "Season 2",
  "playhead_seconds": 350,
  "duration_ms": 1420000,
  "progress_percent": 24,
  "is_completed": false,
  "total_episodes_watched": 23,
  "url": "https://www.crunchyroll.com/series/GY5P48XEY"
}
```

#### `completed_animes`
Contains an array of series watched to completion:
```json
{
  "series_id": "GR751KNZY",
  "series_title": "Black Clover",
  "episode_id": "G60X19426",
  "episode_title": "The Faraway Future",
  "episode_number": "170",
  "is_completed": true,
  "total_episodes_watched": 160,
  "url": "https://www.crunchyroll.com/series/GR751KNZY"
}
```

---

## 🧱 Services

The integration provides a complete set of services for automations and dashboard actions. All query services return response data using Home Assistant's `SupportsResponse.ONLY` standard.

### `crunchyroll.search`
Search the Crunchyroll anime catalog.
```yaml
action: crunchyroll.search
data:
  query: "Attack on Titan"
  limit: 5
```

### `crunchyroll.add_to_watchlist`
Add a series or movie to your account's watchlist.
```yaml
action: crunchyroll.add_to_watchlist
data:
  content_id: "GY5P48XEY"
```

### `crunchyroll.remove_from_watchlist`
Remove an anime from your watchlist.
```yaml
action: crunchyroll.remove_from_watchlist
data:
  content_id: "GY5P48XEY"
```

### `crunchyroll.mark_as_watched`
Mark a specific episode or series as fully watched.
```yaml
action: crunchyroll.mark_as_watched
data:
  content_id: "G50UMKWDZ"
```

### `crunchyroll.get_watchlist`
Fetch current watchlist items with a configurable limit.
```yaml
action: crunchyroll.get_watchlist
data:
  limit: 25
```

### `crunchyroll.get_history`
Fetch recent watch history items with exact playhead timestamps.
```yaml
action: crunchyroll.get_history
data:
  limit: 20
```

### `crunchyroll.get_popular`
Fetch current trending and popular anime series.
```yaml
action: crunchyroll.get_popular
data:
  limit: 10
```

### `crunchyroll.get_similar`
Get recommendations and similar series for a specific anime ID.
```yaml
action: crunchyroll.get_similar
data:
  series_id: "GR751KNZY"
  limit: 5
```

### `crunchyroll.get_seasons`
Fetch season structure for any anime series.
```yaml
action: crunchyroll.get_seasons
data:
  series_id: "GR751KNZY"
```

### `crunchyroll.get_episodes`
Fetch all episodes belonging to a specific season ID.
```yaml
action: crunchyroll.get_episodes
data:
  season_id: "GY9PXGP46"
```

### `crunchyroll.get_custom_list_items`
Retrieve all content items inside a user custom Crunchylist.
```yaml
action: crunchyroll.get_custom_list_items
data:
  list_id: "3d3e8b0a-4a25-4b45-9854-cf2487e4125b"
```

### `crunchyroll.get_simulcasts`
Fetch current seasonal simulcast releases.
```yaml
action: crunchyroll.get_simulcasts
data:
  limit: 20
```

### `crunchyroll.get_movies`
Browse anime movie listings in the catalog.
```yaml
action: crunchyroll.get_movies
data:
  limit: 20
```

### `crunchyroll.get_up_next`
Query the next up episode for any series ID.
```yaml
action: crunchyroll.get_up_next
data:
  series_id: "GR751KNZY"
```

### `crunchyroll.get_series_details`
Retrieve comprehensive metadata (episode count, season count, maturity, and artwork) for any series ID.
```yaml
action: crunchyroll.get_series_details
data:
  series_id: "GR751KNZY"
```

### `crunchyroll.update_playhead`
Update the playback progress position in seconds (resume time) for a specific episode.
```yaml
action: crunchyroll.update_playhead
data:
  content_id: "G9DU9EG8N"
  playhead_seconds: 420
```

---

## 📖 Automation Examples

<details>
<summary><strong>🔔 Notification on New Watchlist Additions</strong></summary>

Trigger instantly when a new show is added to your Crunchyroll watchlist (via Home Assistant or the official app).

```yaml
alias: "Crunchyroll: Watchlist Updated Notification"
trigger:
  - platform: event
    event_type: crunchyroll_watchlist_updated
    event_data:
      action: added
action:
  - action: notify.notify
    data:
      title: "🍿 New Anime in Watchlist"
      message: "{{ trigger.event.data.title }} was added to your Crunchyroll watchlist!"
      data:
        image: "{{ trigger.event.data.image_url }}"
```
</details>

<details>
<summary><strong>✨ Notification on New Episode of Watched / Watchlist Anime</strong></summary>

Receive an immediate push notification as soon as Crunchyroll releases a brand new episode for any series you are watching or have in your watchlist.

```yaml
alias: "Crunchyroll: New Episode Available Notification"
trigger:
  - platform: event
    event_type: crunchyroll_new_episode_available
action:
  - action: notify.notify
    data:
      title: "🎉 New Episode: {{ trigger.event.data.series_title }}"
      message: "Episode {{ trigger.event.data.episode_number }} ({{ trigger.event.data.episode_title }}) is now available on Crunchyroll!"
      data:
        url: "{{ trigger.event.data.url }}"
        image: "{{ trigger.event.data.image_url }}"
```
</details>

<details>
<summary><strong>🎬 Home Cinema Automation: In-Progress Anime Playback</strong></summary>

Automatically set cinema ambient lighting when an anime episode is actively in progress.

```yaml
alias: "Cinema: Anime Night Lighting"
trigger:
  - platform: state
    entity_id: sensor.crunchyroll_user_in_progress_animes
action:
  - choose:
      - conditions:
          - condition: template
            value_template: "{{ trigger.to_state.state | int > 0 }}"
        sequence:
          - action: light.turn_on
            target:
              entity_id: light.living_room_ambient
            data:
              brightness_pct: 25
              rgb_color: [255, 120, 0]
```
</details>

<details>
<summary><strong>🎉 Celebration Announcement on Anime Completion</strong></summary>

Receive a smart speaker notification when a full anime series has been completed.

```yaml
alias: "Crunchyroll: Completed Series Celebration"
trigger:
  - platform: state
    entity_id: sensor.crunchyroll_user_completed_animes
action:
  - condition: template
    value_template: "{{ trigger.to_state.state | int > trigger.from_state.state | int }}"
  - action: tts.speak
    target:
      entity_id: tts.google_en_com
    data:
      media_player_entity_id: media_player.living_room_speaker
      message: >-
        Congratulations! You just finished watching
        {{ state_attr('sensor.crunchyroll_user_completed_animes', 'latest_completed_series') }}!
```
</details>

<details>
<summary><strong>⚠️ Premium Membership Expiration Alert</strong></summary>

Get alerted when your premium membership changes or lapses.

```yaml
alias: "Crunchyroll: Premium Status Alert"
trigger:
  - platform: state
    entity_id: binary_sensor.crunchyroll_user_premium
    from: "on"
    to: "off"
action:
  - action: notify.notify
    data:
      title: "⚠️ Crunchyroll Premium Inactive"
      message: "Your Crunchyroll account is no longer reported as Premium. Check your billing."
```
</details>

<details>
<summary><strong>➕ Quick Dashboard Button: Add Series to Watchlist</strong></summary>

Bind a dashboard button to instantly add a popular anime directly into your queue.

```yaml
alias: "Dashboard: Quick Add Anime"
trigger:
  - platform: state
    entity_id: input_button.quick_add_anime
action:
  - action: crunchyroll.add_to_watchlist
    data:
      content_id: "GY5P48XEY"
```
</details>

---

## 🛡️ Security & Privacy

This integration was engineered with strict security principles:
- **No Web Scraping**: Communicates exclusively via TLS-encrypted REST and OAuth2 endpoints.
- **Credential Safety**: User passwords are exchanged directly for secure bearer tokens and are never transmitted elsewhere.
- **Automatic Diagnostics Redaction**: Home Assistant diagnostics automatically mask sensitive fields including `email`, `account_id`, `access_token`, and `refresh_token`.
- **Zero Third-Party Relays**: All traffic flows directly between your Home Assistant instance and `api.crunchyroll.com`.

---

## ❓ Troubleshooting & FAQ

### Why are my in-progress anime counts different from total history?
Crunchyroll distinguishes between **Continue Watching** (anime episodes you are currently watching or whose next episode is ready) and **Watch History** (an audit trail of every played episode).
- `sensor.crunchyroll_<user>_in_progress_animes` represents your active continue-watching queue with accurate progress percentages.
- `sensor.crunchyroll_<user>_completed_animes` captures series whose logged episodes have been watched to the end without remaining in the active queue.

### Does this integration require a Premium subscription?
**No.** Both free and premium Crunchyroll accounts are supported. If you have a free account, `sensor.crunchyroll_<user>_account` will show state `free`, and the `binary_sensor.crunchyroll_<user>_premium` will indicate `off`. All watchlist and history sensors work regardless of tier.

### How often is data refreshed?
By default, the integration polls Crunchyroll every **300 seconds (5 minutes)**. You can freely adjust this in the integration's **Options Flow** (e.g. 60 seconds or 600 seconds) to match your preferences.

### What happens if my login credentials change?
If your password changes or an authentication token becomes invalid, Home Assistant will prompt you with an automatic re-authentication flow in **Settings > Devices & Services** without losing your sensor entity history.

---

## 🧑‍💻 Development

This project adheres to the highest code quality and testing standards:
- **Code Linter**: `ruff check .`
- **Code Formatter**: `ruff format .`
- **Type Checker**: `mypy custom_components/`
- **Unit Testing**: `pytest` with 100% mocked API coverage

### Local Setup

```bash
git clone https://github.com/FaserF/ha-crunchyroll.git
cd ha-crunchyroll
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
make install
```

### Run Quality Checks

```bash
make check
```

Or run commands individually:
```bash
python -m ruff check . --fix
python -m ruff format .
python -m mypy custom_components/
python -m pytest
```

---

## 💖 Credits & Acknowledgements

- **Main Author**: [FaserF](https://github.com/FaserF)
- **Architecture Inspiration**: [ha-openwrt](https://github.com/FaserF/ha-openwrt) for coordinator structure, automated CI/CD workflows, and testing patterns.
- **Crunchyroll**: All anime metadata, cover art, and trademarks are property of [Crunchyroll, LLC](https://www.crunchyroll.com).

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
