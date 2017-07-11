'''
Created on Jul 10, 2017

@author: darkbk
'''
def get_needs(args):
    """"""
    # first item *.*.*.....
    act_need = [u'*' for i in args]
    needs = [u'//'.join(act_need)]
    pos = 0
    for arg in args:
        act_need[pos] = arg
        needs.append(u'//'.join(act_need))
        pos += 1

    return set(needs)

objid = u'456//555//333'

print get_needs(objid.split(u'//'))