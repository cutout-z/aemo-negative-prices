# VPS Data Monitoring

Production model:

- Hetzner VPS checks daily for updated monthly negative-price data and keeps only a bounded recent NEMOSIS raw cache.
- GitHub stores code and publishable `outputs/`.
- GitHub Pages deploys after the VPS pushes updated outputs.
- GitHub Actions remains available for manual verification, but should not be the primary scheduled data runner.

## Lane

| Lane | Timer | Pipeline args | Purpose |
| --- | --- | --- | --- |
| Negative price data monitor | `aemo-negative-prices.timer` | `--months-back 2` | Check daily for newly published or corrected DISPATCHPRICE archives, reprocess the recent complete-month overlap window, preserve settled history, and publish only when canonical summary data changes. |

Recommended layout:

```text
/opt/aemo-negative-prices      git checkout + virtualenv
/etc/aemo-negative-prices/env  service settings
```

Create `/etc/aemo-negative-prices/env` from `env.example`. The service user needs a repo-scoped deploy key that can push to `cutout-z/aemo-negative-prices`.

## Install Timer

```bash
sudo cp deploy/aemo-negative-prices.service /etc/systemd/system/
sudo cp deploy/aemo-negative-prices.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now aemo-negative-prices.timer
```

Run once manually:

```bash
sudo systemctl start aemo-negative-prices.service
journalctl -u aemo-negative-prices.service -f
```
