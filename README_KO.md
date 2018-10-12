# [Send2KindleBot](http://telegram.me/Send2Kindle)

페이팔로 기부하기 [![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=7Q29T7QE6A948)

![Send2KindleBot](https://github.com/GabrielRF/Send2KindleBot/blob/master/icon.jpg?raw=true)

## 정보

이 [텔레그램](https://telegram.org) 봇은 킨들(Kindle) 기기로 문서를 보냅니다. Python 3에서 작동하며, PostFix와 SQLite3을 사용합니다.

[지금 사용해 보세요!](http://telegram.me/Send2KindleBot)

## 사용법

이 봇이 작동하려면, 사용자는 봇에게 두개의 이메일을 제공해야 합니다. 이 두개의 이메일은 아마존 이메일 주소와 킨들(Kindle) 이메일 주소입니다.

킨들(Kindle) 이메일주소를 설정하는데 도움이 필요하시다면, [여기를](https://www.amazon.com/gp/sendtokindle/email) 참조하세요.

## 설치

먼저, 자신의 컴퓨터나 서버에 Postfix를 설치하세요. 봇이 이메일을 보낼 수 있도록 포트 25번이 열려있는지 확인하세요.

```
# apt-get install postfix
```

초기 설치후, `postfix`폴더에 있던 파일을 `etc/postfix`로 복사하세요.

```
# mv postfix/* /etc/postfix
```

**다음 구성은 이메일이 `localhost`에서만 보내지도록 합니다. 이것은 자신의 서버에 다량의 호출을 보내는 것을 막으므로 중요합니다.** 

Postfix를 재시작후, 이가 작동하는지 확인하세요.

```
# service postfix restart

# service postfix status
```

이 리포지토리를 복제/다운로드하세요. 필수사항을 다운로드하세요.

```
# pip3 install -r requirements.txt
```

Pipenv를 사용하여 필수사항을 다운로드하세요.

```
# pip3 install pipenv
# pipenv install -r requirements.txt
```

`kindle.conf`가 바르게 구성되었는지 확인하세요.

```
cp kindle.conf_sample kindle.conf
```

`TOKEN` = BotFather로 부터 주어진 봇의 고유 토큰

`logfile` = 24시간의 로그 파일

`data_base` = 데이터베이스 위치

`table` = 테이블의 이름

## 실행


```
python3 pdftokindlebot.py
```

