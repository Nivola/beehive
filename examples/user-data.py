'''
Created on Mar 27, 2017

@author: darkbk
'''
user_data = '''#cloud-config
bootcmd:
  - [ ip, route, change, default, via, 10.102.184.1 ]
hostname: instance02
fqdn: instance02.tstsddc.csi.it
manage_etc_hosts: true
manage-resolv-conf: true
resolv_conf:
  nameservers: ['10.102.184.2', '10.102.184.2']
  searchdomains:
    - tstsddc.csi.it
  domain: tstsddc.csi.it
password: mypass
ssh_authorized_keys:
  - ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDpN36RMjBNpQ9lTvbdMjbkU6OyytX78RXKiVNMBU07vBx6REwGWgytg+8rG1pqFAuo6U3lR1q25dpPDQtK8Dad68MPHFydfv0WAYOG6Y02j/pQKJDGPhbeSYS0XF4F/z4UxY6cXB8UdzkUSKtIg93YCTkzbQY6+APOY/K9q1b2ZxTEEBDQgWenZw4McmSbaS+AYwmigSJb5sFMexJRKZCdXESgQcSmUkQFiXRQNJMlgPZBnIcbGlu5UA9G5owLM6LT11bPQPrROqmhcSGoQtYq83RGNX5Kgwe00pqeo/G+SUtcQRp5JtWIE9bLeaXRIhZuInrbP0rmHyCQhBeZDCPr1mw2YDZV9Fbb08/qwbq1UYuUzRXxXroX1F7/mztyXQt7o4AjXWpeyBccR0nkAyZcanOvvJJvoIwLoDqbsZaqCldQJCvtb1WNX9ukce5ToW1y80Rcf1GZrrXRTs2cAbubUkxYQaLQQApVnGIJelR9BlvR7xsmfQ5Y5wodeLfEgqw2hNzJEeKKHs5xnpcgG9iXVvW1Tr0Gf+UsY0UIogZ6BCstfR59lPAt1IRaYVCvgHsHm4hmr0yMvUwGHroztrja50XHp9h0z/EWAt56nioOJcOTloAIpAI05z4Z985bYWgFk8j/1LkEDKH9buq5mHLwN69O7JPN8XaDxBq9xqSP9w== sergio.tonani@csi.it
'''
import base64, json
c=base64.b64encode(user_data)
print c
#print json.loads(base64.b64decode(c))