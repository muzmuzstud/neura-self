# NeuraSelf - Mobile Guide (Termux)

Run NeuraSelf on your Android phone using Termux.

## 1. Installation

1. **Download Termux** from F-Droid (do NOT use the Play Store version, it is outdated).
    * [Download Link](https://f-droid.org/repo/com.termux_118.apk)

2. **Open Termux** and copy-paste these commands one by one:

    * **Update Termux:**

        ```bash
        pkg update -y && pkg upgrade -y
        ```

    * **Install Python & Git:**

        ```bash
        pkg install python git termux-api -y
        ```

    * **IMPORTANT:** You must also install the **Termux:API App** from F-Droid for notifications/vibration to work!
      * [Download Termux:API App](https://f-droid.org/en/packages/com.termux.api/)

        *(Type `y` and Enter if asked)*

    * **Download NeuraSelf:**

        ```bash
        git clone https://github.com/routo-loop/neura-self.git
        cd neura-self
        ```


    * **Install Requirements:**

        ```bash
        pip install -r requirements.txt
        ```

## 2. Starting the Bot

Every time you open Termux, just type:

```bash
cd neura-self
python neura.py
```

## 3. Mobile Configuration

To enable vibrations and notifications on your phone, edit `config/settings.json`.

**Recommended Settings:**

```json
"mobile": {
    "enabled": true,
    "toast": {
        "enabled": true,
        "position": "middle",
        "bg_color": "black",
        "text_color": "white"
    },
    "vibrate": {
        "enabled": true,
        "time": 0.5
    },
    "tts": {
        "enabled": false
    }
}
```

**What this does:**

* **Toast:** Shows a small popup text at the bottom of your screen for events.
* **Vibrate:** Vibrates your phone when a Captcha or Ban is detected (Critical!).
