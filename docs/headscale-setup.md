# 🔐 Headscale Setup für Sprachassistent-Netzwerk

Dieses Dokument beschreibt die Einrichtung von Headscale als selbstgehostete Alternative für ein sicheres Mesh-VPN zwischen den Nodes (Raspi 4, Raspi 400, Odroid, Server).

Um den Dienst automatisch zu starten, kopiere die bereitgestellte
`headscale.service` Datei aus dem Headscale Repository nach
`/etc/systemd/system/` und passe bei Bedarf den Pfad zum Binary an.
Danach `systemctl daemon-reload` ausführen und den Service aktivieren:

```bash
sudo cp Headscale/headscale.systemd.service /etc/systemd/system/headscale.service
sudo systemctl daemon-reload
sudo systemctl enable --now headscale.service
```
---

## 📦 Voraussetzungen

* Ubuntu 22.04+ oder Debian 11+
* Root-/Sudo-Zugriff auf den Server (Headscale Instanz)
* Zugang zu jedem Client (SSH)

---

## 🧠 Was ist Headscale?

Headscale ist ein Open-Source-Server für sichere Mesh-VPNs.
---

## 🖥 Installation (Server mit Headscale)

### Option A – DEB-Paket (empfohlen für Server)

```bash
HEADSCALE_VERSION="<z. B. 0.22.3>"
HEADSCALE_ARCH="amd64" # oder z. B. arm64

wget -O headscale.deb \
  "https://github.com/juanfont/headscale/releases/download/v${HEADSCALE_VERSION}/headscale_${HEADSCALE_VERSION}_linux_${HEADSCALE_ARCH}.deb"

sudo apt install ./headscale.deb
### Odroid ARM64 Installation

```bash
HEADSCALE_VERSION="0.26.1"
HEADSCALE_ARCH="arm64"
wget -O headscale.deb "https://github.com/juanfont/headscale/releases/download/v${HEADSCALE_VERSION}/headscale_${HEADSCALE_VERSION}_linux_${HEADSCALE_ARCH}.deb"
sudo apt install ./headscale.deb
```


### Option B – Snap-Paket (für Raspberry Pi)

```bash
sudo apt update
sudo apt install -y snapd
sudo reboot

# Nach Reboot:
sudo snap install snapd  # optional falls snap veraltet
sudo snap install headscale
```

---

## ⚙️ Konfiguration

```bash
sudo nano /etc/headscale/config.yaml
```

> Wichtige Felder: `server_url`, `listen_addr`, `private_key_path`, `db_type`, `db_path`, `unix_socket`

Dann:

```bash
sudo systemctl enable --now headscale
sudo systemctl status headscale
```

---

## 🛠 Verwaltung (Namespace & Key)

```bash
sudo headscale namespaces create voice
sudo headscale preauthkeys create --namespace voice --reusable --expiration 24h
```

---

## 🤖 Installation auf Clients (raspi4, odroid, raspi400)

# Using packages for Debian/Ubuntu (recommended)

It is recommended to use our DEB packages to install headscale on a Debian based system as those packages configure a
local user to run headscale, provide a default configuration and ship with a systemd service file. Supported
distributions are Ubuntu 22.04 or newer, Debian 11 or newer.

1.  Download the [latest headscale package](https://github.com/juanfont/headscale/releases/latest) for your platform (`.deb` for Ubuntu and Debian).

    ```shell
    HEADSCALE_VERSION="" # See above URL for latest version, e.g. "X.Y.Z" (NOTE: do not add the "v" prefix!)
    HEADSCALE_ARCH="" # Your system architecture, e.g. "amd64"
    wget --output-document=headscale.deb \
     "https://github.com/juanfont/headscale/releases/download/v${HEADSCALE_VERSION}/headscale_${HEADSCALE_VERSION}_linux_${HEADSCALE_ARCH}.deb"
    ```

1.  Install headscale:

    ```shell
    sudo apt install ./headscale.deb
    ```

1.  [Configure headscale by editing the configuration file](../../ref/configuration.md):

    ```shell
    sudo nano /etc/headscale/config.yaml
    ```

1.  Enable and start the headscale service:

    ```shell
    sudo systemctl enable --now headscale
    ```

1.  Verify that headscale is running as intended:

    ```shell
    sudo systemctl status headscale
    ```

## Using standalone binaries (advanced)

!!! warning "Advanced"

    This installation method is considered advanced as one needs to take care of the local user and the systemd
    service themselves. If possible, use the [DEB packages](#using-packages-for-debianubuntu-recommended) or a
    [community package](./community.md) instead.

This section describes the installation of headscale according to the [Requirements and
assumptions](../requirements.md#assumptions). Headscale is run by a dedicated local user and the service itself is
managed by systemd.

1.  Download the latest [`headscale` binary from GitHub's release page](https://github.com/juanfont/headscale/releases):

    ```shell
    sudo wget --output-document=/usr/local/bin/headscale \
    https://github.com/juanfont/headscale/releases/download/v<HEADSCALE VERSION>/headscale_<HEADSCALE VERSION>_linux_<ARCH>
    ```

1.  Make `headscale` executable:

    ```shell
    sudo chmod +x /usr/local/bin/headscale
    ```

1.  Add a dedicated local user to run headscale:

    ```shell
    sudo useradd \
     --create-home \
     --home-dir /var/lib/headscale/ \
     --system \
     --user-group \
     --shell /usr/sbin/nologin \
     headscale
    ```

1.  Download the example configuration for your chosen version and save it as: `/etc/headscale/config.yaml`. Adjust the
    configuration to suit your local environment. See [Configuration](../../ref/configuration.md) for details.

    ```shell
    sudo mkdir -p /etc/headscale
    sudo nano /etc/headscale/config.yaml
    ```

1.  Copy [headscale's systemd service file](https://github.com/juanfont/headscale/blob/main/packaging/systemd/headscale.service)
    to `/etc/systemd/system/headscale.service` and adjust it to suit your local setup. The following parameters likely need
    to be modified: `ExecStart`, `WorkingDirectory`, `ReadWritePaths`.

1.  In `/etc/headscale/config.yaml`, override the default `headscale` unix socket with a path that is writable by the
    `headscale` user or group:

    ```yaml title="config.yaml"
    unix_socket: /var/run/headscale/headscale.sock
    ```

1.  Reload systemd to load the new configuration file:

    ```shell
    systemctl daemon-reload
    ```

1.  Enable and start the new headscale service:

    ```shell
    systemctl enable --now headscale
    ```

1.  Verify that headscale is running as intended:

    ```shell
    systemctl status headscale
    ```

---

## 🗂 Geräte benennen (Hostname)

* Raspi 4: `raspi4`
* Raspi 400: `raspi400`
* Odroid: `odroid`

In `.env` eintragen:

```env
RASPI4_HOST=raspi4.headscale.lan
```

---

## 🔍 Verbindung prüfen

```bash
headscale nodes list
ping raspi400
```

---

## 📌 Tipps

* Aktiviere MagicDNS in Headscale (falls gewünscht)
* Verwende feste Hostnames + IPs im WebSocket-Server
* Authkeys sollten regelmäßig rotiert werden
* Snap-Installationen speichern Logs ggf. abweichend (→ `journalctl --unit snap.headscale.headscale.service`)

---

## 🔗 Referenzen

* [Headscale GitHub](https://github.com/juanfont/headscale)
* [Headscale Doku](https://headscale.net)
* [Snap Install Guide](https://snapcraft.io/install/headscale/raspbian)

