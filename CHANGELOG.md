# Changelog

## Version 1.5.0 (Jun  , 2019)

* Added ...
    * added methods expunge, pre_expunge e post_expunge to ApiObject
    * added methods base_stmp2 and run2 in PaginatedQueryGenerator
    * added logger elk for api and task
    * added microsecond to event stored in mysql db
* Fixed ...
    * modify max query window for event to 2 hours
* Integrated ...
    * introdotta signature Celery che registra il task su redis appena generato l'uuid dall'apply_async
    * added send of log item for the api class to elasticsearch if it is configured
* Various bugfixes

## Version 1.4.0 (May 24, 2019)

* Added ...
    * introdotta il campo provider nella classe common.model.authorization.User per indicare l'autentication provider
    * aggiunta la gestione del campo provider nelle api di auth.user
* Fixed ...
    * revisione del metodo user_request
    * modificata l'api di interrogazione dei domains in interrogazione dei providers
    * modificata la configurazione di un authentication provider ldap
    * aggiornamento firma metodo get_entity: inserimento params *args, **kvargs
    * Class GetAllTasksRequestSchema: corretto errore di validazione swagger, eliminato il parametro missing=None per il 
      fields ttype
    * modificato comportamento del metodo AbstractDbManager.add_perm_tag. Eliminata la rollback in caso di permtag già esistenti
* Integrated ...
* Various bugfixes

## Version 1.3.0 (February 27, 2019)

* Added ...
    * aggiunto runner per realizzare test unit concorrenti
* Fixed ...
    * aumenteta la dimensione del campo desc della tabella event a 500 caratteri
* Integrated ...
* Various bugfixes

## Version 1.2.0 (February 01, 2019)

* Added ...
    * **BeehiveApiClient** aggiunto metodo set_ssh_group_authorization
* Fixed ...
    * corretto bug nella classe PaginatedQueryGenerator che impediva il cambio del campo di group by
* Integrated ...
* Various bugfixes

## Version 1.1.0 (January 13, 2019)

* Added ...
    * aggiunti il riferimento dei jobs invocati nel task chiamanate
* Fixed ...
    * trace: cambiato il tracciato degli eventi. Viene stampato il nome del metodo tracciato
    * event: revisione della query di lista. Era troppo lenta. Limitata la query a un giorno.
    * auth: rivisto metodo per verificare che uno user abbia un certo ruolo
* Integrated ...
* Various bugfixes

## Version 1.0.0 (July 31, 2018)

First production preview release.

## Version 0.1.0 (April 18, 2016)

First private preview release.