<div align="center">

# 🏠 HAAC Bridge

**Share exactly the devices you want with each person in your home. Nothing more.**

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=stacknoise&repository=haac-bridge&category=integration)

[![HACS](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://hacs.xyz)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.9.0%2B-18bcf2.svg)](https://www.home-assistant.io)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

</div>

HAAC Bridge is a small add-on (an *integration*) for Home Assistant. It works together with the **HAAC Android app** ([stacknoise/haac-android](https://github.com/stacknoise/haac-android)). With it, you decide **which lights, sockets, sensors and thermostats each family member sees and controls** in the app. The app never sees anything you did not share.

> The official Home Assistant app shows a user everything they can reach. HAAC only shows what **you** share with that person, device by device.

## ✨ What you get

| | |
| --- | --- |
| 🔒 **Share per person** | Pick for each Home Assistant user which devices the app may show. Everything else stays invisible. |
| 💡 **Control from the app** | Switch sockets and lights, read sensors, set thermostats. Door, window and motion sensors are shown too. |
| ⏰ **Schedules that run reliably** | Create timers in the app, for example "every weekday at 06:45 turn the light on", once or repeating, also at sunrise or sunset. They run inside Home Assistant, so they work with the phone off. |
| ⏸️ **Pause a device** | A person can deactivate a device in the app. It stays visible but cannot be switched, and its timers pause. |
| 📜 **You see what happened** | Every switching action shows up on the Home Assistant *Activity* page, for example "turned on via HAAC app (Pixel 8)". |
| 🛡️ **Safe by default** | A person who is not set up sees nothing. Only switches, sensors, binary sensors and thermostats can ever be shared. |

## 🚀 Install in 3 steps

1. **Click the button** at the top of this page. It opens HAAC Bridge in the HACS of your Home Assistant. (Or open HACS yourself and search for **HAAC Bridge**. It is part of the official HACS list, so you do not need to add a custom repository.)
2. Click **Download**, then **restart Home Assistant**.
3. Go to **Settings → Devices & services → Add integration**, search for **HAAC Bridge** and add it.

You need Home Assistant **2026.9.0** or newer.

## 👤 Share devices with a person

1. Open **Settings → Devices & services → HAAC Bridge** and click **Configure**.
2. **Add a Home Assistant user**, for example your partner or your child.
3. Choose what this person may see: whole types of devices (for example all thermostats), single devices, or patterns such as `sensor.*_humidity`. You can also exclude devices. An exclusion always wins.
4. Done. Changes apply immediately, with no restart.

Then install the HAAC app on the phone, sign in with that person's Home Assistant account and the shared devices appear.

> 💡 **Tip:** Create a separate, **non-admin** Home Assistant user for every person and never sign in to the app with an admin account (see [Good to know](#-good-to-know)).

You can also set everything up in `configuration.yaml`, which is handy for larger setups:

```yaml
haac_bridge:
  users:
    - username: anna
      filter:
        include_domains:
          - climate
        include_entities:
          - switch.garage_socket
        include_entity_globs:
          - sensor.*_humidity
        exclude_entities:
          - climate.server_room
```

All options are explained on the [configuration page](docs/configuration.md), including names for devices, import and export, and logging.

## ❓ Good to know

- **Why does a person see nothing?** Check that the user is added under *Configure* and has at least one *include* rule. People who are not set up see nothing by design.
- **Which devices can be shared?** Switches, sensors, binary sensors (doors, windows, motion) and thermostats.
- **Is this a real permission system?** No. HAAC Bridge limits what the *app* shows and controls. Home Assistant itself has no per-device permissions, so anyone holding a person's login can still use Home Assistant's normal interface. That is why every person should have their own non-admin user, and why you should not rely on it to separate people who do not trust each other. Logins can be revoked per phone in the user's profile in Home Assistant.
- **Where do I see problems?** Under *Settings → Repairs*. Errors also carry a short code such as `HAB-CFG-003`. The [error list](docs/error-codes.md) explains them.
- **Where are the logs?** In the normal Home Assistant log. By default only problems are logged. Switch the level to `info` under *Configure → Logging* to record every action.

## 📚 More

- [All features in detail](docs/features.md)
- [Configuration in detail](docs/configuration.md) (UI, YAML, names, logging)
- [Error codes](docs/error-codes.md)
- [WebSocket API](docs/websocket-api.md) for developers
- [Developer guide](docs/development.md)
- Questions or problems? [Open an issue](https://github.com/stacknoise/haac-bridge/issues).

## 🧑‍💻 Development

Read the [developer guide](docs/development.md), [CLAUDE.md](CLAUDE.md) and [docs/concept.md](docs/concept.md) (chapters 10, 11, 13 and 18) first.

```bash
pip install -r requirements_test.txt -r requirements_lint.txt   # Python 3.14
pytest
ruff check . && ruff format --check .
bandit -c pyproject.toml -r custom_components scripts
python scripts/code_index.py          # regenerate docs/code-index.md and docs/error-codes.md
```

## 📄 License

[Apache License 2.0](LICENSE). See [NOTICE](NOTICE).

*This project is not affiliated with or endorsed by Home Assistant, the Open Home Foundation or Nabu Casa.*
