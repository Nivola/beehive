from beecell.simple import id_gen

prova = []

for i in xrange(0, 20):
    prova.append({u'id': id_gen(), u'name': u'pippo-%s' % id_gen()})

prova = sorted(prova, key=lambda x: x['id'])

for i in prova:
    print i