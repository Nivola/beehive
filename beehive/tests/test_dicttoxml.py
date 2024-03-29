from dict2xml import dict2xml
from dicttoxml import dicttoxml

s = {
    "accounts": [
        {
            "__meta__": {
                "objid": "502edae4ab//e0735b8bea//d64cd2b0a6",
                "type": "service",
                "definition": "Organization.Division.Account",
                "uri": "/v1.0/account/caa57820-dc93-4d80-9311-35a6b6659afd",
            },
            "id": 1979,
            "uuid": "caa57820-dc93-4d80-9311-35a6b6659afd",
            "name": "test_monitoring_02",
            "desc": "",
            "active": True,
            "date": {
                "creation": "2022-10-19T12:59:11Z",
                "modified": "2022-10-19T12:59:26Z",
                "expiry": "",
            },
            "version": "1.0",
            "division_id": "afdc2364-ccdb-4ec4-aaf6-967be49cfce1",
            "status": "ACTIVE",
            "contact": None,
            "note": None,
            "email": None,
            "email_support": None,
            "email_support_link": None,
            "managed": True,
            "services": {"base": 33, "core": 2},
            "acronym": "",
            "division_name": "Datacenter",
        },
        {
            "__meta__": {
                "objid": "502edae4ab//e0735b8bea//75a10b0ad2",
                "type": "service",
                "definition": "Organization.Division.Account",
                "uri": "/v1.0/account/00f256c1-dd50-4d0b-9e34-f580dc937c8c",
            },
            "id": 1976,
            "uuid": "00f256c1-dd50-4d0b-9e34-f580dc937c8c",
            "name": "STAGE_account-private2",
            "desc": "STAGE_account-private2",
            "active": True,
            "date": {
                "creation": "2022-10-18T17:18:17Z",
                "modified": "2022-10-18T17:18:33Z",
                "expiry": "",
            },
            "version": "1.0",
            "division_id": "afdc2364-ccdb-4ec4-aaf6-967be49cfce1",
            "status": "ACTIVE",
            "contact": "",
            "note": "",
            "email": "account.01@mail.it",
            "email_support": "support@mail.it",
            "email_support_link": None,
            "managed": True,
            "services": {"base": 17, "core": 6},
            "acronym": "test2",
            "division_name": "Datacenter",
        },
        {
            "__meta__": {
                "objid": "502edae4ab//e0735b8bea//40be854bdc",
                "type": "service",
                "definition": "Organization.Division.Account",
                "uri": "/v1.0/account/b2f8211d-ee63-4428-b7f3-bcd5a3dae3c6",
            },
            "id": 1973,
            "uuid": "b2f8211d-ee63-4428-b7f3-bcd5a3dae3c6",
            "name": "test_monitoring",
            "desc": "",
            "active": True,
            "date": {
                "creation": "2022-10-18T14:50:01Z",
                "modified": "2022-10-18T14:50:18Z",
                "expiry": "",
            },
            "version": "1.0",
            "division_id": "afdc2364-ccdb-4ec4-aaf6-967be49cfce1",
            "status": "ACTIVE",
            "contact": None,
            "note": None,
            "email": None,
            "email_support": None,
            "email_support_link": None,
            "managed": True,
            "services": {"base": 35, "core": 2},
            "acronym": "",
            "division_name": "Datacenter",
        },
        {
            "__meta__": {
                "objid": "99b510d0b4//4baeb7fcc5//66c8f42374",
                "type": "service",
                "definition": "Organization.Division.Account",
                "uri": "/v1.0/account/53233b08-7d32-43b2-a52c-88bcb3add1e8",
            },
            "id": 1950,
            "uuid": "53233b08-7d32-43b2-a52c-88bcb3add1e8",
            "name": "test",
            "desc": "yesy",
            "active": True,
            "date": {
                "creation": "2022-10-05T12:44:11Z",
                "modified": "2022-11-10T15:04:45Z",
                "expiry": "",
            },
            "version": "1.0",
            "division_id": "451358a3-1719-4fc0-9af5-53529a80cf14",
            "status": "ACTIVE",
            "contact": "test",
            "note": "test",
            "email": "test@gmail.com",
            "email_support": "testsupp@gmail.com",
            "email_support_link": None,
            "managed": True,
            "services": {"core": 0, "base": 0},
            "acronym": "test",
            "division_name": "AFC",
        },
        {
            "__meta__": {
                "objid": "91a6e13a35//78ade9e8c9//227a144e5d",
                "type": "service",
                "definition": "Organization.Division.Account",
                "uri": "/v1.0/account/a02872a9-98c3-47c6-812f-eda8c4ee3bc4",
            },
            "id": 1921,
            "uuid": "a02872a9-98c3-47c6-812f-eda8c4ee3bc4",
            "name": "SISTEMA",
            "desc": "",
            "active": True,
            "date": {
                "creation": "2022-09-19T12:09:32Z",
                "modified": "2022-09-19T12:09:39Z",
                "expiry": "",
            },
            "version": "1.0",
            "division_id": "b647bf09-0550-4c19-a408-4b5cdb7ba392",
            "status": "ACTIVE",
            "contact": None,
            "note": None,
            "email": None,
            "email_support": None,
            "email_support_link": None,
            "managed": True,
            "services": {"base": 21, "core": 4},
            "acronym": "sistema",
            "division_name": "ASLCN1",
        },
        {
            "__meta__": {
                "objid": "502edae4ab//cfcc6a6bdd//b75927557b",
                "type": "service",
                "definition": "Organization.Division.Account",
                "uri": "/v1.0/account/6b7c2308-6878-492d-a5ae-dc5616777643",
            },
            "id": 1919,
            "uuid": "6b7c2308-6878-492d-a5ae-dc5616777643",
            "name": "shib4cifa",
            "desc": "",
            "active": True,
            "date": {
                "creation": "2022-09-14T08:10:13Z",
                "modified": "2022-09-14T08:10:18Z",
                "expiry": "",
            },
            "version": "1.0",
            "division_id": "7c20ad09-b5b6-4247-83e0-624f165172e9",
            "status": "ACTIVE",
            "contact": None,
            "note": None,
            "email": None,
            "email_support": None,
            "email_support_link": None,
            "managed": True,
            "services": {"base": 42, "core": 3},
            "acronym": "shib4cifa",
            "division_name": "Comunicazione-e-Accesso",
        },
        {
            "__meta__": {
                "objid": "502edae4ab//cfcc6a6bdd//e7f7756457",
                "type": "service",
                "definition": "Organization.Division.Account",
                "uri": "/v1.0/account/98b754d0-5bd4-453e-be73-3afab294c0b5",
            },
            "id": 1918,
            "uuid": "98b754d0-5bd4-453e-be73-3afab294c0b5",
            "name": "shib4cifa-preprod",
            "desc": "shib4cifa-preprod",
            "active": True,
            "date": {
                "creation": "2022-09-09T12:22:12Z",
                "modified": "2022-09-09T12:22:19Z",
                "expiry": "",
            },
            "version": "1.0",
            "division_id": "7c20ad09-b5b6-4247-83e0-624f165172e9",
            "status": "ACTIVE",
            "contact": "David Manfrin",
            "note": None,
            "email": "david.manfrin@csi.it",
            "email_support": "david.manfrin@csi.it",
            "email_support_link": None,
            "managed": True,
            "services": {"base": 47, "core": 5},
            "acronym": "shib4cifa",
            "division_name": "Comunicazione-e-Accesso",
        },
        {
            "__meta__": {
                "objid": "502edae4ab//3c11f44f52//d740e7829e",
                "type": "service",
                "definition": "Organization.Division.Account",
                "uri": "/v1.0/account/30fc231d-814c-4bcc-abba-1dbd8be15b4b",
            },
            "id": 1916,
            "uuid": "30fc231d-814c-4bcc-abba-1dbd8be15b4b",
            "name": "atlas-preprod",
            "desc": "ATLAS Preprod",
            "active": True,
            "date": {
                "creation": "2022-09-05T15:14:57Z",
                "modified": "2022-09-12T10:34:49Z",
                "expiry": "",
            },
            "version": "1.0",
            "division_id": "a01c9391-f45c-4217-910d-b20298f564af",
            "status": "ACTIVE",
            "contact": "Marenchino Chiara - Eugenio Vota",
            "note": None,
            "email": None,
            "email_support": None,
            "email_support_link": None,
            "managed": True,
            "services": {"base": 40, "core": 3},
            "acronym": "atlas",
            "division_name": "Flussi-documentali-e-Dematerializzazione",
        },
        {
            "__meta__": {
                "objid": "502edae4ab//6d9ab6709b//31cbcae07f",
                "type": "service",
                "definition": "Organization.Division.Account",
                "uri": "/v1.0/account/a2ab4cbf-2203-46f0-9f22-500ba71fd23c",
            },
            "id": 1915,
            "uuid": "a2ab4cbf-2203-46f0-9f22-500ba71fd23c",
            "name": "aivc-preprod",
            "desc": "AIVC Preprod - progetto di investimento interno",
            "active": True,
            "date": {
                "creation": "2022-08-24T09:16:31Z",
                "modified": "2022-09-15T14:27:31Z",
                "expiry": "",
            },
            "version": "1.0",
            "division_id": "cb269ea8-3a80-4783-be0c-62129db2c7f3",
            "status": "ACTIVE",
            "contact": "Andrea Cinardo",
            "note": None,
            "email": None,
            "email_support": None,
            "email_support_link": None,
            "managed": True,
            "services": {"base": 51, "core": 3},
            "acronym": "aivc",
            "division_name": "Attivita-produttive",
        },
        {
            "__meta__": {
                "objid": "502edae4ab//77cb9c43ad//0db45c86cd",
                "type": "service",
                "definition": "Organization.Division.Account",
                "uri": "/v1.0/account/3bde148c-573f-4d29-903b-e14c99c0d194",
            },
            "id": 1913,
            "uuid": "3bde148c-573f-4d29-903b-e14c99c0d194",
            "name": "risca",
            "desc": "risca",
            "active": True,
            "date": {
                "creation": "2022-08-18T09:16:28Z",
                "modified": "2022-08-22T15:23:45Z",
                "expiry": "",
            },
            "version": "1.0",
            "division_id": "cf1b52a4-fabb-450e-9e1e-87cda178e7cf",
            "status": "ACTIVE",
            "contact": "",
            "note": None,
            "email": None,
            "email_support": None,
            "email_support_link": None,
            "managed": True,
            "services": {"base": 47, "core": 3},
            "acronym": "risca",
            "division_name": "Ambiente-ed-Energia",
        },
        {
            "__meta__": {
                "objid": "502edae4ab//84c5979e1c//3c5eb08e87",
                "type": "service",
                "definition": "Organization.Division.Account",
                "uri": "/v1.0/account/500ddb7d-b3bf-4cbf-b09d-712c6c125c37",
            },
            "id": 1912,
            "uuid": "500ddb7d-b3bf-4cbf-b09d-712c6c125c37",
            "name": "sicradem",
            "desc": "",
            "active": True,
            "date": {
                "creation": "2022-08-09T17:52:21Z",
                "modified": "2022-08-22T15:31:06Z",
                "expiry": "",
            },
            "version": "1.0",
            "division_id": "2679b226-8907-410f-95cb-d18bbb1aad31",
            "status": "ACTIVE",
            "contact": None,
            "note": None,
            "email": None,
            "email_support": None,
            "email_support_link": None,
            "managed": True,
            "services": {"base": 60, "core": 3},
            "acronym": "sicradem",
            "division_name": "Demografia",
        },
        {
            "__meta__": {
                "objid": "502edae4ab//1e837f7239//f198c3880f",
                "type": "service",
                "definition": "Organization.Division.Account",
                "uri": "/v1.0/account/13704177-77e8-4d35-a0c6-2e41d1233491",
            },
            "id": 1909,
            "uuid": "13704177-77e8-4d35-a0c6-2e41d1233491",
            "name": "tsddr-preprod",
            "desc": "A11_FINAN_2_01_int.2.2 P1 TSDDR  F4 NIVO",
            "active": True,
            "date": {
                "creation": "2022-08-03T09:30:56Z",
                "modified": "2022-09-15T13:34:38Z",
                "expiry": "",
            },
            "version": "1.0",
            "division_id": "b8dc0eed-d4f9-4cb0-a03d-feb3adcfdb10",
            "status": "ACTIVE",
            "contact": "Giovanna Bertinetti",
            "note": None,
            "email": "giovanna.bertinetti@csi.it",
            "email_support": None,
            "email_support_link": None,
            "managed": True,
            "services": {"base": 45, "core": 3},
            "acronym": "tsddr",
            "division_name": "Catasto-e-Fiscalita",
        },
        {
            "__meta__": {
                "objid": "502edae4ab//a9a03b195c//923093aebd",
                "type": "service",
                "definition": "Organization.Division.Account",
                "uri": "/v1.0/account/56e4e4d0-c0dd-4a55-ac82-aeb64dde9bd8",
            },
            "id": 1906,
            "uuid": "56e4e4d0-c0dd-4a55-ac82-aeb64dde9bd8",
            "name": "benchmark-preprod",
            "desc": "benchmark-preprod",
            "active": True,
            "date": {
                "creation": "2022-07-28T09:22:58Z",
                "modified": "2022-09-08T16:26:18Z",
                "expiry": "",
            },
            "version": "1.0",
            "division_id": "b11d83b2-2392-4db2-b6b4-dce65c35c646",
            "status": "ACTIVE",
            "contact": "Fabrizio Corsanego",
            "note": None,
            "email": None,
            "email_support": None,
            "email_support_link": None,
            "managed": True,
            "services": {"base": 33, "core": 3},
            "acronym": "benchmark",
            "division_name": "Staging",
        },
        {
            "__meta__": {
                "objid": "502edae4ab//d8d2d1dda9//b7ca8462ab",
                "type": "service",
                "definition": "Organization.Division.Account",
                "uri": "/v1.0/account/14d6882e-17db-4251-b745-d2bd86b3e703",
            },
            "id": 1904,
            "uuid": "14d6882e-17db-4251-b745-d2bd86b3e703",
            "name": "digifert-preprod",
            "desc": "digifert-preprod",
            "active": True,
            "date": {
                "creation": "2022-07-26T10:13:58Z",
                "modified": "2022-07-26T10:14:02Z",
                "expiry": "",
            },
            "version": "1.0",
            "division_id": "753b57fe-64c3-4c0a-81b2-085007760ea4",
            "status": "ACTIVE",
            "contact": "",
            "note": None,
            "email": None,
            "email_support": None,
            "email_support_link": None,
            "managed": True,
            "services": {"base": 37, "core": 3},
            "acronym": "digifert",
            "division_name": "Agricoltura",
        },
        {
            "__meta__": {
                "objid": "502edae4ab//7b07a52245//f1d6d30a6e",
                "type": "service",
                "definition": "Organization.Division.Account",
                "uri": "/v1.0/account/4a2db452-9bb8-4806-b6a1-8ac44a68d5ba",
            },
            "id": 1901,
            "uuid": "4a2db452-9bb8-4806-b6a1-8ac44a68d5ba",
            "name": "screen",
            "desc": "screen",
            "active": True,
            "date": {
                "creation": "2022-07-25T11:40:41Z",
                "modified": "2022-08-22T15:35:18Z",
                "expiry": "",
            },
            "version": "1.0",
            "division_id": "eb6fd3f4-2a25-479b-834e-bad8d2de053c",
            "status": "ACTIVE",
            "contact": "",
            "note": None,
            "email": None,
            "email_support": None,
            "email_support_link": None,
            "managed": True,
            "services": {"core": 0, "base": 0},
            "acronym": "screen",
            "division_name": "Sanita-Regione",
        },
        {
            "__meta__": {
                "objid": "23f4fe4695//967c474b26//85f15a882b",
                "type": "service",
                "definition": "Organization.Division.Account",
                "uri": "/v1.0/account/de9ebcb5-5e8b-4db3-9d42-016b61857b2c",
            },
            "id": 1900,
            "uuid": "de9ebcb5-5e8b-4db3-9d42-016b61857b2c",
            "name": "whr",
            "desc": "",
            "active": True,
            "date": {
                "creation": "2022-07-21T09:31:23Z",
                "modified": "2022-09-01T14:47:47Z",
                "expiry": "",
            },
            "version": "1.0",
            "division_id": "33299c73-d66c-4b15-be78-a87fccb09155",
            "status": "ACTIVE",
            "contact": None,
            "note": None,
            "email": None,
            "email_support": None,
            "email_support_link": None,
            "managed": True,
            "services": {"base": 26, "core": 4},
            "acronym": "",
            "division_name": "AO-AL",
        },
        {
            "__meta__": {
                "objid": "f50b32bef0//178f87b94a//69493528d7",
                "type": "service",
                "definition": "Organization.Division.Account",
                "uri": "/v1.0/account/6421291a-8304-40e0-9471-ec6352f3d9c0",
            },
            "id": 1897,
            "uuid": "6421291a-8304-40e0-9471-ec6352f3d9c0",
            "name": "servizi-applicativi",
            "desc": "",
            "active": True,
            "date": {
                "creation": "2022-07-20T14:58:55Z",
                "modified": "2022-09-15T14:01:17Z",
                "expiry": "",
            },
            "version": "1.0",
            "division_id": "24169013-0c84-4f76-9799-9a6fae19299f",
            "status": "ACTIVE",
            "contact": None,
            "note": None,
            "email": None,
            "email_support": None,
            "email_support_link": None,
            "managed": True,
            "services": {"base": 46, "core": 4},
            "acronym": "",
            "division_name": "ComuneCollegno",
        },
        {
            "__meta__": {
                "objid": "502edae4ab//28a5f31241//dd6451ffd6",
                "type": "service",
                "definition": "Organization.Division.Account",
                "uri": "/v1.0/account/c7fb33f4-7135-4c23-9c19-69d283c6e51e",
            },
            "id": 1894,
            "uuid": "c7fb33f4-7135-4c23-9c19-69d283c6e51e",
            "name": "iss",
            "desc": "iss",
            "active": True,
            "date": {
                "creation": "2022-07-15T11:39:43Z",
                "modified": "2022-09-08T16:37:33Z",
                "expiry": "",
            },
            "version": "1.0",
            "division_id": "e0aefafd-edd1-4a9b-a95d-6329f1448bc2",
            "status": "ACTIVE",
            "contact": "Giuseppe Massimo Olivieri",
            "note": None,
            "email": "giuseppemassimo.olivieri@csi.it",
            "email_support": "giuseppemassimo.olivieri@csi.it",
            "email_support_link": None,
            "managed": True,
            "services": {"base": 32, "core": 4},
            "acronym": "iss",
            "division_name": "Trasporti",
        },
        {
            "__meta__": {
                "objid": "406b87d61d//7bbda94e0a//68c334d26e",
                "type": "service",
                "definition": "Organization.Division.Account",
                "uri": "/v1.0/account/e306539d-b0e8-425c-9cf1-d8c5e6b73cd9",
            },
            "id": 1893,
            "uuid": "e306539d-b0e8-425c-9cf1-d8c5e6b73cd9",
            "name": "aou-novara-SQLMANAGE",
            "desc": "",
            "active": True,
            "date": {
                "creation": "2022-07-13T12:38:23Z",
                "modified": "2022-07-25T11:57:20Z",
                "expiry": "",
            },
            "version": "1.0",
            "division_id": "5d742209-bdb2-40a0-bff4-f438050520ef",
            "status": "ACTIVE",
            "contact": None,
            "note": None,
            "email": None,
            "email_support": None,
            "email_support_link": None,
            "managed": True,
            "services": {"base": 21, "core": 4},
            "acronym": "aou-sqlman",
            "division_name": "AOU-Novara",
        },
        {
            "__meta__": {
                "objid": "502edae4ab//a9a03b195c//9e84f7617c",
                "type": "service",
                "definition": "Organization.Division.Account",
                "uri": "/v1.0/account/32c5be49-8403-4c30-a389-182876c05dd2",
            },
            "id": 1891,
            "uuid": "32c5be49-8403-4c30-a389-182876c05dd2",
            "name": "poc-cittafacile",
            "desc": "poc-cittafacile",
            "active": True,
            "date": {
                "creation": "2022-07-11T08:16:19Z",
                "modified": "2022-09-08T16:38:37Z",
                "expiry": "",
            },
            "version": "1.0",
            "division_id": "b11d83b2-2392-4db2-b6b4-dce65c35c646",
            "status": "ACTIVE",
            "contact": "",
            "note": None,
            "email": None,
            "email_support": None,
            "email_support_link": None,
            "managed": True,
            "services": {"base": 39, "core": 2},
            "acronym": "poccitfac",
            "division_name": "Staging",
        },
    ],
    "count": 20,
    "page": 0,
    "total": 690,
    "sort": {"field": "id", "order": "DESC"},
}
# print(s)

ss = {
    "code": 123,
    "message": "%s" % "msg",
    "description": "%s - %s" % ("exception", "msg"),
}

xml = dicttoxml(s, root=False, attr_type=False)
print(xml)
# xml = dict2xml(s)
# print(xml)
