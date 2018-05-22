import sh, sys

aggregated = ""

def ssh_interact(char, stdin):
    sys.stdout.write(char.encode())
    sys.stdout.flush()


#i=u'/home/io/workspace/git/beehive-mgmt/beehive_mgmt/inventory/.ssh/test/id_rsa',
#                   "tailf /var/log/beehive/beehive100/auth-01.log",
sh.ssh("root@tst-beehive-02.tstsddc.csi.it", "-i", "/home/io/workspace/git/beehive-mgmt/beehive_mgmt/inventory/.ssh/test/id_rsa",
       u'tailf /var/log/beehive/beehive100/auth-01.log', _out=ssh_interact, _out_bufsize=0)
# print(my_server("ifconfig"))
