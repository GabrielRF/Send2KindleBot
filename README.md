<img align="right" alt="Send2KindleBot Logo" width="30%" height="auto" src="https://github.com/GabrielRF/Send2KindleBot/blob/master/icon.png?raw=true">

# [Send2KindleBot](http://telegram.me/Send2Kindle)

[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/donate/?hosted_button_id=GFPPS8QRW3QE2)
[![Deploy](https://github.com/GabrielRF/Send2KindleBot/actions/workflows/deploy.yml/badge.svg)](https://github.com/GabrielRF/Send2KindleBot/actions/workflows/deploy.yml)

## About

This is a [Telegram](http://telegram.org) Bot that sends documents to Kindle devices. It runs on Python 3 and uses Postfix and SQLite3.

[Try it!](https://telegram.me/Send2KindleBot)

## Usage

In order to work, users must register on the bot two e-mails, Amazon's Account e-mail and Kindle's e-mail.

If you need help with your Kindle's e-mail, please, refer to: https://www.amazon.com/gp/sendtokindle/email

## Setup

First of all, install Postfix on your computer/server. Make sure port 25 is opened so the bot can send e-mails.

```
# apt-get install postfix
```

After initial setup, copy both files from the folder `postfix` to `/etc/postfix`.

```
# mv postfix/* /etc/postfix
```

##### This configuration will allow e-mails to be sent only from `localhost`. This is important to avoid spamming from your server.

Make sure to restart postfix and check if its running

```
# service postfix restart
# service postfix status
```

Clone/Download this repository. Install requirements.

```
# pip3 install -r requirements.txt
```

Use Pipenv. Install requirements.

```
# pip3 install pipenv
# pipenv install -r requirements.txt
```

Make sure `kindle.conf` is properly configured.

```
cp kindle.conf_sample kindle.conf
```

`TOKEN` = Bot's token given by the BotFather.

`logfile` = Log file with 24 hour rotation.

`data_base` = Database location.

`table` = Table's name.

# Run it

```
python3 pdftokindlebot.py
```

# Contribute

To contribute install the development dependencies.

```
# pip3 install -r requirements.txt
```

Or use Pipenv to install.

```
# pip3 install pipenv
# pipenv install -r requirements.txt
```

Before sending your pull request, make sure you ran the linter.

```
# make lint
```

And the auto format.

```
# make format
```

# Thanks

Bot icon made by Ariyasu. Thank you!

Contact: Discord `ariyasu#9690`
